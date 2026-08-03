# 📖 Manual del Usuario Final - Plataforma Calidad Televentas

Este manual te guiará paso a paso para utilizar la **Plataforma Calidad Televentas**. El objetivo de esta herramienta es simplificar la descarga de reportes, la orquestación de procesos de Consumo y Calidad, y la carga masiva de datos a Teradata de forma rápida, fluida y segura.

---

## 🚀 1. Iniciar la Aplicación

Para iniciar la aplicación, simplemente haz doble clic en el ejecutable:
- **`APP_CALIDAD.bat`** (ubicado en la carpeta principal del proyecto).

Esto abrirá automáticamente la interfaz web de alto rendimiento (**FastAPI + React**) en tu navegador predeterminado (`http://localhost:8000`).

---

## ⚡ 2. Ventanas y Procesos Principales

La plataforma cuenta con 4 ventanas principales en la barra superior:

### 📁 1. Subir a Teradata
Usa esta opción para cargar archivos Excel (`.xlsx`), CSV (`.csv`) o Texto tabulado (`.txt`) directamente a tablas de Teradata:
1. Arrastra o selecciona tu archivo origen.
2. Visualiza la vista previa de los primeros 10 registros.
3. Configura las columnas (selección, renombrado, tipos de datos SQL).
4. Ingresa el usuario, contraseña y la tabla destino en Teradata (ej. `DLAB_GEC.Mi_Tabla`).
5. Elige la acción (*Solo agregar nuevos registros* o *Reemplazar registros existentes*).
6. Presiona **"🚀 Cargar a Teradata"**.

### 🎧 2. Solicitud de Audios (Genesys)
Permite gestionar la descarga automatizada de audios de llamadas:
- **📧 Leer de Outlook**: Consulta automáticamente los últimos 3 correos con solicitudes de audios en tu aplicación Outlook Desktop.
- **✏️ Ingreso Manual**: Permite ingresar parejas de Registro Ejecutivo (ej. `B12345`) y DNI de 3 formas:
  - *Formulario Directo*
  - *Copiar y Pegar celdas de Excel* (auto-detecta parejas válidas en el texto)
  - *Subir Archivo Excel*

### ⚡ 3. PBI Base Consumo
Orquesta en 5 Fases la actualización completa de la Base de Consumo para Power BI:
- **Fase 1**: Ingesta Insight
- **Fase 2**: Ingesta CD40K
- **Fase 3**: Ingesta SQL Server
- **Fase 4**: Pipelines SQL Teradata (`VENTAS_DN`, `CD40K`, `SOURCE_TVL`, `CA_CONSENTIMIENTO_DIARIO`, `KRI_VENTAS_SIN_AUDIO`, `TLF_NO_AUTORIZADO`)
- **Fase 5**: Selección Consolidada

*Incluye opción para limpiar registros previos de Consentimiento Diario y Stepper gráfico interactivo.*

### 📊 4. PBI Evaluaciones Calidad
Orquesta en 5 Fases la actualización de Evaluaciones de Calidad NTD:
- **Fase 1**: Insumos
- **Fase 2**: Ingesta
- **Fase 3**: Transformaciones
- **Fase 4**: Script SQL
- **Fase 5**: Consolidado NTD

---

## ⚙️ 3. Opciones de la Barra Lateral (Sidebar)

- **Configuración de Lectura**: Permite cambiar el tipo de archivo origen y seleccionar plantillas de mapeo predefinidas (`plantillas.json`).
- **🧹 Limpieza de Datos**:
  - *Eliminar acentos en textos*: Reemplaza tildes (`á` ➔ `a`, `ñ` ➔ `n`) para evitar fallos de codificación en Teradata.
  - *Limpiar caracteres especiales (LATIN)*: Filtra símbolos no soportados por el conjunto de caracteres LATIN (evita el error 6706).
- **🩺 Diagnóstico de Entorno**: Verifica con un clic la disponibilidad de Outlook Desktop, Chrome CDP (Genesys) y Teradata.

---

## 📜 4. Consola de Eventos y Notificaciones en Vivo

- **Consola WebSocket**: Todos los eventos se transmiten en tiempo real con código de colores (Verde = Éxito, Amarillo = Advertencia, Rojo = Error, Azul/Púrpura = Fases).
- **Notificaciones de Escritorio**: Al finalizar cualquier proceso largo de Consumo o Calidad, la plataforma enviará una notificación nativa de Windows durante 5 segundos.

---

## 🛡️ 5. Modo de Respaldo (Streamlit Original)

Si por algún motivo durante semanas de cierre crítico prefieres utilizar la versión anterior de Streamlit:
1. Abre una consola de comandos en la carpeta del proyecto.
2. Ejecuta el comando de respaldo:
   ```cmd
   .\.venv\Scripts\python.exe -m streamlit run index.py
   ```
