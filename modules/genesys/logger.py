import logging
import sys
from pathlib import Path


def get_logger(name: str = "GenesysBot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Formato uniforme
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Handler a consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler opcional a archivo de log centralizado en la raíz (logs/)
    try:
        from datetime import datetime
        from infrastructure.system.logging_config import LOG_DIR
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(LOG_DIR / f"genesys_bot_{date_str}.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger
