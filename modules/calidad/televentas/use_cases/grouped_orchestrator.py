import os
import sys
import re
import glob
import logging
import argparse
from pathlib import Path

# Garantizar resolución de la raíz del proyecto en sys.path
root_dir = Path(__file__).resolve().parents[4]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from infrastructure.database.database import load_credentials, connect_teradata, load_to_teradata
from infrastructure.parsers.readers import read_excel_file
from infrastructure.parsers.cleaners import clean_dataframe
from ui.components import load_templates

logger = logging.getLogger(__name__)

user_home = os.path.expanduser("~")
ONEDRIVE_DIRS = [
    os.path.join(user_home, "OneDrive - Interbank", "Televentas"),
    os.path.join(user_home, "OneDrive", "Televentas"),
]

SQL_SCRIPT_PATH = Path(__file__).parent.parent / "sql" / "01_proceso_televentas_grouped.sql"


def parse_sql_statements(sql_text: str) -> list:
    """
    Limpia comentarios y separa sentencias SQL respetando cadenas.
    """
    sql_cleaned = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
    lines = []
    for line in sql_cleaned.split('\n'):
        line_clean = re.sub(r'--.*$', '', line)
        if line_clean.strip():
            lines.append(line_clean)
    full_clean = '\n'.join(lines)
    statements = [stmt.strip() for stmt in full_clean.split(';') if stmt.strip()]
    return statements


def check_period_exists_in_grouped(con, periodo: str) -> bool:
    """
    Verifica si el periodo existe en DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED.
    """
    cur = con.cursor()
    query = f"SELECT COUNT(*) FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED WHERE TRIM(PERIODO) = '{periodo.strip()}'"
    cur.execute(query)
    row = cur.fetchone()
    cur.close()
    return (row is not None and row[0] > 0)


def check_period_exists_in_p021(con, periodo: str) -> bool:
    """
    Verifica si el periodo existe en la tabla origen DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS.
    """
    cur = con.cursor()
    query = f"SELECT COUNT(*) FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS WHERE TRIM(PERIODO) = '{periodo.strip()}'"
    cur.execute(query)
    row = cur.fetchone()
    cur.close()
    return (row is not None and row[0] > 0)


def find_and_ingest_p021_from_onedrive(periodo: str, progress_callback=None) -> bool:
    """
    Busca en las rutas de OneDrive el archivo Excel P021 para el periodo y lo ingesta a Teradata.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    log(f"🔎 Buscando archivo P021 para el periodo {periodo} en carpetas de OneDrive...", "info")

    excel_file = None
    for base_dir in ONEDRIVE_DIRS:
        if not os.path.exists(base_dir):
            continue
        # Patrones de búsqueda comunes
        patterns = [
            os.path.join(base_dir, f"*{periodo}*.xlsx"),
            os.path.join(base_dir, f"*TELEVENTAS*{periodo}*.xlsx"),
            os.path.join(base_dir, f"*EJECUTIVOS*{periodo}*.xlsx"),
            os.path.join(base_dir, "**", f"*{periodo}*.xlsx"),
        ]
        for pat in patterns:
            matches = glob.glob(pat, recursive=True)
            if matches:
                # Filtrar temporales ~$
                valid_matches = [m for m in matches if not os.path.basename(m).startswith("~$")]
                if valid_matches:
                    excel_file = valid_matches[0]
                    break
        if excel_file:
            break

    if not excel_file:
        log(f"⚠️ No se encontró ningún archivo P021 para el periodo {periodo} en OneDrive.", "warning")
        return False

    log(f"📄 Archivo encontrado en OneDrive: {excel_file}. Iniciando ingesta P021...", "info")

    try:
        templates = load_templates()
        selected_template = "P021-TELEVENTAS_EJECUTIVOS"
        df = read_excel_file(excel_file, selected_template=selected_template, templates=templates)

        template_config = templates.get(selected_template, {})
        selections = []
        for orig_col, cfg in template_config.items():
            if isinstance(cfg, dict) and cfg.get("Añadir", False):
                selections.append({
                    "orig": orig_col,
                    "new_name": cfg.get("Nuevo nombre", orig_col),
                    "type": cfg.get("Tipo de dato", "VARCHAR(255)"),
                    "not_null": cfg.get("Null:0/No Null:1", False)
                })

        df_clean = clean_dataframe(
            df,
            selections=selections,
            convertir_sin_acentos=True,
            transformar_varchar_latin=False,
            max_len_varchar=255
        )

        credenciales = load_credentials()
        host = credenciales.get('teradata_host', 'IBKTD')
        logmech = credenciales.get('teradata_logmech', 'TD2')
        user = credenciales.get('teradata_user', '')
        pwd = credenciales.get('teradata_password', '')
        con = connect_teradata(user, pwd, host=host, logmech=logmech)

        load_to_teradata(
            con,
            "DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS",
            df_clean,
            selections,
            clear_table=False,
            progress_callback=progress_callback
        )
        con.close()
        log(f"✅ Ingesta de P021 desde OneDrive completada exitosamente para periodo {periodo}.", "success")
        return True
    except Exception as err:
        log(f"❌ Error durante la ingesta automática de P021 desde OneDrive: {err}", "error")
        return False


def process_televentas_grouped(periodo: str, force_reprocess: bool = False, progress_callback=None) -> bool:
    """
    Ejecuta la agrupación e inserción en DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED.
    Si force_reprocess=True (modo manual de corrección), ejecuta un DELETE del periodo antes de procesar.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    periodo_str = periodo.strip()
    log(f"🚀 Iniciando procesamiento de TELEVENTAS_EJECUTIVOS_GROUPED para periodo {periodo_str}...", "info")

    if not SQL_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"No se encontró el script SQL en {SQL_SCRIPT_PATH}")

    with open(SQL_SCRIPT_PATH, "r", encoding="utf-8") as fh:
        sql_raw = fh.read()

    sql_injected = sql_raw.replace("{PERIODO}", periodo_str)
    statements = parse_sql_statements(sql_injected)

    credenciales = load_credentials()
    host = credenciales.get('teradata_host', 'IBKTD')
    logmech = credenciales.get('teradata_logmech', 'TD2')
    user = credenciales.get('teradata_user', '')
    pwd = credenciales.get('teradata_password', '')
    con = connect_teradata(user, pwd, host=host, logmech=logmech)
    cur = con.cursor()

    try:
        if force_reprocess:
            log(f"🧹 Modo Corrección Manual: Eliminando datos previos del periodo {periodo_str} en GROUPED...", "info")
            delete_stmt = f"DELETE FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED WHERE TRIM(PERIODO) = '{periodo_str}'"
            cur.execute(delete_stmt)

        total_stmt = len(statements)
        for idx, stmt in enumerate(statements, start=1):
            cur.execute(stmt)

        con.close()
        log(f"🎉 Procesamiento de TELEVENTAS_EJECUTIVOS_GROUPED completado para periodo {periodo_str}.", "success")
        return True
    except Exception as err:
        con.close()
        log(f"❌ Error ejecutando sentencias de GROUPED: {err}", "error")
        raise err


