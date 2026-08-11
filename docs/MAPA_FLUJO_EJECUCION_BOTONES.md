# 🗺️ Mapa de Flujo de Ejecución por Botón en la Interfaz (UPLOADER V2)

Este documento detalla paso a paso qué scripts, módulos backend, funciones y archivos SQL se activan secuencialmente al hacer clic en cada botón de la plataforma web, incluyendo sus condiciones lógicas, entradas y salidas.

---

## 📁 1. Pestaña: Subir a Teradata

### 1.1 Botón: `👁️ Vista Previa de Archivo`

- **Endpoint Backend:** `POST /api/upload/preview` ([backend/main.py](../backend/main.py))
- **Flujo de Ejecución:**
  1. Recibe el archivo temporal enviado desde la interfaz.
  2. Detecta el tipo de archivo especificado (`file_type`):
     - **Si `file_type == "Excel"`:** Ejecuta `read_excel_file()` ([infrastructure/parsers/readers.py](../infrastructure/parsers/readers.py)). Si se seleccionó una plantilla, aplica el mapeo de columnas predefinido (`plantillas.json`).
     - **Si `file_type == "CSV"`:** Ejecuta `read_csv_file()` ([infrastructure/parsers/readers.py](../infrastructure/parsers/readers.py)) detectando delimitadores automáticamente.
     - **Si `file_type == "TXT"`:** Ejecuta `read_unicode_text_file()` ([infrastructure/parsers/readers.py](../infrastructure/parsers/readers.py)) manejando codificaciones UTF-8 / UTF-16 LE / Latin-1.
  3. Ejecuta `suggest_sql_type()` ([infrastructure/parsers/cleaners.py](../infrastructure/parsers/cleaners.py)) sobre cada columna para proponer el tipo de dato SQL (`VARCHAR`, `INTEGER`, `DECIMAL`).
  4. Retorna la vista previa de las primeras 10 filas y el esquema de columnas sugerido a la interfaz.

---

### 1.2 Botón: `🚀 Cargar a Teradata`

- **Endpoint Backend:** `POST /api/upload/teradata` ([backend/main.py](../backend/main.py))
- **Función Principal:** `_run_upload_task()` en hilo de fondo (`BackgroundTasks`)
- **Flujo de Ejecución:**
  1. **Lectura:** Carga el archivo en memoria usando el lector correspondiente (`read_excel_file` / `read_csv_file` / `read_unicode_text_file`).
  2. **Limpieza:** Llama a `clean_dataframe()` ([infrastructure/parsers/cleaners.py](../infrastructure/parsers/cleaners.py)):
     - **Si `convertir_sin_acentos == True`:** Remueve tildes y caracteres especiales con `unidecode`.
     - **Si `transformar_varchar_latin == True`:** Filtra caracteres no compatibles con el conjunto LATIN de Teradata.
     - **Selección de columnas:** Renombra según la configuración enviada desde la UI y trunca textos a `max_len_varchar`.
  3. **Conexión:** Llama a `connect_teradata()` ([infrastructure/database/database.py](../infrastructure/database/database.py)) usando credenciales del usuario o de `.env`.
  4. **Condición de Carga:**
     - **Si `load_action == "Reemplazar registros existentes"`:** Establece `clear_table = True` (vacía la tabla destino mediante `DELETE FROM tabla` antes de insertar).
     - **Si `load_action == "Solo agregar nuevos registros"`:** Establece `clear_table = False` (realiza `INSERT INTO`).
  5. **Ingesta Masiva:** Ejecuta `load_to_teradata()` ([infrastructure/database/database.py](../infrastructure/database/database.py)) por lotes optimizados y emite progreso en vivo vía WebSockets.

---

## 🎧 2. Pestaña: Solicitud de Audios (Genesys & Outlook)

### 2.1 Botón: `📧 Leer de Outlook`

- **Endpoint Backend:** `GET /api/audios/outlook-fetch` ([backend/main.py](../backend/main.py))
- **Flujo de Ejecución:**
  1. Instancia `OutlookService()` ([modules/genesys/services/outlook_service.py](../modules/genesys/services/outlook_service.py)) usando `pywin32` para interactuar con Microsoft Outlook Desktop local.
  2. Ejecuta `obtener_ultimos_correos(limit=3)` buscando los 3 correos más recientes con solicitudes de audio en el Buzón de Entrada.
  3. Parsea el cuerpo del correo o adjuntos en formato Excel/HTML para extraer listas de parejas `(REG_EV, DNI)`.
  4. Retorna la lista parseada al formulario de la UI.

---

### 2.2 Botón: `🎧 Descargar Audios (Genesys)`

