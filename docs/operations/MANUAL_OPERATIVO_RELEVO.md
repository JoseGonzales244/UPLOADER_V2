# Manual Operativo de Relevo — Plataforma Calidad Televentas

Documento operativo para la administración, ejecución recurrente y contingencias de la plataforma `APP_CALIDAD`.

---

## 1. Objetivo y Alcance

Este manual establece los procedimientos de operación rutinaria, calendarios de ejecución, dependencias entre flujos de datos y acciones de contingencia para la gestión de Calidad, Base Consumo, Dotación y auditorías de Televentas. Su propósito es garantizar la continuidad operativa ante relevos de personal o mantenimientos del sistema.

---

## 2. Fuentes de Información y Criterios de Conectividad

### 2.1 Criterio de Consulta: Portal Insight vs. Genesys Cloud
* **Portal Insight (`https://s425vp01/Insight`):** Debe emplearse como canal principal para la extracción masiva de datos estructurados originados en Genesys (métricas de duración, tipificaciones de agentes, notas y atributos de llamada). Los datos se obtienen directamente de las tablas `session_summary` y `conversation_attributes` sin requerir automatizaciones web sobre la consola de Genesys.
* **Genesys Cloud (`https://login.mypurecloud.com`):** Se reserva exclusivamente para la descarga de los archivos de audio (`.mp3` o `.wav`), dado que Insight no almacena grabaciones multimedia. La plataforma utiliza Playwright únicamente como recolector (*token harvester*) para capturar el `Bearer Token` de la sesión activa en el navegador; una vez obtenido, todas las búsquedas de llamadas y descargas de audio se realizan a alta velocidad vía peticiones HTTP directas (`requests`) contra la API REST v2 de Genesys Cloud.

### 2.2 Directorio Telefónico del Data Warehouse (`E_DW_VIEWS.V_CONT_TELEFONO_APICLIENTE`)
En solicitudes de audios donde únicamente se cuenta con el documento de identidad del cliente, la consulta para obtener los números de contacto vigentes registrados en el banco es:
```
SELECT DISTINCT NUMTELEFONO 
FROM E_DW_VIEWS.V_CONT_TELEFONO_APICLIENTE 
WHERE CODDOC = '{DNI_8_DIGITOS}' 
  AND NUMTELEFONO IS NOT NULL;
```
El módulo de búsqueda de audios (`modules/genesys/services/teradata_service.py`) ejecuta esta misma consulta de forma interna para resolver los números asociados antes de consultar en Genesys Cloud.

### 2.3 Administración de Categorías en Verint Speech Analytics
Para crear nuevas categorías de análisis fonético o actualizar las existentes, la ruta en la consola de Verint es:
**Speech Analytics > Diseño > Categorías**.  
En este apartado se pueden probar diferentes términos, operadores lógicos y patrones de coincidencia fonética sobre grabaciones históricas antes de oficializar la regla en producción.

### 2.4 Controlador ODBC Teradata (`CNX_TERA_USER`)
Tanto los modelos de Power BI Desktop como el Gateway de Power BI Service dependen de un DSN de sistema de 64 bits denominado obligatoriamente `CNX_TERA_USER`.
* **Host:** `IBKTD`
* **Mecanismo de Autenticación:** `TD2`
* **Base de Datos:** `DLAB_GEC`
* **Usuario de Servicio:** `APP_GEC`

Cualquier cambio de nombre o falta de configuración en este DSN ocasiona el fallo de las actualizaciones programadas de los tableros de gestión.

### 2.5 Requisitos de Red y VPN
El acceso a Teradata (`IBKTD`), al repositorio de transcripciones en SQL Server (`DB_SPEECH`) y al servidor de Insight (`s425vp01`) requiere una conexión activa a la red interna de Interbank a través de la VPN institucional.

### 2.6 Diagnóstico Rápido de Conectividad y Validación de Accesos Verint
Antes de iniciar los pipelines o procesar auditorías, el operador puede verificar la salud de sus credenciales y accesos mediante dos scripts utilitarios:
* **Diagnóstico integral (Teradata, Insight, Verint y SQL Server):**
  ```
  .\.venv\Scripts\python test_all_connections.py
  ```
