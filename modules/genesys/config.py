import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Directorios base y centralizados bajo data/
BASE_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Descargas centralizadas de audios
DOWNLOADS_DIR = DATA_DIR / "downloads" / "audios" / "genesys"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Runtime, cachés y perfiles
RUNTIME_DIR = DATA_DIR / "runtime"
CACHE_DIR = RUNTIME_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TRACKING_FILE = CACHE_DIR / "genesys_tracking.json"
TELEFONOS_CACHE_FILE = CACHE_DIR / "telefonos_cache.json"
NO_ENCONTRADOS_FILE = CACHE_DIR / "no_encontrados.csv"

# Cargar .env de la raíz si existe
env_root = PROJECT_ROOT / ".env"
if env_root.exists():
    load_dotenv(dotenv_path=env_root)
else:
    load_dotenv()

# Configuración de CDP y Navegador
CDP_URL = os.getenv("GENESYS_CDP_URL", "http://localhost:9222")
GENESYS_URL = os.getenv("GENESYS_URL", "https://apps.mypurecloud.com/directory/#/analytics/interactions")
PROFILES_DIR = RUNTIME_DIR / "browser_profiles"
PROFILE_DIR = PROFILES_DIR / "genesys"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

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

