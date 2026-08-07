"""
Módulo Orquestador de Cierre Mensual:
Ejecuta la consolidación de nota gerencial (01_auditoria_y_cierre.sql)
e inserción de resumen KRI (02_kri_resumen_total.sql) para el período cerrado {PERIODO_ANTERIOR}.
Garantiza idempotencia eliminando datos previos del período antes de la inserción.
"""
import os
import re
import datetime
import logging
import teradatasql

from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.system.logging_config import setup_logging
from infrastructure.database.sql_executor import get_friendly_script_name

logger = setup_logging("modules.cierre.orchestrator", log_prefix="cierre")

def get_cierre_period_params(period_str: str) -> dict:
    """
    Retorna el diccionario de parámetros inyectando directamente el período ingresado.
    """
    if not re.match(r'^\d{6}$', period_str):
        raise ValueError(f"Formato de período inválido '{period_str}'. Debe ser YYYYMM.")
        
    return {
        "PERIODO": period_str,
        "PERIODO_ANTERIOR": period_str,
    }

def inject_variables(sql_text: str, context: dict) -> str:
    """
    Reemplaza variables {VARIABLE} en el código SQL con los valores del contexto.
    """
    for key, val in context.items():
        pattern = r'\{' + re.escape(str(key)) + r'\}'
        sql_text = re.compile(pattern, re.IGNORECASE).sub(str(val), sql_text)
    return sql_text

def parse_statements(sql_text: str) -> list:
    """
    Limpia comentarios y separa sentencias por punto y coma.
    """
    # Eliminar comentarios de bloque
    sql_cleaned = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
    
    # Eliminar comentarios de línea simple
    lines = []
    for line in sql_cleaned.split('\n'):
        in_quote = False
        quote_char = None
        comment_idx = -1
        i = 0
        while i < len(line):
            c = line[i]
            if c in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                if not in_quote:
                    in_quote = True
                    quote_char = c
                elif c == quote_char:
                    in_quote = False
                    quote_char = None
            elif c == '-' and i + 1 < len(line) and line[i+1] == '-' and not in_quote:
                comment_idx = i
                break
            i += 1
        if comment_idx != -1:
            line = line[:comment_idx]
        lines.append(line)
        
    cleaned_text = '\n'.join(lines)
    
    statements = []
    for stmt in cleaned_text.split(';'):
        stmt_clean = stmt.strip()
        if stmt_clean:
            statements.append(stmt_clean)
            
    return statements

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
    periodo_cerrado = params["PERIODO_ANTERIOR"]
    
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
        con = connect_teradata(user, password, host=host, logmech=logmech)
        con.autocommit = True
        cursor = con.cursor()
    except Exception as err:
        logger.error(f"Error al conectar con Teradata: {err}")
        raise RuntimeError(f"Error de conexión con Teradata: {err}")
        
    try:
        total_scripts = len(cierre_scripts)
        for s_idx, script_rel_path in enumerate(cierre_scripts, 1):
            script_path = os.path.join(os.getcwd(), script_rel_path)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Script de cierre no encontrado en: {script_rel_path}")
                
            script_name = os.path.basename(script_path)
            friendly_name = get_friendly_script_name(script_path)
            
            if progress_callback:
                progress_callback(f"⚡ [{s_idx}/{total_scripts}] Procesando script de cierre: **{friendly_name}** ({script_name})...", "info", progress=float(s_idx)/total_scripts)
                
            with open(script_path, "r", encoding="utf-8") as f:
                raw_sql = f.read()
                
            prepared_sql = inject_variables(raw_sql, params)
            statements = parse_statements(prepared_sql)
            
            logger.info(f"Ejecutando {len(statements)} sentencias en {script_name}")
            
            for stmt_idx, stmt in enumerate(statements, 1):
                preview = stmt.split("\n")[0][:90]
                logger.info(f"   [{stmt_idx}/{len(statements)}] Exec: {preview}")
                if progress_callback:
                    progress_callback(f"   🔹 Sentencia {stmt_idx}/{len(statements)}: {preview}...", "info")
                try:
                    cursor.execute(stmt)
                except Exception as stmt_err:
                    from infrastructure.database.sql_executor import SQLScriptExecutionError
                    raise SQLScriptExecutionError(script_name, stmt_idx, stmt, stmt_err)
                    
            if progress_callback:
                progress_callback(f"✅ Script de cierre completado: **{friendly_name}**", "success")
                
        if progress_callback:
            progress_callback("💾 Guardando transacciones finales del cierre (Commit)...", "info")
        con.commit()
        
        msg_success = f"🎉 ¡Cierre Mensual para el período {periodo_cerrado} completado con éxito!"
        logger.info(msg_success)
        if progress_callback:
            progress_callback(msg_success, "success", progress=1.0, phase=6)
            
        return {
            "status": "success",
            "periodo_base": period_str,
            "periodo_cerrado": periodo_cerrado,
            "message": msg_success
        }
    except Exception as e:
        logger.error(f"Fallo en Cierre Mensual: {e}")
        try:
            con.rollback()
        except Exception:
            pass
        raise e
    finally:
        try:
            con.close()
        except Exception:
            pass
