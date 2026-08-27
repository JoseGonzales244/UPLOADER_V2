"""
Implementación concreta de ISpeechDbRepository para SQL Server DB_SPEECH.
"""
import os
import logging
from typing import List, Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

from domain.interfaces.database_repository import ISpeechDbRepository

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("SpeechDbRepository")


class SpeechDbRepository(ISpeechDbRepository):
    """Repositorio para persistencia y verificación de tablas en SQL Server DB_SPEECH."""

    def __init__(
        self,
        server: Optional[str] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        driver: Optional[str] = None
    ):
        self.server = server or os.getenv("SPEECH_SQLSERVER_SERVER") or os.getenv("SQLSERVER_SERVER")
        self.database = database or os.getenv("SPEECH_SQLSERVER_DATABASE") or "DB_SPEECH"
        self.user = user or os.getenv("SPEECH_SQLSERVER_USER") or os.getenv("SQLSERVER_USER")
        self.password = password or os.getenv("SPEECH_SQLSERVER_PASSWORD") or os.getenv("SQLSERVER_PASSWORD")
        self.driver = driver or os.getenv("SPEECH_SQLSERVER_DRIVER") or os.getenv("SQLSERVER_DRIVER", "{ODBC Driver 17 for SQL Server}")

    def _get_connection(self):
        """Crea y retorna una conexión activa a SQL Server."""
        import pyodbc
        if not self.server or self.server in ("tu_servidor_sql", "tu_servidor_sql_speech"):
            raise ValueError("Configura 'SPEECH_SQLSERVER_SERVER' en el archivo .env")

        if self.user and self.password and self.user not in ("tu_usuario", "tu_usuario_speech"):
            conn_str = f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};UID={self.user};PWD={self.password}"
        else:
            conn_str = f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;"

        return pyodbc.connect(conn_str)

    def ensure_speech_table(self, table_name: str = "TRANSCRIPCION") -> None:
        """Verifica y crea la tabla destino DB_SPEECH.TRANSCRIPCION si no existe."""
        full_table = f"DB_SPEECH.{table_name}" if "." not in table_name else table_name
        create_sql = f"""
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = 'DB_SPEECH' AND t.name = '{table_name}')
        BEGIN
            IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'DB_SPEECH')
            BEGIN
                EXEC('CREATE SCHEMA DB_SPEECH');
            END
            CREATE TABLE {full_table} (
                ID_LLAMADA VARCHAR(100) NOT NULL PRIMARY KEY,
                PRODUCTO VARCHAR(50),
                FECHA_LLAMADA VARCHAR(30),
                DNI VARCHAR(20),
                REGISTRO VARCHAR(30),
                TIPO_LEAD VARCHAR(50),
                TRANSCRIPCION_TEXTO NVARCHAR(MAX),
                CREATED_AT DATETIME DEFAULT GETDATE(),
                UPDATED_AT DATETIME DEFAULT GETDATE()
            );
        END
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_sql)
                    conn.commit()
            logger.info(f"✓ Tabla '{full_table}' verificada en SQL Server.")
        except Exception as e:
            logger.warning(f"No se pudo verificar DDL automático ({e}). Asumiendo tabla existente.")

    def upsert_transcripts(
        self,
        records: List[Tuple[str, str, str, str, str, str, str]],
        batch_size: int = 200
    ) -> int:
        """Ejecuta un MERGE upsert masivo por lotes en DB_SPEECH.TRANSCRIPCION."""
        if not records:
            return 0

        upsert_sql = """
        MERGE DB_SPEECH.TRANSCRIPCION AS target
        USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source (ID_LLAMADA, PRODUCTO, FECHA_LLAMADA, DNI, REGISTRO, TIPO_LEAD, TRANSCRIPCION_TEXTO)
        ON target.ID_LLAMADA = source.ID_LLAMADA
        WHEN MATCHED THEN
            UPDATE SET 
                PRODUCTO = source.PRODUCTO,
                FECHA_LLAMADA = source.FECHA_LLAMADA,
                DNI = source.DNI,
                REGISTRO = source.REGISTRO,
                TIPO_LEAD = source.TIPO_LEAD,
                TRANSCRIPCION_TEXTO = source.TRANSCRIPCION_TEXTO,
                UPDATED_AT = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (ID_LLAMADA, PRODUCTO, FECHA_LLAMADA, DNI, REGISTRO, TIPO_LEAD, TRANSCRIPCION_TEXTO, CREATED_AT, UPDATED_AT)
            VALUES (source.ID_LLAMADA, source.PRODUCTO, source.FECHA_LLAMADA, source.DNI, source.REGISTRO, source.TIPO_LEAD, source.TRANSCRIPCION_TEXTO, GETDATE(), GETDATE());
        """

        uploaded_count = 0
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for i in range(0, len(records), batch_size):
                    chunk = records[i:i + batch_size]
                    cur.executemany(upsert_sql, chunk)
                    conn.commit()
                    uploaded_count += len(chunk)
                    logger.info(f"Progreso carga SQL Server: {uploaded_count}/{len(records)}...")

        logger.info(f"✅ Upsert completado: {uploaded_count} registros sincronizados en DB_SPEECH.TRANSCRIPCION.")
        return uploaded_count
