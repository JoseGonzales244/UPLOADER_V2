"""
VerintCookieHarvester
---------------------
Obtiene cookies de sesión de Verint WFO usando Playwright headless (~5 segundos)
y las guarda en caché local. Mientras el caché sea válido, el proceso NO abre
ningún navegador: va directo por API REST con HTTPX.

Caché válido:
- visid_incap_*  → 1 año (la más estable, viene de Imperva WAF)
- JSESSIONID     → TTL configurable (defecto: 4 horas)
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("verint_cookie_harvester")

# Duración máxima de la JSESSIONID antes de renovar (en segundos)
JSESSIONID_TTL_SECONDS = 4 * 60 * 60  # 4 horas

# Ruta del caché de cookies
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COOKIE_CACHE_PATH = PROJECT_ROOT / "logs" / "verint_cookies_cache.json"


def _load_cache() -> Optional[Dict]:
    """Lee el caché de cookies si existe."""
    if not COOKIE_CACHE_PATH.exists():
        return None
    try:
        with open(COOKIE_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.warning(f"No se pudo leer el caché de cookies: {e}")
        return None


def _save_cache(cookies: list) -> None:
    """Persiste las cookies en el caché con timestamp."""
    COOKIE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "harvested_at": time.time(),
        "cookies": cookies
    }
    with open(COOKIE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"✅ Caché de cookies guardado en {COOKIE_CACHE_PATH}")


def _is_cache_valid(cache: Dict) -> bool:
    """Verifica si el caché sigue siendo válido según el TTL de JSESSIONID."""
    if not cache:
        return False
    harvested_at = cache.get("harvested_at", 0)
    age = time.time() - harvested_at
    if age > JSESSIONID_TTL_SECONDS:
        logger.info(f"⏰ Caché de cookies expirado (edad: {age/3600:.1f}h > TTL: {JSESSIONID_TTL_SECONDS/3600:.1f}h). Se renovará.")
        return False
    logger.info(f"✅ Caché válido (edad: {age/60:.1f} min). Sin necesidad de abrir navegador.")
    return True


def _harvest_via_playwright(username: str, password: str, signin_url: str) -> list:
    """
    Abre Chromium headless, hace login y extrae las cookies de sesión.
    Tarda ~5-8 segundos. Cierra el navegador inmediatamente después.
    """
    from playwright.sync_api import sync_playwright

    logger.info("🌐 Abriendo sesión headless de Verint para capturar cookies (5-8 seg)...")
    cookies = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            page.goto(signin_url, timeout=15000)
        except Exception:
            pass

        if page.query_selector("#username"):
            page.fill("#username", username)
            page.press("#username", "Enter")
            try:
                page.wait_for_selector("#password", timeout=6000)
            except Exception:
                pass
            page.fill("#password", password)
            page.press("#password", "Enter")
            # Esperar a que el login complete (networkidle = red inactiva)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                page.wait_for_timeout(4000)

        cookies = context.cookies()
        browser.close()

    logger.info(f"🍪 {len(cookies)} cookies capturadas desde Playwright.")
    return cookies


def get_verint_cookies(
    username: str,
    password: str,
    base_url: str = "https://wfo.mt5.verintcloudservices.com",
    force_refresh: bool = False
) -> Dict[str, str]:
    """
    Retorna un dict {nombre_cookie: valor} listo para inyectar en httpx.
    
    Flujo:
    1. Intenta leer el caché local.
    2. Si el caché es válido (< TTL), lo devuelve directamente.
    3. Si expiró o no existe, lanza Playwright headless por ~5-8 segundos,
       captura las cookies, guarda el caché y las devuelve.
    
    Args:
        force_refresh: Si True, ignora el caché y siempre abre el navegador.
    """
    if not force_refresh:
        cache = _load_cache()
        if _is_cache_valid(cache):
            return {c["name"]: c["value"] for c in cache["cookies"]}

    signin_url = f"{base_url}/wfo/control/signin"
    cookies_list = _harvest_via_playwright(username, password, signin_url)
    
    if not cookies_list:
        raise RuntimeError("Playwright no pudo capturar cookies de sesión de Verint WFO.")
    
    _save_cache(cookies_list)
    return {c["name"]: c["value"] for c in cookies_list}
