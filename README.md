# ⚡ Plataforma Calidad Televentas (FastAPI + React SPA)

Plataforma unificada de alto rendimiento para la orquestación de pipelines de datos de **Consumo (KRI Ventas)**, **Calidad (NTD)**, **Modo Cierre Mensual**, **Solicitud de Audios (Genesys/Outlook)** e **Ingesta de datos a Teradata**.

---

## 📋 Tabla de Contenidos
1. [Arquitectura y Rendimiento](#-arquitectura-y-rendimiento)
2. [Cómo Ejecutar](#-cómo-ejecutar)
3. [Funcionalidades Principales](#-funcionalidades-principales)
4. [Documentación Técnica (Carpeta docs/)](#-documentación-técnica-carpeta-docs)
5. [Estructura del Proyecto](#-estructura-del-proyecto)
6. [Modo de Respaldo (Streamlit)](#-modo-de-respaldo-streamlit)

---

## 🚀 Arquitectura y Rendimiento

La plataforma utiliza una arquitectura desacoplada:
- **Backend**: **FastAPI** (Python 3.11+) con WebSockets para transmisión de eventos en vivo sin bloquear el hilo principal.
- **Frontend**: **React 18 SPA** servido de forma estática ultra-rápida (tiempo de arranque **<30 ms**).
- **Notificaciones**: Notificaciones nativas de escritorio en Windows con duración de 5 segundos al culminar orquestaciones.

---

## ⚡ Cómo Ejecutar

Simplemente ejecuta el archivo ejecutable en la raíz del proyecto:

```cmd
APP_CALIDAD.bat
```

Esto iniciará el servidor Uvicorn FastAPI en `http://127.0.0.1:8000` y abrirá automáticamente la aplicación en tu navegador predeterminado.

---

## 🛠️ Funcionalidades Principales

1. **📁 Subir a Teradata**: Ingesta masiva de archivos Excel, CSV o Texto tabulado con vista previa interactiva, editor de tipos de columnas SQL y prevención de registros duplicados.
2. **🎧 Solicitud de Audios (Genesys)**: Lectura automática de correos en Outlook Desktop y formularios directos o pegado masivo desde Excel para descarga automatizada en Genesys Cloud.
3. **⚡ PBI Base Consumo**: Orquestación en 5 Fases del pipeline de Consumo (`1. Insight`, `2. CD40K`, `3. BN Desembolsos`, `4. Proceso SQL`, `5. SELECT`) con ejecuciones parametrizadas de scripts Teradata SQL (`VENTAS_DN`, `CD40K`, `SOURCE_TVL`, `CA_CONSENTIMIENTO_DIARIO`, `KRI_VENTAS_SIN_AUDIO`, `TLF_NO_AUTORIZADO`).
4. **📊 PBI Evaluaciones Calidad**: Orquestación en 5 Fases para el consolidado de calidad NTD.
5. **🔒 Modo Cierre Mensual**: Ejecución aislada e idempotente de los scripts de cierre mensual (`01_auditoria_y_cierre.sql` y `02_kri_resumen_total.sql`) con selección individual de scripts desde la UI.
6. **🩺 Diagnóstico de Entorno**: Chequeo en tiempo real de disponibilidad para Outlook Desktop, Chrome CDP (Genesys) y conectividad a Teradata.

---

## 📚 Documentación Técnica y Visualizador de Arquitectura

- 🌐 **[architecture.html](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/architecture.html)**: **Visualizador Interactivo de Arquitectura 3D/2D** (Canvas interactivo, 5 capas, 17 componentes y 6 flujos E2E animados).
- 🧩 **[architecture.json](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/architecture.json)**: Topología estructurada en JSON para agentes IA y herramientas de análisis.
- 📖 **[MANUAL_USUARIO.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/MANUAL_USUARIO.md)**: Manual del usuario final y guía paso a paso.
- ⚡ **[FLUJO_CONSUMO.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CONSUMO.md)**: Detalle del proceso PBI Base Consumo (Fases 1 a 5, inputs/outputs por fase).
- 📊 **[FLUJO_CALIDAD.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CALIDAD.md)**: Detalle del proceso PBI Evaluaciones Calidad (Fases 1 a 5, inputs/outputs por fase).
- 🔒 **[FLUJO_CIERRE.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CIERRE.md)**: Detalle del Modo Cierre Mensual (idempotencia DELETE+INSERT, inputs/outputs por script).
- 🚀 **[FLUJO_PILOTOS.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_PILOTOS.md)**: Detalle de Piloto TCAD (Tarjetas Adicionales) y Piloto No Venta (Objeciones Speech Analytics).
- 🎧 **[FLUJO_AUDIOS_Y_CARGA.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_AUDIOS_Y_CARGA.md)**: Descarga de Audios Genesys/Outlook e Ingesta a Teradata.
- 🗺️ **[MAPA_FLUJO_EJECUCION_BOTONES.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/MAPA_FLUJO_EJECUCION_BOTONES.md)**: Mapeo de botones de la interfaz web hacia endpoints FastAPI y scripts SQL.
- 🔄 **[PLAN_TRANSICION.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/PLAN_TRANSICION.md)**: **Plan completo de handover** — dependencias, credenciales, accesos, procedimiento de instalación y agenda de traspaso.

---

## 📂 Estructura del Proyecto

```
PLATAFORMA_CALIDAD_TELEVENTAS/
├── APP_CALIDAD.bat             <-- Ejecutable de inicio rápido
├── .agents/                    <-- Reglas de gobierno del agente (AGENTS.md)
├── logs/                       <-- Registro centralizado de logs por fecha
├── docs/                       <-- Documentación unificada de flujos del sistema
│   ├── MANUAL_USUARIO.md
│   ├── FLUJO_CONSUMO.md
│   ├── FLUJO_CALIDAD.md
│   ├── FLUJO_CIERRE.md
│   ├── FLUJO_AUDIOS_Y_CARGA.md
│   └── MAPA_FLUJO_EJECUCION_BOTONES.md
├── backend/
│   ├── main.py                 <-- Servidor FastAPI con WebSockets y REST API
│   └── __init__.py
├── frontend/
│   ├── app.js                  <-- Interfaz React 18 SPA (Interbank Theme)
│   ├── styles.css              <-- Estilos globales y Stepper custom
│   └── index.html              <-- Contenedor principal de app
├── modules/
│   ├── consumo/                <-- Orquestador y scripts SQL de Consumo
│   ├── calidad/                <-- Orquestador y scripts SQL de Calidad
│   ├── cierre/                 <-- Orquestador y scripts de Cierre Mensual
│   ├── genesys/                <-- Módulo de navegador y audios Genesys
│   └── verint/                 <-- Cliente API Verint Cloud
├── infrastructure/
│   ├── database/               <-- Conexión e Ingesta Batch a Teradata
│   ├── scrapers/               <-- Scraper Insight
│   ├── system/                 <-- Logging centralizado y Notificador Desktop
│   └── llm/                    <-- Cliente Gemini AI
└── legacy/                     <-- Código legado (Streamlit / Deprecado)
```

---

## 🛡️ Modo de Respaldo (Streamlit)

Si por requerimientos operativos de cierre deseas utilizar la versión original en Streamlit:

```cmd
.\.venv\Scripts\python.exe -m streamlit run index.py
```
