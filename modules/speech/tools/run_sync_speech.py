"""
CLI Runner para el pipeline de sincronización de transcripciones TC hacia SQL Server (DB_SPEECH.TRANSCRIPCION).

Uso:
  python -m tools.run_sync_speech --limit 5
  python -m tools.run_sync_speech --plantilla "Exp. Compra - TC"
"""
import sys
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.speech.use_cases.speech_orchestrator import sync_transcripts_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("RunSyncSpeech")


def main():
    parser = argparse.ArgumentParser(description="Sincronizar transcripciones de TC hacia SQL Server DB_SPEECH.TRANSCRIPCION.")
    parser.add_argument("--plantilla", type=str, default="Exp. Compra - TC", help="Nombre de plantilla en Teradata (default: 'Exp. Compra - TC')")
    parser.add_argument("--limit", type=int, default=None, help="Límite de registros para prueba rápida (ej: 5, 10)")
    parser.add_argument("--min-date", type=str, default="2026-07-01", help="Fecha mínima para búsqueda histórica de TIPO_LEAD en Insight (YYYY-MM-DD)")
    parser.add_argument("--skip-sql", action="store_true", help="Detiene el pipeline tras descargar los .txt y omite la carga a SQL Server.")

    args = parser.parse_args()

    logger.info("==================================================================")
    logger.info("🚀 INICIANDO PIPELINE DE SINCRONIZACIÓN DE TRANSCRIPCIONES (SOFIA)")
    logger.info(f"   Plantilla: {args.plantilla}")
    logger.info(f"   Límite: {args.limit or 'Sin límite (todos los casos)'}")
    logger.info(f"   Fecha Mínima Insight: {args.min_date}")
    logger.info(f"   Omitir carga SQL: {args.skip_sql}")
    logger.info("==================================================================")

    try:
        res = sync_transcripts_pipeline(
            plantilla=args.plantilla,
            limit=args.limit,
            min_insight_date=args.min_date,
            skip_sql=args.skip_sql
        )
        logger.info("\n📊 Resumen de Ejecución:")
        logger.info(f"   • Interacciones extraídas de Teradata: {res.get('total_extraidos', 0)}")
        logger.info(f"   • Tipos de Lead obtenidos de Insight : {res.get('total_tipos_lead', 0)}")
        logger.info(f"   • Transcripciones descargadas Verint : {res.get('total_transcritos', 0)}")
        if args.skip_sql:
            logger.info("   • Carga en SQL Server                : OMITIDA (--skip-sql)")
        else:
            logger.info(f"   • Registros sincronizados en SQL     : {res.get('total_sincronizados', 0)}")
        logger.info("✅ PROCESO COMPLETADO.")
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución del pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