* **Validación puntual de acceso y extracción en Verint Speech Analytics:**
  ```
  .\.venv\Scripts\python test_verint_single_id.py <ID_DE_LLAMADA>
  ```
  Permite validar en segundos si la sesión de Verint responde y descarga el diálogo completo en formato Word (`.docx`).

---

## 3. Calendario Operativo y Dependencias de Negocio

### 3.1 Cronograma de Procesos

| Periodicidad | Proceso | Módulo / Ruta | Insumos Requeridos | Resultado Principal |
| :--- | :--- | :--- | :--- | :--- |
| **Diario** *(07:00 - 09:00)* | **Base Consumo** | Interfaz Web > Base Consumo | Reportes de tráfico y ventas desde Insight | Tablas maestras `M_EXP_VENTAS_*` e indicadores de gestión |
| **Diario** | **Proceso Calidad** | Interfaz Web > Calidad | Evaluaciones Insight, Verint SA y `ACCION_TOMADA.xlsx` | Tabla consolidada `M_EXP_CALIDAD_NOTA_FINAL` |
| **Mensual** *(Días 1 a 3)* | **Dotación** | Interfaz Web > Dotación | Plantillas de dotación comercial en OneDrive | Archivo preliminar para carga en aplicativo P021 |
| **Mensual** *(1er día útil)* | **Cierre Preliminar Calidad** | Interfaz Web > Calidad | Pipeline de Calidad consolidado del mes cerrado | Tablero preliminar y envío oficial por buzón |
| **Mensual** *(Día 2 hábil)* | **Consolidado Notas Cierre** | Interfaz Web > Calidad (Solo Cierre) | Calificaciones con levantamientos procesados | `DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE` (insumo oficial para otras áreas) |
| **Diario / Semanal** | **Transcripciones sofIA** | CLI (`run_sync_speech.py`) | Evaluaciones TC en Teradata, API Verint SA e Insight | Transcripciones enriquecidas en `DB_SPEECH.TRANSCRIPCION` para auditoría sofIA |
| **Mensual / Periódico** | **Piloto Tarjetas Adicionales (TCAD)** | CLI (`tcad_orchestrator.py`) | Matriz de tarjetas en `DLAB_DESNEGRET`, plantilla P026 y Speech Teradata | Base `DLAB_GEC.M_EXP_CROSS_TCAD` y consolidado `M_EXP_TCAD_BASE_MES` |
| **A demanda** | **Auditoría WhatsApp** | CLI (`run_transcript_audit.py`) | Archivos `.docx` de conversaciones y matriz de plantillas | Informe en Excel con evaluación de cumplimiento |
| **A demanda** | **Cumplimiento PA-TC** | CLI (`audit_cumplimiento_pa_tc.py`) | `Solicitud Cumplimiento TC 2026.xlsx` | Reporte de objeciones y validación de consentimientos |
| **A demanda** | **Descarga de Audios** | Interfaz Web > Genesys Audios | Correo de solicitud en formato Outlook | Archivos de audio almacenados localmente |

### 3.2 Precedencia Obligatoria: Cierre de Calidad vs. Nueva Base Consumo
Existe una dependencia de datos crítica entre el cierre mensual de Calidad y el inicio de la Base Consumo del mes entrante:
* Las tablas `DLAB_GEC.T_VENTAS_BPE_MARKET` y las vistas maestras `DLAB_GEC.M_EXP_VENTAS_*` contienen exclusivamente las transacciones del mes en curso.
* Si se procesa la Base Consumo de un nuevo período (por ejemplo, Septiembre) antes de finalizar el Cierre Oficial y la Fase 4 de Calidad del mes vencido (Agosto), las notas de calidad no podrán cruzarse contra las ventas del período correspondiente, resultando en notas con base cero.
* **Regla operativa:** Antes de iniciar la Base Consumo del primer día del mes, debe asegurarse que la Fase 4 y el Cierre Oficial de Calidad del mes anterior hayan culminado satisfactoriamente.

