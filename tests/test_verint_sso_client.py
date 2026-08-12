import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.verint.services.verint_api_client import VerintAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def test_verint_sso_connection():
    """
    Prueba de integración para verificar la autenticación SSO de Verint WFO,
    captura del Impact360AuthToken y consumo de la API REST.
    """
    print("\n==================================================")
    print("🚀 INICIANDO PRUEBA DE CONEXIÓN VERINT (SSO + API REST)")
    print("==================================================\n")
    
    # 1. Crear el cliente API
    client = VerintAPIClient()
    
    print(f"👤 Usuario configurado: {client.username}")
    print(f"🌐 Base URL: {client.base_url}")
    
    if not client.username:
        print("❌ ERROR: VERINT_USER no está definido en el entorno / .env")
        sys.exit(1)
        
    # 2. Verificar o forzar inicio de sesión
    print("\n--- Paso 1: Autenticación / Verificación de Sesión ---")
    auth_success = client.login()
    
    if not auth_success:
        print("❌ Falló la autenticación en Verint WFO.")
        sys.exit(1)
        
    print(f"✅ Autenticado exitosamente.")
    print(f"🔑 Impact360AuthToken: {client.impact360_token}")
    
    # 3. Probar llamada real a la API de Speech Analytics
    print("\n--- Paso 2: Inicialización de Sesión de Speech Analytics ---")
    sid = client.init_speech_session()
    
    if sid:
        print(f"✅ SessionId de Speech Analytics inicializado exitosamente: {sid}")
        print("\n--- Paso 3: Consulta de Reportes Guardados (GetSavedReports) ---")
        reports = client.get_saved_reports()
        print(f"📊 Reportes guardados encontrados en Verint: {len(reports)}")
        if reports:
            print(f"   Primer reporte: {reports[0].get('Name')} (URL: {reports[0].get('URL')})")
    else:
        print("⚠️ No se pudo obtener SessionId de Speech Analytics. Revisa los logs.")

    print("\n==================================================")
    print("🎉 PRUEBA FINALIZADA CORRECTAMENTE")
    print("==================================================\n")

if __name__ == "__main__":
    test_verint_sso_connection()
