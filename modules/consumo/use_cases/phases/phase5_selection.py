"""
Fase 5 — Consumo: Transformación de Selección.

Llama run_selection_transformation de sql_executor.py
con conexión secundaria propia.
"""
from __future__ import annotations

import logging

from infrastructure.database.sql_executor import run_selection_transformation

logger = logging.getLogger(__name__)


def run_phase5(ctx) -> bool:
    """
    Fase 5 Consumo: Generación del consolidado de selección.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("⚡ Fase 5: Generando consolidado de selección...", "info")

    run_selection_transformation(
        period_str=ctx.period_str,
        progress_callback=ctx.progress_callback
    )

    log("✅ Fase 5 completada exitosamente.", "success")
    return True