### 3.3 Protocolo de Cierre Mensual y Plazos de Levantamiento
El proceso de cierre comisional se rige por un cronograma predefinido y de conocimiento transversal en todas las salas de televentas:
1. **Primer día útil del mes (Tablero Preliminar):** Se ejecuta el pipeline completo de Calidad del período cerrado. Se valida la consistencia del tablero preliminar en Power BI y se coordina con Carolina el envío formal del comunicado preliminar desde el buzón oficial del área hacia todas las salas.
2. **Ventana de 2 días hábiles (Levantamientos de NTD):** A partir del envío oficial del preliminar, las salas disponen de un plazo improrrogable de dos (2) días hábiles para presentar solicitudes de levantamiento de Not To Do (NTD) o sustentos ante discrepancias en la data.
3. **Cierre de ventana y bloqueo de cambios:** Concluidos los 2 días hábiles, finaliza la recepción de solicitudes. Ningún cambio posterior es admitido, garantizando la equidad y consistencia del período comisional.
4. **Segundo día hábil (Publicación del Consolidado Oficial):** Se procesan los ajustes aprobados en `ACCION_TOMADA.xlsx`, se reejecutan las Fases 4 y 5 del mes cerrado y se corre la opción **Solo Cierre Mensual** en la plataforma. Este proceso genera la tabla principal **`DLAB_GEC.M_EXP_CALIDAD_CONSOLIDADO_NOTAS_CIERRE`** (script `03_consolidado_notas_cierre.sql`), la cual es el insumo central consumido por las demás áreas del banco para comisiones y reportería gerencial, debiendo quedar disponible e inmutable al cierre del segundo día hábil.

### 3.4 Sincronización de Transcripciones para el Motor sofIA
El motor **sofIA** automatiza la auditoría de calidad sobre llamadas de Tarjetas de Crédito evaluando el texto de las conversaciones:
* **Cadena de dependencias:**
  1. **Teradata:** Extrae los identificadores de llamadas (`CONID`/`ID_LLAMADA`) evaluadas bajo la plantilla `Exp. Compra - TC`.
  2. **Verint Speech Analytics:** Descarga las transcripciones completas mediante llamadas directas a la API REST de Verint ([verint_api_client.py](../../modules/verint/services/verint_api_client.py)).
  3. **Servidor Insight (`s425vp01`):** Resuelve y asocia el atributo comercial `TIPO_LEAD` a cada interacción.
  4. **SQL Server (`DB_SPEECH`):** Inserta por lotes (`batch_size=200`) el texto consolidado en la tabla `TRANSCRIPCION`.
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python -m modules.speech.tools.run_sync_speech --plantilla "Exp. Compra - TC"
  ```
  *(Para pruebas o extracciones parciales: use `--limit 10` o el flag `--skip-sql` si solo requiere guardar los archivos `.txt` en `data/transcripciones/`).*

### 3.5 Consolidación del Piloto de Tarjetas Adicionales (TCAD)
Procesa y concilia las colocaciones de tarjetas de crédito adicionales cruzando la venta contra Speech Analytics para verificar el cumplimiento del argumento comercial:
* **Cadena de dependencias y flujo de 2 pasos:**
  1. **Sincronización CROSS TCAD:** Extrae las colocaciones desde `DLAB_DESNEGRET.TLV_TARJETAS_MATRIZ` utilizando credenciales de `DESNEGRET`, aplica la plantilla de homologación `P026-CROSS_TCAD` y carga la data limpia en `DLAB_GEC.M_EXP_CROSS_TCAD`.
  2. **Consolidación Mensual SQL:** Ejecuta el script `01_dml_tcad_monthly_ingest.sql` en Teradata para el período `YYYYMM`, cruzando las colocaciones contra las auditorías de Speech Analytics (`FLG_NEW_SPEECH_TCAD`) para consolidar `DLAB_GEC.M_EXP_TCAD_BASE_MES`.
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python -m modules.Piloto_TCAD.use_cases.tcad_orchestrator --periodo 202608
  ```
  *(Si se despliega por primera vez en el entorno, ejecute previamente con `--setup` para crear las tablas y vistas DDL necesarias en Teradata).*

---

## 4. Operatoria mediante la Interfaz Web

### 4.1 Puesta en Marcha del Entorno
Para iniciar el servicio web local, ejecute el archivo [APP_CALIDAD.bat](../../APP_CALIDAD.bat) o inicie el servidor FastAPI mediante PowerShell:
```
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Ingrese a la consola desde el navegador: `http://127.0.0.1:8000`.

