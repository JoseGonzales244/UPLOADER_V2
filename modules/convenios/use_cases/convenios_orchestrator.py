import os
import sys
import datetime
import logging
from pathlib import Path
from typing import Optional, Callable

# Asegurar path raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from domain.interfaces.database_repository import ITeradataRepository
from infrastructure.database.repositories.teradata_repository import TeradataRepository

logger = logging.getLogger(__name__)

SQL_SETUP_PATH = Path(__file__).parent.parent / "sql" / "00_setup_retencion_convenios.sql"
SQL_QUERY_PATH = Path(__file__).parent.parent / "sql" / "01_query_retencion_convenios.sql"


def run_convenios_setup(
    teradata_repo: Optional[ITeradataRepository] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None
) -> bool:
    """
    Ejecuta el script DDL de creación de tablas y vistas para Convenios en Teradata.
    """
    repo = teradata_repo or TeradataRepository()

    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    try:
        log("🚀 Ejecutando Setup DDL de Convenios en Teradata...", "info")
        with open(SQL_SETUP_PATH, "r", encoding="utf-8") as f:
            sql_text = f.read()

        success = repo.execute_script(sql_text, progress_callback=progress_callback)
        if success:
            log("✅ Estructuras de Convenios creadas exitosamente.", "success")
        return success
    except Exception as e:
        log(f"❌ Error al ejecutar Setup Convenios: {e}", "error")
        return False


def run_convenios_process_flow(
    period_str: Optional[str] = None,
    teradata_repo: Optional[ITeradataRepository] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None
) -> bool:
    """
    Ejecuta el procesamiento mensual de Convenios parametrizado por PERIODO (YYYYMM).
    """
    repo = teradata_repo or TeradataRepository()

    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    if not period_str:
        period_str = datetime.datetime.now().strftime("%Y%m")

    log(f"🔄 Iniciando procesamiento de Convenios para el periodo {period_str}", "info")

    try:
        with open(SQL_QUERY_PATH, "r", encoding="utf-8") as f:
            sql_template = f.read()

        success = repo.execute_script(
            sql_template,
            params={"PERIODO": period_str},
            progress_callback=progress_callback
        )
        if success:
            log(f"🎉 Proceso de Convenios completado con éxito para el periodo {period_str}.", "success")
        return success
    except Exception as e:
        log(f"❌ Error en proceso de Convenios: {e}", "error")
        return False


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else None
    run_convenios_process_flow(p)
