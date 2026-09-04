"""
PowerBI Connector Service
Escribe el timestamp de actualización en el archivo conector de Power BI
correspondiente a cada módulo (calidad, consumo, etc.).
"""
import os
import datetime
import logging
from pathlib import Path

logger = logging.getLogger("powerbi_connector")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_powerbi_dir() -> Path:
    """
    Resuelve dinámicamente el directorio 'POWER BI'.
    1. Prioridad: Carpeta 'POWER BI' al mismo nivel de la raíz del proyecto (hermana de APP_CALIDAD).
    2. Variable de entorno 'POWER_BI_DIR' si está configurada.
    3. Fallback en OneDrive - Interbank.
    """
    env_dir = os.getenv("POWER_BI_DIR")
    if env_dir:
        return Path(env_dir)

    sibling_dir = PROJECT_ROOT.parent / "POWER BI"
    if sibling_dir.exists():
        return sibling_dir

    user_home = Path.home()
    env_onedrive = os.getenv("ONEDRIVE_DIR")
    candidates = [
        Path(env_onedrive) / "Televentas" / "POWER BI" if env_onedrive else None,
        user_home / "OneDrive - Interbank" / "Televentas" / "POWER BI",
        user_home / "OneDrive" / "Televentas" / "POWER BI",
        user_home / "Interbank" / "Televentas" / "POWER BI",
    ]
    for c in candidates:
        if c and c.exists():
            return c

    return sibling_dir


def write_powerbi_timestamp(filename: str) -> None:
    """
    Escribe la hora actual en el archivo de conector correspondiente de Power BI.
    Llamar al finalizar exitosamente el procesamiento SQL de cada módulo.

    Args:
        filename: Nombre del archivo conector, ej: 'conector_calidad.txt'
    """
    try:
        target_dir = get_powerbi_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        logger.info(f"Timestamp escrito en {target_path}")
    except Exception as err:
        logger.warning(f"No se pudo escribir timestamp en '{filename}': {err}")
