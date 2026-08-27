"""
Fase 2 — Consumo: Ingesta manual del archivo CD40K.

Localiza CD40K_NEW.xlsx o CD40K.xlsx, refresca sus conexiones Excel
y carga en DLAB_GEC.T_SP_CD40K en Teradata.
"""
from __future__ import annotations

import os
import glob
import logging
import polars as pl

from infrastructure.parsers.cleaners import clean_dataframe
from infrastructure.parsers.excel_refresh_service import refresh_excel_sharepoint_data
from infrastructure.database.database import load_to_teradata
from ui.components import load_templates
from modules.calidad.use_cases.phases.phase1_ingest_insight import _get_selections_from_template

logger = logging.getLogger(__name__)


def run_phase2(ctx) -> bool:
    """
    Fase 2 Consumo: Ingesta del archivo manual CD40K en Teradata.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("🚀 Fase 2 iniciando: Ingesta de información manual CD40K...", "info")

    templates = load_templates()
    input_dir = ctx.input_dir

    # Buscar archivo CD40K
    cd40k_candidates = [
        os.path.join(input_dir, "CD40K_NEW.xlsx"),
        os.path.join(input_dir, "CD40K.xlsx")
    ]
    cd40k_path = next((c for c in cd40k_candidates if os.path.exists(c) and os.path.getsize(c) > 0), None)

    if not cd40k_path:
        glob_cd40k = glob.glob(os.path.join(input_dir, "*CD40K*.xlsx"))
        if glob_cd40k:
            cd40k_path = glob_cd40k[0]

    if not cd40k_path or not os.path.exists(cd40k_path):
        err_msg = (
            f"❌ Error en Fase 2: No se encontró el archivo Excel manual CD40K en '{input_dir}'. "
            "Se esperaba 'CD40K_NEW.xlsx' o 'CD40K.xlsx'. El proceso no puede continuar sin este insumo."
        )
        logger.error(err_msg)
        log(err_msg, "error")
        raise FileNotFoundError(err_msg)

    log(f"📂 Procesando archivo manual CD40K ({os.path.basename(cd40k_path)})...", "info")

    try:
        refresh_excel_sharepoint_data(cd40k_path, ctx.progress_callback)
    except Exception as refresh_err:
        logger.warning(f"SharePoint Excel refresh warning for CD40K: {refresh_err}")

    df_cd40k = pl.read_excel(cd40k_path)
    template_cd40k = templates.get("P003-CD40K", {})

    if template_cd40k:
        selections_cd40k = _get_selections_from_template(df_cd40k, template_cd40k)
        df_cd40k_clean = clean_dataframe(
            df_cd40k, selections_cd40k,
            convertir_sin_acentos=True, transformar_varchar_latin=False, max_len_varchar=3000
        )

        load_to_teradata(
            con=ctx.td_con, table_name="DLAB_GEC.T_SP_CD40K",
            df=df_cd40k_clean, selected_columns_config=selections_cd40k,
            clear_table=True, progress_callback=ctx.progress_callback
        )
        log("🏁 Fase 2 concluida exitosamente: Base CD40K cargada en Teradata.", "success")
    return True
