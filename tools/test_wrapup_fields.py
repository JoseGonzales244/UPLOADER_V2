import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "Q380dsnrpdyzT8hEhpYbEXdyBCwamAjZwxQytuIMmbAnYJ1KneO4ZqYCsshD28XB4nqhuG0k7zpe46PmUJVjrg"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "accept": "*/*"
}

# Paso 1: Obtener catálogo completo de wrapup codes
print("Obteniendo catálogo de wrapup codes de Genesys...")
url_wrapup = "https://api.mypurecloud.com/api/v2/routing/wrapupcodes?pageSize=500"
resp = requests.get(url_wrapup, headers=headers, verify=False, timeout=15)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    entities = resp.json().get("entities", [])
    print(f"Total wrapup codes encontrados: {len(entities)}")
    
    # Guardar catálogo completo
    with open("tools/wrapupcodes_catalog.json", "w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)
    print("Catálogo guardado en tools/wrapupcodes_catalog.json")

    # Buscar los UUIDs que sabemos
    uuids_buscar = [
        "f1072c12-a557-4f23-93dc-451a0bd50d9a",  # Conversacion #3 (ACEPTA CAMPANA)
        "297e1f14-875d-476d-bd2b-7ae0e06b8abc"   # Conversacion #4 (NO ACEPTA)
    ]
    
    print("\n--- Resolución de UUIDs conocidos ---")
    for e in entities:
        if e.get("id") in uuids_buscar:
            print(f"UUID: {e.get('id')}")
            print(f"  Nombre: {e.get('name')}")
            print(f"  Descripción: {e.get('description')}")
    
    # Imprimir todos los que contengan ACEPTA
    print("\n--- Todos los wrapup codes que contienen ACEPTA ---")
    for e in entities:
        name = (e.get("name") or "").upper()
        if "ACEPTA" in name:
            print(f"  UUID={e.get('id')} | Nombre={e.get('name')}")
else:
    print(f"Error: {resp.text[:300]}")
