import os
import sys
import time
import requests
import urllib3
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(BASE_DIR / ".env")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_teradata_operativo():
    print("\n" + "-" * 70)
    print("1. Teradata Operativo (Pipeline Calidad / Consumo / Cierre)")
    print("-" * 70)
    user = os.getenv("TERADATA_USER")
    pwd = os.getenv("TERADATA_PASSWORD")
    host = os.getenv("TERADATA_HOST", "IBKTD")
    logmech = os.getenv("TERADATA_LOGMECH", "TD2")

    if not user or not pwd:
        print("❌ [FAIL] Variables TERADATA_USER o TERADATA_PASSWORD no configuradas en .env")
        return False

    print(f"   Conectando a {host} (Usuario: {user}, Logmech: {logmech})...")
    t0 = time.time()
    try:
        import teradatasql
        with teradatasql.connect(host=host, user=user, password=pwd, logmech=logmech) as con:
            cur = con.cursor()
            cur.execute("SELECT CURRENT_USER, CURRENT_DATE;")
            row = cur.fetchone()
            dur = time.time() - t0
            print(f"✅ [OK] Conectado exitosamente en {dur:.2f}s | Usuario activo: {row[0]} | Fecha Teradata: {row[1]}")
            return True
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error de conexión ({dur:.2f}s): {e}")
        print("   Orientación: Verificar VPN corporativa y que el usuario/clave APP_GEC sean correctos.")
        return False


def test_teradata_select():
    print("\n" + "-" * 70)
    print("2. Teradata Select (Fase 5 Consumo Select - Credencial Secundaria)")
    print("-" * 70)
    user = os.getenv("TERADATA_USER_SELECT")
    pwd = os.getenv("TERADATA_PASSWORD_SELECT")
    host = os.getenv("TERADATA_HOST_SELECT", "IBKTD")
    logmech = os.getenv("TERADATA_LOGMECH_SELECT", "LDAP")

    if not user or not pwd:
        print("⚠️ [WARN] TERADATA_USER_SELECT o TERADATA_PASSWORD_SELECT no definidos (requerido solo para Fase 5)")
        return None

    print(f"   Conectando a {host} (Usuario: {user}, Logmech: {logmech})...")
    t0 = time.time()
    try:
        import teradatasql
        with teradatasql.connect(host=host, user=user, password=pwd, logmech=logmech) as con:
            cur = con.cursor()
            cur.execute("SELECT CURRENT_USER, CURRENT_DATE;")
            row = cur.fetchone()
            dur = time.time() - t0
            print(f"✅ [OK] Conectado exitosamente en {dur:.2f}s | Usuario: {row[0]} | Fecha: {row[1]}")
            return True
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error en Teradata Select ({dur:.2f}s): {e}")
        print("   Orientación: Verificar que la contraseña LDAP personal no esté vencida.")
        return False


def test_insight():
    print("\n" + "-" * 70)
    print("1. Insight PureCloud (Servicio de Ingesta s425vp01)")
    print("-" * 70)
    user = os.getenv("USERNAME_INSIGHT")
    pwd = os.getenv("PASSWORD_INSIGHT")
    url = "https://s425vp01/Insight"

    if not user or not pwd:
        print("❌ [FAIL] USERNAME_INSIGHT o PASSWORD_INSIGHT no configurados en .env")
        return False

    print(f"   Iniciando sesión en {url} (Usuario: {user})...")
    t0 = time.time()
    try:
        session = requests.Session()
        resp = session.post(
            url,
            data={"registro": user, "password": pwd},
            verify=False,
            timeout=20
        )
        dur = time.time() - t0
        if resp.status_code == 200:
            print(f"✅ [OK] Sesión iniciada exitosamente en {dur:.2f}s (HTTP 200)")
            return True
        else:
            print(f"❌ [FAIL] Servidor retornó código HTTP {resp.status_code} ({dur:.2f}s)")
            return False
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error conectando a Insight ({dur:.2f}s): {e}")
        print("   Orientación: Verificar VPN corporativa y acceso a la red interna s425vp01.")
        return False


def test_verint():
    print("\n" + "-" * 70)
    print("2. Verint WFO Speech Analytics (Transcripciones de Llamadas)")
    print("-" * 70)
    from modules.verint.services.verint_api_client import VerintAPIClient

    user = os.getenv("VERINT_USER")
    pwd = os.getenv("VERINT_PASS")
    if not user:
        print("❌ [FAIL] VERINT_USER no configurado en .env")
        return False

    print(f"   Comprobando autenticación Verint WFO (Usuario: {user})...")
    t0 = time.time()
    try:
        client = VerintAPIClient(username=user, password=pwd or "")
        if client.login():
            token = client.impact360_token or "Token en Cookie de sesión"
            dur = time.time() - t0
            print(f"✅ [OK] Autenticado exitosamente en Verint en {dur:.2f}s | Token: {token[:12]}...")
            client.close()
            return True
        else:
            dur = time.time() - t0
            print(f"❌ [FAIL] Login no completado en Verint ({dur:.2f}s)")
            return False
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error en autenticación Verint ({dur:.2f}s): {e}")
        return False


