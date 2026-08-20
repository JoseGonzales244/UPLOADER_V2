"""
=============================================================================
EVALUADOR IA DE TRANSCRIPCIONES (PAGO AUTOMÁTICO TARJETAS DE CRÉDITO)
=============================================================================
Objetivo: 
  Lee las transcripciones extraídas en 'data/transcripciones_pa/' 
  y evalúa con Gemini si se ofreció y si el cliente aceptó/rechazó
  la afiliación al Pago Automático, actualizando 'Solicitud Cumplimiento TC 2026.xlsx'.
=============================================================================
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import openpyxl
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("EvaluadorIAPA")

from infrastructure.llm.gemini_client import GeminiClient

TRANSCRIPTS_DIR = PROJECT_ROOT / "data" / "transcripciones_pa"
INDEX_FILE = TRANSCRIPTS_DIR / "transcripciones_index.json"
EXCEL_FILE = PROJECT_ROOT / "Solicitud Cumplimiento TC 2026.xlsx"
BACKUP_FILE = PROJECT_ROOT / "Solicitud Cumplimiento TC 2026_Auditada.xlsx"


def evaluate_text_with_gemini(full_text: str, llm_client: GeminiClient) -> Dict[str, Any]:
    prompt = f"""Eres un Auditor Senior de Cumplimiento de Televentas Bancarias de Interbank.
Tu ÚNICO objetivo es auditar la llamada para verificar si el asesor ofreció la AFILIACIÓN AL PAGO AUTOMÁTICO / DÉBITO AUTOMÁTICO de la Tarjeta de Crédito, y si el cliente ACEPTÓ o RECHAZÓ.

REGLAS DE EVALUACIÓN:
1. "NO_ACEPTA": El asesor ofreció afiliar a Pago/Débito Automático (o cargar el pago a su cuenta de ahorros), pero el cliente declinó, dijo que prefiere pagarlo por su cuenta/app, que no desea débito automático, etc.
   -> Debes capturar el timestamp exacto (mm:ss) del momento en que el CLIENTE rechaza o dice que no.
2. "ACEPTA": El asesor ofreció Pago Automático y el cliente dio su consentimiento explícito ("Sí", "De acuerdo", "Afílieme", "Claro").
   -> Debes capturar el timestamp exacto (mm:ss) del momento en que el CLIENTE acepta.
3. "NO_OFRECIDO": En toda la llamada NUNCA se mencionó la afiliación a Pago Automático ni Débito Automático.
   -> Timestamp: null.

TRANSCRIPCIÓN DE LA LLAMADA:
\"\"\"
{full_text}
\"\"\"

