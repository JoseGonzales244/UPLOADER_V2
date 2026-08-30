# 🩺 Guía de Diagnóstico y Resolución de Problemas (Troubleshooting)

Este documento describe las causas y soluciones para los problemas operativos más frecuentes en la plataforma.

---

## 🔌 1. Diagnóstico de Entorno

Puedes verificar el estado de los componentes desde la pestaña **Diagnóstico** en la interfaz web o revisando los puntos clave:

| Componente | Estado Requerido | Solución en Caso de Error |
| :--- | :--- | :--- |
| **Outlook Desktop** | Aplicación abierta y perfil iniciado | Abrir Outlook clásico en Windows antes de pulsar `Leer de Outlook`. |
| **Genesys (Chrome CDP)** | Chrome iniciado con `--remote-debugging-port=9222` | Ejecutar el acceso directo de Chrome con depuración remota habilitada. |
| **Teradata ODBC** | Driver Teradata instalado y credenciales en `.env` | Verificar `TERADATA_USER` y `TERADATA_PASSWORD` en el archivo `.env`. |
| **SQL Server (Desembolsos)** | Host y credenciales configuradas | Verificar conectividad a la red corporativa/VPN e IP del servidor. |

---

## ⚠️ 2. Incidencias Frecuentes y Soluciones

### Error: "No se pudo conectar a Chrome en el puerto 9222"
- **Causa:** El navegador Google Chrome no está corriendo con el flag de depuración remota.
- **Solución:**
  1. Cierra todas las ventanas de Google Chrome.
  2. Inicia Chrome con el siguiente comando en la terminal:
     ```cmd
     chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebug"
     ```
  3. Inicia sesión en Genesys Cloud en esa ventana.

### Error: "Error de autenticación o timeout en Teradata"
- **Causa:** Contraseña de red expirada o bloqueo temporal de cuenta Teradata.
- **Solución:**
  1. Actualiza tu contraseña en `.env` o en el formulario de credenciales de la UI.
  2. Verifica que puedas conectar a Teradata mediante Teradata Studio o SQL Workbench.

### Error: "Fase 2 de Consumo falla: CD40K no encontrado"
- **Causa:** El archivo `CD40K_NEW.xlsx` no se encuentra en `data/input/base_consumo/`.
- **Solución:**
  1. Coloca el archivo actualizado en la ruta `data/input/base_consumo/CD40K_NEW.xlsx`.
  2. Alternativamente, si no requieres actualizar esa tabla hoy, desmarca el checkbox de la **Fase 2** en la UI antes de ejecutar.
