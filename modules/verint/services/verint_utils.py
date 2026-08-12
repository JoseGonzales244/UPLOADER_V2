import os
import csv
import logging
from pathlib import Path
import teradatasql
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("verint_utils")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def load_teradata_config():
    env_user = os.getenv("TERADATA_USER")
    env_password = os.getenv("TERADATA_PASSWORD")
    env_host = os.getenv("TERADATA_HOST")
    env_logmech = os.getenv("TERADATA_LOGMECH")

    if not env_user or not env_password:
        raise ValueError(
            "Faltan credenciales de Teradata. "
            "Verifica TERADATA_USER y TERADATA_PASSWORD en el archivo .env"
        )

    return {
        "teradata_user": env_user,
        "teradata_password": env_password,
        "teradata_host": env_host or "IBKTD",
        "teradata_logmech": env_logmech or "LDAP"
    }

def generate_ev_csv_from_teradata(period):
    """
    Executes Teradata SELECT and creates EV_yyyymm.csv in data/input/proceso_calidad.
    """
    target_dir = os.path.join(BASE_DIR, "data", "input", "proceso_calidad")
    os.makedirs(target_dir, exist_ok=True)
    output_filename = f"EV_{period}.csv"
    output_path = os.path.join(target_dir, output_filename)

    td_config = load_teradata_config()

    query = """
        SELECT DISTINCT REG_EJECUTIVO
        FROM DLAB_GEC.M_EXP_TELEVENTAS_EJECUTIVOS
    """

    logger.info("Connecting to Teradata to generate EV CSV...")
    logger.info(f"Output CSV will be created at: {output_path}")

    rows = []

    try:
        with teradatasql.connect(
            host=td_config["teradata_host"],
            user=td_config["teradata_user"],
            password=td_config["teradata_password"],
            logmech=td_config["teradata_logmech"]
        ) as con:
            with con.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

    except Exception as e:
        logger.error(f"Error querying Teradata: {e}")
        raise

    if not rows:
        raise ValueError(
            "El SELECT de Teradata no devolvió registros para REG_EJECUTIVO."
        )

    with open(output_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["REG_EJECUTIVO"])
        for row in rows:
            writer.writerow([row[0]])

    logger.info(f"Generated CSV successfully: {output_path}")
    logger.info(f"Total executives exported: {len(rows)}")

    return output_path

def find_input_csv(period):
    """
    Finds the local input CSV file for agent IDs in data/input/proceso_calidad.
    If EV_yyyymm.csv does not exist, generates it from Teradata.
    """
    target_dir = os.path.join(BASE_DIR, "data", "input", "proceso_calidad")
    os.makedirs(target_dir, exist_ok=True)
    expected_filename = f"EV_{period}.csv"
    expected_path = os.path.join(target_dir, expected_filename)
    root_fallback_path = os.path.join(BASE_DIR, expected_filename)

    if os.path.exists(expected_path):
        logger.info(f"Found exact input CSV file: {expected_path}")
        return expected_path
    elif os.path.exists(root_fallback_path):
        logger.info(f"Found input CSV file at root fallback: {root_fallback_path}")
        return root_fallback_path

    logger.warning(f"Exact CSV file {expected_filename} not found in {target_dir}.")
    logger.info("Generating EV CSV from Teradata into data/input/proceso_calidad...")

    try:
        generated_path = generate_ev_csv_from_teradata(period)
        if os.path.exists(generated_path):
            logger.info(f"Using generated input CSV file: {generated_path}")
            return generated_path
    except Exception as e:
        logger.error(f"Failed to generate EV CSV: {e}")
        raise

    raise FileNotFoundError(
        f"No se pudo localizar ni generar {expected_filename} en {target_dir} o en {BASE_DIR}"
    )
