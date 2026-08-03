# ⚡ Plataforma Calidad Televentas (FastAPI + React SPA)

Plataforma unificada de alto rendimiento para la orquestación de pipelines de datos de **Consumo (KRI Ventas)**, **Calidad (NTD)**, **Solicitud de Audios (Genesys/Outlook)** e **Ingesta de datos a Teradata**.

---

## 📋 Tabla de Contenidos
1. [Arquitectura y Rendimiento](#-arquitectura-y-rendimiento)
2. [Cómo Ejecutar](#-cómo-ejecutar)
3. [Funcionalidades Principales](#-funcionalidades-principales)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Modo de Respaldo (Streamlit)](#-modo-de-respaldo-streamlit)

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
3. **⚡ PBI Base Consumo**: Orquestación en 5 Fases del pipeline de Consumo con ejecuciones parametrizadas de scripts Teradata SQL (`VENTAS_DN`, `CD40K`, `SOURCE_TVL`, `CA_CONSENTIMIENTO_DIARIO`, `KRI_VENTAS_SIN_AUDIO`, `TLF_NO_AUTORIZADO`).
4. **📊 PBI Evaluaciones Calidad**: Orquestación en 5 Fases para el consolidado de calidad NTD.
5. **🩺 Diagnóstico de Entorno**: Chequeo en tiempo real de disponibilidad para Outlook Desktop, Chrome CDP (Genesys) y conectividad a Teradata.

---

## 📂 Estructura del Proyecto

```
PLATAFORMA_CALIDAD_TELEVENTAS/
├── APP_CALIDAD.bat             <-- Ejecutable de inicio rápido
├── backend/
│   ├── main.py                 <-- Servidor FastAPI con WebSockets y REST API
│   └── __init__.py
├── frontend/
│   └── index.html              <-- Interfaz React 18 SPA (Interbank Theme)
├── core/
│   ├── orchestrator.py         <-- Orquestador de Consumo
│   ├── quality_process_orchestrator.py <-- Orquestador de Calidad
│   ├── notifier.py             <-- Módulo de Notificaciones de Escritorio
│   ├── health_check.py        <-- Diagnóstico de Entorno
│   └── database.py             <-- Conexión e Ingesta Teradata (FastLoad)
├── modules/
│   ├── consumo/sql/            <-- Scripts Teradata SQL optimizados
│   └── calidad/
├── MANUAL_USUARIO.md           <-- Manual detallado para usuario final
└── index.py                    <-- Aplicación Streamlit original (Respaldo)
```

---

## 🛡️ Modo de Respaldo (Streamlit)

Si por requerimientos operativos de cierre deseas utilizar la versión original en Streamlit:

```cmd
.\.venv\Scripts\python.exe -m streamlit run index.py
```
