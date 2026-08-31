"""
=====================================================================
CLI RUNNER LOCAL: Auditoría de Transcripciones WhatsApp (.docx) con Gemini 3.1 Flash Lite
Genera el reporte de auditoría gerencial con el formato exacto de producción (Image 2).
Pestañas: 1. Resumen_Evaluaciones | 2. Detalle_Hallazgos
=====================================================================
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno (.env)
load_dotenv()

from pathlib import Path

# Asegurar importación de módulos del proyecto (desde raíz)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.verint.transcripciones.use_cases.auditor import TranscriptAuditorUseCase
from modules.verint.transcripciones.extractors.wsp_docx_extractor import WhatsAppTranscriptExtractor
from modules.verint.transcripciones.domain.wsp_rules import load_whatsapp_templates_prompt
from modules.verint.transcripciones.presenters.excel_presenter import TranscriptExcelPresenter
from infrastructure.llm.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_transcript_audit")


def main():
    wsp_input_dir = os.environ.get(
        "WSP_INPUT_DIR",
        os.path.join(PROJECT_ROOT, "data", "input", "auditorias_wsp")
    )

    if not os.path.isdir(wsp_input_dir):
        raise FileNotFoundError(
            f"Directorio de entrada WSP no encontrado: '{wsp_input_dir}'. "
            "Define la variable de entorno WSP_INPUT_DIR o asegúrate de que exista 'data/input/auditorias_wsp/'."
        )

    print("\n" + "=" * 70)
    print("   AUDITORÍA GERENCIAL DE TRANSCRIPCIONES WHATSAPP (INTERBANK)")
    print("   Modelo: Gemini 3.1 Flash Lite (Sin fallbacks silenciosos)")
    print(f"   Plantillas Oficiales: {wsp_input_dir}/Plantillas TLV WhatsApp.xlsx")
    print("=" * 70)

    # 1. Verificar API Key de Gemini
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en el archivo .env")

    # 2. Cargar plantillas oficiales de WhatsApp
    template_path = os.path.join(wsp_input_dir, "Plantillas TLV WhatsApp.xlsx")
    wsp_templates_text = load_whatsapp_templates_prompt(template_path)

    # 3. Extraer transcripciones WhatsApp (.docx)
    wsp_extractor = WhatsAppTranscriptExtractor(folder_path=wsp_input_dir)
    transcripts = wsp_extractor.get_all_transcripts()

    if not transcripts:
        raise FileNotFoundError(f"No se encontraron archivos .docx en '{wsp_input_dir}'")

    print(f"\n   Transcripciones detectadas: {len(transcripts)} archivos .docx en '{wsp_input_dir}'")

    import argparse
    parser = argparse.ArgumentParser(description="Auditoría Gerencial de Transcripciones WhatsApp")
    parser.add_argument("--mode", choices=["single", "multi"], help="Modo de auditoría: 'single' o 'multi'")
    parser.add_argument("--count", type=int, help="Número de chats a auditar")
    args, unknown = parser.parse_known_args()

    # 4. Modo de auditoría (Single vs Multi-Agent)
    if args.mode:
        audit_mode = args.mode
    else:
        print("\n" + "=" * 65)
        print("🤖 Seleccione el Modo de Auditoría de Inteligencia Artificial:")
        print("  [1] Single-Agent (Evaluador directo exhaustivo con Gemini 3.1 Flash Lite)")
        print("  [2] Multi-Agent  (Sistema de 4 Agentes: 1 Orquestador + 3 Especialistas)")
        print("=" * 65)
        mode_choice = input("Seleccione el modo (1 o 2) [Enter por defecto: 2 - Multi-Agent]: ").strip()
        audit_mode = "single" if mode_choice == "1" else "multi"

    mode_label = "Multi-Agent (Sistema de 4 Agentes Especializados)" if audit_mode == "multi" else "Single-Agent (Evaluador Directo)"

    # 5. Cantidad de archivos a procesar (Por defecto: 100% de los chats detectados)
    if args.count:
        max_files = min(args.count, len(transcripts))
    else:
        max_files = len(transcripts)

    selected_transcripts = transcripts[:max_files]

    print("\n" + "-" * 70)
    print(f"🚀 Iniciando Auditoría de Calidad:")
    print(f"   • Modo: {mode_label}")
    print(f"   • Modelo: gemini-3.1-flash-lite")
    print(f"   • Chats a procesar: {len(selected_transcripts)} / {len(transcripts)}")
    print("-" * 70 + "\n")

    # 6. Inicializar el caso de uso del auditor (Inyección de dependencias)
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

            # Conteo por Eje (Normalizado e insensible a mayúsculas/tildes)
            cant_gramatica = sum(1 for h in hallazgos if "gram" in h.get("eje", "").lower())
            cant_trato = sum(1 for h in hallazgos if "trato" in h.get("eje", "").lower())
            cant_protocolo = sum(1 for h in hallazgos if "proto" in h.get("eje", "").lower())
            
            # Cualquier hallazgo residual no clasificado se asigna al eje por defecto
            unclassified = len(hallazgos) - (cant_gramatica + cant_trato + cant_protocolo)
            if unclassified > 0:
                cant_gramatica += unclassified

            total_obs = cant_gramatica + cant_trato + cant_protocolo

            print(f"   ✅ Auditoría completada: {total_obs} hallazgo(s) detectado(s) [Gramática: {cant_gramatica}, Trato: {cant_trato}, Protocolo: {cant_protocolo}]")

            # Acumular hallazgos individuales para la pestaña "Detalle_Hallazgos"
            for h in hallazgos:
                all_hallazgos.append({
                    "ID Conversación": item["interaction_id"],
                    "Ejecutivo": colaborador,
                    "Sub-equipo": sub_equipo,
                    "Eje": h.get("eje", "Gramática"),
                    "Gravedad": h.get("gravedad", "Leve"),
                    "Mensaje del Ejecutivo": h.get("mensaje_ejecutivo", ""),
                    "Hallazgo/Error Detectado": h.get("hallazgo", ""),
                    "Sugerencia de Corrección": h.get("sugerencia", "")
                })

            # Acumular resumen por chat para la pestaña "Resumen_Evaluaciones"
            audit_summary.append({
                "ID Conversación": item["interaction_id"],
                "Supervisor": supervisor,
                "Registro Colaborador": registro,
                "Ejecutivo": colaborador,
                "Sub-equipo": sub_equipo,
                "Archivo": filename,
                "Total Observaciones": total_obs,
                "Obs Gramática": cant_gramatica,
                "Obs Trato Cliente": cant_trato,
                "Obs Protocolo": cant_protocolo,
                "Estado Evaluación": "CON OBSERVACIONES" if total_obs > 0 else "CONFORME",
                "Transcripción Completa": item.get("executive_interaction", item["full_text"])
            })

        except Exception as e:
            print(f"   ❌ Error auditando '{filename}': {e}")
            raise e

    # 7. Exportar Excel con el Presenter (Capa de Presentación Desacoplada)
    presenter = TranscriptExcelPresenter(default_output_dir="logs")
    excel_path = presenter.generate_report(audit_summary=audit_summary, all_hallazgos=all_hallazgos)

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