- **Endpoint Backend:** `POST /api/audios/download` ([backend/main.py](../backend/main.py))
- **Función Principal:** `_run_audios_task()` en hilo de fondo (`BackgroundTasks`)
- **Flujo de Ejecución:**
  1. **Enriquecimiento de Teléfonos:** Llama a `TeradataService().enriquecer_solicitudes()` ([modules/genesys/services/teradata_service.py](../modules/genesys/services/teradata_service.py)):
     - Busca en Teradata (`DLAB_GEC...`) o en caché local los números telefónicos asociados a cada DNI en la fecha requerida.
     - **Condición:** Si ningún DNI tiene teléfono registrado, emite advertencia y finaliza.
  2. **Automatización de Navegador:** Instancia `GenesysBrowserAutomation()` ([modules/genesys/services/genesys_browser.py](../modules/genesys/services/genesys_browser.py)):
     - Se conecta a la sesión activa de Chrome vía CDP (puerto 9222) en Genesys Purecloud.
  3. **Iteración por Solicitud:**
     - Navega al menú de Interacciones de Genesys.
     - Busca por teléfono + rango de fechas.
     - **Condición:** Si encuentra la llamada -> Reproduce la grabación y descarga el archivo `.mp3`/`.wav` en `transcripciones_genesys/`.
     - **Condición:** Si se presiona el botón `Detener Proceso` -> Interrumpe el ciclo limpiamente (`stop_checker()`).

---

## ⚡ 3. Pestaña: PBI Base Consumo

### 3.1 Botón: `🚀 Ejecutar Proceso Consumo`

- **Endpoint Backend:** `POST /api/orchestrate/consumo` ([backend/main.py](../backend/main.py))
- **Función Orquestadora:** `run_orchestration_flow()` ([modules/consumo/use_cases/consumo_orchestrator.py](../modules/consumo/use_cases/consumo_orchestrator.py))
- **Flujo de Ejecución (Fases Seleccionables):**
  1. **SI `run_phase1 == True` (Descarga & Carga Insight):**
     - Itera las 7 consultas configuradas en `INSUMOS_CONFIG` (Tráfico Genesys, Conv Attributes, Deriva BT, Cloud Marca Transf, BT Transferencia, IVR Ventas, Evaluations).
     - Ejecuta `download_insight_data()` ([infrastructure/scrapers/insight_downloader.py](../infrastructure/scrapers/insight_downloader.py)).
     - Limpia los `.txt` descargados e ingesta en las 7 tablas staging de Teradata (`DLAB_GEC.M_EXP_...`).

  2. **SI `run_phase2 == True` (Insumo Manual CD40K):**
     - Busca el archivo `CD40K` en `data/input/base_consumo/`.
     - Limpia e ingesta en `DLAB_GEC.M_EXP_CD40K`.

  3. **SI `run_phase3 == True` (Desembolsos SQL Server / Teradata):**
     - Extrae transacciones de desembolsos del período y las carga en `DLAB_GEC.M_EXP_DESEMBOLSOS`.

  4. **SI `run_phase4 == True` (Pipeline SQL Consumo):**
     - Conecta a Teradata y ejecuta secuencialmente los scripts SQL de [modules/consumo/sql/](../modules/consumo/sql):
       - `01_CA_CONSENTIMIENTO_DIARIO.sql` (Cruces de consentimiento informado).
       - `02_TLF_NO_AUTORIZADO.sql` (Filtrado de teléfonos no autorizados por LPDP).
       - `03_VENTAS_DN.sql` (Normalización de ventas digitales y presenciales).
       - `04_KRI_VENTAS_SIN_AUDIO.sql` (Identificación de ventas sin soporte de audio).
       - `05_SOURCE_TVL.sql` (Consolidado de la tabla maestra de Consumo).

  5. **SI `run_phase5 == True` (Exportación & Timestamp PBI):**
     - Ejecuta `CONSUMO_SELECT_TC_CD_SEG.sql` para validación final.
     - Escribe la fecha y hora de actualización en el conector de Power BI (`_write_powerbi_timestamp_file`).

---

## 📊 4. Pestaña: PBI Evaluaciones Calidad y Cierre Mensual

### 4.1 Botón: `🚀 Ejecutar Proceso Calidad` (Modo Normal / Semanal)

