# 📖 Manual del Usuario Final - Plataforma Calidad Televentas

Este manual te guiará paso a paso para utilizar la **Plataforma Calidad Televentas** (Uploader V2). La herramienta simplifica la descarga automatizada de reportes, la orquestación de procesos de Consumo y Calidad, la ejecución de cierres mensuales y la ingesta masiva de datos a Teradata.

---

## 🚀 1. Iniciar la Aplicación

Para iniciar la aplicación, haz doble clic en el archivo ejecutable:
- **`APP_CALIDAD.bat`** (ubicado en la carpeta principal del proyecto).

Esto iniciará el servidor backend (**FastAPI**) y la interfaz web (**React**) en tu navegador predeterminado en `http://localhost:8000`.

---

## ⚡ 2. Ventanas y Procesos Principales

La plataforma cuenta con 4 pestañas principales en la barra superior:

### 📁 1. Subir a Teradata
Permite cargar archivos Excel (`.xlsx`), CSV (`.csv`) o Texto tabulado (`.txt`) directamente a tablas de Teradata:
1. Arrastra o selecciona tu archivo origen.
2. Visualiza la vista previa de los primeros 10 registros.
3. Configura las columnas (selección, renombrado, tipos de datos SQL).
4. Ingresa el usuario, contraseña y tabla destino en Teradata (ej. `DLAB_GEC.Mi_Tabla`).
5. Elige la acción (*Solo agregar nuevos registros* o *Reemplazar registros existentes*).
6. Presiona **"🚀 Cargar a Teradata"**.

### 🎧 2. Solicitud de Audios (Genesys & Outlook)
Permite gestionar la descarga automatizada de audios de llamadas:
- **📧 Leer de Outlook**: Consulta automáticamente los últimos 3 correos con solicitudes de audios en tu aplicación Outlook Desktop.
- **✏️ Ingreso Manual**: Permite ingresar parejas de Registro Ejecutivo (ej. `B12345`) y DNI por formulario, pegando celdas de Excel o subiendo archivo.

### ⚡ 3. PBI Base Consumo
Orquesta las 5 Fases de actualización de la Base de Consumo para Power BI.
Para ver el detalle técnico con diagramas, sentencias, INPUTS y OUTPUTS por fase, consulta [FLUJO_CONSUMO.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CONSUMO.md).

### 📊 4. PBI Evaluaciones Calidad y Cierre Mensual
Orquesta las 5 Fases de actualización de Evaluaciones de Calidad NTD y el **Modo Cierre Mensual**.
- **Proceso Semanal de Calidad**: Fases 1 a 5.
- **Modo Cierre Mensual**: Al activar la casilla `🔒 Modo Cierre Mensual`, permite ejecutar de forma aislada e idempotente los scripts de cierre `01_auditoria_y_cierre.sql` y/or `02_kri_resumen_total.sql`.
Para ver el detalle técnico completo con INPUTS y OUTPUTS explícitos, consulta [FLUJO_CALIDAD.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CALIDAD.md) y [FLUJO_CIERRE.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CIERRE.md).

---

## ⚙️ 3. Opciones de la Barra Lateral (Sidebar)

- **Configuración de Lectura**: Tipo de archivo y selección de plantillas predefinidas (`plantillas.json`).
- **🧹 Limpieza de Datos**:
  - *Eliminar acentos en textos*: Reemplaza tildes para evitar fallos de codificación.
  - *Limpiar caracteres especiales (LATIN)*: Filtra símbolos no soportados por el conjunto LATIN (evita error 6706).
- **🩺 Diagnóstico de Entorno**: Verifica disponibilidad de Outlook Desktop, Chrome CDP (Genesys) y Teradata.

---

## 📜 4. Documentación de Flujos del Sistema

Para consultar la especificación detallada de cada proceso:

- 📑 **[FLUJO_CONSUMO.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CONSUMO.md)**: Proceso PBI Base Consumo (Fases 1 a 5, inputs, outputs y tablas Teradata).
- 📑 **[FLUJO_CALIDAD.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CALIDAD.md)**: Proceso PBI Evaluaciones Calidad (Fases 1 a 5, inputs, outputs y parches de nota cero).
- 📑 **[FLUJO_CIERRE.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_CIERRE.md)**: Modo Cierre Mensual (Idempotencia `DELETE+INSERT`, scripts `01` y `02`, inputs y outputs).
- 📑 **[FLUJO_AUDIOS_Y_CARGA.md](file:///c:/Users/USER/Documents/Documentos%20Personales/INTERBANK/APP_CALIDAD/docs/FLUJO_AUDIOS_Y_CARGA.md)**: Descarga de Audios Genesys/Outlook e Ingesta Genérica a Teradata.
