"""
=============================================================================
TEST AISLADO: AUDITORÍA DE 1 SOLO CASO (CASO 1 DE 35)
=============================================================================
Caso a probar:
  - DNI                  : 45954567
  - Agente (REG_EV)      : B44257 (RAMOS LUJAN FAVIOLA)
  - Fecha Aprobación ADQ : 2026-04-29
=============================================================================
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from modules.verint.services.verint_api_client import VerintAPIClient
from infrastructure.llm.gemini_client import GeminiClient
from modules.genesys.services.genesys_browser import GenesysBrowserAutomation
from modules.genesys.services.teradata_service import TeradataService
from modules.genesys.models import SolicitudAudio
from modules.genesys.config import PROFILE_DIR, GENESYS_URL, CDP_URL


def run_single_test():
    print("\n" + "=" * 70)
    print("   🧪 DIAGNÓSTICO AISLADO DE 1 CASO: PAGO AUTOMÁTICO TC")
    print("   DNI: 45954567 | Agente: B44257 | Fecha ADQ: 2026-04-29")
    print("=" * 70)

    dni_target = "45954567".zfill(8)
    reg_target = "B44257"
    fecha_target = datetime(2026, 4, 29)

    # -------------------------------------------------------------------------
    # PASO 1: Obtener Teléfonos Vinculados al DNI
    # -------------------------------------------------------------------------
    print("\n--- PASO 1: Buscando teléfonos del cliente (DNI 45954567) ---")
    teradata_svc = TeradataService()
    dummy_sol = [SolicitudAudio(nombre_archivo=f"REQ_{dni_target}", dni=dni_target, reg_ev=reg_target)]
    enriquecidas = teradata_svc.enriquecer_solicitudes(dummy_sol)
    telefonos = enriquecidas[0].telefonos if enriquecidas else []
    print(f"✓ Teléfonos encontrados para DNI {dni_target}: {telefonos}")

    # -------------------------------------------------------------------------
    # PASO 2: Obtener Bearer Token de Genesys Cloud
    # -------------------------------------------------------------------------
    print("\n--- PASO 2: Conectando a Genesys Cloud para capturar Bearer Token ---")
    browser_bot = GenesysBrowserAutomation()
    token = None

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 1. Intentar auto-lanzar o conectar a Chrome CDP
            browser_bot._lanzar_chrome_cdp_automatico()
            cdp_url = browser_bot.cdp_url.replace("localhost", "127.0.0.1")
            
            try:
                browser = p.chromium.connect_over_cdp(cdp_url)
                page = browser_bot._obtener_page_principal(browser)
                if page:
                    print(f"✓ Conectado a Chrome CDP ({cdp_url})")
                    token = browser_bot._extraer_bearer_token(page)
            except Exception as e_cdp:
                print(f"⚠️ No se conectó por CDP ({e_cdp}). Abriendo perfil persistente...")
                user_data_dir = str(PROFILE_DIR)
                PROFILE_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        channel="chrome",
                        headless=False,
                        args=["--start-maximized"]
                    )
                except Exception:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=False,
                        args=["--start-maximized"]
                    )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(GENESYS_URL)
                time.sleep(3)
                token = browser_bot._extraer_bearer_token(page)
    except Exception as e_pw:
        print(f"❌ Error en navegador Playwright: {e_pw}")

    if not token:
        print("\n⚠️ No se pudo extraer el Bearer Token automáticamente de Chrome.")
        manual_token = input("👉 Si tienes tu Bearer Token de Genesys a la mano, pégalo aquí (o presiona Enter para cancelar): ").strip()
        if manual_token:
            token = manual_token.replace("Bearer ", "").strip()

    if not token:
        print("❌ Imposible continuar sin Bearer Token de Genesys.")
        return

    print(f"✓ Bearer Token activo: {token[:20]}...{token[-10:]}")

    # -------------------------------------------------------------------------
    # PASO 3: Resolver UserID del Asesor en Genesys
    # -------------------------------------------------------------------------
    print(f"\n--- PASO 3: Resolviendo GUID de usuario en Genesys para '{reg_target}' ---")
    user_id = browser_bot._obtener_user_id_por_matricula(token, reg_target)
    print(f"✓ UserID GUID de '{reg_target}': {user_id}")

    # -------------------------------------------------------------------------
    # PASO 4: Buscar Interacción en Genesys Cloud API
    # -------------------------------------------------------------------------
    d_from = (fecha_target - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00.000Z")
    d_to = (fecha_target + timedelta(days=2)).strftime("%Y-%m-%dT23:59:59.000Z")
    interval = f"{d_from}/{d_to}"
    print(f"\n--- PASO 4: Consultando Genesys API v2 en intervalo '{interval}' ---")

    segment_filters = []
    if user_id:
        segment_filters.append({
            "type": "or",
            "predicates": [{"type": "dimension", "dimension": "userId", "operator": "matches", "value": user_id}]
        })
    if telefonos:
        dnis_preds = [{"dimension": "dnis", "value": str(tlf).strip()} for tlf in telefonos if str(tlf).strip()]
        if dnis_preds:
            segment_filters.append({"type": "or", "predicates": dnis_preds})

    payload = {
        "order": "desc",
        "orderBy": "conversationStart",
        "paging": {"pageSize": 25, "pageNumber": 1},
        "interval": interval,
        "segmentFilters": segment_filters
    }

    api_url = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "accept": "*/*"}

    resp = requests.post(api_url, headers=headers, json=payload, verify=False, timeout=20)
    print(f"Status Code Genesys: {resp.status_code}")

    call_id = None
    call_start = None

    if resp.status_code == 200:
        data = resp.json()
        convs = data.get("conversations", [])
        print(f"✓ Conversaciones encontradas en Genesys: {len(convs)}")
        if convs:
            best_conv = convs[0]
            call_id = best_conv.get("conversationId")
            call_start = best_conv.get("conversationStart")
            print(f"🎯 ID LLAMADA IDENTIFICADO (UUID): {call_id}")
            print(f"   Fecha y Hora de la Llamada    : {call_start}")
    else:
        print(f"❌ Error en respuesta de Genesys: {resp.text[:400]}")
        return

    if not call_id:
        print("⚠️ No se localizó conversación para este cliente en las fechas seleccionadas.")
        return

    # -------------------------------------------------------------------------
    # PASO 5: Descargar Transcripción en Verint API
    # -------------------------------------------------------------------------
    print(f"\n--- PASO 5: Consultando Transcripción en Verint API para CONID '{call_id}' ---")
    verint_user = os.getenv("VERINT_USER")
    verint_pass = os.getenv("VERINT_PASS")
    verint_client = VerintAPIClient(username=verint_user, password=verint_pass)

    if not verint_client.login():
        print("❌ Fallo al iniciar sesión en Verint API.")
        return

    transcript_res = verint_client.get_interaction_transcription_api(call_id)
    if not transcript_res or not isinstance(transcript_res, dict):
        print("❌ Verint no devolvió transcripción para este ID.")
        return

    result_obj = transcript_res.get("GetInteractionTranscriptionResult") or {}
    data_obj = result_obj.get("Data") or {}
    sequences = data_obj.get("WordsSequences") or []

    transcript_lines = []
    for seq in sequences:
        if not isinstance(seq, dict):
            continue
        speaker = "Asesor" if seq.get("SpeakerName") == "Agent" else "Cliente"
        start_ms = seq.get("StartTime", 0)
        total_sec = int(start_ms) // 1000
        mins = total_sec // 60
        secs = total_sec % 60
        ts_str = f"{mins:02d}:{secs:02d}"
        words = " ".join([w.get("WordText", "") for w in seq.get("Words", []) if isinstance(w, dict) and w.get("WordText")]).strip()
        if words:
            transcript_lines.append(f"[{ts_str}] {speaker}: {words}")

    print(f"✓ Transcripción recibida ({len(transcript_lines)} líneas):")
    for line in transcript_lines[:15]:
        print(f"   {line}")
    if len(transcript_lines) > 15:
        print(f"   ... ({len(transcript_lines) - 15} líneas más)")

    # -------------------------------------------------------------------------
    # PASO 6: Auditoría IA con Gemini
    # -------------------------------------------------------------------------
    print("\n--- PASO 6: Evaluando con Gemini (Pago Automático) ---")
    llm = GeminiClient(default_model="gemini-2.5-flash")
    full_text = "\n".join(transcript_lines)

    prompt = f"""Eres un Auditor Senior de Cumplimiento de Televentas de Interbank.
