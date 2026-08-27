import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.verint.services.verint_api_client import VerintAPIClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_verint_transcript_api")

def test_verint_transcript_by_call_id(call_id: str):
    load_dotenv()
    user = os.getenv("VERINT_USER")
    pwd = os.getenv("VERINT_PASS")
    
    logger.info(f"=== Test Extracción Transcripción Verint API Directa ===")
    logger.info(f"Target CONID: {call_id}")
    
    if not user or not pwd:
        logger.error("Faltan VERINT_USER o VERINT_PASS en .env")
        return

    client = VerintAPIClient(username=user, password=pwd)
    if not client.login():
        logger.error("Error en login de Verint API")
        return
        
    client.init_speech_session(instance_id=247115)
    
    # 1. Crear QDI XML buscando el CONID
    qdi_xml = f"""<QDI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <QueryType>Session</QueryType>
  <DataSource>Unified</DataSource>
  <Direction>Full</Direction>
  <Fields>
    <Field xsi:type="QDIFieldExtended">
      <Values>
        <Value>{call_id}</Value>
      </Values>
      <SessionName>
        <FieldID>5</FieldID>
        <Name>CUSTOM_DATA_STRING</Name>
      </SessionName>
      <Operator>contains</Operator>
      <FieldRelation>Segment</FieldRelation>
    </Field>
  </Fields>
</QDI>"""

    client.set_filter_as_search(qdi_xml, instance_id=247115)
        
    # 2. Obtener metadatos del contacto desde GetContactsResultSet
    contacts_res = client.get_contacts_result_set(limit=10, page=1)
    data_obj = contacts_res.get("Data", {})
    contacts_list = data_obj.get("Contacts", []) if isinstance(data_obj, dict) else []
    
    if not contacts_list:
        logger.error(f"No se hallaron contactos en Verint para CONID={call_id}")
        return

    contact = contacts_list[0]
    logger.info(f"✓ Contacto hallado: {contact.get('Agent')} | DbsId: {contact.get('DbsId')} | Sid: {contact.get('Sid') or contact.get('DocumentId')}")
    logger.info(f"Metadatos completos del contacto:\n{json.dumps(contact, indent=2)}")

    # 3. Invocación directa del endpoint TranscriptionService.svc/GetInteractionTranscription
    url = f"{client.base_url}/SpeechAnalytics/Services/Transcription/TranscriptionService.svc/GetInteractionTranscription"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-requested-with": "XMLHttpRequest"
    }
    if client.xsrf_token:
        headers["xsrfToken"] = client.xsrf_token
        headers["impact360authtoken"] = client.xsrf_token

    db_sid = contact.get("DbsId", 247)
    sid_val = int(contact.get("Sid") or contact.get("DocumentId") or 0)
    channel_val = contact.get("Channel", 0) or contact.get("ChannelId", 0) or 258758270
    start_time_val = contact.get("StartTime") or contact.get("StartTimeUTC") or "2026-07-16T22:04:48.977Z"

    payload = {
        "instanceContext": {
            "InstanceId": 247115,
            "ApplicationId": "c6b76d91-5291-4928-f3ec-b97a8d2921b3"
        },
        "channel": channel_val,
        "module": 999502,
        "startTime": start_time_val,
        "localDate": start_time_val[:10] + "T00:00:00.000Z",
        "categoriesIds": [],
        "queryTerms": "",
        "editCategory": None,
        "language": "es-ES",
        "transactionId": "2157019040984375478048370989227333246",
        "docId": None,
        "isDocumentMarkingLayersRequeire": False,
        "isRedactionDisabled": False,
        "hideTranscriptionWrapperViewOn": False,
        "isOutOfSpeechContext": False,
        "dbSid": db_sid,
        "sid": sid_val,
        "redactionStatus": 0
    }

    logger.info(f"\n--- Invocando GetInteractionTranscription ---")
    res = client.session.post(url, json=payload, headers=headers)
    logger.info(f"Status Code: {res.status_code}")
    
    if res.status_code == 200:
        res_data = res.json()
        logger.info(f"🎯 ¡ÉXITO TOTAL! Transcripción recibida ({len(str(res_data))} bytes)")
        
        result_obj = res_data.get("GetInteractionTranscriptionResult", {})
        data_obj = result_obj.get("Data", {})
        sequences = data_obj.get("WordsSequences", [])
        
        transcript_lines = []
        for seq in sequences:
            speaker_raw = seq.get("SpeakerName", "")
            speaker = "Asesor" if speaker_raw == "Agent" else ("Cliente" if speaker_raw == "Customer" else speaker_raw)
            start_ms = seq.get("StartTime", 0)
            total_sec = int(start_ms) // 1000
            mins = total_sec // 60
            secs = total_sec % 60
            ts_str = f"{mins:02d}:{secs:02d}"
            
            words_list = [w.get("WordText", "") for w in seq.get("Words", []) if w.get("WordText")]
            text = " ".join(words_list)
            if text:
                transcript_lines.append(f"[{ts_str}] {speaker}: {text}")
                
        formatted_transcript = "\n".join(transcript_lines)
        logger.info(f"\n=================== TRANSCRIPCIÓN EXTRAÍDA (TOTAL LÍNEAS: {len(transcript_lines)}) ===================")
        logger.info(f"\n{formatted_transcript[:2500]}\n...")
        logger.info(f"====================================================================================================")
    else:
        logger.error(f"Fallo al obtener transcripción ({res.status_code}): {res.text[:1000]}")

if __name__ == "__main__":
    target_conid = "bc6ca477-e5f0-42fa-8eb1-f1605dc933c2"
    test_verint_transcript_by_call_id(target_conid)
