import json
from pathlib import Path

template_path = Path(r"C:\Users\USER\.gemini\config\skills\arch-visualizer\assets\template.html")
json_path = Path(r"c:\Users\USER\Documents\Documentos Personales\INTERBANK\APP_CALIDAD\architecture.json")
out_path = Path(r"c:\Users\USER\Documents\Documentos Personales\INTERBANK\APP_CALIDAD\architecture.html")

template = template_path.read_text(encoding="utf-8")
arch_json = json_path.read_text(encoding="utf-8")

# Verify JSON validity
data = json.loads(arch_json)
print(f"Loaded architecture.json: {len(data['nodes'])} nodes, {len(data['edges'])} edges, {len(data['flows'])} flows.")

marker_start = '<script id="architecture-data" type="application/json">'
marker_end = '</script>'

start_idx = template.find(marker_start)
if start_idx == -1:
    raise ValueError("Start marker not found in template.html")

end_idx = template.find(marker_end, start_idx)
if end_idx == -1:
    raise ValueError("End marker not found in template.html")

new_html = template[:start_idx + len(marker_start)] + "\n" + arch_json + "\n  " + template[end_idx:]
out_path.write_text(new_html, encoding="utf-8")
print(f"Generated {out_path} ({len(new_html)} bytes)")
