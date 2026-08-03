"""
=====================================================================
CLI RUNNER LOCAL: Auditoría de Transcripciones WhatsApp (.docx) con Gemini 3.1 Flash Lite
Genera el reporte de auditoría gerencial con el formato exacto de producción (Image 2).
Pestañas: 1. Resumen_Evaluaciones | 2. Detalle_Hallazgos
=====================================================================
"""
import os
import sys
import glob
import json
import logging
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno (.env)
load_dotenv()

# Asegurar importación de módulos del proyecto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from modules.transcripciones.use_cases.auditor import TranscriptAuditorUseCase
from modules.transcripciones.extractors.wsp_docx_extractor import WhatsAppTranscriptExtractor
from modules.transcripciones.domain.wsp_rules import load_whatsapp_templates_prompt
from infrastructure.llm.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_transcript_audit")


def main():
    print("\n" + "=" * 70)
    print("   AUDITORÍA GERENCIAL DE TRANSCRIPCIONES WHATSAPP (INTERBANK)")
    print("   Modelo: Gemini 3.1 Flash Lite (Sin fallbacks silenciosos)")
    print("   Plantillas Oficiales: Auditorias Wsp/Plantillas TLV WhatsApp.xlsx")
    print("=" * 70)

    # 1. Verificar API Key de Gemini
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ Error: No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en el archivo .env")
        sys.exit(1)

    # 2. Cargar plantillas oficiales de WhatsApp
    wsp_templates_text = load_whatsapp_templates_prompt("Auditorias Wsp/Plantillas TLV WhatsApp.xlsx")

    # 3. Extraer transcripciones WhatsApp (.docx)
    wsp_extractor = WhatsAppTranscriptExtractor(folder_path="Auditorias Wsp")
    transcripts = wsp_extractor.get_all_transcripts()

    if not transcripts:
        print(f"\n⚠️ No se encontraron archivos de transcripción .docx en 'Auditorias Wsp/'")
        sys.exit(1)

    print(f"\n📁 Transcripciones de WhatsApp detectadas: {len(transcripts)} archivos .docx en 'Auditorias Wsp/'")

    # 4. Modo de auditoría (Single vs Multi-Agent)
    print("\n" + "=" * 50)
    print("🤖 Seleccione el Modo de Auditoría de Inteligencia Artificial:")
    print("  [1] Single-Agent (Evaluador directo exhaustivo con Gemini 3.1 Flash Lite)")
    print("  [2] Multi-Agent  (Doble Juez Adversarial: Juez Gramática/Trato + Juez Protocolo)")
    print("=" * 50)
    mode_choice = input("Seleccione el modo (1 o 2) [Enter por defecto: 1 - Single Agent]: ").strip()
    audit_mode = "multi" if mode_choice == "2" else "single"
    mode_label = "Multi-Agent (Doble Juez Adversarial)" if audit_mode == "multi" else "Single-Agent (Evaluador Directo)"

    # 5. Cantidad de archivos a procesar
    max_count_input = input(f"\n¿Cuántos chats deseas auditar? (1 - {len(transcripts)}) [Enter para procesar los {len(transcripts)}]: ").strip()
    if max_count_input.isdigit():
        max_files = min(int(max_count_input), len(transcripts))
    else:
        max_files = len(transcripts)

    selected_transcripts = transcripts[:max_files]

    print("\n" + "-" * 70)
    print(f"🚀 Iniciando Auditoría de Calidad:")
    print(f"   • Modo: {mode_label}")
    print(f"   • Modelo: gemini-3.1-flash-lite")
    print(f"   • Chats a procesar: {len(selected_transcripts)} / {len(transcripts)}")
    print("-" * 70 + "\n")

    # 6. Inicializar el caso de uso del auditor
    llm_client = GeminiClient(default_model="gemini-3.1-flash-lite")
    auditor = TranscriptAuditorUseCase(llm_client=llm_client)

    all_hallazgos = []
    audit_summary = []

    start_time = datetime.now()

    for idx, item in enumerate(selected_transcripts, 1):
        filename = item["archivo"]
        content = item["full_text"]
        metadata = item["metadata"]

        supervisor = metadata.get("SUPERVISOR", "N/A")
        colaborador = metadata.get("COLABORADOR", "N/A")
        registro = metadata.get("REGISTRO COLABORADOR", "N/A")
        sub_equipo = metadata.get("SUB EQUIPO", "Televentas")

        print(f"[{idx}/{len(selected_transcripts)}] Procesando chat '{filename}' ({colaborador} - {sub_equipo})...")

        try:
            result = auditor.audit_transcript(
                conversation_text=content,
                conv_metadata={"archivo": filename, "registro": registro, "colaborador": colaborador},
                sub_equipo=sub_equipo,
                templates_text=wsp_templates_text,
                mode=audit_mode
            )

            hallazgos = result.get("hallazgos", [])

            # Conteo por Eje
            cant_gramatica = sum(1 for h in hallazgos if "Gramática" in h.get("eje", ""))
            cant_trato = sum(1 for h in hallazgos if "Trato" in h.get("eje", ""))
            cant_protocolo = sum(1 for h in hallazgos if "Protocolo" in h.get("eje", ""))

            print(f"   ✅ Auditoría completada: {len(hallazgos)} hallazgo(s) detectado(s) [Gramática: {cant_gramatica}, Trato: {cant_trato}, Protocolo: {cant_protocolo}]")

            # Acumular hallazgos individuales para la pestaña "Detalle_Hallazgos"
            for h in hallazgos:
                all_hallazgos.append({
                    "ID Conversación": item["interaction_id"],
                    "Ejecutivo": colaborador,
                    "Sub-equipo": sub_equipo,
                    "Eje": h.get("eje", "Gramática"),
                    "Gravedad": h.get("gravedad", "Bajo"),
                    "Mensaje del Ejecutivo": h.get("mensaje_ejecutivo", ""),
                    "Hallazgo/Error Detectado": h.get("hallazgo", ""),
                    "Sugerencia de Corrección": h.get("sugerencia", "")
                })

            # Acumular resumen por chat para la pestaña "Resumen_Evaluaciones" (con Transcripción Completa al final)
            audit_summary.append({
                "ID Conversación": item["interaction_id"],
                "Supervisor": supervisor,
                "Registro Colaborador": registro,
                "Ejecutivo": colaborador,
                "Sub-equipo": sub_equipo,
                "Archivo": filename,
                "Total Observaciones": len(hallazgos),
                "Obs Gramática": cant_gramatica,
                "Obs Trato Cliente": cant_trato,
                "Obs Protocolo": cant_protocolo,
                "Estado Evaluación": "CON OBSERVACIONES" if len(hallazgos) > 0 else "CONFORME",
                "Transcripción Completa": content
            })

        except Exception as e:
            print(f"   ❌ Error auditando '{filename}': {e}")
            raise e

    # 6. Exportar Excel con la estructura de producción de 2 Pestañas (Imagen 2)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"Reporte_Auditoria_WhatsApp_{timestamp_str}.xlsx"
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    excel_path = os.path.join(logs_dir, excel_filename)

    df_summary = pd.DataFrame(audit_summary)
    df_hallazgos = pd.DataFrame(all_hallazgos)

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Resumen_Evaluaciones", index=False)
        if not df_hallazgos.empty:
            df_hallazgos.to_excel(writer, sheet_name="Detalle_Hallazgos", index=False)
        else:
            pd.DataFrame(columns=[
                "ID Conversación", "Ejecutivo", "Sub-equipo", "Eje", "Gravedad",
                "Mensaje del Ejecutivo", "Hallazgo/Error Detectado", "Sugerencia de Corrección"
            ]).to_excel(writer, sheet_name="Detalle_Hallazgos", index=False)

    total_time = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 70)
    print("🎉 AUDITORÍA DE WHATSAPP FINALIZADA")
    print("=" * 70)
    print(f" • Tiempo total: {total_time:.2f} segundos")
    print(f" • Transcripciones evaluadas: {len(audit_summary)}")
    print(f" • Hallazgos validados: {len(all_hallazgos)}")
    print(f" • Reporte Excel Gerencial guardado en: {excel_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
