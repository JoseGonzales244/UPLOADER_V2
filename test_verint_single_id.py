import sys
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.verint.services.verint_api_client import VerintAPIClient
from modules.verint.tools.export_verint_docx_by_ids import export_single_call_to_docx


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("Uso: .\\.venv\\Scripts\\python test_verint_single_id.py <ID_DE_LLAMADA>")
        sys.exit(1)

    call_id = sys.argv[1].strip()
    user = os.getenv("VERINT_USER")
    pwd = os.getenv("VERINT_PASS")
    output_dir = BASE_DIR / "data" / "input" / "auditorias_wsp"

    print("=" * 65)
    print(f"Probando extracción Verint a DOCX para ID: {call_id}")
    print(f"Carpeta destino: {output_dir}")
    print("=" * 65)

    client = VerintAPIClient(username=user, password=pwd)
    if not client.login():
        print("❌ Error: No se pudo conectar a Verint WFO. Verifica VPN / .env.")
        sys.exit(1)

    try:
        docx_path = export_single_call_to_docx(call_id, client, output_dir)
        if docx_path and docx_path.exists():
            print(f"\n✅ Archivo Word generado con éxito:\n   {docx_path}")
        else:
            print(f"\n⚠️ Verint no retornó diálogo o contacto para ID: {call_id}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
