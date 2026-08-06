# ADR-001: Descomposición de `core/` y Adopción Estricta de Clean Architecture

- **Status**: Approved
- **Date**: 2026-08-05
- **Author**: Architectural Enforcement Protocol

---

## Context (Problema)

La carpeta `core/` había crecido de forma incontrolada hasta convertirse en un *"God Module"* conteniendo 12 archivos mezclando responsabilidades heterogéneas:
1. Conexión y ejecución SQL a Teradata (`database.py`, `sql_executor.py`, `sql_transcript_importer.py`)
2. Automatización de navegadores / web scraping (`Insight_downloader.py`, `verint_downloader.py`, `verint_transcript_extractor.py`)
3. Parsing de archivos y limpieza de tipos (`readers.py`, `cleaners.py`)
4. Servicios de plataforma (`logging_config.py`, `notifier.py`, `health_check.py`)
5. Orquestación de casos de uso de negocio (`orchestrator.py`)

Esta mezcla violaba el **Single Responsibility Principle (SRP)** y el **Dependency Inversion Principle (DIP)** de SOLID, imposibilitando tests unitarios limpios y desacoplados.

---

## Proposed Decision (Solución)

Redistribuir los componentes de `core/` hacia su capa correspondiente siguiendo la Clean Architecture:

1. **`infrastructure/database/`**: Módulos de conexión Teradata, batch insert y ejecutor de archivos `.sql`.
2. **`infrastructure/scrapers/`**: Descargadores web HTTP/Playwright/Selenium (`insight_downloader`, `verint_downloader`).
3. **`infrastructure/parsers/`**: Manipulación de archivos Excel/CSV/TXT y sanitización Polars (`readers`, `cleaners`).
4. **`infrastructure/system/`**: Infraestructura de logs, notificaciones (Teams/SMTP) y diagnósticos de entorno (`health_check`).
5. **`modules/consumo/use_cases/`**: Orquestador del flujo PBI Base Consumo (`consumo_orchestrator.py`).
6. **`modules/transcripciones/extractors/`**: Extractor de transcripciones Verint.

---

## Consequences (Consecuencias)

### Lo que ganamos (+):
- **Desacoplamiento total**: Cada capa cumple un propósito único y bien delimitado.
- **Testeabilidad**: Los casos de uso pueden probarse aislando la infraestructura mediante mocks o interfaces.
- **Claridad de estructura**: Facilidad de navegación para nuevos desarrolladores y mantenimiento a largo plazo.

### Trade-offs (-):
- Es necesario actualizar las importaciones en `backend/main.py`, `legacy/index.py` y herramientas auxiliares en `tools/`.