Determina si el asesor ofreció AFILIACIÓN AL PAGO AUTOMÁTICO de la Tarjeta de Crédito, y si el cliente ACEPTÓ o RECHAZÓ.

REGLAS:
1. "NO_ACEPTA": El cliente declinó, dijo que pagará por app, que no desea débito automático, etc. Extrae el timestamp mm:ss del rechazo.
2. "ACEPTA": El cliente aceptó expresamente. Extrae el timestamp mm:ss.
3. "NO_OFRECIDO": Nunca se mencionó en la llamada.

TRANSCRIPCIÓN:
\"\"\"
{full_text}
\"\"\"

Responde en JSON:
{{
  "estado": "NO_ACEPTA" | "ACEPTA" | "NO_OFRECIDO",
  "timestamp_cliente": "mm:ss" | null,
  "cita_textual_cliente": "Frase del cliente",
  "explicacion": "Breve explicación"
}}
"""
    res_str = llm.generate_content_with_retry(prompt=prompt, model_name="gemini-2.5-flash", response_json=True)
    res_json = json.loads(res_str)

    estado = str(res_json.get("estado")).upper()
    ts = res_json.get("timestamp_cliente")
    if estado == "NO_ACEPTA":
        res_fmt = f"Cliente no acepta ({ts})" if ts else "Cliente no acepta"
    elif estado == "ACEPTA":
        res_fmt = f"Cliente acepta ({ts})" if ts else "Cliente acepta"
    else:
        res_fmt = "No se ofreció Pago Automático"

    print("\n" + "=" * 70)
    print("🎯 RESULTADO FINAL DE LA AUDITORÍA:")
    print(f"   • Dictamen     : {res_fmt}")
    print(f"   • Cita Cliente : '{res_json.get('cita_textual_cliente')}'")
    print(f"   • Justificación: {res_json.get('explicacion')}")
    print(f"   • ID Llamada   : {call_id}")
    print(f"   • Fecha Llamada: {call_start}")
    print("=" * 70)


if __name__ == "__main__":
    run_single_test()