### 4.2 Proceso Calidad
1. Ingrese a la sección **Calidad**.
2. Indique el período de análisis en formato `YYYYMM` (ejemplo: `202608`).
3. Verifique que las casillas de las Fases 1 a 5 se encuentren marcadas.
4. Haga clic en **Ejecutar Pipeline Completo**.
5. **Flujo interno de ejecución:**
   * **Fases 1, 2 y 3 (Paralelo):** Descarga simultánea de evaluaciones manuales en Insight, registros de Speech Analytics desde Verint WFO y actualización de tipificaciones desde `ACCION_TOMADA.xlsx` en SharePoint.
   * **Fase 4 (Secuencial):** Homologación de preguntas, cruce contra la base de ventas de Teradata y cálculo de notas ponderadas (40% evaluación manual + 60% Speech Analytics).
   * **Fase 5 (Secuencial):** Clasificación de tipologías Not To Do (NTD) y reglas de impacto en nota.
6. **Recuperación ante fallas intermedias:** Si la ejecución se detiene por desconexión en Teradata durante la Fase 4 o 5, desmarque las Fases 1 a 3 (los insumos ya se encuentran en disco y cargados en tablas base) y reanude marcando únicamente las Fases 4 y 5. Puede emplear el control desplegable **Iniciar Fase 4 desde** para retomar desde el script SQL que presentó la contingencia.

### 4.3 Proceso de Base Consumo
1. Ingrese a la sección **Base Consumo**.
2. Seleccione el período de procesamiento correspondiente.
3. Presione **Iniciar Pipeline Consumo**.
4. **Flujo interno de ejecución:**
   * **Fases 1 a 3:** Descarga de insumos operativos de Insight bajo una sesión unificada, identificación de transferencias, desembolsos y validación de líneas de crédito mayores a 40K.
   * **Fase 4:** Ejecución de transformaciones SQL para ventas netas, control de consentimientos y llamadas sin registro de audio.
   * **Fase 5:** Extracción y conciliación del segmento Select.

### 4.4 Generación de Dotación Mensual
1. Ingrese a la sección **Dotación**.
2. Indique el mes de gestión a consolidar.
3. Presione **Ejecutar Pipeline de Dotación**.
4. El sistema consolida los reportes de ausentismo y vacaciones de OneDrive, genera el mapeo de supervisores y guarda el archivo:
   `data/input/proceso_calidad/<MES>_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx`
5. Este archivo debe ser remitido para la carga regular en Teradata mediante el sistema interno **P021**.

### 4.5 Cierre Mensual Definitivo
1. Se lleva a cabo una vez vencido el plazo de 2 días hábiles de descargos y con el visto bueno de jefatura.
2. En la sección **Calidad**, active la opción **Solo Cierre Mensual**.
3. Indique el período a congelar y presione **Ejecutar**. Este proceso traslada las calificaciones finales a la tabla gerencial `M_EXP_CALIDAD_NOTAS_TOTAL_GERENCIAL` para el cálculo de comisiones.

### 4.6 Solicitud y Descarga de Audios Genesys (Pestaña "Audios Genesys")
La plataforma web cuenta con un módulo interactivo dedicado para procesar solicitudes de grabaciones:
1. Ingrese a la pestaña **Audios Genesys** (`🎧 Audios Genesys`).
2. Indique el **Período de Búsqueda Genesys** (ejemplo: `202608`).
3. Elija el origen de las solicitudes:
   * **📧 Leer de Outlook:** Presione **Buscar últimos 3 correos**, seleccione en pantalla el correo deseado (asunto *Solicitud de audio*) y el sistema cargará automáticamente los registros detectados.
   * **✏️ Ingreso Manual:**
     * *Formulario Directo:* Permite digitar puntualmente el Registro del Ejecutivo (`B#####`), DNI y Producto/Prefijo (`AUDIO`, `EC`, `CC`, `SEG`, `HIP`, `PP`, `TC`).
     * *📋 Copiar y Pegar de Excel:* Permite copiar celdas directamente desde Microsoft Excel y pegarlas en el cuadro de texto. El analizador inteligente escaneará cada fila y extraerá el código de ejecutivo (`B#####`) y el DNI (`\d{8}`) **sin importar el orden de las columnas ni la presencia de encabezados**.
