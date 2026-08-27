"""
Implementación concreta de ITeradataRepository para interacción con Teradata.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from dotenv import load_dotenv

from domain.interfaces.database_repository import ITeradataRepository
from infrastructure.database.database import load_credentials, connect_teradata
from infrastructure.database.sql_executor import split_sql_statements

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("TeradataRepository")


class TeradataRepository(ITeradataRepository):
    """Repositorio para ejecutar consultas y extracción de datos en Teradata."""

    def __init__(
        self,
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        logmech: Optional[str] = None
    ):
        creds = load_credentials() if not (user and password) else {}
        self.host = host or os.getenv("TERADATA_HOST") or creds.get("teradata_host", "IBKTD")
        self.user = user or os.getenv("TERADATA_USER_SELECT") or os.getenv("TERADATA_USER") or creds.get("teradata_user")
        self.password = password or os.getenv("TERADATA_PASSWORD_SELECT") or os.getenv("TERADATA_PASSWORD") or creds.get("teradata_password")
        self.logmech = logmech or os.getenv("TERADATA_LOGMECH_SELECT") or os.getenv("TERADATA_LOGMECH") or creds.get("teradata_logmech", "TD2")

    def _get_connection(self):
        """Crea y retorna una conexión activa hacia Teradata."""
        import teradatasql
        return teradatasql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            logmech=self.logmech
        )

    def extract_interactions(
        self,
        plantilla: str = "Exp. Compra - TC",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Extrae interacciones desde DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD."""
        top_clause = f"TOP {limit}" if limit else ""
        query = f"""
        SELECT DISTINCT {top_clause}
            TRIM(CONID) AS CONID,
            'TC' AS PRODUCTO,
            CAST(FECHA_VENTA AS DATE) AS FECHA_LLAMADA,
            TRIM(DNI) AS DNI,
            TRIM(REG_EJECUTIVO) AS REGISTRO
        FROM DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD
        WHERE PLANTILLA = '{plantilla}'
          AND CONID IS NOT NULL
          AND CONID <> ''
        """

        logger.info(f"Conectando a Teradata ({self.host}) para extraer llamadas de plantilla '{plantilla}'...")
        records = []
        with self._get_connection() as con:
            with con.cursor() as cur:
                cur.execute(query)
                cols = [desc[0].upper() for desc in cur.description]
                for row in cur.fetchall():
                    row_dict = dict(zip(cols, row))
                    records.append({
                        "ID_LLAMADA": str(row_dict.get("CONID") or "").strip(),
                        "PRODUCTO": str(row_dict.get("PRODUCTO") or "TC").strip(),
                        "FECHA_LLAMADA": str(row_dict.get("FECHA_LLAMADA") or "").strip(),
                        "DNI": str(row_dict.get("DNI") or "").strip(),
                        "REGISTRO": str(row_dict.get("REGISTRO") or "").strip()
                    })

        logger.info(f"✓ {len(records)} interacciones extraídas desde Teradata.")
        return records

    def execute_script(
        self,
        sql_text: str,
        params: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> bool:
        """Ejecuta un script SQL multi-sentencia en Teradata."""
        def log(msg, level="info"):
            if level == "error":
                logger.error(msg)
            else:
                logger.info(msg)
            if progress_callback:
                progress_callback(msg, level)

        if params:
            for k, v in params.items():
                sql_text = sql_text.replace(f"{{{k}}}", str(v)).replace(f":{k}", str(v))

        statements = split_sql_statements(sql_text)
        with self._get_connection() as con:
            with con.cursor() as cur:
                for idx, stmt in enumerate(statements, 1):
                    log(f"  - Ejecutando sentencia {idx}/{len(statements)}", "info")
                    cur.execute(stmt)
        return True
