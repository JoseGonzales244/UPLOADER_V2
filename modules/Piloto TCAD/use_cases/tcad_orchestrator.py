import os
import re
import datetime
import logging
from pathlib import Path

from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.database.sql_executor import split_sql_statements

logger = logging.getLogger(__name__)

SQL_DDL_PATH = Path(__file__).parent.parent / "sql" / "00_ddl_tcad_tables_views.sql"
SQL_DML_PATH = Path(__file__).parent.parent / "sql" / "01_dml_tcad_monthly_ingest.sql"


def calculate_period_date_range(period_str: str) -> tuple:
    """
    Dada una cadena de periodo YYYYMM (ej: '202603'), retorna
    (fecha_inicio, fecha_fin) en formato ISO string:
    '2026-03-01 00:00:00', '2026-04-01 00:00:00'
    """
    period_clean = period_str.strip()
    year = int(period_clean[:4])
    month = int(period_clean[4:6])

    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_date = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_date = datetime.datetime(year, month + 1, 1, 0, 0, 0)

    return (
        start_date.strftime("%Y-%m-%d %H:%M:%S"),
        end_date.strftime("%Y-%m-%d %H:%M:%S"),
    )


def run_tcad_setup(con=None, progress_callback=None) -> bool:
    """
    Ejecuta el script DDL de tablas y vistas para el reporte TCAD.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(creds)
            close_con = True

        log("🚀 Ejecutando DDL de estructuras TCAD en Teradata...", "info")
        with open(SQL_DDL_PATH, "r", encoding="utf-8") as f:
            sql_text = f.read()

        statements = split_sql_statements(sql_text)
        cur = con.cursor()
        for idx, stmt in enumerate(statements, 1):
            log(f"  - Sentencia DDL {idx}/{len(statements)}", "info")
            cur.execute(stmt)
        cur.close()
        log("✅ Estructuras TCAD (tablas y vistas) creadas/actualizadas exitosamente.", "success")
        return True
    except Exception as e:
        log(f"❌ Error al ejecutar DDL TCAD: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()


def run_tcad_monthly_ingest(period_str: str, con=None, progress_callback=None) -> bool:
    """
    Ejecuta la ingesta mensual TCAD parametrizada por el periodo (YYYYMM).
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    fecha_inicio, fecha_fin = calculate_period_date_range(period_str)
    log(f"🔄 Iniciando ingesta TCAD para periodo {period_str} [{fecha_inicio} -> {fecha_fin}]", "info")

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(creds)
            close_con = True

        with open(SQL_DML_PATH, "r", encoding="utf-8") as f:
            sql_template = f.read()

        sql_executed = sql_template.format(
            PERIODO=period_str,
            FECHA_INICIO=fecha_inicio,
            FECHA_FIN=fecha_fin,
        )

        statements = split_sql_statements(sql_executed)
        cur = con.cursor()
        for idx, stmt in enumerate(statements, 1):
            log(f"  - Sentencia DML {idx}/{len(statements)}", "info")
            cur.execute(stmt)
        cur.close()
        log(f"🎉 Ingesta TCAD completada con éxito para el periodo {period_str}.", "success")
        return True
    except Exception as e:
        log(f"❌ Error en ingesta TCAD: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()
