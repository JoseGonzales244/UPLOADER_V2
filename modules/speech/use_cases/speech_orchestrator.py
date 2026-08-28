import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from domain.interfaces.database_repository import ITeradataRepository, ISpeechDbRepository
from infrastructure.database.repositories.teradata_repository import TeradataRepository
from infrastructure.database.repositories.speech_repository import SpeechDbRepository
from modules.speech.services.insight_lead_service import InsightLeadService
from modules.verint.services.verint_api_client import VerintAPIClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("SpeechOrchestrator")


def extract_interactions_from_teradata(
    plantilla: str = "Exp. Compra - TC",
    limit: Optional[int] = None,
    teradata_repo: Optional[ITeradataRepository] = None
) -> List[Dict[str, Any]]:
    """Extrae las interacciones evaluadas delegando en ITeradataRepository."""
    repo = teradata_repo or TeradataRepository()
    return repo.extract_interactions(plantilla=plantilla, limit=limit)


def extract_transcripts_from_verint(
    call_items: List[Dict[str, Any]],
    output_dir: Path,
    headless: bool = True
) -> Dict[str, str]:
    """
    Descarga los diálogos utilizando el cliente HTTP API REST directo de Verint (rápido y sin navegador).
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

    logger.info(f"Iniciando descarga en Verint API de {len(pending_items)} transcripciones pendientes...")
    api_client = VerintAPIClient()
    api_client.login()
    api_client.init_speech_session()

    try:
        for idx, item in enumerate(pending_items, 1):
            cid = item.get("ID_LLAMADA") or item.get("CONID")
            txt_path = output_dir / f"TRANSCRIPT_{cid}.txt"
            logger.info(f"[{idx}/{len(pending_items)}] Extrayendo transcripción por API para CONID: {cid}...")
            try:
                res_json = api_client.get_interaction_transcription_api(cid)
                if res_json:
                    formatted_text = api_client.format_dialogue(res_json)
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(formatted_text)
                    transcripts_map[cid] = formatted_text
                    logger.info(f"[{idx}/{len(pending_items)}] ✓ Guardado por API: {txt_path}")
                else:
                    logger.warning(f"[{idx}/{len(pending_items)}] ⚠️ Sin contenido de transcripción para CONID: {cid}")
            except Exception as e:
                logger.error(f"[{idx}/{len(pending_items)}] Error extrayendo {cid} vía API: {e}")
    finally:
        api_client.close()

    return transcripts_map


def sync_transcripts_pipeline(
    plantilla: str = "Exp. Compra - TC",
    limit: Optional[int] = None,
    output_dir: Optional[Path] = None,
    min_insight_date: str = "2026-07-01",
    skip_sql: bool = False,
    teradata_repo: Optional[ITeradataRepository] = None,
    speech_repo: Optional[ISpeechDbRepository] = None
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline integral:
    1. Extrae interacciones desde Teradata (vía ITeradataRepository).
    2. Calcula TIPO_LEAD en Insight vía session_summary.
    3. Descarga transcripciones desde Verint.
    4. Carga/Merge masivo en SQL Server DB_SPEECH.TRANSCRIPCION (vía ISpeechDbRepository).
    """
    t_repo = teradata_repo or TeradataRepository()
    s_repo = speech_repo or SpeechDbRepository()

    out_dir = output_dir or (PROJECT_ROOT / "data" / "transcripciones")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extracción Teradata
    interactions = extract_interactions_from_teradata(plantilla=plantilla, limit=limit, teradata_repo=t_repo)
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
    s_repo.ensure_speech_table(table_name="TRANSCRIPCION")

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

    uploaded_count = s_repo.upsert_transcripts(records_to_insert, batch_size=200)
    logger.info(f"✅ Pipeline completado exitosamente: {uploaded_count} registros sincronizados en DB_SPEECH.TRANSCRIPCION.")

    return {
        "total_extraidos": len(interactions),
        "total_transcritos": len(transcripts_map),
        "total_tipos_lead": len(lead_map),
        "total_sincronizados": uploaded_count
    }
