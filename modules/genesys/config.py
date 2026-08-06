import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Directorios base
BASE_DIR = Path(__file__).parent.resolve()
DOWNLOADS_DIR = Path.home() / "Downloads"

# Ruta OneDrive de destino corporativo
USER_PROFILE = os.environ.get("USERPROFILE", str(Path.home()))
ONEDRIVE_SOLICITUDES_DIR = Path(USER_PROFILE) / "OneDrive - Interbank" / "1. EXPERIENCIA DE COMPRA" / "GESTIÓN 2026" / "SOLICITUD DE AUDIOS"

def obtener_o_crear_carpeta_destino(nombre_sugerido: str = "Solicitud de Audios - General") -> Path:
    """Busca una carpeta existente en OneDrive que coincida con el nombre para reutilizarla (evita v2, v3, v4)."""
    if not ONEDRIVE_SOLICITUDES_DIR.exists():
        try:
            ONEDRIVE_SOLICITUDES_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            return DOWNLOADS_DIR

    sug_clean = nombre_sugerido.strip().lower()
    
    # Buscar si ya existe una carpeta que contenga las palabras clave principales
    for carpeta in ONEDRIVE_SOLICITUDES_DIR.iterdir():
        if carpeta.is_dir():
            c_name = carpeta.name.strip().lower()
            if c_name == sug_clean or sug_clean in c_name or c_name in sug_clean:
                return carpeta

    # Si no existe, crear la carpeta sugerida limpia (sin sufijos v2/v3)
    target = ONEDRIVE_SOLICITUDES_DIR / nombre_sugerido
    target.mkdir(parents=True, exist_ok=True)
    return target

# Archivos de persistencia
TRACKING_FILE = BASE_DIR / "tracking.json"
TELEFONOS_CACHE_FILE = BASE_DIR / "telefonos_cache.json"
NO_ENCONTRADOS_FILE = BASE_DIR / "no_encontrados.csv"

# Configuración de CDP y Navegador
CDP_URL = os.getenv("GENESYS_CDP_URL", "http://localhost:9222")
GENESYS_URL = os.getenv("GENESYS_URL", "https://apps.mypurecloud.com/directory/#/analytics/interactions")
PROFILE_DIR = BASE_DIR / ".chrome_genesys_profile"

# Credenciales y conexión Teradata
TERADATA_USER = os.getenv("TERADATA_USER")
TERADATA_PASSWORD = os.getenv("TERADATA_PASSWORD")
TERADATA_HOST = os.getenv("TERADATA_HOST", "IBKTD")
TERADATA_LOGMECH = os.getenv("TERADATA_LOGMECH", "LDAP")

# Timeouts (en milisegundos para Playwright)
TIMEOUT_DEFAULT = 10000
TIMEOUT_LONG = 60000
TIMEOUT_DETAILS_LOAD = 90000

# Selectores CSS/XPath centralizados para Genesys Cloud UI
SELECTORS = {
    "analytics_iframe_url": "analytics-ui",
    "details_iframe_url": "interaction-details-ui",
    "toggle_filters_btn": "button.toggle-filters",
    "clear_filters_btn": "a.clear-all-filters",
    "interactions_section": 'h3.section-name:has-text("Interacciones")',
    "user_filter_input": 'input[placeholder="Buscar usuarios"]',
    "contact_filter_input": 'input[placeholder="Filtrar por ID de contacto"]',
    "dnis_filter_input": 'input[aria-label="Filtrar por DNIS"]',
    "action_rows": "div.dt-row.action-row",
    "loading_spinner": "gux-page-loading-spinner.active, gux-page-loading-spinner.loading-overlay-v2.active",
    "pager_count": "span.pager-count",
    "prev_recording_btn": "gux-button.previous-recording",
    "next_recording_btn": "gux-button.next-recording",
    "duration_container": "div.content-duration",
    "download_trigger_btn": "div.details-subrow.edit-download gux-button",
    "filename_input": "#download-file-name-input",
    "format_dropdown": 'button[name="Opus Desplegable"]',
    "format_mp3_option": 'gux-option:has-text("MP3")',
    "confirm_download_btn": "gux-button.recording-download-button",
    "tab_button": "button.gux-tab-button",
    "interactions_tab_btn": 'button.gux-tab-button:has(.tab-name:has-text("Interacciones")), button.gux-tab-button:has-text("Interacciones")',
    "date_filter_btn": "button:has(.current-date-display-container)",
    "date_filter_btn_alt": 'button[aria-label*="cambiar fecha seleccionada"]',
    "apply_date_btn": "gux-button:has-text('Aplicar'), button:has-text('Aplicar')",
    "calendar_component": "gux-calendar",
}

