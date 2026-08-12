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
    
    # 3. Probar llamada API nativa a empleados
    print("\n--- Paso 2: Consulta de API REST (/user-mgmt-api/v2/employees) ---")
    emp_url = f"{client.base_url}/wfo/user-mgmt-api/v2/employees?filter[username][EQUAL]={client.username}"
    
    res = client.session.get(emp_url)
    print(f"Status Code: {res.status_code}")
    
    if res.status_code == 200:
        data = res.json()
        print("✅ Respuesta recibida exitosamente desde la API de Verint:")
        print(f"   Contenido: {str(data)[:300]}...")
    else:
        print(f"⚠️ Error en consulta API. HTTP Status: {res.status_code}")
        print(f"   Respuesta: {res.text[:300]}")

    print("\n==================================================")
    print("🎉 PRUEBA FINALIZADA CORRECTAMENTE")
    print("==================================================\n")

if __name__ == "__main__":
    test_verint_sso_connection()
