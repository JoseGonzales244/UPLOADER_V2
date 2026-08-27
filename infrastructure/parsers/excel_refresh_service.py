"""
Excel Refresh Service
Refresca las conexiones de datos de un archivo Excel vía COM (win32com) en un subproceso
aislado con timeout de 60 segundos para evitar bloqueos.
Extraído de quality_orchestrator.py y compartido por módulos calidad y consumo.
"""
import os
import sys
import subprocess
import logging

logger = logging.getLogger("excel_refresh_service")


def _refresh_excel_com_process(file_path: str) -> None:
    """
    Ejecutado en subproceso aislado: abre Excel, refresca conexiones y guarda.
    Códigos de salida: 0=OK, 1=Error COM, 2=pywin32 no disponible.
    """
    import time

    abs_path = os.path.abspath(file_path)

    try:
        import win32com.client
        import pythoncom
    except ImportError:
        sys.exit(2)  # Code 2: pywin32 missing

    pythoncom.CoInitialize()
    excel = None
    wb = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False

        # 1. Open workbook, resolving Protected View if necessary
        try:
            wb = excel.Workbooks.Open(abs_path)
        except Exception:
            pv_win = None
            for i in range(1, excel.ProtectedViewWindows.Count + 1):
                win = excel.ProtectedViewWindows.Item(i)
                if win.SourceName.lower() == os.path.basename(abs_path).lower():
                    pv_win = win
                    break
            if pv_win:
                wb = pv_win.Edit()
            else:
                raise

        # 2. Disable background queries so RefreshAll runs synchronously
        for i in range(1, wb.Connections.Count + 1):
            conn = wb.Connections.Item(i)
            try:
                if conn.Type == 1:
                    conn.OLEDBConnection.BackgroundQuery = False
                elif conn.Type == 2:
                    conn.ODBCConnection.BackgroundQuery = False
            except Exception:
                pass

        # 3. Perform refresh, save, and quit
        wb.RefreshAll()
        time.sleep(2)
        wb.Save()
        wb.Close(SaveChanges=True)
        excel.Quit()
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)
    finally:
        pythoncom.CoUninitialize()


def refresh_excel_sharepoint_data(file_path: str, progress_callback=None) -> None:
    """
    Refresca las conexiones de datos de un archivo Excel en un subproceso con timeout de 60s.
    Instala pywin32 automáticamente si no está disponible.

    Args:
        file_path: Ruta absoluta o relativa al archivo Excel.
        progress_callback: Callback opcional (message: str, level: str).
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"No se encontró el archivo Excel en {abs_path}")

    # 1. Unblock file in Windows
    try:
        subprocess.run(
            ["powershell.exe", "-Command", f"Unblock-File -Path '{abs_path}'"],
            capture_output=True,
            check=False
        )
    except Exception:
        pass

    # 2. Check/Install pywin32 in parent
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        if progress_callback:
            progress_callback("📦 Biblioteca 'pywin32' no detectada. Instalándola automáticamente...", "info")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])
        except Exception as inst_err:
            raise RuntimeError(f"No se pudo instalar pywin32: {inst_err}")

    # 3. Launch subprocess with 60-second hard timeout
    if progress_callback:
        progress_callback("🔄 Conectando con Excel para actualizar desde SharePoint...", "info")

    project_root = os.getcwd()
    cmd = [
        sys.executable,
        "-c",
        f"import sys; sys.path.append(r'{project_root}'); "
        f"from infrastructure.parsers.excel_refresh_service import _refresh_excel_com_process; "
        f"_refresh_excel_com_process(r'{abs_path}')"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if progress_callback:
                progress_callback("✅ Excel actualizado correctamente desde SharePoint.", "success")
        elif result.returncode == 2:
            raise RuntimeError("pywin32 no cargó correctamente en el subproceso.")
        else:
            error_details = result.stderr.strip()
            raise RuntimeError(f"Error en actualización de Excel: {error_details}")
    except subprocess.TimeoutExpired:
        try:
            subprocess.run(["taskkill", "/f", "/im", "excel.exe"], capture_output=True, check=False)
        except Exception:
            pass
        raise TimeoutError(
            "Se superó el límite de tiempo de 60s al actualizar Excel desde SharePoint. "
            "(Se omitió actualización automática)"
        )
