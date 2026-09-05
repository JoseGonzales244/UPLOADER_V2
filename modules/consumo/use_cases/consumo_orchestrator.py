"""
Consumo Orchestrator — Fachada Pipeline (Nivel 4 Refactorización)

Punto de entrada público para el proceso de Consumo. Construye el ConsumoPipelineContext
y delega en los Casos de Uso atómicos (phases/) en orden.
La firma de run_orchestration_flow es 100% compatible hacia atrás con backend/main.py.
"""
import os
import sys
import json
import datetime
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.system.logging_config import setup_logging

logger = setup_logging("modules.consumo.consumo_orchestrator", log_prefix="consumo")


@dataclass
class ConsumoPipelineContext:
    """Contexto tipado compartido entre todas las fases del Pipeline de Consumo."""
    period_str: str
    insight_user: str
    insight_password: str
    td_user: str
    td_password: str
    host: str = "IBKTD"
    logmech: str = "TD2"
    input_dir: str = ""
    clear_consent: bool = False
    progress_callback: Optional[Callable] = None
    insumos_config: dict = field(default_factory=dict)
    # Conexión Teradata compartida entre Fases 1-4
    td_con: object = None


def run_orchestration_flow(
    insight_user: str,
    insight_password: str,
    td_user: str,
    td_password: str,
    period_str: str,
    clear_consent: bool = False,
    progress_callback: Optional[Callable] = None,
    run_phase1: bool = True,
    run_phase2: bool = True,
    run_phase3: bool = True,
    run_phase4: bool = True,
    run_phase5: bool = True,
    start_from_script: Optional[str] = None
):
    """
    Ejecuta el flujo de orquestación de Consumo en 5 Fases.
    Firma 100% compatible con backend/main.py.
    """
    from modules.consumo.use_cases.phases import phase1_insight_ingest, phase2_cd40k
    from modules.consumo.use_cases.phases import phase3_desembolsos, phase4_sql_scripts, phase5_selection

    logger.info(f"=== INICIANDO PROCESO DE CONSUMO PARA EL PERÍODO {period_str} ===")
    log = progress_callback or (lambda msg, lvl="info": None)

    credenciales = load_credentials()
    host = credenciales.get("teradata_host", "IBKTD")
    logmech = credenciales.get("teradata_logmech", "TD2")

    # Cargar INSUMOS_CONFIG desde config.json
    config_path = os.path.join(os.getcwd(), "config", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    insumos_config = config.get("consumo_insumos_config", {})

    input_dir = os.path.join(os.getcwd(), "data", "input", "base_consumo")
    os.makedirs(input_dir, exist_ok=True)

    # Establecer conexión Teradata compartida
    con = None
    if run_phase1 or run_phase2 or run_phase3 or run_phase4:
        msg_conn = "⚡ Estableciendo conexión segura con Teradata..."
        logger.info(f"Connecting to Teradata (Host: {host}, User: {td_user})...")
        log(msg_conn, "info")
        try:
            con = connect_teradata(td_user, td_password, host=host, logmech=logmech)
            con.autocommit = True
        except Exception as err:
            logger.error(f"Error crítico al conectar con Teradata: {err}")
            raise RuntimeError(f"Error de conexión con Teradata: {err}")

    ctx = ConsumoPipelineContext(
        period_str=period_str,
        insight_user=insight_user,
        insight_password=insight_password,
        td_user=td_user,
        td_password=td_password,
        host=host,
        logmech=logmech,
        input_dir=input_dir,
        clear_consent=clear_consent,
        progress_callback=progress_callback,
        insumos_config=insumos_config,
        td_con=con
    )

    try:
        # --- BLOQUE 1: INGESTAS PREVIAS EN PARALELO (Fases 1, 2 y 3) ---
        ingest_phases = []
        if run_phase1:
            ingest_phases.append((phase1_insight_ingest.run_phase1, "Fase 1 (Insight)"))
        if run_phase2:
            ingest_phases.append((phase2_cd40k.run_phase2, "Fase 2 (CD40K)"))
        if run_phase3:
            ingest_phases.append((phase3_desembolsos.run_phase3, "Fase 3 (Desembolsos)"))

        if len(ingest_phases) > 1:
            log(f"⚡ Ejecutando {len(ingest_phases)} fases de ingesta en paralelo (Fan-Out)...", "info")

            def _execute_parallel_ingest(phase_fn, phase_name):
                worker_con = connect_teradata(td_user, td_password, host=host, logmech=logmech)
                worker_con.autocommit = True
                worker_ctx = replace(ctx, td_con=worker_con)
                try:
                    logger.info(f"Iniciando {phase_name} en worker paralelo...")
                    return phase_fn(worker_ctx)
                finally:
                    try:
                        worker_con.close()
                    except Exception:
                        pass

            with ThreadPoolExecutor(max_workers=len(ingest_phases)) as executor:
                futures = {executor.submit(_execute_parallel_ingest, fn, name): name for fn, name in ingest_phases}
                for fut in as_completed(futures):
                    pname = futures[fut]
                    fut.result()
                    logger.info(f"✅ {pname} finalizada exitosamente en paralelo.")
        elif len(ingest_phases) == 1:
            fn, name = ingest_phases[0]
            fn(ctx)

        # --- BLOQUE 2: PROCESAMIENTO SQL CONCURRENTE (Fases 4 y 5) ---
        sql_phases = []
        if run_phase4:
            sql_phases.append((phase4_sql_scripts.run_phase4, (ctx,), {"start_from_script": start_from_script}, "Fase 4 (SQL Consumo)"))
        if run_phase5:
            sql_phases.append((phase5_selection.run_phase5, (ctx,), {}, "Fase 5 (Consumo Select)"))

        if len(sql_phases) > 1:
            log("⚡ Ejecutando Fase 4 (SQL Consumo) y Fase 5 (Select) concurrentemente...", "info")
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {
                    executor.submit(fn, *args, **kwargs): name
                    for fn, args, kwargs, name in sql_phases
                }
                for fut in as_completed(futures):
                    pname = futures[fut]
                    fut.result()
                    logger.info(f"✅ {pname} finalizada exitosamente.")
        elif len(sql_phases) == 1:
            fn, args, kwargs, _ = sql_phases[0]
            fn(*args, **kwargs)

        msg_ok = "🎉 ¡Proceso de Consumo completado exitosamente!"
        logger.info(f"=== PROCESO DE CONSUMO COMPLETADO EXITOSAMENTE PARA EL PERÍODO {period_str} ===")
        log(msg_ok, "success")

        # Notificación de escritorio
        try:
            from infrastructure.system.notifier import notify_desktop
            notify_desktop(
                title="Plataforma Calidad - Consumo",
                message=f"¡Proceso completado exitosamente para el período {period_str}!",
                duration_sec=5
            )
        except Exception as err:
            logger.warning(f"No se pudo enviar la notificación de escritorio: {err}")

    finally:
        if con:
            try:
                con.close()
                logger.info("Conexión de Teradata cerrada limpiamente.")
            except Exception:
                pass
