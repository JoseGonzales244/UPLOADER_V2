import requests
import json
import urllib3
import os
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOWNLOADS_DIR = Path.home() / "Downloads"
CDP_URL = "http://localhost:9222"

def extraer_bearer_token():
    print("Conectando a Chrome vía CDP para capturar Bearer Token...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            token_box = {"token": None}
            def _on_req(req):
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer ") and len(auth) > 20:
                    token_box["token"] = auth.replace("Bearer ", "").strip()

            page.on("request", _on_req)
            page.wait_for_timeout(2000)
            
            if not token_box["token"]:
                try:
                    token_js = page.evaluate("""() => {
                        for (let i = 0; i < localStorage.length; i++) {
                            let k = localStorage.key(i);
                            let v = localStorage.getItem(k);
                            if (v && v.includes("Bearer ")) return v.split("Bearer ")[1].split('"')[0].trim();
                        }
                        return null;
                    }""")
                    if token_js and len(token_js) > 20:
                        token_box["token"] = token_js
                except Exception:
                    pass

            return token_box["token"]
        except Exception as e:
            print(f"Error conectando a Chrome CDP: {e}")
            return None

def ejecutar_test_especifico():
    token = extraer_bearer_token()
    if not token:
        print("❌ No se pudo capturar el Bearer Token. Asegúrate de tener Chrome abierto con Genesys.")
        return

    print("✓ Bearer Token capturado correctamente.")

    # 1. Cargar catálogo de wrapup codes
    print("Cargando catálogo de wrapUp codes de Genesys...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "accept": "*/*"}
    catalog = {}
    cat_resp = requests.get("https://api.mypurecloud.com/api/v2/routing/wrapupcodes?pageSize=500", headers=headers, verify=False, timeout=15)
    if cat_resp.status_code == 200:
        for e in cat_resp.json().get("entities", []):
            if "id" in e and "name" in e:
                catalog[e["id"]] = e["name"]
        print(f"✓ Catálogo cargado: {len(catalog)} wrapUp codes.")

    # 2. Datos del test específico del usuario
    reg_ev = "B44255"
    dni = "09076261"
    telefonos = ["965774357", "5812697", "995084684"]
    nombre_archivo = f"TC_{reg_ev}_DNI{dni}_20260715"

    print(f"\n--- Probando consulta API para DNI {dni} (Teléfonos: {telefonos}) ---")
    
    dnis_preds = [{"dimension": "dnis", "value": tlf} for tlf in telefonos]
    payload = {
        "order": "desc",
        "orderBy": "conversationStart",
        "paging": {"pageSize": 50, "pageNumber": 1},
        "interval": "2026-07-01T05:00:00.000Z/2026-08-01T05:00:00.000Z",
        "segmentFilters": [{"type": "or", "predicates": dnis_preds}]
    }

    query_url = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"
    resp = requests.post(query_url, headers=headers, json=payload, verify=False, timeout=15)
    print(f"Status respuesta consulta: {resp.status_code}")

    if resp.status_code != 200:
        print(f"❌ Error en API: {resp.text[:300]}")
        return

    conversations = resp.json().get("conversations", [])
    print(f"Conversaciones encontradas para esos teléfonos: {len(conversations)}")

    # 3. Filtrar conversaciones ACEPTA CAMPAÑA
    candidatas = []
    for c in conversations:
        conv_id = c.get("conversationId")
        wrapup_names = []
        for p in c.get("participants", []):
            for s in p.get("sessions", []):
                for seg in s.get("segments", []):
                    if seg.get("segmentType") == "wrapup":
                        w_code = seg.get("wrapUpCode", "")
                        w_name = seg.get("wrapUpName", "")
                        resolved = catalog.get(w_code, w_name or w_code or "")
                        wrapup_names.append(resolved)

        es_negativa = any("NO ACEPTA" in str(w).upper() or "RECHAZA" in str(w).upper() for w in wrapup_names)
        es_acepta = any("ACEPTA" in str(w).upper() for w in wrapup_names)

        if es_acepta and not es_negativa:
            candidatas.append((c, wrapup_names))
            print(f"  [VÁLIDA] Conv ID={conv_id} | WrapUp={wrapup_names}")
        else:
            print(f"  [DESCARTADA] Conv ID={conv_id} | WrapUp={wrapup_names}")

    print(f"\nTotal llamadas válidas ACEPTA CAMPAÑA: {len(candidatas)}")

    # 4. Descargar MP3 de las llamadas válidas
    for sub_idx, (conv, wrapups) in enumerate(candidatas, 1):
        conv_id = conv.get("conversationId")
        print(f"\nDescargando audio para Conv ID: {conv_id}...")
        
        rec_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings"
        rec_resp = requests.get(rec_url, headers=headers, verify=False, timeout=15)
        if rec_resp.status_code != 200 or not rec_resp.json():
            print(f"❌ No se obtuvieron grabaciones para {conv_id}")
            continue

        rec_id = rec_resp.json()[0].get("id")
        media_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?formatId=MP3&download=true"

        download_link = None
        for attempt in range(1, 6):
            m_resp = requests.get(media_url, headers=headers, verify=False, timeout=15)
            if m_resp.status_code == 200:
                m_uris = m_resp.json().get("mediaUris", {})
                if "S" in m_uris:
                    download_link = m_uris["S"].get("mediaUri")
                else:
                    for v in m_uris.values():
                        if isinstance(v, dict) and "mediaUri" in v:
                            download_link = v.get("mediaUri")
                            break
                break
            elif m_resp.status_code == 202:
                time.sleep(2)

        if not download_link:
            print(f"❌ No se generó la URL de descarga para {conv_id}")
            continue

        nombre_mp3 = f"{nombre_archivo}_P{sub_idx:02d}.mp3" if len(candidatas) > 1 else f"{nombre_archivo}.mp3"
        archivo_salida = DOWNLOADS_DIR / nombre_mp3

        audio_resp = requests.get(download_link, verify=False, stream=True, timeout=60)
        if audio_resp.status_code == 200:
            with open(archivo_salida, "wb") as f:
                for chunk in audio_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"==================================================")
            print(f"  ¡PRUEBA EXITOSA! AUDIO MP3 DESCARGADO    ")
            print(f"  Ruta: {archivo_salida.resolve()}")
            print(f"  Tamaño: {os.path.getsize(archivo_salida) / 1024:.2f} KB")
            print(f"==================================================")
        else:
            print(f"❌ Error descargando audio MP3: Status {audio_resp.status_code}")

if __name__ == "__main__":
    ejecutar_test_especifico()
