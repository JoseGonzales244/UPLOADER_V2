"""
=============================================================================
AUDITORÍA FOCALIZADA DE CUMPLIMIENTO: PAGO AUTOMÁTICO TARJETAS DE CRÉDITO
=============================================================================
Archivo Objetivo: 'Solicitud Cumplimiento TC 2026.xlsx'
Item Único Auditado: Ofrecimiento y Aceptación/Rechazo de Pago Automático (PA)
Formato Resultado: 'Cliente no acepta (mm:ss)' | 'Cliente acepta (mm:ss)' | 'No se ofreció Pago Automático'
Logs: 'logs/audit_pago_automatico.log' (Rotativo, detallado por caso con tracebacks)
=============================================================================
"""
import os
import sys
import re
import json
import time
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import openpyxl
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# Asegurar creación del directorio de logs
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "audit_pago_automatico.log"

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configuración de Logging de Doble Canal (Consola UTF-8 + Archivo con traceback completo)
logger = logging.getLogger("AuditPagoAutomatico")
logger.setLevel(logging.INFO)

# Limpiar handlers previos para evitar duplicados
if logger.hasHandlers():
    logger.handlers.clear()

c_handler = logging.StreamHandler(sys.stdout)
c_handler.setLevel(logging.INFO)
c_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
c_handler.setFormatter(c_formatter)
logger.addHandler(c_handler)

f_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
f_handler.setLevel(logging.DEBUG)
f_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s")
f_handler.setFormatter(f_formatter)
logger.addHandler(f_handler)

from modules.verint.services.verint_api_client import VerintAPIClient
from infrastructure.llm.gemini_client import GeminiClient

EXCEL_FILE = PROJECT_ROOT / "Solicitud Cumplimiento TC 2026.xlsx"
BACKUP_FILE = PROJECT_ROOT / "Solicitud Cumplimiento TC 2026_Auditada.xlsx"


