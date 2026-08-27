# ADR-002: Diagnóstico Arquitectónico SOLID y Hoja de Ruta Clean Architecture

- **Status**: Proposed
- **Date**: 2026-08-27
- **Author**: Architectural Enforcement Protocol (`architect-solid-patterns`)

---

## 1. Context (Problema Actual)

Tras la revisión exhaustiva de la base de código activa (`backend/`, `modules/`, `infrastructure/`, `domain/`, `frontend/`), se identifican los siguientes cuellos de botella arquitectónicos:

1. **Violación de SRP (Single Responsibility Principle) en Orquestadores:**
   - `modules/calidad/use_cases/quality_orchestrator.py` (>1,000 líneas) y `modules/consumo/use_cases/consumo_orchestrator.py` asumen múltiples responsabilidades: parsing de archivos, transformaciones Polars, conexión y ejecución SQL Teradata, control de flujos scraping y escrituras en Power BI.
2. **Duplicación de Lógica SQL (DRY & SRP):**
   - Las funciones `parse_statements`, `inject_variables` y `get_period_params` están duplicadas en `quality_orchestrator.py`, `cierre_orchestrator.py`, `tcad_orchestrator.py` en lugar de delegar centralizadamente en `infrastructure/database/sql_executor.py`.
3. **Violación de DIP (Dependency Inversion Principle):**
   - Módulos de caso de uso instancian directamente conectores concretos (`teradatasql.connect`, `pyodbc.connect`, `requests.Session`) en lugar de depender de abstracciones/repositorios inyectados (`ISqlExecutor`, `IScraperClient`).
4. **Acoplamiento en Interface Adapters (`backend/main.py`):**
   - El controlador FastAPI contiene lógica de previsualización, lectura de plantillas y mutaciones de dataframes en lugar de delegar a capas de aplicación/servicios dedicadas.

---

## 2. Proposed Decision (Solución Arquitectónica)

1. **Unificación del Motor SQL (`infrastructure/database/sql_executor.py`):**
   - Centralizar toda tokenización, inyección de variables (`{PERIODO}`, `:periodo_num`) y particionado de sentencias SQL en `sql_executor.py`. Eliminar reimplementaciones ad-hoc en los orquestadores.
2. **Descomposición de Orquestadores Monolíticos:**
   - Separar `quality_orchestrator.py` en Casos de Uso atómicos por fase (`Phase1DownloadUseCase`, `Phase2TeradataLoadUseCase`, `Phase3QualityEvaluationUseCase`, etc.) orquestados mediante un pipeline declarativo.
3. **Inyección de Dependencias (DIP) y Repositorios:**
   - Definir contratos en `domain/interfaces/` para operaciones de base de datos y scrapers (`IDatabaseConnection`, `ISqlScriptRunner`), permitiendo testing unitario 100% aislado con mocks.
4. **Idempotencia y Resiliencia Estándar:**
   - Implementar un wrapper transaccional uniforme para ejecuciones SQL multisentencia con política explícita de rollback y reintentos en llamadas a servicios externos.

---

## 3. Consequences (Consecuencias y Trade-offs)

### Lo que ganamos (+):
- **Alta Testeabilidad:** Cobertura unitaria sin requerir conexiones activas a Teradata o SQL Server.
- **Mantenibilidad Extrema:** Modificar una fase de negocio no impacta las demás fases ni el controlador API.
- **Cero Duplicación de Código:** Reglas de parsing y sanitización centralizadas y estandarizadas.

### Trade-offs (-):
- Refactorización gradual requerida en imports y firmas de métodos en `backend/main.py` y `modules/`.
