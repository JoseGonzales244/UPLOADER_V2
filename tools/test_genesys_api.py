import requests
import json

TOKEN = "Q380dsnrpdyzT8hEhpYbEXdyBCwamAjZwxQytuIMmbAnYJ1KneO4ZqYCsshD28XB4nqhuG0k7zpe46PmUJVjrg"
URL = "https://api.mypurecloud.com/api/v2/analytics/conversations/details/query"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "accept": "*/*"
}

payload = {
    "order": "desc",
    "orderBy": "conversationStart",
    "paging": {
        "pageSize": 10,
        "pageNumber": 1
    },
    "interval": "2026-07-01T05:00:00.000Z/2026-08-01T05:00:00.000Z",
    "segmentFilters": [
        {
            "type": "or",
            "predicates": [
                {"dimension": "direction", "value": "inbound"},
                {"dimension": "direction", "value": "outbound"}
            ]
        }
    ],
    "conversationFilters": [],
    "evaluationFilters": [],
    "surveyFilters": []
}

print("Enviando consulta a la API de Genesys Cloud...")
resp = requests.post(URL, headers=headers, json=payload)
print(f"Respuesta HTTP Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    conversations = data.get("conversations", [])
    print(f"[OK] Total conversaciones devueltas: {len(conversations)}")
    
    if conversations:
        conv = conversations[0]
        conv_id = conv.get("conversationId")
        print(f"\nConsultando grabaciones de la interacción: {conv_id}")
        rec_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings"
        rec_resp = requests.get(rec_url, headers=headers)
        print(f"List Recordings Status: {rec_resp.status_code}")
        
        if rec_resp.status_code == 200:
            recordings = rec_resp.json()
            print(f"[OK] Grabaciones obtenidas: {len(recordings)}")
            for r in recordings:
                rec_id = r.get("id")
                print(f"\nSolicitando URL de descarga MP3 para Recording ID: {rec_id}...")
                media_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?formatId=MP3&download=true"
                media_resp = requests.get(media_url, headers=headers)
                print(f"Media Download URL Status: {media_resp.status_code}")
                for attempt in range(1, 6):
                    media_resp = requests.get(media_url, headers=headers)
                    print(f"Intento {attempt} Status: {media_resp.status_code}")
                    if media_resp.status_code == 200:
                        media_data = media_resp.json()
                        media_uri = media_data.get("mediaUri")
                        print(f"\n[ÉXITO] URL directa de descarga del MP3 obtenida:\n{media_uri}")
                        break
                    elif media_resp.status_code == 202:
                        import time
                        time.sleep(2)
                    else:
                        print(f"Error: {media_resp.text[:300]}")
                        break
else:
    print(f"Error en API: {resp.text[:500]}")
