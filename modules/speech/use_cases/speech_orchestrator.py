import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pyodbc
from dotenv import load_dotenv
import teradatasql

from modules.speech.services.insight_lead_service import InsightLeadService
from modules.verint.transcripciones.extractors.verint_transcript_extractor import (
    initialize_verint_session,
    extract_single_transcript_in_session
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("SpeechOrchestrator")



def get_speech_sqlserver_connection() -> pyodbc.Connection:
    """Establece conexión con el SQL Server destino de DB_SPEECH."""
    server = os.getenv("SPEECH_SQLSERVER_SERVER") or os.getenv("SQLSERVER_SERVER")
    database = os.getenv("SPEECH_SQLSERVER_DATABASE") or "DB_SPEECH"
    user = os.getenv("SPEECH_SQLSERVER_USER") or os.getenv("SQLSERVER_USER")
    password = os.getenv("SPEECH_SQLSERVER_PASSWORD") or os.getenv("SQLSERVER_PASSWORD")
    driver = os.getenv("SPEECH_SQLSERVER_DRIVER") or os.getenv("SQLSERVER_DRIVER", "{ODBC Driver 17 for SQL Server}")

    if not server or server in ("tu_servidor_sql", "tu_servidor_sql_speech"):
        raise ValueError("Configura 'SPEECH_SQLSERVER_SERVER' en el archivo .env")

    if user and password and user not in ("tu_usuario", "tu_usuario_speech"):
        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password}"
    else:
        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"

    return pyodbc.connect(conn_str)


def ensure_speech_table(conn: pyodbc.Connection, table_name: str = "TRANSCRIPCION"):
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
        with conn.cursor() as cur:
            cur.execute(create_sql)
            conn.commit()
        logger.info(f"✓ Tabla '{full_table}' verificada en SQL Server.")
    except Exception as e:
        logger.warning(f"No se pudo verificar DDL automático ({e}). Asumiendo tabla existente.")


