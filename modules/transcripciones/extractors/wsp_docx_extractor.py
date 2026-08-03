"""
Extractor de Transcripciones de WhatsApp (.docx) con Filtrado de Ejecutivo a Evaluar.
Filtra estrictamente la conversación entre el Cliente y el Ejecutivo asignado en Ejecutivos_Gestion_Wsp.xlsx,
omitiendo mensajes de Bot/Flujo y de otros ejecutivos no evaluados.
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
        Extrae y filtra la transcripción de un archivo .docx de WhatsApp.
        Filtra únicamente los mensajes emitidos por el ejecutivo asignado a la interacción y el cliente.
        Omite bots y otros ejecutivos no evaluados.
        """
        filename = os.path.basename(docx_path)
        interaction_id = os.path.splitext(filename)[0]

        # Buscar metadatos del ejecutivo evaluado en el Excel
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
        
        filtered_dialogue = []
        excluded_other_execs = 0
        excluded_bots = 0

        for p in doc.paragraphs:
            txt = p.text.strip()
            if not txt:
                continue

            parts = txt.split("\t")
            if len(parts) >= 3 and parts[1] in ("Interno", "Externo"):
                fecha_hora = parts[0]
                tipo_part = parts[1]
                sender = parts[2]
                mensaje_texto = parts[3] if len(parts) >= 4 else ""

                if tipo_part == "Externo":
                    linea = f"Cliente ({sender})"
                    if mensaje_texto:
                        linea += f": {mensaje_texto}"
                    filtered_dialogue.append(linea)

                elif tipo_part == "Interno":
                    sender_lower = sender.lower()

                    # Comprobar si corresponde al bot/flujo
                    if "bot" in sender_lower or "flujo" in sender_lower or "acd" in sender_lower:
                        excluded_bots += 1
                        continue

                    # Comprobar si el emisor es el Ejecutivo Evaluado por Registro o Nombre
                    is_target = False
                    if target_registro and target_registro.lower() in sender_lower:
                        is_target = True
                    elif target_nombre and any(token.lower() in sender_lower for token in target_nombre.split(",") if len(token.strip()) > 3):
                        is_target = True

                    if is_target:
                        linea = f"Ejecutivo Evaluado [{target_nombre or sender}] ({fecha_hora})"
                        if mensaje_texto:
                            linea += f": {mensaje_texto}"
                        filtered_dialogue.append(linea)
                    else:
                        excluded_other_execs += 1

        logger.info(
            f"Chat '{filename}' parseado: {len(filtered_dialogue)} líneas validadas "
            f"(Excluidos: {excluded_other_execs} mensajes de otros ejecutivos, {excluded_bots} de bots)."
        )

        header_summary = (
            f"=== FICHA DE EVALUACIÓN WHATSAPP ===\n"
            f"ID Interacción: {interaction_id}\n"
            f"Ejecutivo Evaluado: {exec_info['COLABORADOR']} (Registro: {exec_info['REGISTRO COLABORADOR']})\n"
            f"Supervisor: {exec_info['SUPERVISOR']} | Sub-Equipo: {exec_info['SUB EQUIPO']}\n"
            f"====================================\n\n"
        )

        full_text = header_summary + ("\n".join(filtered_dialogue) if filtered_dialogue else "Sin mensajes registrados para el ejecutivo evaluado.")

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
