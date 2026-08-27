"""
Fase 1 — Consumo: Descarga e Ingesta de Insumos de Insight.

Itera sobre consumo_insumos_config (leído de config.json), descarga cada
query de Insight y lo carga en su tabla Teradata correspondiente.
"""
from __future__ import annotations

import os
import glob
import datetime
import logging
import polars as pl

from infrastructure.scrapers.insight_downloader import download_insight_data
from infrastructure.parsers.cleaners import clean_dataframe
from infrastructure.database.database import load_to_teradata
from ui.components import load_templates
from modules.calidad.use_cases.phases.phase1_ingest_insight import _get_selections_from_template

logger = logging.getLogger(__name__)


def run_phase1(ctx) -> bool:
    """
    Fase 1 Consumo: Descarga 7 insumos de Insight e ingesta en Teradata.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("📥 Fase 1: Descargando fuentes de información de Insight...", "info")

    templates = load_templates()
    input_dir = ctx.input_dir
    insumos_config = ctx.insumos_config

    downloaded_files: dict = {}

    # --- Descarga ---
    for insumo_key, conf in insumos_config.items():
        q_name = conf["query_name"]
        n_ejecutivo = conf["nombre_ejecutivo"]
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        expected_path = os.path.join(input_dir, f"Reporte_Insight_{q_name}_{today_str}.txt")

        if os.path.exists(expected_path) and os.path.getsize(expected_path) > 0:
            log(f"ℹ️ Archivo local encontrado para {n_ejecutivo}. Se usará la copia guardada de hoy.", "info")
            downloaded_files[insumo_key] = expected_path
            continue

        log(f"📡 Descargando insumo: {n_ejecutivo}...", "info")
        try:
            local_path = download_insight_data(
                query_name=q_name,
                username=ctx.insight_user,
                password=ctx.insight_password,
                progress_callback=ctx.progress_callback,
                output_dir=input_dir,
                period_str=ctx.period_str
            )
            downloaded_files[insumo_key] = local_path
            log(f"✅ Descarga lista: {n_ejecutivo}", "success")
        except Exception as err:
            log(f"⚠️ No se pudo descargar el insumo '{n_ejecutivo}'. Se continuará con datos disponibles.", "warning")
            logger.warning(f"Failed to download Insight insumo '{q_name}': {err}")

    # --- Ingesta a Teradata ---
    for insumo_key, conf in insumos_config.items():
        q_name = conf["query_name"]
        t_key = conf["template_key"]
        tables = conf["tables"]
        n_ejecutivo = conf["nombre_ejecutivo"]

        local_path = downloaded_files.get(insumo_key)
        if not local_path or not os.path.exists(local_path):
            matching = glob.glob(os.path.join(input_dir, f"Reporte_Insight_{q_name}_*.txt"))
            if matching:
                local_path = sorted(matching)[-1]

        if not local_path or not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            log(f"⚠️ Omitiendo la ingesta de '{n_ejecutivo}' por no contar con archivo válido.", "warning")
            continue

        log(f"🧹 Procesando y limpiando datos de {n_ejecutivo}...", "info")
        try:
            df = pl.read_csv(
                local_path, separator="\t", infer_schema_length=0,
                truncate_ragged_lines=True, quote_char=None, ignore_errors=True
            )
        except Exception as err_tsv:
            logger.warning(f"Error TSV para '{q_name}' ({err_tsv}). Intentando latin-1...")
            try:
                df = pl.read_csv(
                    local_path, separator="\t", infer_schema_length=0,
                    truncate_ragged_lines=True, ignore_errors=True, encoding="latin1"
                )
            except Exception as err_fallback:
                raise RuntimeError(f"Error de formato TSV '{os.path.basename(local_path)}': {err_fallback}")

        if df.is_empty():
            logger.warning(f"El archivo '{local_path}' está vacío. Omitiendo carga.")
            continue

        template_config = templates.get(t_key, {})
        selections = _get_selections_from_template(df, template_config)
        df_clean = clean_dataframe(df, selections, convertir_sin_acentos=True,
                                   transformar_varchar_latin=False, max_len_varchar=3000)

        for table_name in tables:
            log(f"🚀 Actualizando base de datos para {n_ejecutivo}...", "info")
            load_to_teradata(
                con=ctx.td_con, table_name=table_name,
                df=df_clean, selected_columns_config=selections,
                clear_table=True, progress_callback=ctx.progress_callback
            )
            logger.info(f"Table '{table_name}' loaded successfully.")

    log("✅ Fase 1 completada exitosamente.", "success")
    return True
