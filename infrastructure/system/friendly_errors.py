"""
Módulo de Formateo y Traducción de Errores Amigables:
Convierte excepciones técnicas (Calamine, Teradata, SQL, Red, Archivos, Permisos, APIs)
en mensajes claros, ejecutivos y con recomendaciones de reanudación paso a paso para el usuario.
"""
import os
import re
from typing import Optional


def extract_filename(text: str) -> Optional[str]:
    """Extrae el nombre base del archivo de una ruta o mensaje de error."""
    if not text:
        return None
    match = re.search(r'([a-zA-Z0-9_\-\s\(\)]+\.(xlsx|xls|csv|txt|sql|log))', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _append_resume_tip(base_msg: str, raw_msg: str, context: str) -> str:
    """Añade recomendaciones accionables específicas (desmarcar fases previas / reanudar por script)."""
    combined = (raw_msg + " " + context).lower()
    script_match = re.search(r'([a-zA-Z0-9_]+\.sql)', raw_msg + " " + context, re.IGNORECASE)

    if script_match:
        script_name = script_match.group(1)
        tip = f"\n💡 Acción recomendada: Puede desmarcar las fases anteriores y reanudar directamente desde '{script_name}' usando el selector 'Iniciar desde script'."
    elif "fase 5" in combined or "ntd" in combined:
        tip = "\n💡 Acción recomendada: Desmarque las Fases 1 a 4 y ejecute únicamente la Fase 5 (Proceso NTD)."
    elif "fase 4" in combined or "pipeline" in combined:
        tip = "\n💡 Acción recomendada: Desmarque las Fases 1, 2 y 3 y ejecute a partir de la Fase 4 (Scripts SQL)."
    elif "fase 3" in combined or "accion_tomada" in combined:
        tip = "\n💡 Acción recomendada: Desmarque las Fases 1 y 2 y ejecute a partir de la Fase 3 (Acciones Tomadas)."
    elif "fase 2" in combined or "verint" in combined or "speech analytics" in combined:
        tip = "\n💡 Acción recomendada: Si la Fase 1 ya completó con éxito, desmarque la Fase 1 y ejecute a partir de la Fase 2."
    elif "fase 1" in combined or "insight" in combined or "evaluations" in combined:
        tip = "\n💡 Acción recomendada: Verifique sus credenciales/conexión y reintente la ejecución desde la Fase 1."
    else:
        tip = ""

    return f"{base_msg}{tip}" if tip and tip not in base_msg else base_msg


def format_friendly_error(err: Exception | str, context: str = "") -> str:
    """
    Traduce una excepción o mensaje de error técnico a un mensaje amigable en español con sugerencia de reanudación.
    """
    raw_msg = str(err).strip()
    filename = extract_filename(raw_msg) or extract_filename(context) or "Excel"

    # 1. Error de archivo Excel dañado / incompleto / no ZIP (Calamine / Zip error / EOCD)
    if any(k in raw_msg.lower() for k in [
        "calamine error", "zip error", "invalid zip archive", "could not find eocd",
        "badzipfile", "cannot find zip central directory", "could not open workbook",
        "could not load excel file"
    ]):
        msg = (
            f"El archivo Excel '{filename}' está dañado o incompleto "
            f"(posible descarga interrumpida de Verint o formato no válido). "
            f"El sistema lo descartará automáticamente para volver a descargarlo."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 2. Error de archivo en uso / permisos bloqueados (PermissionError / Errno 13)
    if "permission denied" in raw_msg.lower() or "errno 13" in raw_msg.lower() or "being used by another process" in raw_msg.lower():
        msg = (
            f"El archivo '{filename}' está bloqueado o abierto en otra aplicación (como Microsoft Excel). "
            f"Por favor cierre el archivo e intente ejecutar el proceso nuevamente."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 3. Error de archivo no encontrado (FileNotFoundError / Errno 2)
    if "filenotfounderror" in raw_msg.lower() or "no such file or directory" in raw_msg.lower() or "errno 2" in raw_msg.lower():
        msg = (
            f"No se encontró el archivo necesario '{filename}'. "
            f"Asegúrese de que el archivo exista en la carpeta de insumos y no haya sido renombrado."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 4. Error de Teradata 7547 (Target row updated by multiple source rows)
    if "error 7547" in raw_msg.lower() or "target row updated by multiple source rows" in raw_msg.lower():
        msg = (
            "Conflicto de registros en Teradata (Error 7547): Se detectaron registros duplicados en los datos de origen "
            "intentando actualizar la misma fila de destino. El query SQL requiere deduplicación."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 5. Error de Teradata 3807 / 3802 (Tabla o vista no existe)
    if "error 3807" in raw_msg.lower() or "error 3802" in raw_msg.lower() or ("object" in raw_msg.lower() and "does not exist" in raw_msg.lower()):
        obj_match = re.search(r"'(DLAB_GEC\.[A-Za-z0-9_]+|[A-Za-z0-9_\.]+)'", raw_msg)
        obj_name = obj_match.group(1) if obj_match else "especificada"
        msg = (
            f"La tabla o vista '{obj_name}' no existe en Teradata (Error 3807). "
            f"Verifique que las fases previas de carga se hayan completado correctamente."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 6. Error de Teradata 8017 (Autenticación / Credenciales inválidas)
    if "error 8017" in raw_msg.lower() or "userid, password or account is invalid" in raw_msg.lower():
        msg = (
            "Credenciales incorrectas en Teradata (Error 8017): Usuario o contraseña de base de datos no válidos. "
            "Verifique las credenciales ingresadas o el archivo de configuración .env."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 7. Error de Teradata 2801 / 395 / 528 / Conexión / VPN / Timeout (WinError 10060 / 10061 / wsarecv)
    if any(k in raw_msg.lower() for k in [
        "error 2801", "error 395", "error 528", "08s01", "wsarecv", "failure receiving message header",
        "read tcp", "10060", "10061", "connection refused", "connection reset", "timed out",
        "host unreachable", "network unreachable"
    ]):
        msg = (
            "Se perdió la conexión con el servidor de Teradata durante la transferencia de datos. "
            "Verifique la estabilidad de su conexión a la VPN de Interbank o reintente la ejecución."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 8. Error de Verint WFO (Sesión / Autenticación / Timeout)
    if "verint" in raw_msg.lower() and any(k in raw_msg.lower() for k in ["autenticación", "timeout", "sesión", "reporte", "401", "403"]):
        msg = (
            "Error en el servicio de Verint Speech Analytics: La sesión expiró o se agotó el tiempo de espera generando el reporte. "
            "Verifique sus credenciales de Verint o reintente la descarga."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 9. Error de Insight / PureCloud (Autenticación / Descarga)
    if "insight" in raw_msg.lower() and any(k in raw_msg.lower() for k in ["autenticación", "credenciales", "login", "descarga"]):
        msg = (
            "Error al conectar con Insight / PureCloud: No se pudo autenticar o descargar las evaluaciones. "
            "Verifique las credenciales de Insight."
        )
        return _append_resume_tip(msg, raw_msg, context)

    # 10. Limpieza general de trazas técnicas para mensajes desconocidos
    clean_msg = raw_msg
    clean_msg = re.sub(r'\s+at\s+[a-zA-Z0-9_\/\.\*\(\)\:\-]+', '', clean_msg)
    clean_msg = re.sub(r'([A-Z]\:[\\\/][^:\n\r]+)', '', clean_msg)
    clean_msg = re.sub(r'\s{2,}', ' ', clean_msg).strip()

    if len(clean_msg) > 300:
        clean_msg = clean_msg[:300] + "..."

    main_msg = clean_msg if clean_msg else "Ocurrió un error inesperado durante el procesamiento."
    return _append_resume_tip(main_msg, raw_msg, context)