class PagoAutomaticoAuditor:
    def __init__(self):
        self.verint_user = os.getenv("VERINT_USER")
        self.verint_pass = os.getenv("VERINT_PASS")
        self.verint_client: Optional[VerintAPIClient] = None
        self.llm_client: Optional[GeminiClient] = None

    def init_services(self) -> bool:
        """Inicializa conexiones a Verint API y cliente LLM con diagnóstico detallado en logs."""
        logger.info("[INIT] Inicializando cliente LLM Gemini...")
        try:
            self.llm_client = GeminiClient(default_model="gemini-2.5-flash")
            logger.info("[INIT] ✓ Cliente LLM Gemini configurado.")
        except Exception as e:
            logger.error(f"[INIT] ❌ No se pudo inicializar GeminiClient: {e}", exc_info=True)

        logger.info("[INIT] Conectando a Verint API...")
        if self.verint_user and self.verint_pass:
            try:
                self.verint_client = VerintAPIClient(username=self.verint_user, password=self.verint_pass)
                if self.verint_client.login():
                    logger.info("[INIT] ✓ Sesión en Verint API activa y autenticada.")
                    return True
                else:
                    logger.error("[INIT] ❌ Fallo en autenticación de Verint API (credenciales inválidas o endpoint inaccesible).")
            except Exception as e:
                logger.error(f"[INIT] ❌ Excepción al conectar con Verint API: {e}", exc_info=True)
        else:
            logger.warning("[INIT] ⚠️ Variables VERINT_USER o VERINT_PASS no configuradas en .env.")
        return False

    def search_verint_by_dni_and_date(self, dni: str, target_date: datetime) -> List[Dict[str, Any]]:
        """
        Busca contactos en Verint filtrando por DNI en CUSTOM_DATA_STRING en el rango +- 3 días.
        Registra detalles en logs para diagnóstico en caso de error.
        """
        if not self.verint_client:
            logger.debug(f"[VERINT_SEARCH] Cliente Verint no inicializado. Omitiendo búsqueda para DNI {dni}.")
            return []

        d_from = (target_date - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00")
        d_to = (target_date + timedelta(days=3)).strftime("%Y-%m-%dT23:59:59")

        qdi_xml = f"""<QDI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <QueryType>Session</QueryType>
  <DataSource>Unified</DataSource>
  <Direction>Full</Direction>
  <UserPreferences>
    <TimeZone>UserTime</TimeZone>
    <AdditionalEvalInfo>NOTHING</AdditionalEvalInfo>
  </UserPreferences>
  <OrderDef>
    <TimeOfDateBegin>00:00:00</TimeOfDateBegin>
    <TimeOfDateEnd>00:00:00</TimeOfDateEnd>
    <From>{d_from}</From>
    <To>{d_to}</To>
    <RefFrom>0001-01-01T00:00:00.0000000+00:00</RefFrom>
    <RefTo>0001-01-01T00:00:00.0000000+00:00</RefTo>
    <OrderDefType>GREATER_LESS_EQUAL</OrderDefType>
    <RangeInDays>0</RangeInDays>
    <FieldRelation>Segment</FieldRelation>
    <TimeOfDayID>-1</TimeOfDayID>
  </OrderDef>
  <Fields>
    <Field xsi:type="QDIFieldExtended">
      <Values>
        <Value>{dni}</Value>
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

        try:
            self.verint_client.init_speech_session(instance_id=247115)
            self.verint_client.set_filter_as_search(qdi_xml, instance_id=247115)
            contacts_res = self.verint_client.get_contacts_result_set(limit=10, page=1)
            data_obj = contacts_res.get("Data", {}) if isinstance(contacts_res, dict) else {}
            contacts_list = data_obj.get("Contacts", []) if isinstance(data_obj, dict) else []
            logger.debug(f"[VERINT_SEARCH] DNI {dni} -> {len(contacts_list)} contacto(s) devuelto(s) por Verint.")
            return contacts_list
        except Exception as e:
            logger.error(f"[VERINT_SEARCH] ❌ Error consultando Verint para DNI {dni}: {e}", exc_info=True)
            return []

    def get_transcript_lines(self, contact: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Invoca TranscriptionService de Verint y devuelve una lista de (timestamp_mm_ss, speaker, text).
        """
        if not self.verint_client:
            return []

        url = f"{self.verint_client.base_url}/SpeechAnalytics/Services/Transcription/TranscriptionService.svc/GetInteractionTranscription"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest"
        }
        if self.verint_client.xsrf_token:
            headers["xsrfToken"] = self.verint_client.xsrf_token
            headers["impact360authtoken"] = self.verint_client.xsrf_token

        db_sid = contact.get("DbsId", 247)
        sid_val = int(contact.get("Sid") or contact.get("DocumentId") or 0)
        channel_val = contact.get("Channel", 0) or contact.get("ChannelId", 0) or 258758270
        start_time_val = contact.get("StartTime") or contact.get("StartTimeUTC") or "2026-04-29T00:00:00.000Z"

        payload = {
            "instanceContext": {
                "InstanceId": 247115,
                "ApplicationId": "c6b76d91-5291-4928-f3ec-b97a8d2921b3"
            },
            "channel": channel_val,
            "module": 999502,
            "startTime": start_time_val,
            "localDate": str(start_time_val)[:10] + "T00:00:00.000Z",
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

        try:
            res = self.verint_client.session.post(url, json=payload, headers=headers, timeout=25)
            if res.status_code == 200:
                res_data = res.json()
                result_obj = res_data.get("GetInteractionTranscriptionResult", {})
                data_obj = result_obj.get("Data", {})
                sequences = data_obj.get("WordsSequences", [])
                
                transcript_tuples = []
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
                        transcript_tuples.append((ts_str, speaker, text))
                logger.info(f"[TRANSCRIPT] ✓ Transcripción obtenida ({len(transcript_tuples)} turnos de diálogo).")
                return transcript_tuples
            else:
                logger.warning(f"[TRANSCRIPT] ⚠️ Error HTTP {res.status_code} en GetInteractionTranscription: {res.text[:300]}")
        except Exception as e:
            logger.error(f"[TRANSCRIPT] ❌ Excepción al invocar TranscriptionService de Verint: {e}", exc_info=True)
        return []

    def evaluate_pago_automatico(self, transcript_tuples: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """
        Evalúa el diálogo enfocado exclusivamente en:
        ¿Se ofreció la afiliación a Pago Automático / Débito Automático?
        ¿El cliente aceptó o rechazó?
        """
        if not transcript_tuples:
            return {
                "estado": "SIN_TRANSCRIPCION",
                "timestamp": None,
                "resultado_formateado": "REVISIÓN MANUAL PENDIENTE",
                "cita": ""
            }

        full_text = "\n".join([f"[{ts}] {spk}: {txt}" for ts, spk, txt in transcript_tuples])

        prompt = f"""Eres un Auditor Senior de Cumplimiento de Televentas Bancarias de Interbank.
Tu ÚNICO objetivo es auditar la llamada para verificar si el asesor ofreció la AFILIACIÓN AL PAGO AUTOMÁTICO / DÉBITO AUTOMÁTICO de la Tarjeta de Crédito, y si el cliente ACEPTÓ o RECHAZÓ.

REGLAS DE EVALUACIÓN:
1. "NO_ACEPTA": El asesor ofreció afiliar a Pago/Débito Automático (o cargar el pago a su cuenta de ahorros), pero el cliente declinó, dijo que prefiere pagarlo por su cuenta, que lo verá en su app, que no desea débito automático, etc.
   -> Debes capturar el timestamp exacto (mm:ss) del momento en que el CLIENTE rechaza o dice que no.
2. "ACEPTA": El asesor ofreció la afiliación al Pago Automático y el cliente dio su consentimiento explícito ("Sí", "De acuerdo", "Afílieme", "Claro").
   -> Debes capturar el timestamp exacto (mm:ss) del momento en que el CLIENTE acepta.
3. "NO_OFRECIDO": En toda la llamada el asesor NUNCA mencionó la afiliación al Pago Automático ni el Débito Automático de la tarjeta.
   -> Timestamp: null.

TRANSCRIPCIÓN DE LA LLAMADA:
\"\"\"
{full_text}
\"\"\"

Responde estrictamente en formato JSON con la siguiente estructura:
{{
  "estado": "NO_ACEPTA" | "ACEPTA" | "NO_OFRECIDO",
  "timestamp_cliente": "mm:ss" | null,
  "cita_textual_cliente": "Texto exacto donde el cliente responde o rechaza",
  "cita_textual_asesor": "Texto exacto donde el asesor ofrece el pago automático",
  "explicacion": "Breve justificación de 1 línea"
}}
"""
        if self.llm_client:
            try:
                response_str = self.llm_client.generate_content_with_retry(
                    prompt=prompt,
                    model_name="gemini-2.5-flash",
                    temperature=0.0,
                    response_json=True
                )
                data = json.loads(response_str)
                estado = data.get("estado", "INCIERTO").upper()
                ts = data.get("timestamp_cliente")

                if estado == "NO_ACEPTA":
                    res_fmt = f"Cliente no acepta ({ts})" if ts else "Cliente no acepta"
                elif estado == "ACEPTA":
                    res_fmt = f"Cliente acepta ({ts})" if ts else "Cliente acepta"
                elif estado == "NO_OFRECIDO":
                    res_fmt = "No se ofreció Pago Automático"
                else:
                    res_fmt = "REVISIÓN MANUAL PENDIENTE"

                logger.info(f"[LLM_EVAL] Estado: {estado} | Timestamp: {ts} | Dictamen: {res_fmt}")
                logger.debug(f"[LLM_EVAL] Cita cliente: '{data.get('cita_textual_cliente')}' | Explicación: {data.get('explicacion')}")

                return {
                    "estado": estado,
                    "timestamp": ts,
                    "resultado_formateado": res_fmt,
                    "cita": data.get("cita_textual_cliente", ""),
                    "explicacion": data.get("explicacion", "")
                }
            except Exception as e:
                logger.error(f"[LLM_EVAL] ❌ Error en evaluación LLM: {e}", exc_info=True)

        # Fallback heurístico si no hay respuesta de LLM
        pa_keywords = ["pago automático", "pago automatico", "debito automático", "débito automatico", "debito", "débito", "afiliar al pago", "afiliación", "afiliacion"]
        has_pa_offer = any(kw in full_text.lower() for kw in pa_keywords)
        if not has_pa_offer:
            return {
                "estado": "NO_OFRECIDO",
                "timestamp": None,
                "resultado_formateado": "No se ofreció Pago Automático",
                "cita": ""
            }
        return {
            "estado": "INCIERTO",
            "timestamp": None,
            "resultado_formateado": "REVISIÓN MANUAL PENDIENTE",
            "cita": ""
        }


def process_audit():
    start_time_exec = time.time()
    if not EXCEL_FILE.exists():
        logger.critical(f"❌ No se encontró el archivo de entrada: '{EXCEL_FILE}'")
        return

    logger.info("=" * 75)
    logger.info("   INICIANDO AUDITORÍA FOCALIZADA: PAGO AUTOMÁTICO TC 2026")
    logger.info(f"   Archivo Entrada : {EXCEL_FILE.name}")
    logger.info(f"   Archivo Respaldo: {BACKUP_FILE.name}")
    logger.info(f"   Log de Auditoría: {LOG_FILE}")
    logger.info("=" * 75)

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active
    except Exception as e:
        logger.critical(f"❌ Error al abrir el archivo Excel '{EXCEL_FILE}': {e}", exc_info=True)
        return

    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    logger.info(f"Columnas detectadas: {headers}")

    col_map = {str(h).strip().upper(): idx + 1 for idx, h in enumerate(headers) if h}
    col_dni = col_map.get("NRO DOCUMENTO", 4)
    col_reg = col_map.get("REG_EJECUTIVO", 2)
    col_ejec = col_map.get("EJECUTIVO", 3)
    col_fec_adq = col_map.get("FECHA APROBACIN ADQ") or col_map.get("FECHA APROBACION ADQ") or 5
    col_res = col_map.get("RESULTADO", 7)
    col_id_llamada = col_map.get("ID LLAMADA", 8)
    col_fec_llamada = col_map.get("FECHA LLAMADA", 9)

    auditor = PagoAutomaticoAuditor()
    verint_ready = auditor.init_services()

    total_rows = ws.max_row
    procesados = 0
    auditados_exito = 0
    pendientes_manual = 0
    errores_procesamiento = 0

    for row_idx in range(2, total_rows + 1):
        try:
            dni_val = ws.cell(row=row_idx, column=col_dni).value
            reg_val = ws.cell(row=row_idx, column=col_reg).value
            ejec_val = ws.cell(row=row_idx, column=col_ejec).value
            fec_adq_val = ws.cell(row=row_idx, column=col_fec_adq).value

            if not dni_val:
                continue

            dni_str = str(int(dni_val) if isinstance(dni_val, float) else dni_val).strip()
            fec_dt = fec_adq_val if isinstance(fec_adq_val, datetime) else (datetime.combine(fec_adq_val, datetime.min.time()) if isinstance(fec_adq_val, date) else None)
            if not fec_dt:
                try:
                    fec_dt = datetime.strptime(str(fec_adq_val)[:10], "%Y-%m-%d")
                except Exception:
                    fec_dt = datetime(2026, 4, 1)

            procesados += 1
            logger.info(f"\n--- [Caso {procesados}/{total_rows - 1}] DNI: {dni_str} | Agente: {reg_val} ({ejec_val}) | Fec ADQ: {fec_dt.strftime('%Y-%m-%d')} ---")

            contacts = []
            if verint_ready:
                contacts = auditor.search_verint_by_dni_and_date(dni_str, fec_dt)

            if contacts:
                contact = contacts[0]
                call_id = contact.get("Sid") or contact.get("DocumentId") or ""
                fec_llamada_str = contact.get("StartTime") or contact.get("StartTimeUTC") or ""
                logger.info(f"✓ Contacto localizado en Verint: ID={call_id} | Fecha={fec_llamada_str}")

                transcript = auditor.get_transcript_lines(contact)
                eval_res = auditor.evaluate_pago_automatico(transcript)

                resultado_texto = eval_res["resultado_formateado"]
                logger.info(f"🎯 Dictamen: {resultado_texto} (Cita: {eval_res.get('cita', '')})")

                ws.cell(row=row_idx, column=col_res, value=resultado_texto)
                ws.cell(row=row_idx, column=col_id_llamada, value=str(call_id))
                ws.cell(row=row_idx, column=col_fec_llamada, value=str(fec_llamada_str))
                auditados_exito += 1
            else:
                logger.warning(f"⚠️ No se halló interacción en Verint para DNI {dni_str}.")
                ws.cell(row=row_idx, column=col_res, value="REVISIÓN MANUAL PENDIENTE")
                pendientes_manual += 1

            # Auto-guardado progresivo cada 5 casos para evitar pérdida de datos
            if procesados % 5 == 0:
                wb.save(EXCEL_FILE)
                logger.debug(f"[CHECKPOINT] Progreso auto-guardado en {EXCEL_FILE.name} (Caso {procesados}).")

        except Exception as e_row:
            errores_procesamiento += 1
            logger.error(f"❌ Error inesperado procesando fila {row_idx} (DNI: {dni_val}): {e_row}", exc_info=True)
            ws.cell(row=row_idx, column=col_res, value="REVISIÓN MANUAL PENDIENTE (Error técnico)")

    # Guardado final
    try:
        wb.save(EXCEL_FILE)
        wb.save(BACKUP_FILE)
    except Exception as e_save:
        logger.critical(f"❌ Error al guardar el archivo Excel final: {e_save}", exc_info=True)

    elapsed = time.time() - start_time_exec
    logger.info("\n" + "=" * 75)
    logger.info("✅ AUDITORÍA FINALIZADA:")
    logger.info(f"   • Tiempo Total              : {elapsed:.1f} segundos")
    logger.info(f"   • Total Casos Procesados    : {procesados}")
    logger.info(f"   • Resueltos con Éxito       : {auditados_exito}")
    logger.info(f"   • Pendientes Escucha Manual : {pendientes_manual}")
    logger.info(f"   • Errores Técnicos          : {errores_procesamiento}")
    logger.info(f"   • Excel Actualizado         : {EXCEL_FILE}")
    logger.info(f"   • Respaldo                  : {BACKUP_FILE}")
    logger.info(f"   • Log Completo              : {LOG_FILE}")
    logger.info("=" * 75)


if __name__ == "__main__":
    process_audit()
