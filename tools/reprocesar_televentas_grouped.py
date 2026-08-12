#!/usr/bin/env python
"""
Herramienta manual para forzar el reprocesamiento (corrección) de TELEVENTAS_EJECUTIVOS_GROUPED.
Uso:
    python tools/reprocesar_televentas_grouped.py --periodo 202608
"""

import sys
import argparse
import logging
from pathlib import Path

# Añadir directorio raíz al PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from modules.televentas.use_cases.grouped_orchestrator import process_televentas_grouped

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Forzar reproceso/corrección manual de TELEVENTAS_EJECUTIVOS_GROUPED para un periodo.")
    parser.add_argument("--periodo", required=True, help="Periodo en formato YYYYMM (ejemplo: 202608)")
    args = parser.parse_args()

    periodo = args.periodo.strip()
    logger.info(f"🔄 Iniciando reproceso manual de corrección para el periodo {periodo}...")

    def progress_cb(msg, level="info"):
        print(f"[{level.upper()}] {msg}")

    try:
        success = process_televentas_grouped(periodo, force_reprocess=True, progress_callback=progress_cb)
        if success:
            logger.info(f"🎉 Reproceso manual completado con éxito para el periodo {periodo}.")
        else:
            logger.error(f"❌ Ocurrió un problema durante el reproceso manual del periodo {periodo}.")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"💥 Error durante el reproceso manual: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
