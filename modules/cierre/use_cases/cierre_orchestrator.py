"""
Módulo Orquestador de Cierre Mensual:
Ejecuta la consolidación de nota gerencial (01_auditoria_y_cierre.sql)
e inserción de resumen KRI (02_kri_resumen_total.sql) para el período indicado.
Garantiza idempotencia eliminando datos previos del período antes de la inserción.
"""
import os
import re
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import teradatasql

from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.system.logging_config import setup_logging
from infrastructure.database.sql_executor import (
    get_friendly_script_name,
    get_cierre_period_params,
    inject_variables,
    parse_statements
)

logger = setup_logging("modules.cierre.orchestrator", log_prefix="cierre")


def run_cierre_process_flow(
    period_str: str,
    td_user: str = None,
    td_password: str = None,
    run_cierre_01: bool = True,
    run_cierre_02: bool = True,
    run_cierre_03: bool = True,
    progress_callback=None
):
    """
    Ejecuta el flujo de Cierre Mensual seleccionando individualmente los scripts deseados.
    """
    params = get_cierre_period_params(period_str)
    periodo_cerrado = params["PERIODO"]
    
    cierre_scripts = []
    if run_cierre_01:
        cierre_scripts.append("modules/cierre/sql/01_auditoria_y_cierre.sql")
    if run_cierre_02:
        cierre_scripts.append("modules/cierre/sql/02_kri_resumen_total.sql")
    if run_cierre_03:
        cierre_scripts.append("modules/cierre/sql/03_consolidado_notas_cierre.sql")
        
    if not cierre_scripts:
        raise ValueError("Debe seleccionar al menos un script de cierre a ejecutar.")
        
    logger.info(f"=== INICIANDO PROCESO DE CIERRE MENSUAL PARA PERÍODO CERRADO {periodo_cerrado} ({len(cierre_scripts)} script(s) seleccionados) ===")
    if progress_callback:
        progress_callback(f"🔒 Iniciando Cierre Mensual para el período cerrado: **{periodo_cerrado}** ({len(cierre_scripts)} script(s))...", "info", progress=0.0, phase=6)
        
    credenciales = load_credentials()
    user = td_user or credenciales.get("teradata_user")
    password = td_password or credenciales.get("teradata_password")
    host = credenciales.get("teradata_host", "IBKTD")
    logmech = credenciales.get("teradata_logmech", "TD2")
    
    if not user or not password:
        raise ValueError("Credenciales de Teradata no proporcionadas ni encontradas en .env.")
    
    if progress_callback:
        progress_callback("🔌 Conectando a Teradata...", "info")
        
    try:
        test_con = connect_teradata(user, password, host=host, logmech=logmech)
        test_con.close()
    except Exception as err:
        logger.error(f"Error al conectar con Teradata: {err}")
        raise RuntimeError(f"Error de conexión con Teradata: {err}")

    def _execute_cierre_script(script_rel_path: str):
        script_path = os.path.join(os.getcwd(), script_rel_path)
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script de cierre no encontrado en: {script_rel_path}")

        script_name = os.path.basename(script_path)
        friendly_name = get_friendly_script_name(script_path)

        if progress_callback:
            progress_callback(f"⚡ Procesando script de cierre: **{friendly_name}** ({script_name})...", "info")

        with open(script_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        prepared_sql = inject_variables(raw_sql, params)
        statements = parse_statements(prepared_sql)

        logger.info(f"Ejecutando {len(statements)} sentencias en {script_name}")

        worker_con = connect_teradata(user, password, host=host, logmech=logmech)
        worker_con.autocommit = True
        worker_cursor = worker_con.cursor()
        try:
            for stmt_idx, stmt in enumerate(statements, 1):
                preview = stmt.split("\n")[0][:90]
                logger.info(f"   [{stmt_idx}/{len(statements)}] Exec ({script_name}): {preview}")
                try:
                    worker_cursor.execute(stmt)
                except Exception as stmt_err:
                    from infrastructure.database.sql_executor import SQLScriptExecutionError
                    raise SQLScriptExecutionError(script_name, stmt_idx, stmt, stmt_err)
            worker_con.commit()
            if progress_callback:
                progress_callback(f"✅ Script de cierre completado: **{friendly_name}**", "success")
            return friendly_name
        except Exception as e:
            try:
                worker_con.rollback()
            except Exception:
                pass
            raise e
        finally:
            try:
                worker_con.close()
            except Exception:
                pass

    try:
        if len(cierre_scripts) > 1:
            if progress_callback:
                progress_callback(f"⚡ Ejecutando {len(cierre_scripts)} vías de cierre mensual en paralelo (Fan-Out)...", "info")
            with ThreadPoolExecutor(max_workers=len(cierre_scripts)) as executor:
                futures = {executor.submit(_execute_cierre_script, s): s for s in cierre_scripts}
                for fut in as_completed(futures):
                    fut.result()
        else:
            _execute_cierre_script(cierre_scripts[0])

        msg_success = f"🎉 ¡Cierre Mensual para el período {periodo_cerrado} completado con éxito!"
        logger.info(msg_success)
        if progress_callback:
            progress_callback(msg_success, "success", progress=1.0, phase=6)

        try:
            from infrastructure.system.notifier import notify_desktop
            notify_desktop(
                title="Plataforma Calidad - Cierre Mensual",
                message=f"¡Cierre Mensual completado exitosamente para el período {periodo_cerrado}!",
                duration_sec=5
            )
        except Exception as notify_err:
            logger.warning(f"No se pudo enviar la notificación de escritorio: {notify_err}")

        return {
            "status": "success",
            "periodo_base": period_str,
            "periodo_cerrado": periodo_cerrado,
            "message": msg_success
        }
    except Exception as e:
        logger.error(f"Fallo en Cierre Mensual: {e}")
        raise e
