import os
import sys
import datetime
import logging
from pathlib import Path

# Asegurar path raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.database.sql_executor import split_sql_statements

logger = logging.getLogger(__name__)

SQL_SETUP_PATH = Path(__file__).parent.parent / "sql" / "00_setup_retencion_convenios.sql"
SQL_QUERY_PATH = Path(__file__).parent.parent / "sql" / "01_query_retencion_convenios.sql"


def run_convenios_setup(con=None, progress_callback=None) -> bool:
    """
    Ejecuta el script DDL de creación de tablas y vistas para Convenios en Teradata.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(
                user=creds["teradata_user"],
                password=creds["teradata_password"],
                host=creds.get("teradata_host", "IBKTD"),
                logmech=creds.get("teradata_logmech", "TD2")
            )
            close_con = True

        log("🚀 Ejecutando Setup DDL de Convenios en Teradata...", "info")
        with open(SQL_SETUP_PATH, "r", encoding="utf-8") as f:
            sql_text = f.read()

        statements = split_sql_statements(sql_text)
        with con.cursor() as cur:
            for idx, stmt in enumerate(statements, 1):
                log(f"  - Sentencia DDL {idx}/{len(statements)}", "info")
                cur.execute(stmt)

        log("✅ Estructuras de Convenios creadas exitosamente.", "success")
        return True
    except Exception as e:
        log(f"❌ Error al ejecutar Setup Convenios: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()


def run_convenios_process_flow(period_str: str = None, con=None, progress_callback=None) -> bool:
    """
    Ejecuta el procesamiento mensual de Convenios parametrizado por PERIODO (YYYYMM).
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    if not period_str:
        period_str = datetime.datetime.now().strftime("%Y%m")

    log(f"🔄 Iniciando procesamiento de Convenios para el periodo {period_str}", "info")

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(
                user=creds["teradata_user"],
                password=creds["teradata_password"],
                host=creds.get("teradata_host", "IBKTD"),
                logmech=creds.get("teradata_logmech", "TD2")
            )
            close_con = True

        with open(SQL_QUERY_PATH, "r", encoding="utf-8") as f:
            sql_template = f.read()

        sql_executed = sql_template.replace("{PERIODO}", period_str)
        statements = split_sql_statements(sql_executed)

        with con.cursor() as cur:
            for idx, stmt in enumerate(statements, 1):
                log(f"  - Ejecutando sentencia {idx}/{len(statements)}", "info")
                cur.execute(stmt)

        log(f"🎉 Proceso de Convenios completado con éxito para el periodo {period_str}.", "success")
        return True
    except Exception as e:
        log(f"❌ Error en proceso de Convenios: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else None
    run_convenios_process_flow(p)
