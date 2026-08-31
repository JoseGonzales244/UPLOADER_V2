# Workspace Rules for APP_CALIDAD (Plataforma Calidad Televentas)

## 1. Active Architecture & Technology Stack

- **Active Frontend (UI):** `frontend/` (`app.js`, `styles.css`, `index.html`). Single-page architecture without Node build steps.
- **Active Backend (API/Services):** `backend/` (`main.py`) powered by FastAPI, WebSockets and Pydantic schemas.
- **Active Domain Modules:** `modules/`
  - `modules/calidad/`: Calidad NTD pipeline & SQL transformations.
  - `modules/consumo/`: Base Consumo 5-phase pipeline.
  - `modules/cierre/`: Monthly closing & KRI snapshots.
  - `modules/convenios/`: Convenios setup & ETL.
  - `modules/genesys/`: Genesys audio downloader & Outlook parser.
  - `modules/speech/`: Transcripts orchestrator & Insight lead service.
  - `modules/verint/`: Verint WFO REST API & Cookie harvester.
  - `modules/dotacion/`: Monthly staffing (Fases 1-4), analyst vacations & Verint SA licensing.
- **Active Infrastructure:** `infrastructure/` (`database/`, `parsers/`, `system/`, `scrapers/`).
- **Centralized Data Storage:** `data/` (`downloads/`, `transcripciones/`, `input/`, `reports/`, `runtime/`).

---

## 2. Frontend & Code Standards

- **Active Frontend Architecture:**
  - All UI modifications must be made exclusively in `frontend/app.js` and `frontend/styles.css` (React 18 SPA).
  - Backend is 100% FastAPI (`backend/main.py`) with domain-driven modules in `modules/`.

---

## 3. Environment & Execution Rules

- **PowerShell Command Chaining:** NEVER use `&&` to chain commands in PowerShell. Always use `;` instead (e.g. `git add -A; git status`).
- **Virtual Environment Execution:** NEVER execute Python globally. Always use the local virtual environment executable:
  - `.\.venv\Scripts\python`
- **Unit Test Runner:** Always execute testing frameworks as Python modules through the virtual environment runner:
  - `.\.venv\Scripts\python -m unittest discover -s tests`

---

## 4. Communication & Output Policy

- **Zero Chat Dump:** NEVER print datasets, large reports, tables, or complete scripts in chat. Always write them to markdown artifacts in the brain directory and reply in chat with strictly ≤ 2 lines plus the clickable markdown file link.
- **Direct & Pragmatic:** Zero conversational filler, greetings, or apologies. Focus directly on code diffs, logs, and verifiable deliverables.
- **Strict Markdown Link Syntax:**
  - **In Workspace Markdown Docs (`docs/*.md`):** Use workspace-relative paths: `[filename:L10](../path/to/file.py)` so the IDE Markdown previewer renders clickable links natively without line wrapping.
  - **In Chat Responses:** Use absolute `file://` URIs: `[filename](file:///path/to/file)`.
  - **Zero Backticks inside `[]`:** NEVER nest backticks inside brackets (e.g. NEVER `[`file.py`](...)`).

---

## 5. Verification & Safety Protocol

- **Automated Validation:** Always run the complete unit test suite before finalizing features or refactors.
- **Deprecado = Eliminar:** Lo que ya no sirve o ha sido unificado/reemplazado se elimina inmediatamente. Nunca dejar wrappers vacíos, scripts obsoletos o código muerto.
- **Non-Destructive Operations:** Never delete production databases or drop production tables without explicit validation and safeguards.
