"""
Quality Orchestrator — Fachada Pipeline (Nivel 4 Refactorización)

Punto de entrada público para el proceso de Calidad. Construye el QualityPipelineContext
y delega en los Casos de Uso atómicos (phases/) en orden.
La firma de run_quality_process_flow es 100% compatible hacia atrás con backend/main.py.
"""
import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, List

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from infrastructure.database.database import load_credentials
from infrastructure.database.sql_executor import get_quality_period_params

# Re-exportar utilidades que otros módulos (ej: consumo_orchestrator) pudieran importar de aquí
from infrastructure.parsers.excel_refresh_service import (  # noqa: F401
    refresh_excel_sharepoint_data,
    _refresh_excel_com_process,
)
from modules.calidad.use_cases.phases.phase3_ingest_accion_tomada import (  # noqa: F401
    deduplicate_observations_by_severity,
)

from modules.calidad.use_cases.phases import (
    phase1_ingest_insight,
    phase2_ingest_verint,
    phase3_ingest_accion_tomada,
    phase4_sql_scripts,
    phase5_ntd,
)

logger = logging.getLogger(__name__)


@dataclass
class QualityPipelineContext:
    """Contexto tipado compartido entre todas las fases del Pipeline de Calidad."""
    period_str: str
    insight_user: str
    insight_password: str
    verint_user: str
    td_user: str
    td_password: str
    host: str = "IBKTD"
    logmech: str = "TD2"
    input_dir: str = ""
    progress_callback: Optional[Callable] = None
    stop_checker: Optional[Callable] = None
    # Parámetros de negocio construidos a partir del periodo
    params: dict = field(default_factory=dict)
    business_vars: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    quality_sequence: List[str] = field(default_factory=list)
    # Estado propagado entre fases
    local_insight_path: str = ""
    downloaded_verint_files: List[str] = field(default_factory=list)


def run_quality_process_flow(
    insight_user: str,
    insight_password: str,
    verint_user: str,
    verint_password: str,
    td_user: str,
    td_password: str,
    period_str: str,
    progress_callback: Optional[Callable] = None,
    run_phase1: bool = True,
    run_phase2: bool = True,
    run_phase3: bool = True,
    run_phase4: bool = True,
    run_phase5: bool = True,
    start_from_script: Optional[str] = None,
    stop_checker: Optional[Callable] = None
):
    """
    Ejecuta el Pipeline Unificado de Proceso Calidad (5 fases).
    Firma 100% compatible con backend/main.py.
    """
    log = progress_callback or (lambda msg, lvl="info": None)
    log("🚀 Iniciando Pipeline Unificado de Proceso Calidad...", "info")

    credenciales = load_credentials()
    host = credenciales.get("teradata_host", "IBKTD")
    logmech = credenciales.get("teradata_logmech", "TD2")

    config_path = os.path.join(os.getcwd(), "config", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    params = get_quality_period_params(period_str)
    context = {**params, **config.get("business_vars", {})}

    input_dir = os.path.join(os.getcwd(), "data", "input", "proceso_calidad")
    os.makedirs(input_dir, exist_ok=True)

    ctx = QualityPipelineContext(
        period_str=period_str,
        insight_user=insight_user,
        insight_password=insight_password,
        verint_user=verint_user,
        td_user=td_user,
        td_password=td_password,
        host=host,
        logmech=logmech,
        input_dir=input_dir,
        progress_callback=progress_callback,
        stop_checker=stop_checker,
        params=params,
        business_vars=config.get("business_vars", {}),
        context=context,
        config=config,
        quality_sequence=config.get("quality_execution_sequence", [])
    )

    if run_phase1:
        phase1_ingest_insight.run_phase1(ctx)
    if run_phase2:
        phase2_ingest_verint.run_phase2(ctx)
    if run_phase3:
        phase3_ingest_accion_tomada.run_phase3(ctx)
    if run_phase4:
        phase4_sql_scripts.run_phase4(ctx, start_from_script=start_from_script)
    if run_phase5:
        phase5_ntd.run_phase5(ctx)

    # Notificación de escritorio global
    try:
        from infrastructure.system.notifier import notify_desktop
        active_phases = []
        if run_phase1: active_phases.append("Fase 1")
        if run_phase2: active_phases.append("Fase 2 (Verint SA)")
        if run_phase3: active_phases.append("Fase 3")
        if run_phase4: active_phases.append("Fase 4")
        if run_phase5: active_phases.append("Fase 5")
        phases_label = ", ".join(active_phases) if active_phases else "Proceso de Calidad"
        notify_desktop(
            title="Plataforma Calidad",
            message=f"¡{phases_label} completada(s) exitosamente para el período {period_str}!",
            duration_sec=5
        )
    except Exception as notify_err:
        logger.warning(f"No se pudo enviar la notificación de escritorio: {notify_err}")
