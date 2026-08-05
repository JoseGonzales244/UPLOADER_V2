"""
Extractor de Transcripciones de WhatsApp (.docx) con Extracción de Conversación Limpia y Filtrado de Ejecutivo.
Soporta tanto documentos con sección de 'Conversación Limpia' como exportaciones tabuladas de Genesys.
Implementa ITranscriptExtractor para respetar contratos abstractos.
"""
import os
import re
import glob
import logging
import docx
import pandas as pd
from typing import List, Dict, Any, Optional

from core.interfaces.transcript_extractor import ITranscriptExtractor

logger = logging.getLogger("modules.transcripciones.extractors.wsp_docx_extractor")


def get_paragraph_full_text(p) -> str:
    """Extrae el texto completo del párrafo conservando nodos <w:t> y tabulaciones <w:tab/>."""
    text_pieces = []
    for node in p._element.xpath(".//w:t | .//w:tab"):
        if node.tag.endswith("tab"):
            text_pieces.append("\t")
        elif node.text:
            text_pieces.append(node.text)
    return "".join(text_pieces)


class WhatsAppTranscriptExtractor(ITranscriptExtractor):
    def __init__(self, folder_path: Optional[str] = None):
        self.folder_path = folder_path or os.environ.get(
            "WSP_INPUT_DIR",
            os.path.join("data", "input", "auditorias_wsp")
        )
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
        Extrae la conversación correspondiente AL EJECUTIVO EVALUADO del archivo .docx de WhatsApp.
        Filtra bots, otros ejecutivos y mensajes no relacionados del cliente fuera de la gestión.
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
        
        # Extraer líneas usando XPath para recuperar nodos <w:dir> y <w:t>
        paragraphs_text = []
        for p in doc.paragraphs:
            txt = get_paragraph_full_text(p).strip()
            if txt:
                paragraphs_text.append(txt)

        # 1. Buscar si existe sección "Conversación limpia" en el Word
        clean_section = []
        is_clean_started = False

        for txt in paragraphs_text:
            txt_lower = txt.lower()
            if any(k in txt_lower for k in ["conversación limpia", "conversacion limpia", "parte 1", "parte 2", "derivación a especialista", "derivacion a especialista", "atención por asesor"]):
                is_clean_started = True
            
            if is_clean_started:
                if not txt.startswith("Archivo:") and not txt.startswith("Tipo de") and not txt.startswith("ID de"):
                    clean_section.append(txt)

        if clean_section:
            eval_dialogue = []
            for line in clean_section:
                line_lower = line.lower()
                if ":" in line and not any(k in line_lower for k in ["cliente", "usuario", "externo"]):
                    if target_nombre and not any(t.lower() in line_lower for t in target_nombre.split(",") if len(t.strip()) > 3):
                        if target_registro and target_registro.lower() not in line_lower:
                            continue
                eval_dialogue.append(line)

            raw_dialogue_text = "\n".join(eval_dialogue if eval_dialogue else clean_section)
            
            header_summary = (
                f"=== FICHA DE EVALUACIÓN WHATSAPP (CONVERSACIÓN LIMPIA) ===\n"
                f"ID Interacción: {interaction_id}\n"
                f"Ejecutivo Evaluado: {exec_info['COLABORADOR']} (Registro: {exec_info['REGISTRO COLABORADOR']})\n"
                f"Supervisor: {exec_info['SUPERVISOR']} | Sub-Equipo: {exec_info['SUB EQUIPO']}\n"
                f"====================================\n\n"
            )
            full_text = header_summary + raw_dialogue_text
            return {
                "archivo": filename,
                "interaction_id": interaction_id,
                "full_text": full_text,
                "executive_interaction": raw_dialogue_text,
                "metadata": exec_info
            }

        # 2. Parsear eventos tabulados de Genesys
        events = []
        for line in paragraphs_text:
            parts = line.split("\t")
            if len(parts) >= 3 and parts[1] in ("Interno", "Externo"):
                fecha_hora = parts[0]
                tipo_part = parts[1]
                sender = parts[2]
                mensaje_texto = parts[3] if len(parts) >= 4 else ""
                # Limpiar caracteres invisibles de formato RTL/LTR de Genesys
                mensaje_texto = mensaje_texto.replace("\u202c", "").replace("\u202b", "").strip()

                events.append({
                    "fecha_hora": fecha_hora,
                    "tipo": tipo_part,
                    "sender": sender,
                    "texto": mensaje_texto
                })

        def is_target_exec(sender):
            s_lower = sender.lower()
            if "bot" in s_lower or "flujo" in s_lower or "acd" in s_lower:
                return False
            if target_registro:
                digits = re.sub(r"\D", "", target_registro)
                if digits and digits in s_lower:
                    return True
            if target_nombre:
                words = [w.lower() for w in re.split(r"[\s,]+", target_nombre) if len(w.strip()) > 3]
                match_count = sum(1 for w in words if w in s_lower)
                if match_count >= 2 or (len(words) == 1 and match_count == 1):
                    return True
            return False

        target_indices = [i for i, ev in enumerate(events) if ev["tipo"] == "Interno" and is_target_exec(ev["sender"])]

        if not target_indices:
            raw_dialogue_text = "Sin mensajes de texto registrados para el ejecutivo evaluado en la transcripción."
        else:
            min_idx = target_indices[0]
            max_idx = target_indices[-1]

            start_idx = min_idx
            if start_idx > 0 and events[start_idx - 1]["tipo"] == "Externo":
                start_idx -= 1

            end_idx = max_idx
            if end_idx < len(events) - 1 and events[end_idx + 1]["tipo"] == "Externo":
                end_idx += 1

            dialogue_lines = []
            for i in range(start_idx, end_idx + 1):
                ev = events[i]
                if ev["tipo"] == "Externo":
                    dialogue_lines.append(f"Cliente ({ev['sender']}) [{ev['fecha_hora']}]: {ev['texto']}")
                elif ev["tipo"] == "Interno" and is_target_exec(ev["sender"]):
                    dialogue_lines.append(f"Ejecutivo Evaluado [{target_nombre or ev['sender']}] [{ev['fecha_hora']}]: {ev['texto']}")

            raw_dialogue_text = "\n".join(dialogue_lines)

        header_summary = (
            f"=== FICHA DE EVALUACIÓN WHATSAPP ===\n"
            f"ID Interacción: {interaction_id}\n"
            f"Ejecutivo Evaluado: {exec_info['COLABORADOR']} (Registro: {exec_info['REGISTRO COLABORADOR']})\n"
            f"Supervisor: {exec_info['SUPERVISOR']} | Sub-Equipo: {exec_info['SUB EQUIPO']}\n"
            f"====================================\n\n"
        )
        full_text = header_summary + raw_dialogue_text

        return {
            "archivo": filename,
            "interaction_id": interaction_id,
            "full_text": full_text,
            "executive_interaction": raw_dialogue_text,
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
