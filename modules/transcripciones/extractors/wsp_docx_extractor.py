"""
Extractor de Transcripciones de WhatsApp (.docx) y Mapeo de Ejecutivos.
Extrae metadatos y texto formateado de chats de WhatsApp desde documentos Word (.docx).
"""
import os
import glob
import logging
import docx
import pandas as pd
from typing import List, Dict, Any, Optional

logger = logging.getLogger("modules.transcripciones.extractors.wsp_docx_extractor")

class WhatsAppTranscriptExtractor:
    def __init__(self, folder_path: str = "Auditorias Wsp"):
        self.folder_path = folder_path
        self.ejecutivos_df = self._load_ejecutivos_mapping()

    def _load_ejecutivos_mapping() -> pd.DataFrame:
        excel_path = os.path.join(self.folder_path, "Ejecutivos_Gestion_Wsp.xlsx")
        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path)
                logger.info(f"Cargado mapeo de ejecutivos desde {excel_path} ({len(df)} registros).")
                return df
            except Exception as e:
                logger.error(f"Error leyendo {excel_path}: {e}")
        return pd.DataFrame()

    def extract_single_docx(self, docx_path: str) -> Dict[str, Any]:
        """Extrae el contenido de un archivo .docx de transcripción WhatsApp."""
        filename = os.path.basename(docx_path)
        interaction_id = os.path.splitext(filename)[0]

        doc = docx.Document(docx_path)
        
        paragraphs_text = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                paragraphs_text.append(txt)

        # Buscar tablas si el chat viene formateado en tabla (Fecha/Hora | Tipo | Participante | Texto)
        table_rows = []
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    table_rows.append(" | ".join(cells))

        full_text = "\n".join(paragraphs_text)
        if table_rows:
            full_text += "\n\nDETALLE DE MENSAJES (TABLA):\n" + "\n".join(table_rows)

        # Buscar metadatos en el dataframe de ejecutivos
        exec_info = {}
        if not self.ejecutivos_df.empty and "ID_Interaccion" in self.ejecutivos_df.columns:
            match = self.ejecutivos_df[self.ejecutivos_df["ID_Interaccion"] == interaction_id]
            if not match.empty:
                row = match.iloc[0]
                exec_info = {
                    "SUPERVISOR": str(row.get("SUPERVISOR", "N/A")),
                    "REGISTRO COLABORADOR": str(row.get("REGISTRO COLABORADOR", "N/A")),
                    "COLABORADOR": str(row.get("COLABORADOR", "N/A")),
                    "SUB EQUIPO": str(row.get("SUB EQUIPO", "Televentas"))
                }

        return {
            "archivo": filename,
            "interaction_id": interaction_id,
            "full_text": full_text,
            "metadata": exec_info
        }

    def get_all_transcripts() -> List[Dict[str, Any]]:
        """Busca y extrae todos los archivos .docx en la carpeta Auditorias Wsp."""
        docx_files = glob.glob(os.path.join(self.folder_path, "*.docx"))
        results = []
        for filepath in sorted(docx_files):
            try:
                data = self.extract_single_docx(filepath)
                if data["full_text"].strip():
                    results.append(data)
            except Exception as e:
                logger.error(f"Error extrayendo {filepath}: {e}")
        return results
