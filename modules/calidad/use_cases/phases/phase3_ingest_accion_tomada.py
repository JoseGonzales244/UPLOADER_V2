"""
Fase 3 — Calidad: Ingesta de Acciones Tomadas (ACCION_TOMADA.xlsx).

Lee el archivo Excel, deduplica por severidad de acción tomada y
carga en DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE en Teradata.
"""
from __future__ import annotations

import os
import logging
import polars as pl

from infrastructure.parsers.readers import read_excel_file
from infrastructure.parsers.cleaners import clean_dataframe
from infrastructure.parsers.excel_refresh_service import refresh_excel_sharepoint_data
from infrastructure.database.database import connect_teradata, load_to_teradata
from ui.components import load_templates
from modules.calidad.use_cases.phases.phase1_ingest_insight import _get_selections_from_template

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "DESVINCULACION": 1, "DESVINCULACIÓN": 1, "Desvinculación": 1,
    "EV YA NO LABORA EN IBK": 2,
    "SUSPENSION": 3, "SUSPENSIÓN": 3, "Suspensión": 3,
    "ENVIADO A GDH": 4,
    "CARTA DE LLAMADA DE ATENCION SEVERA": 5, "CARTA DE LLAMADA DE ATENCIÓN SEVERA": 5,
    "Ll. atencion severa": 6, "Ll. atención severa": 6,
    "CARTA DE LLAMADA DE ATENCION SIMPLE": 7, "CARTA DE LLAMADA DE ATENCIÓN SIMPLE": 7,
    "ACTA DE LLAMADA DE ATENCION": 8, "ACTA DE LLAMADA DE ATENCIÓN": 8,
    "Ll. atencion simple": 9, "Ll. atención simple": 9,
    "Ll. atencion verbal": 10, "Ll. atención verbal": 10,
    "FEEDBACK": 11, "Feedback": 11,
    "-": 12, "Accion No Definida": 12, "Acción No Definida": 12
}


def deduplicate_observations_by_severity(df: pl.DataFrame) -> pl.DataFrame:
    """Deduplica por CODIGO_NTD conservando la acción de mayor severidad."""
    df_with_rank = df.with_columns(
        pl.col("ACCION_TOMADA")
        .map_elements(
            lambda x: SEVERITY_ORDER.get(str(x).strip() if x is not None else "-", 99),
            return_dtype=pl.Int32
        )
        .alias("SEVERITY_RANK")
    )
    df_sorted = df_with_rank.sort(["CODIGO_NTD", "SEVERITY_RANK"])
    df_deduplicated = df_sorted.unique(subset=["CODIGO_NTD"], keep="first")
    return df_deduplicated.drop("SEVERITY_RANK")


def run_phase3(ctx) -> bool:
    """
    Fase 3: Ingesta de Acciones Tomadas desde ACCION_TOMADA.xlsx a Teradata.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("🚀 Fase 3 iniciando: Ingesta de Acciones Tomadas (ACCION_TOMADA.xlsx)...", "info")

    templates = load_templates()
    excel_path = os.path.join(ctx.input_dir, "ACCION_TOMADA.xlsx")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(
            f"No se encontró el archivo requerido en: {excel_path}. "
            "Colócalo en 'data/input/proceso_calidad/'."
        )

    # Auto-refresh Excel via COM
    try:
        refresh_excel_sharepoint_data(excel_path, ctx.progress_callback)
    except Exception as refresh_err:
        log(f"⚠️ Advertencia al actualizar Excel desde SharePoint: {refresh_err}. "
            "Se continuará con el archivo en su estado actual.", "warning")

    df_observaciones = read_excel_file(excel_path)
    template_obs = templates.get("P004-ACC_TOMADA", {})
    if not template_obs:
        raise ValueError("No se encontró la plantilla P004-ACC_TOMADA en plantillas.json.")

    selections_obs = _get_selections_from_template(df_observaciones, template_obs)
    df_obs_clean = clean_dataframe(
        df_observaciones, selections_obs,
        convertir_sin_acentos=True, transformar_varchar_latin=False, max_len_varchar=3000
    )

    log("🧹 Deduplicando registros de Acciones Tomadas por orden de severidad...", "info")
    df_obs_clean = deduplicate_observations_by_severity(df_obs_clean)

    con = connect_teradata(ctx.td_user, ctx.td_password, host=ctx.host, logmech=ctx.logmech)
    try:
        log("🚀 Cargando en la tabla DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE...", "info")
        load_to_teradata(
            con=con, table_name="DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE",
            df=df_obs_clean, selected_columns_config=selections_obs,
            clear_table=True, progress_callback=ctx.progress_callback
        )
        log("🏁 Fase 3 concluida exitosamente: Acciones Tomadas cargadas en Teradata.", "success")
        return True
    finally:
        try:
            con.close()
        except Exception:
            pass
