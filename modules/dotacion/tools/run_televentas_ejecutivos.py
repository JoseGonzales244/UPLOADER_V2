"""
Herramienta CLI para ejecutar directamente la Fase 4: Generación de Televentas Ejecutivos.

Uso en terminal:
    .\\.venv\\Scripts\\python -m modules.dotacion.tools.run_televentas_ejecutivos --periodo 2026-08
"""
from __future__ import annotations

import os
import sys
import argparse
import openpyxl

from modules.dotacion.dotacion_config import DotacionConfig
from modules.dotacion.phases import fase4_televentas


def generate_televentas_ejecutivos(periodo: str = "AUTO", progress_callback=None) -> bool:
    """
    Ejecuta directamente la Fase 4 para generar el archivo TELEVENTAS_EJECUTIVOS
    a partir del libro EQUIPO DE VENTAS sincronizado.
    """
    log = progress_callback or (lambda msg, lvl="info": print(f"[{lvl.upper()}] {msg}"))
    cfg = DotacionConfig(target_period=periodo)

    log(f"🚀 Iniciando generación de Televentas Ejecutivos para periodo: {cfg.TARGET_PERIOD}...", "info")

    source_wb = cfg.OUTPUT_WORKBOOK
    if not os.path.exists(source_wb):
        source_wb = cfg.INPUT_WORKBOOK
        if not os.path.exists(source_wb):
            raise FileNotFoundError(
                f"No se encontró ni el libro de salida '{cfg.OUTPUT_WORKBOOK}' "
                f"ni el libro de entrada '{cfg.INPUT_WORKBOOK}'."
            )
        log(f"ℹ️ Archivo preliminar no encontrado. Usando archivo base: {source_wb}", "warning")

    log(f"📖 Cargando libro base: {os.path.basename(source_wb)}...", "info")
    wb = openpyxl.load_workbook(source_wb, keep_links=True, data_only=False)
    try:
        fase4_televentas.run(wb, cfg)
        log(f"🎉 Archivo TELEVENTAS_EJECUTIVOS generado con éxito: {os.path.basename(cfg.CURR_EXEC_FILE)}", "success")
        return True
    finally:
        wb.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar archivo Televentas Ejecutivos (Fase 4)")
    parser.add_argument("--periodo", type=str, default="AUTO", help="Periodo en formato YYYY-MM o YYYYMM (defecto: AUTO)")
    args = parser.parse_args()

    generate_televentas_ejecutivos(periodo=args.periodo)
