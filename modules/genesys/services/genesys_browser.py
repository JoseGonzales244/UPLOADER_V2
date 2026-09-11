import datetime
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
import requests
import urllib3
from playwright.sync_api import Page, sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from modules.genesys.config import (
    CDP_URL,
    DOWNLOADS_DIR,
    GENESYS_URL,
    PROFILE_DIR,
    TOKEN_CACHE_FILE,
)
from modules.genesys.logger import get_logger
from modules.genesys.models import EstadoRegistro, SolicitudAudio
from modules.genesys.storage.tracking_store import TrackingStore

logger = get_logger("GenesysBrowser")


class GenesysBrowserAutomation:
    """Automatización de descargas en Genesys Cloud.

    Opera exclusivamente mediante la API REST v2 de Genesys Cloud.
    Extrae o reutiliza el Bearer Token de la sesión de Chrome y descarta
    por completo el scraping frágil por interfaz gráfica (UI).
    """

    def __init__(self, cdp_url: str = CDP_URL, genesys_url: str = GENESYS_URL, tracking_store: TrackingStore = None):
        self.cdp_url = cdp_url
        self.genesys_url = genesys_url
        self.tracking_store = tracking_store or TrackingStore()
        self._user_id_cache: Dict[str, str] = {}
        self._wrapup_catalog: Dict[str, str] = {}

    @staticmethod
    def _verificar_token(token: str) -> bool:
        """Verifica si un Bearer Token está vigente consultando el endpoint /api/v2/users/me."""
        if not token or len(token) < 20:
            return False
        try:
            resp = requests.get(
                "https://api.mypurecloud.com/api/v2/users/me",
                headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
                verify=False,
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _guardar_token_cache(token: str) -> None:
        try:
            TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"token": token, "timestamp": time.time()}, f, indent=2)
            logger.info(f"✓ Bearer Token guardado en caché local ({TOKEN_CACHE_FILE.name}).")
        except Exception as e:
            logger.debug(f"Error guardando token en caché: {e}")

    @staticmethod
    def _cargar_token_cache() -> Optional[str]:
        try:
            if TOKEN_CACHE_FILE.exists():
                with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                token = data.get("token")
                ts = data.get("timestamp", 0)
                # Validar expiración estimada de 12 horas
                if token and (time.time() - ts) < 43200:
                    return token
        except Exception as e:
            logger.debug(f"Error leyendo token de caché: {e}")
        return None

    def _lanzar_chrome_cdp_automatico(self) -> bool:
        """Verifica si Chrome CDP responde; si no, lanza Chrome del sistema con el perfil persistente."""
        try:
            req = urllib.request.urlopen(f"{self.cdp_url}/json/version", timeout=1)
            if req.status == 200:
                logger.info(f"Chrome ya está escuchando en puerto CDP ({self.cdp_url})")
                return True
        except Exception:
            pass

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
            shutil.which("chrome") or "",
        ]

        chrome_cmd = next((p for p in chrome_paths if p and os.path.exists(p)), None)
        if not chrome_cmd:
            logger.warning("No se encontró el ejecutable de Chrome en las rutas estándar.")
            return False

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        port = self.cdp_url.split(":")[-1].split("/")[0] if ":" in self.cdp_url else "9222"

        cmd = [
            chrome_cmd,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={PROFILE_DIR.resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            self.genesys_url,
        ]

        logger.info(f"Auto-iniciando Chrome con perfil persistente ({PROFILE_DIR.name}) en puerto CDP {port}...")
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error al ejecutar Chrome: {e}")
            return False

        start_time = time.time()
        while time.time() - start_time < 12:
            try:
                req = urllib.request.urlopen(f"{self.cdp_url}/json/version", timeout=1)
                if req.status == 200:
                    logger.info("Chrome con puerto CDP inicializado correctamente.")
                    return True
            except Exception:
                time.sleep(0.5)

        logger.warning("Chrome fue ejecutado pero no respondió a tiempo en el puerto CDP.")
        return False

    def _obtener_page_principal(self, browser_or_context) -> Optional[Page]:
        if not browser_or_context:
            return None
        contexts = getattr(browser_or_context, "contexts", [browser_or_context] if hasattr(browser_or_context, "pages") else [])
        for ctx in contexts:
            for pg in getattr(ctx, "pages", []):
                try:
                    if not pg.is_closed() and "/admin" not in pg.url and ("analytics/interactions" in pg.url or "purecloud" in pg.url or "genesys" in pg.url):
                        return pg
                except Exception:
                    continue
        for ctx in contexts:
            for pg in getattr(ctx, "pages", []):
                try:
                    if not pg.is_closed() and "/admin" not in pg.url:
                        return pg
                except Exception:
                    continue
        return None

    def _extraer_bearer_token(self, page: Page, timeout_ms: int = 8000) -> Optional[str]:
        """Escucha las peticiones de red e inspecciona la sesión web para capturar el Bearer Token activo."""
        token_holder = {"token": None}

        def _capturar_req(req):
            try:
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer ") and len(auth) > 20:
                    cand = auth.replace("Bearer ", "").strip()
                    token_holder["token"] = cand
            except Exception:
                pass

        page.on("request", _capturar_req)

        # 1. Inspeccionar almacenamiento local y de sesión
        try:
            token_storage = page.evaluate("""() => {
                try {
                    for (let storage of [sessionStorage, localStorage]) {
                        for (let i = 0; i < storage.length; i++) {
                            let k = storage.key(i);
                            let v = storage.getItem(k);
                            if (!v) continue;
                            if (v.includes("Bearer ")) {
                                return v.split("Bearer ")[1].split('"')[0].trim();
                            }
                            if (v.startsWith("{") && v.endsWith("}")) {
                                try {
                                    let p = JSON.parse(v);
                                    if (p.accessToken && typeof p.accessToken === "string") return p.accessToken;
                                    if (p.token && typeof p.token === "string" && p.token.length > 25) return p.token;
                                    if (p.authenticated?.token) return p.authenticated.token;
                                    if (p.authenticated?.accessToken) return p.authenticated.accessToken;
                                } catch(e) {}
                            }
                        }
                    }
                } catch(e) {}
                return null;
            }""")
            if token_storage and self._verificar_token(token_storage):
                self._guardar_token_cache(token_storage)
                return token_storage
        except Exception:
            pass

        # 2. Gatillar una llamada API desde la sesión autenticada de Genesys
        try:
            page.evaluate("""() => {
                fetch('/api/v2/users/me', { headers: { 'accept': 'application/json' } }).catch(() => {});
            }""")
            start_wait = time.time()
            while time.time() - start_wait < 3.0:
                if token_holder["token"] and self._verificar_token(token_holder["token"]):
                    self._guardar_token_cache(token_holder["token"])
                    return token_holder["token"]
                page.wait_for_timeout(300)
        except Exception:
            pass

        # 3. Recarga ligera si aún no se capturó tráfico
        if not token_holder["token"]:
            try:
                logger.info("Solicitando recarga ligera para capturar emisión de Bearer Token...")
                page.reload(wait_until="domcontentloaded", timeout=12000)
                start_wait = time.time()
                while time.time() - start_wait < (timeout_ms / 1000):
                    if token_holder["token"] and self._verificar_token(token_holder["token"]):
                        self._guardar_token_cache(token_holder["token"])
                        return token_holder["token"]
                    page.wait_for_timeout(500)
            except Exception:
                pass

        if token_holder["token"] and self._verificar_token(token_holder["token"]):
            self._guardar_token_cache(token_holder["token"])
            return token_holder["token"]

        return None

    def _capturar_token_desde_navegador(self, headless: bool = True, stop_checker=None) -> Optional[str]:
        """Abre sesión de Chrome mediante CDP/Playwright para capturar el Bearer Token."""
        with sync_playwright() as p:
            browser = None
            context = None
            page = None

            if self._lanzar_chrome_cdp_automatico():
                try:
                    browser = p.chromium.connect_over_cdp(self.cdp_url)
                    logger.info(f"Conectado exitosamente a Chrome vía CDP ({self.cdp_url})")
                    page = self._obtener_page_principal(browser)
                except Exception as e:
                    logger.warning(f"Error conectando vía CDP a Chrome: {e}")

            if not page:
                user_data_dir = str(PROFILE_DIR)
                PROFILE_DIR.mkdir(parents=True, exist_ok=True)
                args = ["--start-maximized"] if not headless else []
                try:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        channel="chrome",
                        headless=headless,
                        args=args,
                    )
                except Exception:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=headless,
                        args=args,
                    )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(self.genesys_url)
                time.sleep(3)

            # Verificar si está en pantalla de login de Microsoft / Genesys SSO
            if page:
                try:
                    def _es_url_login(url_str: str) -> bool:
                        u = url_str.lower()
                        return any(d in u for d in ["microsoftonline.com", "login.live.com", "accounts.google.com", "login.windows.net"]) or "/login" in u or "login?" in u

                    if _es_url_login(page.url):
                        logger.info("🔑 Sesión no iniciada o token expirado en Microsoft/Genesys.")
                        logger.info("👉 Por favor complete el inicio de sesión en Chrome. (Tiempo de espera: 5 minutos)...")
                        start_time = time.time()
                        while time.time() - start_time < 300:
                            if stop_checker and stop_checker():
                                logger.warning("🛑 Cancelado durante espera de login.")
                                return None
                            if page.is_closed():
                                logger.warning("Navegador cerrado por el usuario.")
                                return None
                            try:
                                curr = page.url.lower()
                                if not _es_url_login(curr) and ("purecloud" in curr or "genesys" in curr or "mypurecloud" in curr):
                                    logger.info("✅ Login completado exitosamente.")
                                    break
                            except Exception:
                                pass
                            time.sleep(2)
                except Exception as e:
                    logger.debug(f"Error verificando redirección de login: {e}")

            if not page:
                for ctx in (browser.contexts if browser else [context] if context else []):
                    for pg in ctx.pages:
                        try:
                            if "purecloud" in pg.url or "genesys" in pg.url:
                                page = pg
                                break
                        except Exception:
                            continue
                    if page:
                        break

            if not page:
                logger.error("No se encontró sesión activa de Genesys Cloud.")
                return None

            return self._extraer_bearer_token(page, timeout_ms=8000)

    def _obtener_catalogo_wrapups(self, token: str) -> dict:
        """Consulta una sola vez el catálogo de wrapUp codes para traducir UUIDs a nombres legibles."""
        if self._wrapup_catalog:
            return self._wrapup_catalog

        catalog = {}
        try:
            url = "https://api.mypurecloud.com/api/v2/routing/wrapupcodes?pageSize=500"
            headers = {"Authorization": f"Bearer {token}", "accept": "*/*"}
            resp = requests.get(url, headers=headers, verify=False, timeout=15)
            if resp.status_code == 200:
                entities = resp.json().get("entities", [])
                for e in entities:
                    if "id" in e and "name" in e:
                        catalog[e["id"]] = e["name"]
                logger.info(f"✓ Catálogo de {len(catalog)} wrapUp codes cargado exitosamente.")
        except Exception as e:
            logger.warning(f"No se pudo cargar el catálogo de wrapUp codes: {e}")

        self._wrapup_catalog = catalog
        return catalog

    @staticmethod
    def _es_conclusion_acepta(conv: dict, catalog: dict = None) -> bool:
        """Determina si la conversación tiene una conclusión válida de ACEPTA CAMPAÑA (descartando NO ACEPTA)."""
        catalog = catalog or {}
        wrapup_names = []

        for p in conv.get("participants", []):
            for s in p.get("sessions", []):
                for seg in s.get("segments", []):
                    if seg.get("segmentType") == "wrapup":
                        w_code = seg.get("wrapUpCode", "")
                        w_name = seg.get("wrapUpName", "")
                        w_note = seg.get("wrapUpNote", "")

                        resolved_name = catalog.get(w_code, w_name or w_code or "")
                        wrapup_names.extend([resolved_name, w_note])

        for w in wrapup_names:
            w_str = str(w).upper()
            if "NO ACEPTA" in w_str or "RECHAZA" in w_str:
                return False

        for w in wrapup_names:
            w_str = str(w).upper()
            if "ACEPTA" in w_str:
                return True

        return False

    @staticmethod
    def _duracion_grabacion(rec: dict) -> float:
        """Calcula la duración total en segundos de un tramo individual de grabación."""
        try:
            if "durationMs" in rec and rec["durationMs"]:
                return float(rec["durationMs"])
            s = rec.get("startTime") or rec.get("originalRecordingStartTime")
            e = rec.get("endTime")
            if s and e:
                t_s = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
                t_e = datetime.datetime.fromisoformat(e.replace("Z", "+00:00"))
                return (t_e - t_s).total_seconds()
        except Exception:
            pass
        return 0.0

    def _obtener_user_id_por_matricula(self, token: str, reg_ev: str) -> Optional[str]:
        """Resuelve el userId GUID de un promotor/ejecutivo (activo o inactivo) en Genesys Cloud."""
        if not reg_ev or not str(reg_ev).strip():
            return None

        val = str(reg_ev).strip()
        if re.match(r"^[0-9a-fA-F-]{36}$", val):
            return val

        if val in self._user_id_cache:
            return self._user_id_cache[val]

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "accept": "*/*"}

        # 1. POST /users/search (usuarios activos)
        try:
            search_url = "https://api.mypurecloud.com/api/v2/users/search"
            search_payload = {
                "query": [
                    {"fields": ["name", "username", "email"], "type": "CONTAINS", "value": val}
                ]
            }
            resp = requests.post(search_url, headers=headers, json=search_payload, verify=False, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    user_id = results[0].get("id")
                    if user_id:
                        self._user_id_cache[val] = user_id
                        logger.info(f"✓ UserId resuelto vía /users/search para '{val}': {user_id}")
                        return user_id
        except Exception as e:
            logger.debug(f"Error en /users/search para '{val}': {e}")

        # 2. GET /users?state=inactive (ejecutivos inactivos)
        try:
            logger.info(f"Buscando ejecutivos inactivos en Genesys para '{val}'...")
            page_num = 1
            while page_num <= 5:
                get_url = f"https://api.mypurecloud.com/api/v2/users?state=inactive&pageSize=100&pageNumber={page_num}"
                resp = requests.get(get_url, headers=headers, verify=False, timeout=10)
                if resp.status_code != 200:
                    break
                data = resp.json()
                entities = data.get("entities", [])
                for u in entities:
                    u_name = u.get("name", "").upper()
                    u_username = u.get("username", "").upper()
                    u_email = u.get("email", "").upper()
                    target_val = val.upper()
                    if target_val in u_name or target_val in u_username or target_val in u_email:
                        user_id = u.get("id")
                        if user_id:
                            self._user_id_cache[val] = user_id
                            logger.info(f"✓ UserId inactivo localizado para '{val}': {user_id} ({u.get('name')})")
                            return user_id
                if page_num >= data.get("pageCount", 1):
                    break
                page_num += 1
        except Exception as e:
            logger.warning(f"Error consultando usuarios inactivos para '{val}': {e}")

        return None

    def ejecutar_descargas_api(self, solicitudes: List[SolicitudAudio], token: str, stop_checker=None, period_str: str = None) -> bool:
        """Descarga audios masivamente consumiendo la API REST directa de Genesys Cloud a alta velocidad.

        Busca simultáneamente por DNIS y por ANI con variantes de código de país (+51 / tel:).
        """
        logger.info(f"⚡ Iniciando descargas vía API REST directa para {len(solicitudes)} registro(s)...")

        wrapup_catalog = self._obtener_catalogo_wrapups(token)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        api_query_url = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"

        def parse_period_dates(p_str):
            if p_str and len(p_str) == 6 and p_str.isdigit():
                y, m = int(p_str[:4]), int(p_str[4:])
            else:
                d = datetime.datetime.now()
                y, m = d.year, d.month
            m_next = 1 if m == 12 else m + 1
            y_next = y + 1 if m == 12 else y
            return f"{y:04d}-{m:02d}-01T05:00:00.000Z/{y_next:04d}-{m_next:02d}-01T05:00:00.000Z"

        default_intervalo = parse_period_dates(period_str)

        for idx, sol in enumerate(solicitudes, 1):
            if stop_checker and stop_checker():
                logger.warning("🛑 Proceso detenido por el usuario.")
                return False

            logger.info(f"--- [API REST {idx}/{len(solicitudes)}] Promotor: {sol.reg_ev} | DNI: {sol.dni} ---")

            # Formatear el intervalo de fecha
            intervalo = default_intervalo
            m = re.search(r"_(\d{4})(\d{2})\d{2}", sol.nombre_archivo)
            if m:
                anio_n, mes_n = int(m.group(1)), int(m.group(2))
                m_next = 1 if mes_n == 12 else mes_n + 1
                y_next = anio_n + 1 if mes_n == 12 else anio_n
                intervalo = f"{anio_n:04d}-{mes_n:02d}-01T05:00:00.000Z/{y_next:04d}-{m_next:02d}-01T05:00:00.000Z"

            # Construir predicados de teléfono evaluando DNIS y ANI (incluyendo variantes +51 / tel:)
            phone_preds = []
            for tlf in (sol.telefonos or []):
                t = str(tlf).strip()
                if not t:
                    continue
                phone_preds.extend([
                    {"dimension": "dnis", "value": t},
                    {"dimension": "ani", "value": t},
                    {"dimension": "ani", "value": f"tel:{t}"},
                ])
                if len(t) == 9:
                    phone_preds.extend([
                        {"dimension": "dnis", "value": f"+51{t}"},
                        {"dimension": "ani", "value": f"+51{t}"},
                        {"dimension": "dnis", "value": f"tel:+51{t}"},
                        {"dimension": "ani", "value": f"tel:+51{t}"},
                        {"dimension": "dnis", "value": f"51{t}"},
                        {"dimension": "ani", "value": f"51{t}"},
                    ])
                elif len(t) in (7, 8):
                    phone_preds.extend([
                        {"dimension": "dnis", "value": f"+51{t}"},
                        {"dimension": "ani", "value": f"+51{t}"},
                        {"dimension": "dnis", "value": f"+511{t}"},
                        {"dimension": "ani", "value": f"+511{t}"},
                    ])

            segment_filters = []
            if phone_preds:
                segment_filters.append({"type": "or", "predicates": phone_preds})
            else:
                segment_filters.append({
                    "type": "or",
                    "predicates": [
                        {"dimension": "direction", "value": "inbound"},
                        {"dimension": "direction", "value": "outbound"},
                    ],
                })

            payload = {
                "order": "desc",
                "orderBy": "conversationStart",
                "paging": {"pageSize": 100, "pageNumber": 1},
                "interval": intervalo,
                "segmentFilters": segment_filters,
            }

            try:
                resp = requests.post(api_query_url, headers=headers, json=payload, verify=False, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Error consultando API para DNI {sol.dni}: Status {resp.status_code}")
                    continue

                conversations = resp.json().get("conversations", [])
                candidatas = [c for c in conversations if self._es_conclusion_acepta(c, wrapup_catalog)]

                # Si hay múltiples llamadas y se especificó promotor, priorizar la que coincida con reg_ev
                if len(candidatas) > 1 and sol.reg_ev:
                    reg_ev_upper = str(sol.reg_ev).strip().upper()
                    user_id = self._obtener_user_id_por_matricula(token, sol.reg_ev)
                    candidatas_promotor = [
                        c for c in candidatas
                        if reg_ev_upper in str(c.get("participants", [])).upper()
                        or (user_id and user_id in str(c.get("participants", [])))
                    ]
                    if candidatas_promotor:
                        candidatas = candidatas_promotor

                if not candidatas:
                    logger.warning(f"No se hallaron interacciones 'ACEPTA CAMPAÑA' vía API (DNIS/ANI) para DNI {sol.dni}")
                    self.tracking_store.registrar_no_encontrado(sol.reg_ev, sol.dni)
                    self.tracking_store.marcar_como_procesado(sol.reg_ev, sol.dni, EstadoRegistro.NO_ENCONTRADO, telefonos=sol.telefonos)
                    continue

                descargas_exitosas = 0

                for sub_idx, conv in enumerate(candidatas, 1):
                    conv_id = conv.get("conversationId")
                    logger.info(f"Procesando conversación API {conv_id} ({sub_idx}/{len(candidatas)})...")

                    # Extraer fecha exacta de la llamada para asegurar el nombre estándar
                    conv_start = conv.get("conversationStart", "")
                    fecha_exacta = ""
                    if conv_start:
                        try:
                            dt_conv = datetime.datetime.fromisoformat(conv_start.replace("Z", "+00:00"))
                            fecha_exacta = dt_conv.strftime("%Y%m%d")
                        except Exception:
                            pass

                    nombre_base = sol.nombre_archivo
                    if fecha_exacta and f"_{fecha_exacta}" not in nombre_base:
                        prefijo = sol.prefijo or "AUDIO"
                        nombre_base = f"{prefijo}_{sol.reg_ev}_DNI{sol.dni}_{fecha_exacta}"

                    recs = []
                    rec_list_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings"
                    rec_resp = requests.get(rec_list_url, headers=headers, verify=False, timeout=15)
                    if rec_resp.status_code == 200 and rec_resp.json():
                        recs = rec_resp.json()

                    if not recs:
                        meta_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordingmetadata"
                        meta_resp = requests.get(meta_url, headers=headers, verify=False, timeout=15)
                        if meta_resp.status_code == 200 and meta_resp.json():
                            recs = meta_resp.json()

                    if not recs:
                        logger.warning(f"No se obtuvieron grabaciones para {conv_id}")
                        continue

                    # Si una misma conversación contiene múltiples tramos de grabación, seleccionar la más extensa
                    if len(recs) > 1:
                        recs.sort(key=self._duracion_grabacion, reverse=True)
                        logger.info(f"  La llamada posee {len(recs)} tramos de audio. Seleccionando el tramo de mayor duración...")

                    rec_target = recs[0]
                    rec_id = rec_target.get("id")

                    download_link = rec_target.get("mediaUri")
                    if not download_link and rec_target.get("mediaUris"):
                        for m_v in rec_target.get("mediaUris", {}).values():
                            if isinstance(m_v, dict) and m_v.get("mediaUri"):
                                download_link = m_v.get("mediaUri")
                                break

                    # Transcodificación directa MP3 / WAV
                    if not download_link:
                        format_urls = [
                            f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?formatId=MP3&download=true",
                            f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?download=true",
                            f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?formatId=WAV&download=true",
                        ]

                        for media_url in format_urls:
                            for attempt in range(1, 6):
                                m_resp = requests.get(media_url, headers=headers, verify=False, timeout=15)
                                if m_resp.status_code in [200, 202]:
                                    try:
                                        m_data = m_resp.json()
                                        m_uris = m_data.get("mediaUris", {})
                                        if "S" in m_uris:
                                            download_link = m_uris["S"].get("mediaUri")
                                        elif m_data.get("mediaUri"):
                                            download_link = m_data.get("mediaUri")
                                        else:
                                            for v in m_uris.values():
                                                if isinstance(v, dict) and "mediaUri" in v:
                                                    download_link = v.get("mediaUri")
                                                    break
                                        if download_link:
                                            break
                                    except Exception:
                                        pass
                                time.sleep(1.5)
                            if download_link:
                                break

                    # Fallback Batch Request API si la transcodificación directa demoró
                    if not download_link:
                        try:
                            batch_url = "https://api.mypurecloud.com/api/v2/recording/batchrequests"
                            b_resp = requests.post(batch_url, headers=headers, json={"conversationIds": [conv_id]}, verify=False, timeout=15)
                            if b_resp.status_code in [200, 202]:
                                job_id = b_resp.json().get("id")
                                if job_id:
                                    for _ in range(1, 8):
                                        time.sleep(2)
                                        j_resp = requests.get(f"{batch_url}/{job_id}", headers=headers, verify=False, timeout=15)
                                        if j_resp.status_code == 200:
                                            res = j_resp.json().get("results", [])
                                            if res and res[0].get("mediaResultUrl"):
                                                download_link = res[0].get("mediaResultUrl")
                                                break
                        except Exception as e_b:
                            logger.warning(f"Fallback Batch API no disponible: {e_b}")

                    if not download_link:
                        logger.warning(f"No se obtuvo el enlace de descarga MP3 para {conv_id}")
                        continue

                    nombre_mp3 = f"{nombre_base}_P{sub_idx:02d}" if len(candidatas) > 1 else nombre_base
                    archivo_mp3 = DOWNLOADS_DIR / f"{nombre_mp3}.mp3"
                    if archivo_mp3.exists():
                        archivo_mp3.unlink()

                    audio_resp = requests.get(download_link, verify=False, stream=True, timeout=60)
                    if audio_resp.status_code == 200:
                        with open(archivo_mp3, "wb") as f:
                            for chunk in audio_resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        descargas_exitosas += 1
                        logger.info(f"✓ MP3 guardado en Downloads: {archivo_mp3}")
                    else:
                        logger.error(f"Error descargando stream MP3: Status {audio_resp.status_code}")

                if descargas_exitosas > 0:
                    self.tracking_store.marcar_como_procesado(sol.reg_ev, sol.dni, EstadoRegistro.DESCARGADO, telefonos=sol.telefonos)
                    logger.info(f"✓ Solicitud Promotor {sol.reg_ev} | DNI {sol.dni} completada ({descargas_exitosas} MP3 descargado(s)).")
                else:
                    self.tracking_store.registrar_no_encontrado(sol.reg_ev, sol.dni)
                    self.tracking_store.marcar_como_procesado(sol.reg_ev, sol.dni, EstadoRegistro.NO_ENCONTRADO, telefonos=sol.telefonos)
                    logger.warning(f"No se lograron descargar archivos MP3 físicos para DNI {sol.dni}")

            except Exception as e:
                logger.error(f"Error procesando solicitud API {sol.reg_ev} - DNI {sol.dni}: {e}")

        return True

    def procesar_solicitudes(self, solicitudes: List[SolicitudAudio], headless: bool = True):
        """Alias retrocompatible para ejecutar_descargas."""
        return self.ejecutar_descargas(solicitudes, headless=headless)

    def ejecutar_descargas(self, solicitudes: List[SolicitudAudio], headless: bool = True, stop_checker=None, period_str: str = None) -> None:
        """Punto de entrada principal para la descarga masiva de llamadas en Genesys Cloud.

        Ejecuta 100% mediante API REST v2 sin interactuar con la interfaz gráfica.
        """
        solicitudes = self.tracking_store.filtrar_no_procesados(solicitudes)
        if not solicitudes:
            logger.info("No hay solicitudes pendientes por procesar.")
            return

        logger.info(f"Iniciando descargas en Genesys Cloud para {len(solicitudes)} registro(s) [Período: {period_str or 'actual'}]...")

        # 1. Intentar reutilizar token vigente desde la caché local
        token = self._cargar_token_cache()
        if token and self._verificar_token(token):
            logger.info("⚡ Bearer Token activo reutilizado de la caché local.")
            self.ejecutar_descargas_api(solicitudes, token, stop_checker=stop_checker, period_str=period_str)
            return

        # 2. Conectar a Chrome para capturar el token de la sesión activa
        logger.info("Conectando con Chrome para capturar Bearer Token activo de Genesys Cloud...")
        token = self._capturar_token_desde_navegador(headless=headless, stop_checker=stop_checker)

        if not token:
            logger.error("❌ No se pudo capturar el Bearer Token de Genesys Cloud. Verifique que Chrome tenga la sesión iniciada.")
            return

        logger.info("🔑 Bearer Token capturado exitosamente. Ejecutando descargas masivas vía API REST...")
        self.ejecutar_descargas_api(solicitudes, token, stop_checker=stop_checker, period_str=period_str)
