import requests
import json
import urllib3
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOWNLOADS_DIR = Path.home() / "Downloads"
CDP_URL = "http://localhost:9222"
GENESYS_URL = "https://apps.mypurecloud.com/directory/#/analytics/interactions"
PROFILE_DIR = Path(__file__).parent.parent / "modules" / "genesys" / ".chrome_genesys_profile"

def auto_lanzar_chrome():
    try:
        req = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1)
        if req.status == 200:
            print("[OK] Chrome ya escucha en puerto CDP 9222.")
            return True
    except Exception:
        pass

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
        shutil.which("chrome") or ""
    ]
    chrome_cmd = next((p for p in chrome_paths if p and os.path.exists(p)), None)
    if not chrome_cmd:
        print("[ERROR] No se encontro ejecutable de Chrome.")
        return False

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome_cmd,
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_DIR.resolve()}",
        "--no-first-run",
        "--no-default-browser-check",
        GENESYS_URL
    ]

    print("[INFO] Auto-iniciando Chrome...")
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error ejecutando Chrome: {e}")
        return False

    start = time.time()
    while time.time() - start < 12:
        try:
            req = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1)
            if req.status == 200:
                print("[OK] Chrome auto-iniciado y listo.")
                return True
        except Exception:
            time.sleep(0.5)

    return False

def extraer_bearer_token():
    if not auto_lanzar_chrome():
        print("[ERROR] No se pudo conectar a Chrome.")
        return None

    print("Conectando a Chrome via CDP...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else None
            page = context.pages[0] if (context and context.pages) else browser.new_page() if hasattr(browser, "new_page") else None

            if not page:
                for ctx in browser.contexts:
                    if ctx.pages:
                        page = ctx.pages[0]
                        break

            if not page:
                print("[ERROR] No hay pagina abierta.")
                return None

            token_box = {"token": None}
            def _on_req(req):
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer ") and len(auth) > 20:
                    token_box["token"] = auth.replace("Bearer ", "").strip()

            page.on("request", _on_req)
            page.wait_for_timeout(2500)

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
            print(f"Error capturando token: {e}")
            return None

def ejecutar_test_especifico():
    print("=== Test con Conversation ID 289b9afe-d517-480d-8cf6-5028e1429ee4 ===")
    token = extraer_bearer_token()
    if not token:
        print("[ERROR] No se pudo capturar Bearer Token.")
        return

    print("Bearer Token capturado exitosamente.")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "accept": "*/*"}
    conv_id = "289b9afe-d517-480d-8cf6-5028e1429ee4"

    # 1. Obtener detalles de la conversación especifica
    url_details = f"https://api.mypurecloud.com/api/v2/analytics/conversations/{conv_id}/details"
    r_det = requests.get(url_details, headers=headers, verify=False, timeout=15)
    print(f"\n1. GET /api/v2/analytics/conversations/{conv_id}/details -> Status: {r_det.status_code}")
    
    user_id = None
    if r_det.status_code == 200:
        participants = r_det.json().get("participants", [])
        print(f"   Participantes en la llamada: {len(participants)}")
        for p in participants:
            p_user_id = p.get("userId")
            p_purpose = p.get("purpose")
            print(f"   - Participant Purpose: {p_purpose} | userId: {p_user_id}")
            if p_user_id:
                user_id = p_user_id

    # 2. Consultar nombre de usuario usando el userId encontrado y probar /users/search por campo 'name'
    if user_id:
        url_usr = f"https://api.mypurecloud.com/api/v2/users/{user_id}"
        r_usr = requests.get(url_usr, headers=headers, verify=False, timeout=15)
        print(f"\n2. GET /api/v2/users/{user_id} -> Status: {r_usr.status_code}")
        if r_usr.status_code == 200:
            u_data = r_usr.json()
            print(f"   [DATOS EXACTOS DE B46108 EN GENESYS]:")
            print(f"   -> ID GUID: {u_data.get('id')}")
            print(f"   -> Name: {u_data.get('name')}")
            print(f"   -> Username: {u_data.get('username')}")
            print(f"   -> State: {u_data.get('state')}")

        # Probar POST /api/v2/users/search filtrando especificamente por campo 'name' y state='any'
        search_url = "https://api.mypurecloud.com/api/v2/users/search"
        search_payload = {
            "query": [
                {"fields": ["name"], "type": "CONTAINS", "value": "B46108"},
                {"fields": ["state"], "type": "EXACT", "value": "any"}
            ]
        }
        r_search = requests.post(search_url, headers=headers, json=search_payload, verify=False, timeout=15)
        print(f"\n   POST /api/v2/users/search por campo 'name' -> Status: {r_search.status_code}")
        if r_search.status_code == 200:
            results = r_search.json().get("results", [])
            print(f"   Resultados encontrados: {len(results)}")
            for res in results:
                print(f"   - Match ID: {res.get('id')} | Name: {res.get('name')} | State: {res.get('state')}")

    # 3. Probar la búsqueda en /analytics/conversations/details/query con la sintaxis exacta de Genesys
    if user_id:
        print(f"\n3. Consultando /analytics/conversations/details/query para userId {user_id}...")
        conv_url = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"
        conv_payload = {
            "order": "desc",
            "orderBy": "conversationStart",
            "paging": {"pageSize": 20, "pageNumber": 1},
            "interval": "2026-07-01T05:00:00.000Z/2026-08-01T05:00:00.000Z",
            "segmentFilters": [
                {
                    "type": "or",
                    "predicates": [
                        {
                            "type": "dimension",
                            "dimension": "userId",
                            "operator": "matches",
                            "value": user_id
                        }
                    ]
                }
            ]
        }
        r_conv = requests.post(conv_url, headers=headers, json=conv_payload, verify=False, timeout=15)
        print(f"   Status respuesta consulta: {r_conv.status_code}")
        if r_conv.status_code == 200:
            convs = r_conv.json().get("conversations", [])
            print(f"   ¡EXITO TOTAL! Conversaciones recuperadas para la ejecutiva inactiva {user_id}: {len(convs)}")
            for c in convs[:5]:
                print(f"   - Conv ID: {c.get('conversationId')} | Start: {c.get('conversationStart')}")
        else:
            print(f"   Detalle error {r_conv.status_code}: {r_conv.text}")

if __name__ == "__main__":
    ejecutar_test_especifico()


)

