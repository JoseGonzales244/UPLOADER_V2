"""
Fase 2 — Calidad: Descarga e Ingesta de Speech Analytics Verint.

Detecta archivos Verint descargados hoy, o los baja vía API REST directa.
Carga los datos en DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS.
"""
from __future__ import annotations

import os
import glob
import datetime
import logging
import polars as pl

from infrastructure.parsers.readers import read_excel_file
from infrastructure.parsers.cleaners import clean_dataframe
from infrastructure.database.database import connect_teradata, load_to_teradata
from ui.components import load_templates
from modules.calidad.use_cases.phases.phase1_ingest_insight import _get_selections_from_template

logger = logging.getLogger(__name__)


def _is_valid_verint_file(fpath: str) -> bool:
    try:
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 1000:
            return False
        with open(fpath, "rb") as fp:
            header = fp.read(8)
        return header.startswith(b"PK\x03\x04") or header.startswith(b"\xd0\xcf\x11\xe0")
    except Exception:
        return False


def run_phase2(ctx) -> bool:
    """
    Fase 2: Descarga e ingesta de Speech Analytics Verint a Teradata.
    Mutará ctx.downloaded_verint_files con la lista de archivos procesados.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log(f"🚀 Fase 2 iniciando: Descarga e Ingesta de Speech Analytics Verint ({ctx.period_str})...", "info")

    templates = load_templates()
    input_dir = ctx.input_dir
    today_date = datetime.date.today()

    # Detectar archivos ya descargados hoy
    all_files = sorted(glob.glob(os.path.join(input_dir, "Export_Calidad_*.xlsx")))
    if not all_files:
        all_files = sorted(glob.glob(os.path.join(input_dir, "Export_Calidad_*.xls")))

    existing_verint_files = [
        f for f in all_files
        if datetime.date.fromtimestamp(os.path.getmtime(f)) == today_date and _is_valid_verint_file(f)
    ]

    if existing_verint_files:
        downloaded_verint_files = existing_verint_files
        log(f"ℹ️ Archivos Verint descargados hoy detectados ({len(downloaded_verint_files)} archivo(s)). Omitiendo descarga.", "info")
    else:
        # Preparar credenciales para el cliente API
        verint_user = ctx.verint_user or os.getenv("VERINT_USER", "")

        anio_p = int(ctx.period_str[:4])
        mes_p = int(ctx.period_str[4:6])
        m_next = 1 if mes_p == 12 else mes_p + 1
        y_next = anio_p + 1 if mes_p == 12 else anio_p
        from_iso = f"{anio_p:04d}-{mes_p:02d}-01T00:00:00.000"
        to_iso = f"{y_next:04d}-{m_next:02d}-01T00:00:00.000"

        try:
            log("⚡ Intentando descarga ultrarrápida de Verint vía API REST...", "info")
            from modules.verint.services.verint_api_client import VerintAPIClient
            from modules.verint.services.verint_utils import find_input_csv

            csv_path = find_input_csv(ctx.period_str)
            api_client = VerintAPIClient(username=verint_user)
            res_file = api_client.export_televentas_period(
                from_iso=from_iso,
                to_iso=to_iso,
                csv_filepath=csv_path,
                output_dir=input_dir,
                poll_interval_seconds=60,
                timeout_minutes=35,
                stop_checker=ctx.stop_checker
            )
            if res_file:
                downloaded_verint_files = [
                    f.strip() for f in res_file.split(",")
                    if f.strip() and os.path.exists(f.strip())
                ]
                log(f"⚡ ¡Descarga vía API completada ({len(downloaded_verint_files)} archivo(s))!", "success")
            else:
                downloaded_verint_files = []
        except Exception as api_err:
            import traceback as _tb
            from infrastructure.system.logging_config import LOG_DIR
            _err_detail = f"{type(api_err).__name__}: {api_err}"
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            log_file_hint = LOG_DIR / f"proceso_calidad_{date_str}.log"
            logger.error(f"Fallo en API REST de Verint. {_err_detail}\n{_tb.format_exc()}")
            log(f"❌ Fallo crítico en API REST de Verint: {_err_detail} (Detalles en: {log_file_hint})", "error")
            raise RuntimeError(f"Fallo en descarga por API de Verint: {api_err}") from api_err

    if not downloaded_verint_files:
        raise ValueError("No se obtuvieron archivos desde la descarga de Verint.")

    ctx.downloaded_verint_files = downloaded_verint_files

    # Cargar en Teradata
    template_verint = templates.get("P001-CALIDAD_SA", {})
    if not template_verint:
        raise ValueError("No se encontró la plantilla P001-CALIDAD_SA en plantillas.json.")

    log(f"🧹 Cargando {len(downloaded_verint_files)} archivo(s) de Verint a Teradata...", "info")
    con = connect_teradata(ctx.td_user, ctx.td_password, host=ctx.host, logmech=ctx.logmech)
    try:
        clear_table = True
        for file_path in downloaded_verint_files:
            filename = os.path.basename(file_path)
            log(f"📂 Procesando archivo Verint: {filename}...", "info")

            df_verint = read_excel_file(file_path, selected_template="P001-CALIDAD_SA", templates=templates)
            if df_verint.is_empty():
                log(f"⚠️ El archivo '{filename}' no contiene registros. Se omitirá.", "warning")
                continue

            selections_verint = _get_selections_from_template(df_verint, template_verint)
            df_verint_clean = clean_dataframe(
                df_verint, selections_verint,
                convertir_sin_acentos=True, transformar_varchar_latin=False, max_len_varchar=3000
            )

            log(f"🚀 Subiendo a DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS (Vaciar={clear_table})...", "info")
            load_to_teradata(
                con=con, table_name="DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS",
                df=df_verint_clean, selected_columns_config=selections_verint,
                clear_table=clear_table, progress_callback=ctx.progress_callback
            )
            clear_table = False

        log("🏁 Fase 2 concluida exitosamente: Speech Analytics Verint cargado en Teradata.", "success")
        return True
    finally:
        try:
            con.close()
        except Exception:
            pass
