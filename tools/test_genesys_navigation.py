import os
import sys
import time
from pathlib import Path

# Agregar raíz del proyecto al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright
from modules.genesys.config import CDP_URL, GENESYS_URL, PROFILE_DIR, SELECTORS
from modules.genesys.logger import get_logger
from modules.genesys.services.genesys_browser import GenesysBrowserAutomation

logger = get_logger("TestGenesysNav")


def ejecutar_test_navegacion():
    logger.info("==================================================")
    logger.info("   TEST DE NAVEGACIÓN Y PERSISTENCIA EN GENESYS   ")
    logger.info("==================================================")

    automation = GenesysBrowserAutomation()
    
    # 1. Asegurar lanzamiento de Chrome con puerto CDP
    chrome_listo = automation._lanzar_chrome_cdp_automatico()
    if not chrome_listo:
        logger.warning("No se pudo iniciar Chrome vía CDP. Intentando abrir contexto persistente...")

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        if chrome_listo:
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL)
                logger.info(f"✓ Conectado a Chrome por CDP ({CDP_URL})")
                page = automation._obtener_page_principal(browser)
            except Exception as e:
                logger.warning(f"Error conectando a CDP: {e}")

        if not page:
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=["--start-maximized"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(GENESYS_URL)

        # 2. Verificar sesión de login
        def _es_url_login(url_str: str) -> bool:
            u = url_str.lower()
            return any(d in u for d in ["microsoftonline.com", "login.live.com", "accounts.google.com", "login.windows.net"]) or "/login" in u or "login?" in u

        logger.info("Verificando estado de sesión...")
        if _es_url_login(page.url):
            logger.info("🔑 Por favor inicie sesión en la ventana de Chrome abierta...")
            start_time = time.time()
            while time.time() - start_time < 300:
                if page.is_closed():
                    logger.error("El navegador fue cerrado.")
                    return
                curr = page.url.lower()
                if not _es_url_login(curr) and ("purecloud" in curr or "genesys" in curr or "mypurecloud" in curr):
                    logger.info("✓ Sesión iniciada con éxito.")
                    break
                time.sleep(2)

        if "analytics/interactions" not in page.url and ("purecloud" in page.url or "genesys" in page.url):
            try:
                origin = page.url.split("/directory")[0] if "/directory" in page.url else GENESYS_URL.split("/directory")[0]
                target_url = automation.construir_url_interacciones_fecha(origin, anio=2026, mes=7)
                logger.info(f"Navegando dinámicamente con fecha pre-filtrada a {target_url}...")
                page.goto(target_url)
                time.sleep(2)
            except Exception:
                pass

        page.bring_to_front()
        page.wait_for_timeout(2000)

        # 3. Localizar iframe de analytics
        logger.info("Localizando iframe 'analytics-ui'...")
        analytics_frame = automation._localizar_iframe(page, SELECTORS["analytics_iframe_url"], max_intentos=20)
        if not analytics_frame:
            logger.error("❌ No se pudo encontrar el iframe 'analytics-ui'.")
            return

        logger.info("Esperando hidratación completa de componentes Web (5 segundos)...")
        analytics_frame.wait_for_timeout(5000)

        # 4. Verificar y aplicar filtro de fecha
        automation._asegurar_panel_filtros_abierto(analytics_frame)
        automation._asegurar_filtro_fecha(analytics_frame, mes_deseado="julio", anio_deseado="2026")

        # 5. Esperar filas de interacciones
        logger.info("Buscando interacciones disponibles en la lista...")
        cantidad = automation._esperar_y_contar_filas(analytics_frame, max_reintentos=15)
        if cantidad == 0:
            logger.warning("No hay filas visibles en la tabla actual de interacciones.")
            logger.info("Sugerencia: Ingrese un filtro manual o borre filtros para tener al menos 1 interacción.")
            return

        # 6. Hacer clic en la primera interacción para abrir pestaña de detalle
        logger.info(f"Seleccionando la 1ª interacción de {cantidad} disponibles...")
        filas = analytics_frame.locator(SELECTORS["action_rows"])
        filas.first.click(force=True)

        logger.info("Esperando apertura de la vista de detalles (/admin)...")
        detalle_encontrado = False
        for _ in range(15):
            if "/admin" in page.url or any("/admin" in pg.url for pg in page.context.pages):
                detalle_encontrado = True
                break
            page.wait_for_timeout(1000)

        if not detalle_encontrado:
            logger.error("❌ No se detectó la navegación a la vista de detalle.")
            return

        logger.info(f"✓ Vista de detalle detectada en URL: {page.url}")
        logger.info("Permaneciendo 3 segundos en la vista de detalles...")
        page.wait_for_timeout(3000)

        # 7. Regresar a la pestaña de Interacciones mediante el botón interno de la SPA
        logger.info("Retornando a la vista principal mediante la pestaña interna 'Interacciones'...")
        automation._regresar_a_pestana_interacciones(page)
        page.wait_for_timeout(2000)

        # 8. Validar la persistencia del estado en la página principal
        logger.info("Verificando persistencia del estado de filtros en la página de origen...")
        analytics_frame = automation._localizar_iframe(page, SELECTORS["analytics_iframe_url"], max_intentos=10)
        
        texto_fecha = "NO VISIBLE"
        if analytics_frame:
            btn_selector = SELECTORS.get("date_filter_btn", "button:has(.current-date-display-container)")
            btn = analytics_frame.locator(btn_selector).first
            try:
                if btn.count() > 0 and btn.is_visible():
                    texto_fecha = btn.inner_text().strip()
            except Exception:
                pass

        logger.info(f"Estado actual del botón de fecha: '{texto_fecha}'")

        if "julio de 2026" in texto_fecha.lower():
            logger.info("==================================================")
            logger.info("   ¡TEST COMPLETADO CON ÉXITO! STATUS: PASSED    ")
            logger.info("   La fecha se mantuvo y la página no se recargó. ")
            logger.info("==================================================")
        else:
            logger.warning(f"La fecha actual es '{texto_fecha}'. Verifique si requiere re-aplicación.")


if __name__ == "__main__":
    ejecutar_test_navegacion()
