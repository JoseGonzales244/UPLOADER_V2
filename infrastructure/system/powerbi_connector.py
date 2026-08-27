"""
PowerBI Connector Service
Escribe el timestamp de actualización en el archivo conector de Power BI
correspondiente a cada módulo (calidad, consumo, etc.).
"""
import os
import datetime
import logging

logger = logging.getLogger("powerbi_connector")

POWER_BI_DIR = r"C:\Users\b47756\OneDrive - Interbank\Televentas\POWER BI"


def write_powerbi_timestamp(filename: str) -> None:
    """
    Escribe la hora actual en el archivo de conector correspondiente de Power BI.
    Llamar al finalizar exitosamente el procesamiento SQL de cada módulo.

    Args:
        filename: Nombre del archivo conector, ej: 'conector_calidad.txt'
    """
    try:
        os.makedirs(POWER_BI_DIR, exist_ok=True)
        target_path = os.path.join(POWER_BI_DIR, filename)
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        logger.info(f"Timestamp escrito en {target_path}")
    except Exception as err:
        logger.warning(f"No se pudo escribir timestamp en '{filename}': {err}")
