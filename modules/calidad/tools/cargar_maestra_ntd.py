"""
Módulo utilitario para cargar la maestra de niveles NTD desde Excel hacia Teradata.
Lee data/input/MAESTRA_NIVEL_NTD.xlsx y realiza inserciones en DLAB_GEC.M_EXP_MAESTRA_NIVEL_NTD_NORM.
"""
from pathlib import Path
import pandas as pd
from infrastructure.database.database import load_credentials, connect_teradata

def cargar_maestra_ntd(excel_path: Path = None):
    project_root = Path(__file__).resolve().parents[3]
    if excel_path is None:
        excel_path = project_root / "data" / "input" / "MAESTRA_NIVEL_NTD.xlsx"

    if not excel_path.exists():
        print(f"❌ Error: Archivo no encontrado en {excel_path}")
        return False

    print(f"📖 Leyendo {excel_path}...")
    df = pd.read_excel(excel_path)
    print(f"✓ Registros encontrados: {len(df)}")

    cols = [c.upper().strip() for c in df.columns]
    if not all(c in cols for c in ["PLANTILLA", "CASUISTICA", "NIVEL_NTD"]):
        print(f"❌ Error: Las columnas deben ser PLANTILLA, CASUISTICA, NIVEL_NTD. Encontradas: {df.columns.tolist()}")
        return False

    df.columns = cols
    df["PLANTILLA_NORM"] = df["PLANTILLA"].astype(str).str.strip().str.upper()
    df["CASUISTICA_NORM"] = df["CASUISTICA"].astype(str).str.strip().str.upper()
    df["NIVEL_NTD"] = df["NIVEL_NTD"].astype(str).str.strip().str.upper()

    creds = load_credentials()
    print(f"🔌 Conectando a Teradata ({creds['teradata_host']})...")

    try:
        con = connect_teradata(
            creds["teradata_user"],
            creds["teradata_password"],
            host=creds["teradata_host"],
            logmech=creds["teradata_logmech"]
        )
        con.autocommit = True
        cur = con.cursor()

        print("🔍 Verificando existencia de la tabla DLAB_GEC.M_EXP_MAESTRA_NIVEL_NTD_NORM...")
        cur.execute("SELECT COUNT(*) FROM DLAB_GEC.M_EXP_MAESTRA_NIVEL_NTD_NORM")
        filas_previas = cur.fetchone()[0]
        print(f"  Filas previas en la tabla: {filas_previas}")

        print("🚀 Insertando 286 registros normalizados...")
        insert_sql = "INSERT INTO DLAB_GEC.M_EXP_MAESTRA_NIVEL_NTD_NORM (PLANTILLA_NORM, CASUISTICA_NORM, NIVEL_NTD) VALUES (?, ?, ?)"
        
        datos = df[["PLANTILLA_NORM", "CASUISTICA_NORM", "NIVEL_NTD"]].values.tolist()
        cur.executemany(insert_sql, datos)

        cur.execute("SELECT COUNT(*) FROM DLAB_GEC.M_EXP_MAESTRA_NIVEL_NTD_NORM")
        filas_finales = cur.fetchone()[0]
        print(f"✅ Inserción exitosa. Total final en Teradata: {filas_finales} filas.")
        return True

    except Exception as e:
        print(f"❌ Error durante la carga a Teradata: {e}")
        return False

if __name__ == "__main__":
    cargar_maestra_ntd()
