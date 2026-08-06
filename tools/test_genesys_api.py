import requests
import json
import urllib3

# Deshabilitar advertencias de SSL debido al Proxy/Inspección SSL de la red corporativa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
resp = requests.post(URL, headers=headers, json=payload, verify=False)
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
        rec_resp = requests.get(rec_url, headers=headers, verify=False)
        print(f"List Recordings Status: {rec_resp.status_code}")
        
        if rec_resp.status_code == 200:
            recordings = rec_resp.json()
            print(f"[OK] Grabaciones obtenidas: {len(recordings)}")
            for r in recordings:
                rec_id = r.get("id")
                print(f"\nSolicitando URL de descarga MP3 para Recording ID: {rec_id}...")
                media_url = f"https://api.mypurecloud.com/api/v2/conversations/{conv_id}/recordings/{rec_id}?formatId=MP3&download=true"
                
                for attempt in range(1, 6):
                    media_resp = requests.get(media_url, headers=headers, verify=False)
                    print(f"Intento {attempt} Status: {media_resp.status_code}")
                    if media_resp.status_code == 200:
                        media_data = media_resp.json()
                        media_uris = media_data.get("mediaUris", {})
                        
                        # Extraer mediaUri de la clave 'S' o primer valor disponible
                        download_url = None
                        if "S" in media_uris:
                            download_url = media_uris["S"].get("mediaUri")
                        else:
                            for k, v in media_uris.items():
                                if isinstance(v, dict) and "mediaUri" in v:
                                    download_url = v.get("mediaUri")
                                    break

                        if download_url:
                            print(f"\n[ÉXITO] URL de descarga directa obtenida:")
                            print(download_url[:120] + "...")
                            
                            output_filename = f"TEST_AUDIO_{conv_id[:8]}.mp3"
                            print(f"\nDescargando archivo MP3 a '{output_filename}'...")
                            
                            audio_resp = requests.get(download_url, verify=False, stream=True)
                            if audio_resp.status_code == 200:
                                with open(output_filename, "wb") as f:
                                    for chunk in audio_resp.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                print(f"[¡COMPLETADO!] Archivo MP3 guardado exitosamente: {output_filename}")
                            else:
                                print(f"❌ Error descargando MP3: Status {audio_resp.status_code}")
                        else:
                            print("❌ No se encontró el campo 'mediaUri' dentro de 'mediaUris'.")
                        break
                    elif media_resp.status_code == 202:
                        import time
                        time.sleep(2)
                    else:
                        print(f"Error: {media_resp.text[:300]}")
                        break
else:
    print(f"Error en API: {resp.text[:500]}")