Responde estrictamente en formato JSON:
{{
  "estado": "NO_ACEPTA" | "ACEPTA" | "NO_OFRECIDO",
  "timestamp_cliente": "mm:ss" | null,
  "cita_textual_cliente": "Texto exacto donde el cliente responde o rechaza",
  "cita_textual_asesor": "Texto exacto donde el asesor ofrece el pago automático",
  "explicacion": "Breve justificación de 1 línea"
}}
"""
    try:
        response_str = llm_client.generate_content_with_retry(
            prompt=prompt,
            model_name="gemini-2.5-flash",
            temperature=0.0,
            response_json=True
        )
        data = json.loads(response_str)
        estado = str(data.get("estado", "INCIERTO")).upper()
        ts = data.get("timestamp_cliente")

        if estado == "NO_ACEPTA":
            res_fmt = f"Cliente no acepta ({ts})" if ts else "Cliente no acepta"
        elif estado == "ACEPTA":
            res_fmt = f"Cliente acepta ({ts})" if ts else "Cliente acepta"
        elif estado == "NO_OFRECIDO":
            res_fmt = "No se ofreció Pago Automático"
        else:
            res_fmt = "REVISIÓN MANUAL PENDIENTE"

        return {
            "estado": estado,
            "timestamp": ts,
            "resultado_formateado": res_fmt,
            "cita": data.get("cita_textual_cliente", ""),
            "explicacion": data.get("explicacion", "")
        }
    except Exception as e:
        logger.error(f"Error evaluando con Gemini: {e}")
        return {
            "estado": "INCIERTO",
            "timestamp": None,
            "resultado_formateado": "REVISIÓN MANUAL PENDIENTE",
            "cita": "",
            "explicacion": str(e)
        }


def main():
    if not EXCEL_FILE.exists():
        logger.critical(f"❌ No se encontró '{EXCEL_FILE}'")
        return

    logger.info("=" * 75)
    logger.info("   EVALUADOR IA DE TRANSCRIPCIONES (PAGO AUTOMÁTICO TC)")
    logger.info("=" * 75)

    llm = GeminiClient(default_model="gemini-2.5-flash")

    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active

    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    col_map = {str(h).strip().upper(): idx + 1 for idx, h in enumerate(headers) if h}
    col_dni = col_map.get("NRO DOCUMENTO", 4)
    col_res = col_map.get("RESULTADO", 7)
    col_id_llamada = col_map.get("ID LLAMADA", 8)

    total_rows = ws.max_row
    evaluados = 0
    auditados_exito = 0

    for row_idx in range(2, total_rows + 1):
        dni_raw = ws.cell(row=row_idx, column=col_dni).value
        call_id_raw = ws.cell(row=row_idx, column=col_id_llamada).value

        if not dni_raw:
            continue

        dni_8 = str(int(dni_raw) if isinstance(dni_raw, float) else dni_raw).strip().zfill(8)
        call_id = str(call_id_raw).strip() if call_id_raw else ""

        # Buscar archivo de transcripción
        matched_file = None
        if call_id and call_id not in ["", "None", "7464"]:
            candidate = TRANSCRIPTS_DIR / f"TRANSCRIPT_DNI_{dni_8}_{call_id}.txt"
            if candidate.exists():
                matched_file = candidate

        if not matched_file:
            # Buscar cualquier archivo para ese DNI
            for f in TRANSCRIPTS_DIR.glob(f"TRANSCRIPT_DNI_{dni_8}_*.txt"):
                matched_file = f
                break

        evaluados += 1
        if matched_file and matched_file.exists():
            text_content = matched_file.read_text(encoding="utf-8")
            logger.info(f"\n--- [Caso {evaluados}/{total_rows - 1}] Evaluando DNI {dni_8} ({matched_file.name}) ---")
            eval_res = evaluate_text_with_gemini(text_content, llm)

            resultado_texto = eval_res["resultado_formateado"]
            logger.info(f"🎯 Dictamen: {resultado_texto}")
            logger.info(f"   Cita    : '{eval_res.get('cita')}'")
            logger.info(f"   Motivo  : {eval_res.get('explicacion')}")

            ws.cell(row=row_idx, column=col_res, value=resultado_texto)
            auditados_exito += 1
        else:
            logger.warning(f"--- [Caso {evaluados}/{total_rows - 1}] DNI {dni_8}: Sin transcripción en '{TRANSCRIPTS_DIR.name}' ---")
            ws.cell(row=row_idx, column=col_res, value="REVISIÓN MANUAL PENDIENTE")

    wb.save(EXCEL_FILE)
    wb.save(BACKUP_FILE)

    logger.info("\n" + "=" * 75)
    logger.info("✅ EVALUACIÓN DE TRANSCRIPCIONES FINALIZADA:")
    logger.info(f"   • Total Casos Evaluados     : {evaluados}")
    logger.info(f"   • Auditados con Éxito       : {auditados_exito}")
    logger.info(f"   • Archivo Excel Actualizado : {EXCEL_FILE}")
    logger.info(f"   • Respaldo                  : {BACKUP_FILE}")
    logger.info("=" * 75)


if __name__ == "__main__":
    main()
