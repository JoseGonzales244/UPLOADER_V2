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

# Buscar la interaccion que sabemos que tiene ACEPTA CAMPANA
# DNI 09076261, telefono 965774357, julio 2026, duracion 15m 37s aprox (15/07/2026)
URL = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"

payload = {
    "order": "asc",
    "orderBy": "conversationStart",
    "paging": {"pageSize": 50, "pageNumber": 1},
    "interval": "2026-07-01T05:00:00.000Z/2026-08-01T05:00:00.000Z",
    "segmentFilters": [
        {
            "type": "or",
            "predicates": [
                {"dimension": "dnis", "value": "965774357"},
                {"dimension": "dnis", "value": "995084684"}
            ]
        }
    ]
}

print("Buscando interacciones del DNI de prueba...")
resp = requests.post(URL, headers=headers, json=payload, verify=False, timeout=15)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    conversations = resp.json().get("conversations", [])
    print(f"Conversaciones encontradas: {len(conversations)}")
    
    for idx, conv in enumerate(conversations, 1):
        conv_id = conv.get("conversationId")
        start = conv.get("conversationStart", "")
        print(f"\n=== Conversacion #{idx} ID={conv_id} | Start={start} ===")
        
        for p in conv.get("participants", []):
            purpose = p.get("purpose", "")
            for s in p.get("sessions", []):
                for seg in s.get("segments", []):
                    seg_type = seg.get("segmentType", "")
                    w_code = seg.get("wrapUpCode")
                    w_name = seg.get("wrapUpName")
                    w_note = seg.get("wrapUpNote")
                    if w_code or w_name or w_note or seg_type == "wrapup":
                        print(f"  [{purpose}] segType={seg_type}")
                        print(f"    wrapUpCode={w_code}")
                        print(f"    wrapUpName={w_name}")
                        print(f"    wrapUpNote={w_note}")

        # Guardar el JSON completo de la interacción para inspeccion
        with open(f"tools/wrapup_conv_{idx}.json", "w", encoding="utf-8") as f:
            json.dump(conv, f, indent=2, ensure_ascii=False)
        print(f"  -> JSON completo guardado en tools/wrapup_conv_{idx}.json")
else:
    print(f"Error: {resp.text[:300]}")
