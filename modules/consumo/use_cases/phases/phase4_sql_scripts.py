"""
Fase 4 — Consumo: Scripts SQL de transformación post-carga.

Llama run_post_load_transformations de sql_executor.py.
Al finalizar con éxito actualiza el timestamp de Power BI (conector_base_consumo.txt).
"""
from __future__ import annotations

import logging
from typing import Optional

from infrastructure.database.sql_executor import run_post_load_transformations
from infrastructure.system.powerbi_connector import write_powerbi_timestamp

logger = logging.getLogger(__name__)


def run_phase4(ctx, start_from_script: Optional[str] = None) -> bool:
    """
    Fase 4 Consumo: Ejecución de reglas de negocio y cálculo diario de Consumo.
    Actualiza timestamp Power BI al finalizar.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("⚡ Fase 4: Ejecutando reglas de negocio y cálculo diario de Consumo...", "info")

    run_post_load_transformations(
        con=ctx.td_con,
        period_str=ctx.period_str,
        clear_consent=ctx.clear_consent,
        progress_callback=ctx.progress_callback,
        start_from_script=start_from_script
    )

    # Actualizar conector Power BI al finalizar el SQL
    write_powerbi_timestamp("conector_base_consumo.txt")

    log("✅ Fase 4 completada exitosamente.", "success")
    return True