4. Presione **▶️ Iniciar Descarga de Audios Genesys**. La plataforma se conectará al navegador Chrome vía CDP (`http://localhost:9222`), enriquecerá los teléfonos de gestión desde Teradata (`E_DW_VIEWS.V_CONT_TELEFONO_APICLIENTE`) y descargará los archivos de audio en `data/downloads/audios/genesys/`.

### 4.7 Verificación de Sincronización con Power BI
Power BI valida la actualización de las fuentes consultando la fecha y hora de los siguientes archivos testigo en `data/reports/`:
* `conector_calidad.txt`: Se actualiza al concluir exitosamente la Fase 4 de Calidad.
* `conector_base_consumo.txt`: Se actualiza al concluir exitosamente la Fase 4 de Consumo.
Si los tableros no reflejan la información procesada, compruebe que estos archivos muestren la marca temporal del día.

---

## 5. Procesos por Línea de Comandos (CLI) y Pilotos

Estos módulos se ejecutan mediante scripts independientes utilizando el entorno virtual del proyecto (`.\.venv\Scripts\python`).

### 5.1 Auditoría de Conversaciones de WhatsApp mediante Gemini
Evalúa el cumplimiento normativo y argumentario comercial en conversaciones de chat.
* **Origen de los archivos `.docx`:** No provienen de un script de descarga automática; son **exportaciones directas de Genesys Cloud** (obtenidas desde la consola web en el detalle de cada interacción mediante la opción *Descargar/Exportar transcripción*, nombradas por defecto como `<conversationId>.docx`) o remitidas como muestra mensual por la supervisión de canales digitales.
* **Insumos necesarios (en `data/input/auditorias_wsp/`):**
  * Archivos `.docx` de las interacciones a evaluar.
  * `Ejecutivos_Gestion_Wsp.xlsx`: Archivo de mapeo que asocia el `ID_Interaccion` (nombre del `.docx`) con la matrícula (`REGISTRO COLABORADOR`), nombre y supervisor del ejecutivo evaluado.
  * `Plantillas TLV WhatsApp.xlsx`: Matriz de plantillas y reglas normativas oficiales.
* **Configuración previa:** Verificar la presencia de `GEMINI_API_KEY` en el archivo `.env`.
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python modules/verint/tools/run_transcript_audit.py
  ```
* **Resultado:** Reporte consolidado en `logs/Reporte_Auditoria_WhatsApp_YYYYMMDD_HHMMSS.xlsx` con la calificación global y la tipificación de desvíos detectados por conversación.

### 5.2 Auditoría de Cumplimiento PA-TC (Pago Automático)
Identifica interacciones donde se registró venta de Pago Automático sin consentimiento expreso o ante negativa explícita del cliente.
* **Flujo end-to-end integrado:**
  1. Extrae teléfonos por DNI desde Teradata (`E_DW_VIEWS.V_CONT_TELEFONO_APICLIENTE`).
  2. Consulta la API de Genesys Cloud para ubicar el `conversationId` y fecha de llamada.
  3. Consulta la API de Verint Speech Analytics para descargar la transcripción con marcas temporales `mm:ss`.
  4. Audita con el modelo Gemini para ubicar el minuto/segundo de objeción o no aceptación del cliente.
* **Insumo necesario:** Archivo `Solicitud Cumplimiento TC 2026.xlsx` en la raíz del proyecto.
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python modules/calidad/tools/audit_cumplimiento_pa_tc.py
  ```
* **Resultado:** Archivo con los segundos exactos de la llamada donde se localiza la objeción del usuario.

### 5.3 Extracción Masiva de Transcripciones desde Verint por ID de Conversación
Extrae en lote las transcripciones completas de llamadas de voz desde Verint Speech Analytics navegando y consultando por ID de conversación (`CONID`):
* **Flujo técnico:**
  1. Consulta en Teradata (`DLAB_GEC.M_EXP_CALIDAD_DETALLE_PURE_CLOUD`) todos los `CONID` de llamadas de televentas (`SUB_EQUIPO = 'TC'`) para el período indicado.
  2. Inicia una sesión automatizada en Verint WFO y abre Speech Analytics.
  3. Consulta llamada por llamada por su ID (`CONID`), extrayendo el texto íntegro de la conversación.
  4. Genera los archivos `.txt` en `data/transcripciones/` con el patrón `Transcripcion_Verint_{CONID}_{FECHA}_{DNI}_{EJECUTIVO}.txt`.
