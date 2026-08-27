"""
CLI de diagnóstico para probar y depurar la consulta y conexión a Insight.

Uso:
  python -m tools.test_insight_service --id "0040b97b-a5ca-45f3-a12c-46e8c0f790f6"
  python -m tools.test_insight_service --limit-td 5
"""
import sys
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.speech.services.insight_lead_service import InsightLeadService
from modules.speech.use_cases.speech_orchestrator import extract_interactions_from_teradata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TestInsight")


def main():
    parser = argparse.ArgumentParser(description="Diagnóstico y pruebas de InsightLeadService.")
    parser.add_argument("--id", type=str, help="CONID / conversationID específico a consultar.")
    parser.add_argument("--limit-td", type=int, default=None, help="Extraer N casos desde Teradata para probar en Insight.")
    parser.add_argument("--min-date", type=str, default="2026-07-01", help="Fecha mínima histórica (YYYY-MM-DD).")
    args = parser.parse_args()

    cids = []
    if args.id:
        cids = [args.id.strip()]
    elif args.limit_td:
        logger.info(f"Obteniendo {args.limit_td} IDs desde Teradata...")
        interactions = extract_interactions_from_teradata(limit=args.limit_td)
        cids = [item["ID_LLAMADA"] for item in interactions if item.get("ID_LLAMADA")]
    else:
        logger.error("Especifica --id <CONID> o --limit-td <N>")
        sys.exit(1)

    logger.info(f"🔍 IDs a consultar en Insight ({len(cids)}): {cids}")

    service = InsightLeadService()
    logger.info(f"Usuario Insight: {service.username}")
    logger.info(f"URL Base: {service.base_url}")
    
    # Mostrar el SQL exacto que se va a enviar
    sql = service._build_query_sql(cids, min_date=args.min_date)
    logger.info("================== SQL GENERADO ==================\n" + sql + "\n==================================================")

    try:
        results = service.get_tipos_lead_batch(cids, min_date=args.min_date)
        logger.info("================== RESULTADOS ==================")
        for cid in cids:
            logger.info(f" • {cid} -> {results.get(cid, 'NO_MAPEADO')}")
        logger.info("================================================")
    except Exception as e:
        logger.error(f"❌ Error consultando Insight: {e}", exc_info=True)


if __name__ == "__main__":
    main()
