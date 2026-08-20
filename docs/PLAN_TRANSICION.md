# 🔄 Plan de Transición — APP_CALIDAD (Plataforma Calidad Televentas)

> Documento para el equipo receptor. Cubre dependencias absolutas, credenciales, rutas, accesos y el procedimiento paso a paso para levantar la plataforma en una máquina nueva.

---

## 1. 📋 Resumen Ejecutivo

| Campo | Valor |
|---|---|
| **Nombre del proyecto** | APP_CALIDAD / UPLOADER_V2 |
| **Stack principal** | Python 3.11 · FastAPI · Polars · Playwright · Teradata |
| **Sistema operativo** | Windows 10/11 (OBLIGATORIO — COM automation con Outlook y Excel) |
| **Punto de entrada** | `APP_CALIDAD.bat` (doble clic) |
| **Puerto local** | `http://127.0.0.1:8000` |

---

## 2. 🔑 Credenciales y Accesos (CRÍTICO)

> [!CAUTION]
> Todo lo que está en esta sección es información sensible. El equipo receptor debe rotar las contraseñas personales y obtener sus propios accesos. Las credenciales del usuario genérico `APP_GEC` pueden mantenerse.

### 2.1 Teradata (Conexión Principal — `IBKTD`)

| Variable `.env` | Valor Actual | Quién gestiona |
|---|---|---|
| `TERADATA_HOST` | `IBKTD` | DBAs Interbank |
| `TERADATA_USER` | `APP_GEC` | DBAs Interbank (usuario genérico) |
| `TERADATA_PASSWORD` | `Int3l1g3nc14cl0ud*` | DBAs Interbank |
| `TERADATA_LOGMECH` | `TD2` | — |

> [!NOTE]
> El usuario **`APP_GEC`** es un usuario genérico de servicio compartido del área. No cambiar y no rotar sin coordinación con los DBAs.

### 2.2 Teradata (Conexión Secundaria — `SELECT` consultas analíticas)

| Variable `.env` | Valor Actual | Quién gestiona |
|---|---|---|
| `TERADATA_USER_SELECT` | `B44922` | **Personal del exresponsable — ROTAR** |
| `TERADATA_PASSWORD_SELECT` | `Interbank20263.#` | **Personal del exresponsable — ROTAR** |
| `TERADATA_HOST_SELECT` | `IBKTD` | DBAs Interbank |
| `TERADATA_LOGMECH_SELECT` | `LDAP` | — |

> [!WARNING]
> Esta credencial es el usuario corporativo personal `B44922`. El nuevo responsable debe poner su propio código de usuario LDAP en `.env`.

### 2.3 Insight (PureCloud — Evaluaciones Manuales)

| Campo | Valor |
|---|---|
| **URL** | `https://s425vp01/Insight` |
| **Usuario** | `B44922` (personal — **ROTAR**) |
| **Quién gestiona acceso** | **Carlos Alexander Cruz Valeria** — solicitar acceso manual a la plataforma Insight |

### 2.4 Verint Cloud (Speech Analytics)

| Campo | Valor |
|---|---|
| **URL** | `https://wfo.mt5.verintcloudservices.com/wfo/control/signin` |
| **Usuario** | `jgonzaleses@intercorp.com.pe` (personal — **ROTAR**) |
| **Quién gestiona acceso** | **Carlos Jurado** — solicitar por correo con: nombre completo, correo y registro |
| **Nota técnica** | La app renueva cookies automáticamente con Playwright SSO. Las `VERINT_COOKIES` en `.env` son caché y se regeneran. No son críticas, pero permiten arranque sin SSO. |

### 2.5 Genesys Cloud (PureCloud CX — Descarga de Audios)

| Campo | Valor |
|---|---|
| **URL** | `https://apps.mypurecloud.com/directory/#/analytics/interactions` |
| **Acceso** | Login con credenciales corporativas (SSO Interbank) |
| **Chrome CDP** | La app se conecta a Chrome con `--remote-debugging-port=9222`. Chrome DEBE estar abierto y sesión iniciada antes de lanzar la app. |

### 2.6 SQL Server (Ingesta BN_DESEMBOLSO — PENDIENTE COMPLETAR)

| Variable `.env` | Valor Actual |
|---|---|
| `SQLSERVER_SERVER` | `tu_servidor_sql` (**No configurado — completar**) |
| `SQLSERVER_DATABASE` | `tu_base_de_datos` |
| `SQLSERVER_USER` | `tu_usuario` |
| `SQLSERVER_PASSWORD` | `tu_contraseña` |
| `SQLSERVER_DRIVER` | `{ODBC Driver 17 for SQL Server}` |

