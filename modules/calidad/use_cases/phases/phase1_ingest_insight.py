"""
Fase 1 — Calidad: Descarga e Ingesta de Evaluaciones de Insight.

Descarga la query EVALUATIONS desde Insight, limpia el DataFrame con Polars
y lo carga en DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE en Teradata.
"""
from __future__ import annotations

import os
import datetime
import logging
import polars as pl
from dataclasses import dataclass, field
from typing import Callable, Optional

from infrastructure.scrapers.insight_downloader import download_insight_data
from infrastructure.parsers.cleaners import clean_dataframe
from infrastructure.database.database import connect_teradata, load_to_teradata
from ui.components import load_templates

logger = logging.getLogger(__name__)


def _get_selections_from_template(df: pl.DataFrame, template_config: dict) -> list:
    from infrastructure.parsers.cleaners import sanitize_identifier
    selections = []
    for col in df.columns:
        if col in template_config:
            selections.append({
                "name": col,
                "selected": template_config[col].get("Añadir", True),
                "convert_nulls": template_config[col].get("Null:0/No Null:1", False),
                "datatype": template_config[col].get("Tipo de dato", "VARCHAR(255)"),
                "new_name": sanitize_identifier(template_config[col].get("Nuevo nombre", col))
            })
        else:
            selections.append({
                "name": col,
                "selected": False,
                "convert_nulls": False,
                "datatype": "VARCHAR(255)",
                "new_name": sanitize_identifier(col)
            })
    return selections


def run_phase1(ctx) -> bool:
    """
    Fase 1: Descarga e ingesta de Evaluaciones de Insight a Teradata.
    Mutar ctx.local_insight_path con la ruta del archivo descargado.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("🚀 Fase 1 iniciando: Descarga e Ingesta de Evaluaciones de Insight...", "info")

    templates = load_templates()
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    input_dir = ctx.input_dir
    expected_insight_file = os.path.join(input_dir, f"Reporte_Insight_EVALUATIONS_{today_str}.txt")

    if os.path.exists(expected_insight_file) and os.path.getsize(expected_insight_file) > 0:
        local_insight_path = expected_insight_file
        log(f"ℹ️ Archivo de Insight para hoy ya existe localmente ({os.path.basename(local_insight_path)}). Omitiendo descarga.", "info")
    else:
        try:
            local_insight_path = download_insight_data(
                query_name="EVALUATIONS",
                username=ctx.insight_user,
                password=ctx.insight_password,
                progress_callback=ctx.progress_callback,
                output_dir=input_dir,
                period_str=ctx.period_str
            )
        except Exception as err:
            raise RuntimeError(f"Fallo crítico al descargar evaluaciones de Insight: {err}")

    ctx.local_insight_path = local_insight_path

    # Read TSV with fallback encoding
    try:
        df_insight = pl.read_csv(
            local_insight_path, separator="\t", infer_schema_length=0,
            truncate_ragged_lines=True, quote_char=None, ignore_errors=True
        )
    except Exception as err_tsv:
        logger.warning(f"Error primario leyendo TSV de Evaluaciones ({err_tsv}). Intentando latin-1...")
        try:
            df_insight = pl.read_csv(
                local_insight_path, separator="\t", infer_schema_length=0,
                truncate_ragged_lines=True, ignore_errors=True, encoding="latin1"
            )
        except Exception as err_fallback:
            raise RuntimeError(f"Error de formato TSV '{os.path.basename(local_insight_path)}': {err_fallback}")

    template_insight = templates.get("P008-INSIGHT_07_EVALUATIONS", {})
    if not template_insight:
        raise ValueError("No se encontró la plantilla P008-INSIGHT_07_EVALUATIONS en plantillas.json.")

    selections = _get_selections_from_template(df_insight, template_insight)
    df_clean = clean_dataframe(df_insight, selections, convertir_sin_acentos=True,
                               transformar_varchar_latin=False, max_len_varchar=3000)

    log("🚀 Cargando en la tabla DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE...", "info")
    con = connect_teradata(ctx.td_user, ctx.td_password, host=ctx.host, logmech=ctx.logmech)
    try:
        load_to_teradata(
            con=con, table_name="DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE",
            df=df_clean, selected_columns_config=selections, clear_table=True,
            progress_callback=ctx.progress_callback
        )
        log("🏁 Fase 1 concluida exitosamente: Evaluaciones Insight cargadas.", "success")
        return True
    finally:
        try:
            con.close()
        except Exception:
            pass