def ensure_grouped_data_for_period(periodo: str, progress_callback=None) -> bool:
    """
    Manejador automático de pre-vuelo (Guardrail):
    1. Si el periodo ya está en GROUPED -> Usa la data existente y continúa.
    2. Si NO está en GROUPED -> Revisa si está en P021 Teradata. Si tampoco está en P021, lo descarga e ingesta desde OneDrive.
    3. Llena GROUPED mediante INSERT directo y continúa.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    periodo_str = periodo.strip()

    credenciales = load_credentials()
    host = credenciales.get('teradata_host', 'IBKTD')
    logmech = credenciales.get('teradata_logmech', 'TD2')
    user = credenciales.get('teradata_user', '')
    pwd = credenciales.get('teradata_password', '')
    con = connect_teradata(user, pwd, host=host, logmech=logmech)

    try:
        # 1. Comprobar si ya existe en GROUPED
        if check_period_exists_in_grouped(con, periodo_str):
            con.close()
            log(f"✅ El período {periodo_str} ya existe en TELEVENTAS_EJECUTIVOS_GROUPED. Usando data existente.", "success")
            return True

        # 2. Si no existe en GROUPED, verificar P021
        p021_exists = check_period_exists_in_p021(con, periodo_str)
        con.close()

        if not p021_exists:
            log(f"⚠️ El período {periodo_str} no existe en la tabla P021 de Teradata. Buscando en OneDrive...", "warning")
            ingested = find_and_ingest_p021_from_onedrive(periodo_str, progress_callback=progress_callback)
            if not ingested:
                error_msg = f"❌ ALERTA CRÍTICA: El período {periodo_str} no existe en M_EXP_TELEVENTAS_EJECUTIVOS_GROUPED, tampoco en P021 (Teradata), ni se encontró el archivo Excel correspondiente en OneDrive. Proceso detenido."
                log(error_msg, "error")
                raise RuntimeError(error_msg)

        # 3. Insertar datos del periodo en GROUPED (Primera vez)
        process_televentas_grouped(periodo_str, force_reprocess=False, progress_callback=progress_callback)
        return True

    except Exception as err:
        log(f"💥 Fallo en la verificación/carga de TELEVENTAS_EJECUTIVOS_GROUPED: {err}", "error")
        raise err


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesar TELEVENTAS_EJECUTIVOS_GROUPED")
    parser.add_argument("--periodo", "--PERIODO", dest="periodo", required=True, help="Periodo en formato YYYYMM (ejemplo: 202608)")
    parser.add_argument("--force", "--FORCE", dest="force", action="store_true", help="Forzar reprocesamiento (elimina y reprocesa el periodo)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    def progress_cb(msg, level="info"):
        print(f"[{level.upper()}] {msg}")

    if args.force:
        process_televentas_grouped(args.periodo, force_reprocess=True, progress_callback=progress_cb)
    else:
        ensure_grouped_data_for_period(args.periodo, progress_callback=progress_cb)

