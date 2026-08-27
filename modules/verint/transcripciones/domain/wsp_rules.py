"""
Módulo de Dominio: Reglas y Cargador de Plantillas Oficiales de WhatsApp (Interbank TLV).
Carga el archivo Excel de plantillas autorizadas en Auditorias Wsp/Plantillas TLV WhatsApp.xlsx.
"""
import os
import logging
import pandas as pd

logger = logging.getLogger("modules.transcripciones.domain.wsp_rules")

_CACHED_WSP_TEMPLATES_TEXT = None

def load_whatsapp_templates_prompt(excel_path: str = "Auditorias Wsp/Plantillas TLV WhatsApp.xlsx") -> str:
    """Carga y genera el prompt de plantillas oficiales de WhatsApp desde el Excel oficial."""
    global _CACHED_WSP_TEMPLATES_TEXT
    if _CACHED_WSP_TEMPLATES_TEXT is not None:
        return _CACHED_WSP_TEMPLATES_TEXT

    if not os.path.exists(excel_path):
        logger.warning(f"No se encontró el archivo de plantillas WhatsApp en {excel_path}. Se usará guion estándar.")
        return "Guion estándar de bienvenida, indagación, oferta de producto, aclaración de dudas y cierre."

    try:
        df_p = pd.read_excel(excel_path)
        templates_list = []
        for _, row in df_p.iterrows():
            nombre = str(row.get("Response", "") or row.get("Template Name", "")).strip()
            contenido = str(row.get("Content", "")).strip()
            tipo = str(row.get("Tipo Plantilla", "")).strip()
            
            if nombre and contenido and contenido != "nan":
                templates_list.append(f"• PLANTILLA: [{nombre}] ({tipo})\n  TEXTO AUTORIZADO: \"{contenido}\"")

        if templates_list:
            _CACHED_WSP_TEMPLATES_TEXT = "\n\n".join(templates_list)
            logger.info(f"Cargadas {len(templates_list)} plantillas oficiales de WhatsApp desde {excel_path}.")
            return _CACHED_WSP_TEMPLATES_TEXT
        else:
            return "Guion estándar de bienvenida, oferta y cierre."
    except Exception as e:
        logger.error(f"Error cargando plantillas de WhatsApp desde {excel_path}: {e}")
        return "Guion estándar de bienvenida, oferta y cierre."
