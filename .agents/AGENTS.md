# Workspace Rules for UPLOADER_V2 (APP_CALIDAD)

## Active Architecture & Technology Stack

- **Active Frontend (UI):** `frontend/` (`app.js`, `styles.css`, `index.html`).
- **Active Backend (API/Services):** `backend/` (`main.py`) and modular domain logic in `modules/`.
- **Active Database/System Infrastructure:** `infrastructure/` (`database/`, `system/`, `scrapers/`, `llm/`).

## Deprecated & Legacy Code (DO NOT TOUCH OR CONSULT)

- **IGNORE `legacy/` DIRECTORY ENTIRELY:**
  - Files under `legacy/` (e.g. `legacy/index.py`, `legacy/verint_downloader.py`) are legacy Streamlit/deprecated code.
  - Do NOT modify, read, search, or update files in `legacy/`.
  - All UI modifications must be made exclusively in `frontend/app.js` and `frontend/styles.css`.