* **Comandos de ejecución:**
  ```
  # Modo estándar en segundo plano (headless)
  .\.venv\Scripts\python modules/verint/tools/batch_verint_extractor.py --periodo 202608

  # Modo con ventana visible de navegador (para monitoreo visual)
  .\.venv\Scripts\python modules/verint/tools/batch_verint_extractor.py --periodo 202608 --visible
  ```
* **Descarga de transcripciones por lista Excel (Cumplimiento PA):**
  Para extraer transcripciones de una muestra específica listada en Excel, ejecute:
  ```
  .\.venv\Scripts\python modules/verint/tools/download_transcripts_from_verint.py "Solicitud Cumplimiento TC 2026.xlsx" "data/transcripciones_pa"
  ```

### 5.4 Ejecución de Audios Genesys por Consola (CLI Alternativo)
> **Nota Operativa:** El método principal y recomendado para el día a día es a través de la pestaña **Audios Genesys** de la interfaz web (ver [Sección 4.6](#46-solicitud-y-descarga-de-audios-genesys-pestaña-audios-genesys)). La ejecución por consola se reserva para automatizaciones batch o tareas desatendidas.

Permite procesar solicitudes de Outlook o listas de casos directamente desde la terminal:
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python modules/genesys/main.py
  ```

### 5.5 Piloto de Tarjetas Adicionales (TCAD)
Procesa la base de colocaciones de tarjetas de crédito adicionales.
* **Comando de ejecución:**
  ```
  .\.venv\Scripts\python -m modules.Piloto_TCAD.use_cases.tcad_orchestrator --periodo 202608
  ```

### 5.6 Piloto No Venta
Extrae y cataloga llamadas sin cierre comercial para análisis de motivos de rechazo.
* **Ubicación:** `modules/piloto_no_venta/sql/`
* **Procedimiento:** Ejecución de las consultas en Teradata (`DLAB_GEC`) filtrando por el rango de fechas requerido.

### 5.7 Extracción y Sincronización de Transcripciones a SQL Server (Motor sofIA)
Pipeline automatizado end-to-end que extrae diálogos, los enriquece con metadatos comerciales y los persiste en la base central consumida por el modelo de IA **sofIA** para la auditoría y precalificación automática de llamadas de Tarjetas de Crédito (TC).

* **Arquitectura del flujo (4 etapas secuenciales):**
  1. **Extracción desde Teradata:** Consulta las llamadas evaluadas de la plantilla comercial (por defecto `Exp. Compra - TC`), obteniendo `ID_LLAMADA`, `PRODUCTO`, `FECHA_LLAMADA`, `DNI` y matrícula (`REGISTRO`) del ejecutivo.
  2. **Descarga de transcripciones desde Verint:** Comprueba si el diálogo ya reside localmente en `data/transcripciones/`. Si no existe, invoca al cliente HTTP API REST de Verint ([verint_api_client.py](../../modules/verint/services/verint_api_client.py)) para descargar el texto íntegro en milisegundos sin requerir navegador.
  3. **Enriquecimiento comercial en Insight:** Consulta la base de datos de Insight (`s425vp01`) mediante [insight_lead_service.py](../../modules/speech/services/insight_lead_service.py) para catalogar la procedencia de la gestión comercial (`TIPO_LEAD`).
  4. **Persistencia por lotes en SQL Server (`DB_SPEECH`):** Garantiza la existencia de la tabla `TRANSCRIPCION` y ejecuta un upsert masivo por lotes de 200 registros (`ID_LLAMADA`, `PRODUCTO`, `FECHA_LLAMADA`, `DNI`, `REGISTRO`, `TIPO_LEAD`, `TRANSCRIPCION`).
* **Comandos CLI de ejecución:**
  ```powershell
  # Ejecución completa para la plantilla oficial de TC
  .\.venv\Scripts\python -m modules.speech.tools.run_sync_speech --plantilla "Exp. Compra - TC"

  # Muestra de validación rápida (ejemplo: primeras 10 interacciones)
  .\.venv\Scripts\python -m modules.speech.tools.run_sync_speech --limit 10

  # Modo solo descarga (almacena los .txt localmente sin impactar SQL Server)
  .\.venv\Scripts\python -m modules.speech.tools.run_sync_speech --skip-sql

  # Modo solo carga a SQL Server (reutiliza transcripciones .txt ya descargadas)
  .\.venv\Scripts\python -m modules.speech.tools.run_sync_speech --skip-download
  ```
* **Propósito e impacto de negocio:** Permite que el motor de machine learning sofIA evalúe automáticamente las llamadas de televentas, liberando horas hombre a las analistas de calidad para enfocarse en análisis de objeciones y salas complejas como SELECT.

### 5.8 Mapeo de Nuevas Preguntas de Calidad en Teradata
Si durante la Fase 4 de Calidad se emite una advertencia por preguntas no reconocidas:
1. Abra el script [00_setup_homologaciones.sql](../../modules/calidad/sql/00_setup_homologaciones.sql).
2. Agregue el insert en la tabla `DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_PREGUNTA` asociando el texto original de la pregunta de Insight con su código homologado.
3. Ejecute la sentencia con el usuario `APP_GEC`, aplique `COMMIT` y reanude la Fase 4 desde la interfaz web.

---

## 6. Procedimientos de Contingencia Operativa

### 6.1 Liberación de Bloqueos de Archivo en Microsoft Excel
La actualización de vínculos en libros compartidos de SharePoint (`ACCION_TOMADA.xlsx` y plantillas de dotación) se realiza mediante automatización COM de Windows.
* **Síntoma:** Error de ejecución `PermissionError: [Errno 13] Permission denied`.
* **Causa:** Un proceso previo de Excel no cerró correctamente y mantiene bloqueado el archivo en segundo plano.
* **Solución:** Abra el Administrador de Tareas de Windows (Ctrl + Shift + Esc), localice en la lista de procesos en segundo plano cualquier entrada denominada **Microsoft Excel** (`EXCEL.EXE`) y presione **Finalizar tarea**. Posteriormente, vuelva a ejecutar la fase correspondiente.

### 6.2 Desconexión de Sesiones en Teradata
* **Síntoma:** Mensaje `Error de comunicación con el Gateway` o `Socket connection reset`.
* **Causa:** Caída temporal de la VPN corporativa o expiración del límite de conexiones concurrentes del usuario `APP_GEC`.
* **Solución:** Compruebe que la VPN se encuentre activa. Si la desconexión ocurrió en Fase 4 o 5, no reinicie la descarga de insumos; ejecute únicamente a partir de la Fase 4 indicando el último script exitoso.

### 6.3 Renovación de Credenciales
* **Contraseña de Teradata (`APP_GEC`):** Si el log reporta `Error 8017: UserId or Password invalid`, actualice el valor de la clave `TERADATA_PASSWORD` en el archivo local `.env`.
* **Sesión Web de Verint:** Si la descarga de Speech Analytics retorna error de autenticación (código 401), inicie sesión en Verint WFO desde el navegador, copie los valores vigentes de cookies de sesión y actualice la variable `VERINT_COOKIES` en el archivo `.env`.

---

## 7. Directorio de Soporte y Contactos Clave

| Rol / Especialidad | Persona de Contacto / Canal | Área | Detalle de Gestión |
| :--- | :--- | :--- | :--- |
| **Aprobación de Accesos Teradata (`DLAB_DESNEGRET`)** | Jose Salcedo (Aprobador) | Inteligencia Comercial | Aprobación formal de tickets de acceso e instalación vía **Smart Desk**. |
| **Soporte de Conexión ODBC Teradata (`CNX_TERA_USER`)** | Juan Carlos Mondalgo | Inteligencia Comercial | Orientación técnica para la configuración del DSN y modelos de datos. |
| **Acceso a SharePoint de Calidad y Reportes** | Vanessa Ortega / Juan Carlos Mondalgo | Calidad y Experiencia | Habilitación de permisos en el sitio SharePoint `InteligenciayExperienciaCanal` y acceso al área de trabajo (workspace) en Power BI Service (**CANALES Y SRVICIO AL CLIENTE**, reporte **CALIDAD de servicios**). |
| **Dotación Comercial y Ausentismos** | Carolina Angulo | Operaciones Televentas | Coordinación y entrega de plantillas de dotación y ausentismos (tanto General como sala Select). |
| **Infraestructura Speech Analytics Verint** | Carlos Jurado | Canales Digitales | Soporte de la consola Verint WFO y recepción del consolidado mensual de licencias SA para su asignación. |
| **Acceso a Portal Insight (`s425vp01`)** | Portal de Accesos (**Smart Desk**) | Canales Digitales | Solicitud formal mediante Portal de Accesos (orientación con **Juan Carlos Mondalgo**). Indicar acceso obligatorio a las 2 bases/áreas: **`GCI_PRD_Insight_TLVentas`** y **`GCI_PRD_Insight_ACOE`**. |
| **Acceso a Insight Digital (WhatsApp)** | Gary Tamara | Canales Digitales | Orientación y gestión de acceso al entorno de Insight Digital para la extracción de métricas y gestiones estructuradas de WhatsApp. |
| **Genesys Cloud** | Acceso estándar corporativo | Canales Digitales | Habilitado por defecto para el equipo mediante inicio de sesión único (SSO Microsoft). |

---

## 8. Hoja de Ruta e Iniciativas Pendientes (Próximos Pasos)

Proyectos estratégicos en cartera y mejoras técnicas identificadas para la continuidad y evolución operativa de la plataforma:

| # | Iniciativa | Estado Actual | Objetivo y Detalle Operativo |
| :---: | :--- | :---: | :--- |
| **1** | **Redistribución de Reclamos en GIRU** | Backlog Prioritario | Implementar el algoritmo de balanceo y asignación equitativa de reclamos operativos en la plataforma GIRU para descongestionar colas de atención. |
| **2** | **Ampliación a 2 Evaluaciones en SELECT** | En espera de capacidad | Incrementar la cuota de auditoría de 1 a 2 evaluaciones por asesor en la sala SELECT. Requiere la liberación de horas del equipo cuando se estabilice la automatización de tarjetas (sofIA) y el flujo de Retenciones. |
| **3** | **Cursos Modulares para Asesores TLV** | Backlog | Despliegue de contenidos formativos y de auto-evaluación para ejecutivos de televentas en estándares normativos, manejo de objeciones y causales frecuentes de NTD. |
| **4** | **Estandarización de Power Apps Blacklist** | Mejora de UI | Reemplazar campos de texto libre por categorías predefinidas en el formulario de Blacklist para evitar dispersión y facilitar cruces automatizados. |
| **5** | **Consolidación del Piloto No Venta** | En desarrollo (`modules/piloto_no_venta/`) | Integrar las consultas SQL actuales a un flujo automatizado dentro de la interfaz web para cruzar gestiones sin cierre contra ventas efectivas posteriores. |
| **6** | **Automatización del Piloto TCAD** | En transición (`modules/Piloto TCAD/`) | Convertir la rutina de análisis de Tarjetas Adicionales en un reporte automatizado semanal recurrente. |
| **7** | **Centralización de Insumos en SharePoint Institucional** | Estratégico | Migrar los insumos que hoy residen en carpetas de OneDrive personales hacia un SharePoint del área de Inteligencia y Experiencia, garantizando la independencia de rutas ante rotación de colaboradores. |
| **8** | **Planificador Automático (Scheduler) y Alertas** | Mejora Técnica | Configurar un servicio de ejecución programada desatendida para la Base Consumo diaria y alertas automáticas por correo o Teams ante errores de conexión en scripts SQL. |
| **9** | **Unificación de Tableros Power BI de Base Consumo** | En Cartera (Optimización BI) | Consolidar los 3 tableros actuales de Base Consumo en un único modelo semántico centralizado en Power BI Service, reduciendo la redundancia de consultas en Teradata (`CNX_TERA_USER`), optimizando el Gateway y unificando la vista ejecutiva para el negocio. |