def extract_interactions_from_teradata(
    plantilla: str = "Exp. Compra - TC",
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Extrae las interacciones evaluadas desde Teradata DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD."""
    user = os.getenv("TERADATA_USER_SELECT") or os.getenv("TERADATA_USER")
    password = os.getenv("TERADATA_PASSWORD_SELECT") or os.getenv("TERADATA_PASSWORD")
    host = os.getenv("TERADATA_HOST") or "IBKTD"
    logmech = os.getenv("TERADATA_LOGMECH_SELECT") or os.getenv("TERADATA_LOGMECH") or "LDAP"

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

    logger.info(f"Conectando a Teradata ({host}) para extraer llamadas de plantilla '{plantilla}'...")
    records = []
    with teradatasql.connect(host=host, user=user, password=password, logmech=logmech) as con:
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


def extract_transcripts_from_verint(
    call_items: List[Dict[str, Any]],
    output_dir: Path,
    headless: bool = True
) -> Dict[str, str]:
    """
    Descarga los diálogos reutilizando la sesión y extractor estándar de modules/verint.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    transcripts_map = {}

    # Filtrar llamadas que ya tengan archivo .txt descargado
    pending_items = []
    for item in call_items:
        cid = item.get("ID_LLAMADA") or item.get("CONID")
        txt_path = output_dir / f"TRANSCRIPT_{cid}.txt"
        if txt_path.exists() and txt_path.stat().st_size > 0:
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                transcripts_map[cid] = f.read()
        else:
            pending_items.append(item)

    if not pending_items:
        logger.info(f"✓ Todas las {len(call_items)} transcripciones ya existen localmente en {output_dir}.")
        return transcripts_map

    logger.info(f"Iniciando descarga en Verint de {len(pending_items)} transcripciones pendientes (Headless={headless})...")
    playwright, browser, context, page = initialize_verint_session(headless=headless)

    try:
        for idx, item in enumerate(pending_items, 1):
            cid = item.get("ID_LLAMADA") or item.get("CONID")
            metadata = {
                "FECHA_VENTA": item.get("FECHA_LLAMADA"),
                "DNI": item.get("DNI"),
                "REG_EJECUTIVO": item.get("REGISTRO")
            }

            logger.info(f"[{idx}/{len(pending_items)}] Extrayendo transcripción para CONID: {cid}...")
            try:
                txt_path = extract_single_transcript_in_session(
                    page=page,
                    call_id=cid,
                    metadata=metadata,
                    output_dir=str(output_dir)
                )
                if txt_path and os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        transcripts_map[cid] = f.read()
                    logger.info(f"[{idx}/{len(pending_items)}] ✓ Guardado: {txt_path}")
            except Exception as e:
                logger.error(f"[{idx}/{len(pending_items)}] Error extrayendo {cid}: {e}")

            time.sleep(1.5)

    finally:
        try:
            context.close()
            browser.close()
            playwright.stop()
        except Exception:
            pass

    return transcripts_map


def sync_transcripts_pipeline(
    plantilla: str = "Exp. Compra - TC",
    limit: Optional[int] = None,
    output_dir: Optional[Path] = None,
    min_insight_date: str = "2026-07-01",
    skip_sql: bool = False
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline integral:
    1. Extrae interacciones desde Teradata.
    2. Calcula TIPO_LEAD en Insight vía session_summary.
    3. Descarga transcripciones desde Verint.
    4. Carga/Merge masivo en SQL Server DB_SPEECH.TRANSCRIPCION (omitido si skip_sql=True).
    """
    out_dir = output_dir or (PROJECT_ROOT / "data" / "transcripciones_tc")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extracción Teradata
    interactions = extract_interactions_from_teradata(plantilla=plantilla, limit=limit)
    if not interactions:
        logger.warning("No se encontraron registros en Teradata para procesar.")
        return {"total": 0, "uploaded": 0}

    conid_list = [item["ID_LLAMADA"] for item in interactions]

    # 2. Consulta TIPO_LEAD en Insight
    logger.info("Calculando TIPO_LEAD en Insight...")
    insight_service = InsightLeadService()
    try:
        lead_map = insight_service.get_tipos_lead_batch(conid_list, min_date=min_insight_date)
    except Exception as e:
        logger.error(f"Error consultando Insight: {e}. Se asignará 'NO_MAPEADO'.")
        lead_map = {}

    # 3. Descarga de Transcripciones Verint
    transcripts_map = extract_transcripts_from_verint(interactions, output_dir=out_dir)


    if skip_sql:
        logger.info("⏭️ Flag '--skip-sql' activo: Omitiendo carga en SQL Server.")
        logger.info(f"📁 Transcripciones guardadas en: {out_dir}")
        return {
            "total_extraidos": len(interactions),
            "total_transcritos": len(transcripts_map),
            "total_tipos_lead": len(lead_map),
            "total_sincronizados": 0,
            "skip_sql": True
        }

    # 4. Consolidación y Carga en SQL Server
    logger.info("Iniciando carga a SQL Server DB_SPEECH.TRANSCRIPCION...")
    conn = get_speech_sqlserver_connection()
    ensure_speech_table(conn, table_name="TRANSCRIPCION")

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

    records_to_insert = []
    for item in interactions:
        cid = item["ID_LLAMADA"]
        transcript_text = transcripts_map.get(cid, "")
        tipo_lead = lead_map.get(cid, "NO_MAPEADO")

        records_to_insert.append((
            cid,
            item["PRODUCTO"],
            item["FECHA_LLAMADA"],
            item["DNI"],
            item["REGISTRO"],
            tipo_lead,
            transcript_text
        ))

    uploaded_count = 0
    with conn.cursor() as cur:
        batch_size = 200
        for i in range(0, len(records_to_insert), batch_size):
            chunk = records_to_insert[i:i + batch_size]
            cur.executemany(upsert_sql, chunk)
            conn.commit()
            uploaded_count += len(chunk)
            logger.info(f"Progreso carga SQL Server: {uploaded_count}/{len(records_to_insert)}...")

    conn.close()
    logger.info(f"✅ Pipeline completado exitosamente: {uploaded_count} registros sincronizados en DB_SPEECH.TRANSCRIPCION.")

    return {
        "total_extraidos": len(interactions),
        "total_transcritos": len(transcripts_map),
        "total_tipos_lead": len(lead_map),
        "total_sincronizados": uploaded_count
    }
