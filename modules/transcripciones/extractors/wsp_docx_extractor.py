"""
Extractor de Transcripciones de WhatsApp (.docx) con Extracción de Conversación Limpia y Filtrado de Ejecutivo.
Soporta tanto documentos con sección de 'Conversación Limpia' como exportaciones tabuladas de Genesys.
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

    def _load_ejecutivos_mapping(self) -> pd.DataFrame:
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
        """
        Extrae la conversación limpia del archivo .docx de WhatsApp.
        Privilegia la sección 'Conversación limpia' si existe en el Word.
        """
        filename = os.path.basename(docx_path)
        interaction_id = os.path.splitext(filename)[0]

        exec_info = {
            "SUPERVISOR": "N/A",
            "REGISTRO COLABORADOR": "N/A",
            "COLABORADOR": "N/A",
            "SUB EQUIPO": "Televentas"
        }
        
        target_registro = ""
        target_nombre = ""

        if not self.ejecutivos_df.empty and "ID_Interaccion" in self.ejecutivos_df.columns:
            match = self.ejecutivos_df[self.ejecutivos_df["ID_Interaccion"].astype(str).str.strip() == interaction_id]
            if not match.empty:
                row = match.iloc[0]
                target_registro = str(row.get("REGISTRO COLABORADOR", "") or "").strip()
                target_nombre = str(row.get("COLABORADOR", "") or "").strip()
                exec_info = {
                    "SUPERVISOR": str(row.get("SUPERVISOR", "N/A")),
                    "REGISTRO COLABORADOR": target_registro or "N/A",
                    "COLABORADOR": target_nombre or "N/A",
                    "SUB EQUIPO": str(row.get("SUB EQUIPO", "Televentas"))
                }

        doc = docx.Document(docx_path)
        paragraphs_text = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        # 1. Buscar si existe sección "Conversación limpia" o "Parte 1" / "Derivación a especialista"
        clean_section = []
        is_clean_started = False

        for txt in paragraphs_text:
            txt_lower = txt.lower()
            if any(k in txt_lower for k in ["conversación limpia", "conversacion limpia", "parte 1", "parte 2", "derivación a especialista", "derivacion a especialista", "atención por asesor"]):
                is_clean_started = True
            
            if is_clean_started:
                if not txt.startswith("Archivo:") and not txt.startswith("Tipo de") and not txt.startswith("ID de"):
                    clean_section.append(txt)

        # Si se encontró la sección de conversación limpia en el Word
        if clean_section:
            header_summary = (
                f"=== FICHA DE EVALUACIÓN WHATSAPP (CONVERSACIÓN LIMPIA) ===\n"
                f"ID Interacción: {interaction_id}\n"
                f"Ejecutivo Evaluado: {exec_info['COLABORADOR']} (Registro: {exec_info['REGISTRO COLABORADOR']})\n"
                f"Supervisor: {exec_info['SUPERVISOR']} | Sub-Equipo: {exec_info['SUB EQUIPO']}\n"
                f"====================================\n\n"
            )
            full_text = header_summary + "\n".join(clean_section)
            return {
                "archivo": filename,
                "interaction_id": interaction_id,
                "full_text": full_text,
                "metadata": exec_info
            }

        # 2. Fallback: Parsear la tabla tabulada de Genesys
        filtered_dialogue = []
        current_speaker = None

        for txt in paragraphs_text:
            parts = txt.split("\t")
            if len(parts) >= 3 and parts[1] in ("Interno", "Externo"):
                fecha_hora = parts[0]
                tipo_part = parts[1]
                sender = parts[2]
                mensaje_texto = parts[3] if len(parts) >= 4 else ""

                if tipo_part == "Externo":
                    current_speaker = f"Cliente ({sender})"
                    linea = f"{current_speaker}"
                    if mensaje_texto:
                        linea += f": {mensaje_texto}"
                    filtered_dialogue.append(linea)

                elif tipo_part == "Interno":
                    sender_lower = sender.lower()
                    if "bot" in sender_lower or "flujo" in sender_lower or "acd" in sender_lower:
                        current_speaker = None
                        continue

                    is_target = False
                    if target_registro and target_registro.lower() in sender_lower:
                        is_target = True
                    elif target_nombre and any(token.lower() in sender_lower for token in target_nombre.split(",") if len(token.strip()) > 3):
                        is_target = True

                    if is_target:
                        current_speaker = f"Ejecutivo Evaluado [{target_nombre or sender}]"
                        linea = f"{current_speaker}"
                        if mensaje_texto:
                            linea += f": {mensaje_texto}"
                        filtered_dialogue.append(linea)
                    else:
                        current_speaker = None

        header_summary = (
            f"=== FICHA DE EVALUACIÓN WHATSAPP ===\n"
            f"ID Interacción: {interaction_id}\n"
            f"Ejecutivo Evaluado: {exec_info['COLABORADOR']} (Registro: {exec_info['REGISTRO COLABORADOR']})\n"
            f"Supervisor: {exec_info['SUPERVISOR']} | Sub-Equipo: {exec_info['SUB EQUIPO']}\n"
            f"====================================\n\n"
        )
        full_text = header_summary + ("\n".join(filtered_dialogue) if filtered_dialogue else "Sin mensajes de texto registrados para el ejecutivo evaluado en la transcripción.")

        return {
            "archivo": filename,
            "interaction_id": interaction_id,
            "full_text": full_text,
            "metadata": exec_info
        }

    def get_all_transcripts(self) -> List[Dict[str, Any]]:
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
