# 🎧 Flujo de Solicitud de Audios e Ingesta a Teradata

Este documento describe la funcionalidad de **Solicitud de Audios (Genesys & Outlook)** y el módulo de **Subida a Teradata (Ingesta Genérica)**.

---

## 🎧 1. Solicitud y Descarga de Audios (Genesys & Outlook)

### 📌 Módulo Outlook Service

- 📥 **INPUTS**:
  - **Aplicación Origen**: Outlook Desktop local conectado vía COM (`win32com.client`).
  - **Criterios de Búsqueda**: Últimos correos con el asunto *"Solicitud de audio"*.
  - **Contenido del Correo**: Celdas en tablas HTML o adjuntos en formato Excel (`.xlsx`).

- 📤 **OUTPUTS**:
  - **Objetos Normalizados**: Lista de parejas de `REG_EV` (ej. `B12345`) y `DNI` extraídas del cuerpo del correo.

---

### 📌 Módulo Genesys Downloader

- 📥 **INPUTS**:
  - **Navegador**: Chrome CDP en puerto `9222` con sesión activa en Genesys Cloud.
  - **Datos de Solicitud**: Parejas de Registro Ejecutivo (`reg_ev`), `DNI`, producto/prefijo (ej. `AUDIO`, `EC`, `TC`) y nombre de archivo.

- 📤 **OUTPUTS**:
  - **Archivos Descargados**: Archivos de audio (`.mp3` / `.wav`) de las interacciones localizadas, guardados localmente en la carpeta de descargas del usuario.

---

## 📁 2. Subida a Teradata (Ingesta Genérica de Archivos)

- 📥 **INPUTS**:
  - **Archivos Origen**: Excel (`.xlsx`, `.xls`), CSV (`.csv`), o Texto Unicode tabulado (`.txt`).
  - **Plantillas de Mapeo**: Plantillas predefinidas en `plantillas.json` o mapeo de columnas manual.
  - **Parámetros de Limpieza**:
    - *Eliminar acentos en textos* (Normalización NFKD).
    - *Limpiar caracteres especiales LATIN* (Sanitización para evitar error Teradata 6706).
    - *Longitud máxima VARCHAR* (defecto: 3,000).

- 📤 **OUTPUTS**:
  - **Tabla Destino Teradata**: Tabla especificada por el usuario (ej. `DLAB_GEC.Mi_Tabla_Cargada`).
  - **Modo de Acción**:
    - `Append`: Insertar registros sin vaciar.
    - `Replace`: Vaciar la tabla (`DELETE FROM ...`) antes de insertar los nuevos registros.