### 2.7 Gemini API (LLM — Auditoría de Transcripciones)

| Campo | Detalle |
|---|---|
| **Variable** | `GEMINI_API_KEY` en `.env` (clave personal — **ROTAR con clave propia**) |
| **Uso** | Módulo `tools/run_transcript_audit.py` + `infrastructure/llm/gemini_client.py` |
| **Cómo obtener** | Generar nueva API Key en [console.cloud.google.com](https://console.cloud.google.com) con cuenta corporativa Interbank |

### 2.8 Power BI (Workspace de Reportería)

| Campo | Detalle |
|---|---|
| **Acceso** | Ingresar con usuario corporativo propio (no se usan cuentas genéricas) |
| **Workspace** | `CANALES Y SERVICIO AL CLIENTE` en Power BI Service |
| **Quién otorga permisos** | **Vanessa Ortega** o **Juan Carlos Mondalgo** — solicitar acceso al workspace |

---

## 3. 💻 Dependencias de Software (Requisitos de la Máquina)

### 3.1 Sistema Operativo

- ✅ **Windows 10 o Windows 11** (OBLIGATORIO)
- ❌ NO funciona en Linux/Mac por dependencias de COM Automation (`win32com`, `pywin32`)

### 3.2 Software Pre-Instalado (ANTES de clonar el repo)

| Software | Versión mínima | Motivo |
|---|---|---|
| **Python** | 3.11+ | Runtime de la app |
| **Microsoft Excel** | 2016+ | COM Automation para descarga de Insight (`.xlsx`) |
| **Microsoft Outlook Desktop** | 2016+ | Lectura de buzón para solicitudes de audios Genesys |
| **Google Chrome** | Cualquier estable | CDP (remote debugging) para módulo Genesys |
| **Teradata JDBC / ODBC Driver** | Compatible con `IBKTD` | Conexión `teradatasql` / `pyodbc` |
| **ODBC Driver 17 for SQL Server** | 17+ | Ingesta BN_DESEMBOLSO desde SQL Server |
| **Git** | 2.x | Clonación y control de versiones |

### 3.3 Dependencias Python (`requirements.txt`)

```
fastapi          # Framework API REST
uvicorn          # Servidor ASGI
polars           # Engine de DataFrames de alto rendimiento
python-calamine  # Lector nativo .xlsx sin Java (Calamine/Rust)
pyarrow          # Serialización Arrow
fastexcel        # Lector Excel rápido
openpyxl         # Lector/escritor Excel (fallback)
pandas           # DataFrames (uso puntual)
teradatasql      # Driver oficial Teradata Python
pyodbc           # Driver ODBC genérico (SQL Server)
python-dotenv    # Carga de .env
playwright       # Browser automation (Verint SSO y Genesys CDP)
pywin32          # COM Automation (Outlook + Excel COM)
requests         # HTTP client (Verint API)
rapidfuzz        # Fuzzy matching de nombres de columnas
google-genai     # Gemini LLM API client
websockets       # SSE/WebSocket para logs en tiempo real
python-multipart # Soporte multipart/form-data (uploads)
plyer            # Notificaciones nativas Windows
```

---

## 4. 🗂️ Rutas Críticas y Estructura

### 4.1 Rutas Absolutas Hardcodeadas

> La app **NO tiene rutas absolutas hardcodeadas**. Usa `Path(__file__).resolve().parents[N]` y rutas relativas. Puede copiarse a **cualquier ruta** en la máquina destino.

### 4.2 Directorios que DEBEN existir (se crean automáticamente en primer uso)

| Directorio | Propósito |
|---|---|
| `data/input/proceso_calidad/` | CSVs de entrada para descarga Verint (`EV_{PERIODO}.csv`) |
| `data/verint_browser_profile/` | Perfil de sesión headless Playwright para Verint |
| `modules/genesys/.chrome_genesys_profile/` | Perfil persistente de Chrome CDP para Genesys |
| `modules/genesys/tracking.json` | Tracking de audios ya descargados |
| `modules/genesys/telefonos_cache.json` | Caché de teléfonos de contacto |
| `logs/` | Logs de ejecución de la app |
| `transcripciones_genesys/` | Output de transcripciones descargadas |

### 4.3 Archivos de Configuración Clave

| Archivo | Propósito | Frecuencia de cambio |
|---|---|---|
| `.env` | **TODAS las credenciales** | Por rotación de contraseñas |
| `config/config.json` | Tablas Teradata a validar, secuencia SQL de calidad, cortes de fechas | Por cambio de proceso de negocio |
| `config/plantillas.json` | Mapeo de columnas Excel → Teradata para las ~31 plantillas | Por nuevas fuentes o renombrado de columnas en Verint/Insight |
| `APP_CALIDAD.bat` | Launcher — detecta `.venv` y arranca uvicorn en puerto 8000 | Raramente |

---

## 5. 📊 Tablas Teradata Requeridas

Todas las tablas listadas a continuación deben existir en `IBKTD`. El usuario `APP_GEC` ya cuenta con los permisos necesarios por ser una cuenta genérica del área.

### Tablas de Destino (INSERT/DELETE)

| Tabla | Módulo |
|---|---|
| `DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE` | Calidad — Insight |
| `DLAB_GEC.M_EXP_CALIDAD_DATA_SPEECH_ANALYTICS` | Calidad — Verint SA |
| `DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE` | Calidad — Acciones Tomadas |
| `DLAB_GEC.M_EXP_NTD_REPORTING_HISTORICO` | Calidad — NTD histórico |
| `DLAB_GEC.M_EXP_STAGE_NO_VENTA` | Piloto No Venta — Stage |
| `DLAB_GEC.M_EXP_PILOTO_NO_VENTA` | Piloto No Venta — Histórico |
| `DLAB_GEC.M_EXP_DATA_TCAD_SA` | Piloto TCAD — Stage SA |
| `DLAB_GEC.M_EXP_CROSS_TCAD` | Piloto TCAD — Cruce final |

### Tablas de Origen (SELECT — READ ONLY)

`M_EXP_VENTAS_TC`, `M_EXP_VENTAS_PP`, `M_EXP_VENTAS_EC`, `M_EXP_VENTAS_CD`, `M_EXP_VENTAS_SEG`, `M_EXP_VENTAS_CON`, `M_EXP_VENTAS_IL`, `M_EXP_VENTAS_TCA`, `M_EXP_VENTAS_UPG`, `M_EXP_VENTAS_PA`, `T_VENTAS_BPE_MARKET`, `TLV_CARGA_ACTUAL`, `TLV_CARGA_ACTUAL_DIGITAL`, `V_GESTION_BNC`, `V_GESTION_CHIP`, `T_RETENCION_BASE_CALIDAD_GIRU`, `E_DW_VIEWS_DLAB.V_CNV_VISTA_RETENCION_BT`, `E_DW_VIEWS.V_FCT_RT_TC_HISTORICO`.

---

## 6. 🚀 Procedimiento de Instalación en Máquina Nueva

```powershell
# Paso 1 — Verificar pre-requisitos
python --version          # debe ser 3.11+
git --version

# Paso 2 — Clonar repositorio
git clone <URL_REPO> APP_CALIDAD
cd APP_CALIDAD

# Paso 3 — Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\activate

# Paso 4 — Instalar dependencias
pip install -r requirements.txt

# Paso 5 — Instalar Chromium para Playwright (solo para módulo Verint SSO)
# NOTA: El módulo Genesys NO requiere esto — usa el Chrome.exe instalado del usuario
#       vía remote-debugging-port=9222. Playwright solo se usa para el harvester
#       de cookies de Verint (login headless automático).
.\.venv\Scripts\playwright install chromium

# Paso 6 — Configurar credenciales
notepad .env
# Actualizar: TERADATA_USER_SELECT, TERADATA_PASSWORD_SELECT,
#             USERNAME_INSIGHT, PASSWORD_INSIGHT,
#             VERINT_USER, VERINT_PASS

# Paso 7 — Verificar Teradata
.\.venv\Scripts\python -c "import teradatasql, os; from dotenv import load_dotenv; load_dotenv(); con = teradatasql.connect(host='IBKTD', user=os.getenv('TERADATA_USER'), password=os.getenv('TERADATA_PASSWORD'), logmech='TD2'); print('OK'); con.close()"

# Paso 8 — Configurar Chrome para Genesys (una vez)
# Abrir en CMD:
# "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%APPDATA%\ChromeGenesys"
# Iniciar sesión en Genesys Cloud manualmente. Dejar Chrome abierto.

# Paso 9 — Arrancar la app
.\APP_CALIDAD.bat
```

---

## 7. ⚠️ Cuidados Críticos (Gotchas)

| # | Riesgo | Solución |
|---|---|---|
| 1 | **Sesión Teradata volátil** | Las `VT_*` se borran al desconectarse. Ejecutar todo el SQL en una sesión. La tabla final `M_EXP_PILOTO_NO_VENTA` es permanente. |
| 2 | **`CD` como alias Teradata** | `CD` es token reservado. Nunca usar como alias. Usar `CDEUDA` o similar. |
| 3 | **Cookies Verint expiran** | Si falla con 401/403, limpiar `data/verint_browser_profile/` y dejar que Playwright haga login nuevamente. |
| 4 | **Chrome debe estar abierto** | Para Genesys, Chrome con `--remote-debugging-port=9222` debe estar abierto y logueado ANTES de arrancar la app. |
| 5 | **Outlook debe estar abierto** | El módulo de solicitud de audios requiere Outlook Desktop abierto y activo. |
| 6 | **Fila 29 en reportes Verint** | Los `.xlsx` de Verint tienen 28 filas de metadatos. Si Verint cambia el formato, actualizar en `infrastructure/parsers/readers.py`. |
| 7 | **`.env` NO en Git** | `.gitignore` ya lo excluye. NUNCA subir al repositorio. |
| 8 | **Rotar credenciales personales** | Las credenciales `B44922` son del exresponsable. ROTAR antes del primer uso en producción. |
| 9 | **SQL Server pendiente** | Las credenciales de SQL Server en `.env` son placeholders. Coordinar con el equipo de datos. |
| 10 | **Directorio `legacy/`** | Código Streamlit obsoleto. NO usar, NO modificar, NO ejecutar. |

---

## 8. 📞 Contactos Clave para Accesos

| Sistema | Contacto |
|---|---|
| Teradata `IBKTD` — usuario `APP_GEC` | DBAs Interbank — Soporte de Datos |
| Verint WFO (Speech Analytics) | **Carlos Jurado** — correo con nombre completo, correo corporativo y registro |
| Insight / PureCloud (evaluaciones) | **Carlos Alexander Cruz Valeria** — solicitud manual de acceso |
| Power BI — workspace `CANALES Y SERVICIO AL CLIENTE` | **Vanessa Ortega** o **Juan Carlos Mondalgo** |
| SharePoint (Speech Explorers y archivos del área) | **Vanessa Ortega** o **Juan Carlos Mondalgo** |
| Genesys Cloud | SSO corporativo — Soporte TI Interbank |
| Gemini API Key | Generar en Google Cloud Console con cuenta corporativa propia |

---

## 9. 📁 Checklist de Archivos a Traspasar

```
✅ APP_CALIDAD/               ← Carpeta completa del proyecto
   ✅ .env                    ← CREDENCIALES (entregar en canal seguro, NO por email)
   ✅ config/plantillas.json  ← Mapeo de columnas (~160KB — CRÍTICO)
   ✅ config/config.json      ← Configuración de proceso
   ✅ requirements.txt        ← Dependencias Python
   ✅ APP_CALIDAD.bat         ← Launcher
   ✅ ACCESOS_EXPERIENCIA.txt ← Accesos históricos del área
   ✅ Diccionario_Categorias_Verint.json  ← Diccionario Verint (~980KB)
   ✅ docs/                   ← Documentación técnica de flujos
   ✅ architecture.html       ← Visualizador interactivo de arquitectura
   ✅ architecture.json       ← Topología estructurada
   ⚠️ .venv/                 ← Opcional (900MB+). Preferible recrear.
   ❌ legacy/                 ← NO traspasar. Código obsoleto.
```

---

## 10. 🗓️ Agenda de Transición Sugerida

| Semana | Actividad |
|---|---|
| **Semana 1** | Solicitar accesos: Verint (Carlos Jurado), Insight (Carlos Alexander Cruz Valeria), Power BI workspace (Vanessa Ortega / Juan Carlos Mondalgo) |
| **Semana 1** | Instalar pre-requisitos en máquina del sucesor (Python 3.11+, Excel, Outlook, Chrome, drivers Teradata) |
| **Semana 1** | Clonar repositorio, instalar dependencias Python y ejecutar `playwright install chromium` |
| **Semana 2** | Configurar `.env` con credenciales propias. Verificar conectividad Teradata y diagnóstico de entorno en la app. |
| **Semana 2** | **Shadowing**: ejecutar proceso Calidad (PBI evaluaciones) completo juntos |
| **Semana 3** | **Shadowing**: ejecutar proceso Consumo (KRI ventas) completo |
| **Semana 3** | Ejecutar Cierre Mensual y validar módulo Genesys (abrir Chrome con `--remote-debugging-port=9222` e iniciar sesión) |
| **Semana 4** | Primera ejecución autónoma del sucesor (con soporte de respaldo) |
| **Semana 4** | Entrega formal: rotar TODAS las credenciales personales del exresponsable en `.env` |
