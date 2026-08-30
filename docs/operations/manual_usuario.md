# 📖 Manual Operativo de Usuario

Guía paso a paso para el uso operativo de la **Plataforma Calidad Televentas**.

---

## ⚡ 1. Inicio Rápido de la Aplicación

Para iniciar la plataforma en un entorno Windows:

1. Ejecuta el archivo en la raíz del proyecto:
   ```cmd
   APP_CALIDAD.bat
   ```
2. La plataforma levantará el servidor FastAPI en `http://127.0.0.1:8000` y abrirá automáticamente la interfaz web en tu navegador predeterminado.
3. Verifica el indicador de estado en la barra superior (debe mostrar conexión WebSocket activa).

---

## 📁 2. Módulo: Subir a Teradata

Permite la ingesta estructurada de archivos tabulares (Excel, CSV o TXT) hacia tablas de Teradata con validación de tipos y control de duplicados.

### Pasos Operativos:
1. **Seleccionar Archivo:** Haz clic en *Seleccionar archivo* o arrastra tu Excel (`.xlsx`), CSV o TXT.
2. **Plantilla de Limpieza (Opcional):** Si el archivo corresponde a un formato estándar (e.g. `P003-CD40K`), selecciona la plantilla para mapear y limpiar columnas automáticamente.
3. **Vista Previa:** Haz clic en `👁️ Vista Previa de Archivo`. Se mostrarán las primeras 10 filas y la inferencia de tipos SQL (`VARCHAR`, `INTEGER`, `DECIMAL`).
4. **Configuración de Carga:**
   - **Tabla Destino:** Ingresa el nombre calificado de la tabla (e.g., `DLAB_GEC.T_SP_CD40K`).
   - **Modo de Carga:**
     - *Reemplazar registros existentes:* Vacía la tabla (`DELETE`) antes de cargar el nuevo contenido.
     - *Solo agregar nuevos registros:* Inserta filas adicionales (`INSERT INTO`) sin borrar las existentes.
5. **Ejecución:** Haz clic en `🚀 Cargar a Teradata`. La barra de progreso reportará el avance en tiempo real.

---

## 🎧 3. Módulo: Solicitud y Descarga de Audios (Genesys)

Automatiza la recolección de solicitudes de audio desde Microsoft Outlook y su descarga en Genesys Cloud.

### Pasos Operativos:
1. **Importación desde Outlook:**
   - Abre Microsoft Outlook Desktop en tu estación de trabajo.
   - Haz clic en `📧 Leer de Outlook`. El sistema buscará los 3 correos más recientes con solicitudes de calidad y extraerá los DNIs y Registros.
2. **Entrada Manual / Pegado Masivo:**
   - Si no usas Outlook, pega directamente las columnas desde Excel en el área de texto con formato `REG_EV` y `DNI`.
3. **Enriquecimiento y Descarga:**
   - Haz clic en `🎧 Descargar Audios (Genesys)`.
   - El sistema enriquecerá los DNIs buscando los números de teléfono en Teradata.
   - Conectará a la sesión de Chrome en el puerto CDP `9222`, descargará las interacciones y guardará los archivos de audio en `data/downloads/audios/`.

---

## 🚀 4. Módulo: Orquestación de Pipelines (Consumo, Calidad y Cierre)

### 4.1 PBI Base Consumo
1. Navega a la pestaña **PBI Base Consumo**.
2. Marca o desmarca las fases a ejecutar (`1. Insight`, `2. CD40K`, `3. BN Desembolsos`, `4. Proceso SQL`, `5. SELECT`).
3. Haz clic en `▶️ Iniciar Proceso Consumo`. Las fases se ejecutarán secuencialmente y recibirás una notificación de escritorio al finalizar.

### 4.2 PBI Evaluaciones Calidad
1. Navega a la pestaña **PBI Evaluaciones Calidad**.
2. Configura las fases deseadas y haz clic en `▶️ Iniciar Proceso Calidad`.

### 4.3 Modo Cierre Mensual
1. Navega a la pestaña **Modo Cierre**.
2. Selecciona los scripts específicos a procesar (`01_auditoria_y_cierre.sql` y/o `02_kri_resumen_total.sql`).
3. Haz clic en `🔒 Ejecutar Cierre Mensual`.