- **Endpoint Backend:** `POST /api/orchestrate/calidad` con `solo_cierre = False` ([backend/main.py](../backend/main.py))
- **Función Orquestadora:** `run_quality_process_flow()` ([modules/calidad/use_cases/quality_orchestrator.py](../modules/calidad/use_cases/quality_orchestrator.py))
- **Flujo de Ejecución (5 Fases Semanales):**
  1. **SI `run_fase1 == True` (Insight Evaluaciones):**
     - Descarga `EVALUATIONS` de Insight con `download_insight_data()`. ([infrastructure/scrapers/insight_downloader.py](../infrastructure/scrapers/insight_downloader.py)).
     - Carga el archivo `.txt` limpio en la tabla `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE`.

  2. **SI `run_fase2 == True` (Verint Speech Analytics):**
     - Intenta la descarga rápida vía `VerintAPIClient` ([modules/verint/services/verint_api_client.py](../modules/verint/services/verint_api_client.py)).
     - Ingesta reportes descargados en `DLAB_GEC.M_EXP_SPEECH_ANALYTICS_PRE`.

  3. **SI `run_fase3 == True` (Observaciones & Preprocesamiento SQL):**
     - Lee `ACCION_TOMADA.xlsx` usando `deduplicate_observations_by_severity()` e ingesta en Teradata.

  4. **SI `run_fase4 == True` (Cálculo de Pesos & Parches Nota Cero):**
     - Ejecuta los scripts SQL de transformación de [modules/calidad/sql/](../modules/calidad/sql):
       - `01_evaluacion_manual_pc.sql` (Consolidado de evaluaciones manuales).
       - `02_sa_marcacion_ventas_lpdp.sql` (Cruce de marcaciones de Speech Analytics).
       - `03_sa_calculo_pesos_unpivot.sql` (Unpivot de categorías y cálculo ponderado).
       - `04_sa_ajustes_curva.sql` (Calibración de nota de calidad).
       - `04_b_sa_parche_nota_cero.sql` (Aplicación de regla de negocio: nota 0% ante faltas graves/críticas).
       - `05_consolidacion_nota_final.sql` (Tabla final de evaluaciones acumuladas).

  5. **SI `run_fase5 == True` (Consolidado PBI & Carga NTD):**
     - Ejecuta:
       - `06_carga_ntd.sql` (Vista final para tableros NTD).
     - Actualiza el timestamp de conexión en OneDrive/Power BI.

---

### 4.2 Botón: `🔒 Ejecutar Cierre Mensual` (Casilla `🔒 Modo Cierre Mensual` activada)

- **Endpoint Backend:** `POST /api/orchestrate/calidad` con `solo_cierre = True` ([backend/main.py](../backend/main.py))
- **Función Orquestadora:** `run_cierre_process_flow()` ([modules/cierre/use_cases/cierre_orchestrator.py](../modules/cierre/use_cases/cierre_orchestrator.py))
- **Flujo de Ejecución:**
  1. **Inyección de Parámetros:** Inyecta `{PERIODO}` y `{PERIODO_ANTERIOR}` (formato `YYYYMM`).
  2. **SI `run_cierre_01 == True`:**
     - Ejecuta `modules/cierre/sql/01_auditoria_y_cierre.sql`:
       - Aplica `DELETE FROM DLAB_GEC.M_EXP_CALIDAD_CIERRE_MENSUAL WHERE PERIODO = '{PERIODO}'` (Garantiza idempotencia).
       - Realiza `INSERT INTO` congelando la foto final auditada del mes.
  3. **SI `run_cierre_02 == True`:**
     - Ejecuta `modules/cierre/sql/02_kri_resumen_total.sql`:
       - Elimina y reinserta el resumen de indicadores KRI por supervisor/ejecutivo del período en `DLAB_GEC.M_EXP_KRI_RESUMEN`.
  4. **SI `run_cierre_03 == True`:**
     - Ejecuta `modules/cierre/sql/03_consolidado_notas_cierre.sql`:
       - Genera el reporte ejecutivo consolidador de notas finales de cierre.
     - Escribe el timestamp en el archivo de conector de Power BI Cierre.

---

## 🛠️ 5. Acciones Globales & Diagnóstico (Sidebar)

### 5.1 Botón: `🛑 Detener Proceso`

- **Endpoint Backend:** `POST /api/orchestrate/stop` ([backend/main.py](../backend/main.py))
- **Flujo de Ejecución:**
  1. Modifica la variable de estado global `stop_requested = True`.
  2. Las funciones orquestadoras activas (`consumo_orchestrator`, `quality_orchestrator`, `genesys_browser`) verifican periódicamente `stop_checker()` entre cada sentencia SQL o paso del bot.
  3. Al detectar `stop_requested == True`, realizan un `ROLLBACK` en la base de datos o cierran el navegador Chrome, terminando el hilo de ejecución sin corromper tablas.

---

### 5.2 Botón: `🩺 Ejecutar Diagnóstico de Entorno`

- **Endpoint Backend:** `GET /api/health-check` ([backend/main.py](../backend/main.py))
- **Flujo de Ejecución:**
  1. Llama a `run_preflight_health_check()` ([infrastructure/system/health_check.py](../infrastructure/system/health_check.py)).
  2. **Verificación Outlook:** Comprueba la disponibilidad de la librería COM de Windows (`win32com`).
  3. **Verificación Chrome CDP:** Revisa si Chrome está corriendo con el puerto de depuración remota `9222` abierto para Genesys.
  4. **Verificación Teradata:** Realiza un `SELECT 1;` en Teradata para confirmar que las credenciales de `.env` y la red empresarial estén activas.
  5. Devuelve el estado de cada componente a la barra lateral de la interfaz.
