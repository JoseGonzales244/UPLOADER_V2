"""
VerintCookieHarvester
---------------------
Obtiene cookies de sesión e Impact360AuthToken de Verint WFO usando Playwright headless (~5 segundos)
soporta SSO Microsoft (Entra ID / SAML2) y guarda en caché local. Mientras el caché sea válido, 
el proceso NO abre ningún navegador: va directo por API REST con HTTPX.

Caché válido:
- visid_incap_*  → 1 año (Imperva WAF)
- JSESSIONID / Impact360AuthToken → TTL configurable (defecto: 4 horas)
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger("verint_cookie_harvester")

# Duración máxima de la sesión antes de renovar (en segundos)
SESSION_TTL_SECONDS = 4 * 60 * 60  # 4 horas

# Ruta del caché de cookies
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COOKIE_CACHE_PATH = PROJECT_ROOT / "logs" / "verint_cookies_cache.json"


def _load_cache() -> Optional[Dict]:
    """Lee el caché de cookies y token si existe."""
    if not COOKIE_CACHE_PATH.exists():
        return None
    try:
        with open(COOKIE_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.warning(f"No se pudo leer el caché de cookies: {e}")
        return None


def _save_cache(cookies: list, impact360_token: Optional[str] = None) -> None:
    """Persiste las cookies y token en el caché con timestamp."""
    COOKIE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "harvested_at": time.time(),
        "cookies": cookies,
        "impact360_token": impact360_token
    }
    with open(COOKIE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"✅ Caché de sesión guardado en {COOKIE_CACHE_PATH} (Token: {impact360_token})")


def _is_cache_valid(cache: Dict) -> bool:
    """Verifica si el caché sigue siendo válido según el TTL."""
    if not cache:
        return False
    harvested_at = cache.get("harvested_at", 0)
    age = time.time() - harvested_at
    if age > SESSION_TTL_SECONDS:
        logger.info(f"⏰ Caché de sesión expirado (edad: {age/3600:.1f}h > TTL: {SESSION_TTL_SECONDS/3600:.1f}h). Se renovará.")
        return False
    logger.info(f"✅ Caché válido (edad: {age/60:.1f} min). Sin necesidad de abrir navegador.")
    return True


def _harvest_via_playwright(username: str, password: str, signin_url: str) -> Tuple[list, Optional[str]]:
    """
    Abre Chromium headless, completa el flujo SSO / login de Verint,
    captura las cookies de sesión y el token Impact360AuthToken.
    Tarda ~5-8 segundos. Cierra el navegador inmediatamente después.
    """
    from playwright.sync_api import sync_playwright

    logger.info("🌐 Abriendo sesión headless de Verint (SSO Microsoft) para capturar token/cookies...")
    cookies = []
    token_container = {"impact360_token": None}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Interceptamos respuestas para extraer el authToken de AppShellStartupData o headers
        def handle_response(response):
            try:
                # 1. Intentar capturar desde la respuesta de AppShellStartupData
                if "AppShellStartupData" in response.url and response.status == 200:
                    data = response.json()
                    sec_entity = data.get("StartupData", {}).get("securityContextEntity", {})
                    token = sec_entity.get("authToken") or sec_entity.get("xsrfToken")
                    if token:
                        token_container["impact360_token"] = token
                        logger.info(f"🔑 Token capturado desde AppShellStartupData: {token}")

                # 2. Revisar cabeceras de respuesta por Impact360AuthToken
                for name, val in response.headers.items():
                    if name.lower() == "impact360authtoken" and val:
                        token_container["impact360_token"] = val
                        logger.info(f"🔑 Token capturado desde Response Header: {val}")
            except Exception:
                pass

        def handle_request(request):
            try:
                for name, val in request.headers.items():
                    if name.lower() == "impact360authtoken" and val:
                        token_container["impact360_token"] = val
            except Exception:
                pass

        page.on("response", handle_response)
        page.on("request", handle_request)
        
        try:
            page.goto(signin_url, timeout=20000)
        except Exception as e:
            logger.warning(f"Navegación inicial a signin_url: {e}")

        # --- Manejo del Formulario de Inicio de Sesión (Microsoft SSO / Verint) ---
        # Buscar campo de usuario (puede ser #username, input[type='email'], input[name='username'])
        user_input = page.query_selector("input[name='username']") or page.query_selector("#username") or page.query_selector("input[type='email']")
        if user_input:
            logger.info(f"Ingresando usuario SSO: {username}")
            user_input.fill(username)
            
            # Buscar botón Continuar o presionar Enter
            btn_continuar = page.query_selector("button:has-text('Continuar')") or page.query_selector("input[type='submit']") or page.query_selector("button[type='submit']")
            if btn_continuar:
                btn_continuar.click()
            else:
                user_input.press("Enter")

        # Esperar redirección SAML de Microsoft / Carga de interfaz Verint
        try:
            page.wait_for_url("**/wfo/ui/**", timeout=25000)
        except Exception:
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                page.wait_for_timeout(5000)

        cookies = context.cookies()
        browser.close()

    captured_token = token_container.get("impact360_token")
    logger.info(f"🍪 {len(cookies)} cookies capturadas. Token: {captured_token}")
    return cookies, captured_token


def get_verint_session(
    username: str,
    password: str = "",
    base_url: str = "https://wfo.mt5.verintcloudservices.com",
    force_refresh: bool = False
) -> Tuple[Dict[str, str], Optional[str]]:
    """
    Retorna una tupla (cookies_dict, impact360_token) lista para usar en httpx/requests.
    
    Flujo:
    1. Intenta leer el caché local.
    2. Si el caché es válido (< TTL), devuelve (cookies, token) directamente.
    3. Si expiró o no existe, ejecuta Playwright headless para autenticar por SSO,
       guarda en caché y devuelve los valores actualizados.
    """
    if not force_refresh:
        cache = _load_cache()
        if _is_cache_valid(cache):
            cookies_dict = {c["name"]: c["value"] for c in cache.get("cookies", [])}
            token = cache.get("impact360_token")
            return cookies_dict, token

    signin_url = f"{base_url}/wfo/control/signin"
    cookies_list, token = _harvest_via_playwright(username, password, signin_url)
    
    if not cookies_list:
        raise RuntimeError("Playwright no pudo capturar cookies de sesión de Verint WFO.")
    
    _save_cache(cookies_list, token)
    cookies_dict = {c["name"]: c["value"] for c in cookies_list}
    return cookies_dict, token


def get_verint_cookies(
    username: str,
    password: str = "",
    base_url: str = "https://wfo.mt5.verintcloudservices.com",
    force_refresh: bool = False
) -> Dict[str, str]:
    """
    Wrapper compatible hacia atrás. Devuelve el diccionario {cookie_name: cookie_value}.
    """
    cookies_dict, _ = get_verint_session(username, password, base_url, force_refresh)
    return cookies_dict

