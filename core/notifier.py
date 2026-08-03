"""
Módulo Notificador de Escritorio:
Envía notificaciones nativas de Windows al finalizar los procesos de Streamlit.
"""
import os
import sys
import logging
import subprocess
import threading

logger = logging.getLogger(__name__)

def notify_desktop(title: str = "Uploader V2", message: str = "Proceso completado exitosamente", duration_sec: int = 5):
    """
    Envía una notificación nativa de Windows (Toast / Balloon) que permanece en pantalla
    durante el tiempo especificado en seconds (por defecto 5s).
    Se ejecuta de forma asíncrona para no bloquear la aplicación.
    """
    def _send():
        try:
            # Script PowerShell para notificación Toast nativa en Windows 10 / 11
            ps_script = f"""
            $ErrorActionPreference = 'SilentlyContinue'
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $titleText = '{title}'
            $msgText = '{message}'
            $template = "<toast duration='short'><visual><binding template='ToastGeneric'><text>$titleText</text><text>$msgText</text></binding></visual></toast>"

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Uploader V2')
            $notifier.Show($toast)
            Start-Sleep -Seconds {duration_sec}
            """
            
            creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                creationflags=creation_flags,
                timeout=duration_sec + 3,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.warning(f"No se pudo mostrar la notificación de escritorio: {e}")

    # Ejecutar en hilo secundario para no congelar la UI de Streamlit
    threading.Thread(target=_send, daemon=True).start()