def test_genesys_cdp():
    print("\n" + "-" * 70)
    print("3. Genesys Cloud (Descarga de Audios vía Chrome CDP)")
    print("-" * 70)
    cdp_url = os.getenv("GENESYS_CDP_URL", "http://localhost:9222")
    print(f"   Consultando puerto de depuración Chrome en {cdp_url}...")
    t0 = time.time()
    try:
        resp = requests.get(f"{cdp_url}/json/version", timeout=3)
        dur = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            browser = data.get("Browser", "Chrome")
            print(f"✅ [OK] Chrome CDP activo y respondiendo ({dur:.2f}s) | Navegador: {browser}")
            return True
        else:
            print(f"⚠️ [WARN] Chrome CDP retornó código {resp.status_code}")
            return False
    except Exception:
        dur = time.time() - t0
        print(f"⚠️ [INFO] Chrome no está abierto en modo depuración (puerto 9222) ({dur:.2f}s)")
        print("   Esto es normal si no se está ejecutando la descarga de audios de Genesys en este instante.")
        print("   Para habilitarlo antes de descargar audios, abra Chrome con:")
        print('   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\ChromeProfile"')
        return None


def test_sqlserver_speech():
    print("\n" + "-" * 70)
    print("4. SQL Server DB_SPEECH (Motor sofIA)")
    print("-" * 70)
    server = os.getenv("SPEECH_SQLSERVER_SERVER")
    db = os.getenv("SPEECH_SQLSERVER_DATABASE", "DB_SPEECH")
    user = os.getenv("SPEECH_SQLSERVER_USER")
    pwd = os.getenv("SPEECH_SQLSERVER_PASSWORD")
    driver = os.getenv("SPEECH_SQLSERVER_DRIVER", "{ODBC Driver 17 for SQL Server}")

    if not server or "tu_servidor" in server.lower():
        print("ℹ️ [OMITIDO] SPEECH_SQLSERVER_SERVER no configurado o con valores plantilla.")
        return None

    print(f"   Conectando a {server} (Base: {db})...")
    t0 = time.time()
    try:
        import pyodbc
        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={db};UID={user};PWD={pwd};Timeout=10;"
        with pyodbc.connect(conn_str) as con:
            cur = con.cursor()
            cur.execute("SELECT 1;")
            dur = time.time() - t0
            print(f"✅ [OK] Conectado exitosamente a SQL Server en {dur:.2f}s")
            return True
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error en SQL Server DB_SPEECH ({dur:.2f}s): {e}")
        return False


def test_gemini_api():
    print("\n" + "-" * 70)
    print("5. Google Gemini AI (Auditorías WhatsApp y Cumplimiento PA)")
    print("-" * 70)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ [FAIL] GEMINI_API_KEY no configurada en .env")
        return False

    print("   Enviando ping de validación a la API de Gemini...")
    t0 = time.time()
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Responde únicamente con la palabra: OK"
        )
        dur = time.time() - t0
        txt = (resp.text or "").strip()
        print(f"✅ [OK] Respuesta recibida de Gemini en {dur:.2f}s | Salida: {txt}")
        return True
    except Exception as e:
        dur = time.time() - t0
        print(f"❌ [FAIL] Error en API de Gemini ({dur:.2f}s): {e}")
        return False


def main():
    include_teradata = "--teradata" in sys.argv or "-t" in sys.argv

    print("=" * 75)
    print(" 🚀 DIAGNÓSTICO INTEGRAL DE SERVICIOS Y ACCESOS EN VIVO")
    print(" Plataforma Calidad & Inteligencia Comercial Televentas")
    print("=" * 75)

    results = {}
    if include_teradata:
        results["Teradata Operativo"] = test_teradata_operativo()
        results["Teradata Select"] = test_teradata_select()

    results["Insight PureCloud"] = test_insight()
    results["Verint WFO"] = test_verint()
    results["Genesys Chrome CDP"] = test_genesys_cdp()
    results["SQL Server sofIA"] = test_sqlserver_speech()
    results["Gemini AI"] = test_gemini_api()

    print("\n" + "=" * 75)
    print(" 📊 RESUMEN FINAL DE DISPONIBILIDAD DE SERVICIOS")
    print("=" * 75)
    for service, res in results.items():
        if res is True:
            badge = "✅ ACTIVO / OPERATIVO"
        elif res is False:
            badge = "❌ INACCESIBLE / ERROR"
        else:
            badge = "ℹ️ OMITIDO / EN ESPERA"
        print(f"  • {service.ljust(26)}: {badge}")
    print("=" * 75)


if __name__ == "__main__":
    main()
