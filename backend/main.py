"""
FastAPI Backend Server - UPLOADER V2
Proporciona endpoints REST y WebSockets en tiempo real para:
- Orquestación de Consumo (PBI Base Consumo)
- Orquestación de Calidad (PBI Evaluaciones Calidad)
- Solicitud y Descarga de Audios (Genesys & Outlook)
- Subida e Ingesta de Archivos (Excel/CSV/TXT a Teradata)
- Diagnóstico de Entorno y Plantillas
"""
import os
import sys
import json
import asyncio
import logging
import datetime
import traceback
import tempfile
import polars as pl
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

# Asegurar path raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.logging_config import setup_logging
from core.orchestrator import run_orchestration_flow
from core.quality_process_orchestrator import run_quality_process_flow
from core.readers import read_excel_file, read_csv_file, read_unicode_text_file
from core.cleaners import clean_dataframe, sanitize_identifier, suggest_sql_type
from core.database import load_credentials, connect_teradata, load_to_teradata
from core.health_check import run_preflight_health_check
from ui.components import load_templates

logger = setup_logging("backend.main", log_prefix="fastapi")

app = FastAPI(
    title="Uploader V2 - API Server",
    description="Servidor Backend unificado para la Plataforma Uploader V2 Interbank",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestor de conexiones WebSocket para Logs en vivo
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Global event loop reference for thread-safe WebSocket broadcasting
main_loop: Optional[asyncio.AbstractEventLoop] = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

# Estado global de ejecución
process_state = {
    "running": False,
    "current_process": None,
    "progress": 0.0,
    "current_phase": 0,
    "message": "Sistema listo.",
    "status": "idle"
}

def send_progress_update(message: str, type_str: str = "info", progress: Optional[float] = None, phase: Optional[int] = None):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if progress is not None:
        process_state["progress"] = progress
    if phase is not None:
        process_state["current_phase"] = phase
    process_state["message"] = message
    process_state["status"] = type_str

    payload = {
        "timestamp": timestamp,
        "message": message,
        "type": type_str,
        "progress": process_state["progress"],
        "phase": process_state["current_phase"],
        "running": process_state["running"],
        "current_process": process_state["current_process"]
    }
    
    global main_loop
    try:
        if main_loop is None:
            main_loop = asyncio.get_event_loop()
        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), main_loop)
    except Exception as e:
        print(f"Error broadcasting WebSocket message: {e}")

# Modelos Pydantic
class ConsumoRequest(BaseModel):
    periodo: str
    run_phase1: bool = True
    run_phase2: bool = True
    run_phase3: bool = True
    run_phase4: bool = True
    run_phase5: bool = True
    clear_consent: bool = False
    start_script: Optional[str] = None

class CalidadRequest(BaseModel):
    periodo: str
    run_fase1: bool = True
    run_fase2: bool = True
    run_fase3: bool = True
    run_fase4: bool = True
    run_fase5: bool = True
    start_script: Optional[str] = None

class AudioItem(BaseModel):
    reg_ev: str
    dni: str
    nombre_archivo: str
    prefijo: str = "AUDIO"

class AudioRequest(BaseModel):
    solicitudes: List[AudioItem]

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "Uploader V2 API",
        "timestamp": datetime.datetime.now().isoformat(),
        "process_state": process_state
    }

@app.get("/api/health-check")
def preflight_check():
    """Ejecuta diagnóstico de entorno (Outlook, Chrome CDP, Teradata)"""
    try:
        results = run_preflight_health_check()
        return {"status": "ok", "health": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/templates")
def get_templates():
    """Retorna las plantillas de mapeo configuradas"""
    templates = load_templates()
    return {"templates": templates}

@app.get("/api/credentials")
def get_default_credentials():
    """Retorna credenciales por defecto desde .env (ocultando passwords)"""
    creds = load_credentials()
    return {
        "teradata_user": creds.get("teradata_user", ""),
        "teradata_host": creds.get("teradata_host", "IBKTD"),
        "teradata_logmech": creds.get("teradata_logmech", "TD2")
    }

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "message": process_state["message"],
            "type": process_state["status"],
            "progress": process_state["progress"],
            "phase": process_state["current_phase"],
            "running": process_state["running"],
            "current_process": process_state["current_process"]
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- FLUSO CONSUMO ---
def _run_consumo_task(req: ConsumoRequest):
    process_state["running"] = True
    process_state["current_process"] = "PBI Base Consumo"
    process_state["progress"] = 0.0
    process_state["current_phase"] = 1
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        insight_user = os.getenv("INSIGHT_USER", "")
        insight_password = os.getenv("INSIGHT_PASSWORD", "")
        td_user = os.getenv("TERADATA_USER", "")
        td_password = os.getenv("TERADATA_PASSWORD", "")

        run_orchestration_flow(
            insight_user=insight_user,
            insight_password=insight_password,
            td_user=td_user,
            td_password=td_password,
            period_str=req.periodo,
            clear_consent=req.clear_consent,
            progress_callback=send_progress_update,
            run_phase1=req.run_phase1,
            run_phase2=req.run_phase2,
            run_phase3=req.run_phase3,
            run_phase4=req.run_phase4,
            run_phase5=req.run_phase5,
            start_from_script=req.start_script
        )
    except Exception as e:
        logger.error(f"Error en flujo de Consumo: {e}")
        send_progress_update(f"❌ Error en flujo de Consumo: {e}", "error")
    finally:
        process_state["running"] = False
        process_state["current_process"] = None

@app.post("/api/orchestrate/consumo")
def start_consumo(req: ConsumoRequest, background_tasks: BackgroundTasks):
    if process_state["running"]:
        raise HTTPException(status_code=400, detail=f"Ya hay un proceso en ejecución: {process_state['current_process']}")

    background_tasks.add_task(_run_consumo_task, req)
    return {"status": "started", "process": "Consumo", "periodo": req.periodo}

# --- FLUJO CALIDAD ---
def _run_calidad_task(req: CalidadRequest):
    process_state["running"] = True
    process_state["current_process"] = "PBI Evaluaciones Calidad"
    process_state["progress"] = 0.0
    process_state["current_phase"] = 1
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        insight_user = os.getenv("INSIGHT_USER", "")
        insight_password = os.getenv("INSIGHT_PASSWORD", "")
        verint_user = os.getenv("VERINT_USER", "")
        verint_password = os.getenv("VERINT_PASSWORD", "")
        td_user = os.getenv("TERADATA_USER", "")
        td_password = os.getenv("TERADATA_PASSWORD", "")

        run_quality_process_flow(
            insight_user=insight_user,
            insight_password=insight_password,
            verint_user=verint_user,
            verint_password=verint_password,
            td_user=td_user,
            td_password=td_password,
            period_str=req.periodo,
            progress_callback=send_progress_update,
            run_phase1=req.run_fase1,
            run_phase2=req.run_fase2,
            run_phase3=req.run_fase3,
            run_phase4=req.run_fase4,
            run_phase5=req.run_fase5,
            start_from_script=req.start_script
        )
    except Exception as e:
        logger.error(f"Error en flujo de Calidad: {e}")
        send_progress_update(f"❌ Error en flujo de Calidad: {e}", "error")
    finally:
        process_state["running"] = False
        process_state["current_process"] = None

@app.post("/api/orchestrate/calidad")
def start_calidad(req: CalidadRequest, background_tasks: BackgroundTasks):
    if process_state["running"]:
        raise HTTPException(status_code=400, detail=f"Ya hay un proceso en ejecución: {process_state['current_process']}")

    background_tasks.add_task(_run_calidad_task, req)
    return {"status": "started", "process": "Calidad", "periodo": req.periodo}

# --- GENESYS AUDIOS & OUTLOOK ---
@app.get("/api/audios/outlook-fetch")
def fetch_outlook_emails():
    """Consulta los últimos 3 correos de solicitud de audios en Outlook Desktop"""
    try:
        from genesys_bot.services.outlook_service import OutlookService
        svc = OutlookService()
        correos = svc.obtener_ultimos_correos(limit=3)
        return {"status": "ok", "correos": correos}
    except Exception as e:
        logger.error(f"Error al conectar con Outlook: {e}")
        return {"status": "error", "message": str(e), "correos": []}

def _run_audios_task(req: AudioRequest):
    process_state["running"] = True
    process_state["current_process"] = "Solicitud de Audios (Genesys)"
    process_state["progress"] = 0.0
    
    try:
        from genesys_bot.services.genesys_browser import GenesysBrowserAutomation
        from genesys_bot.models import SolicitudAudio
        
        solicitudes = [
            SolicitudAudio(reg_ev=item.reg_ev, dni=item.dni, nombre_archivo=item.nombre_archivo, prefijo=item.prefijo)
            for item in req.solicitudes
        ]
        
        send_progress_update(f"🎧 Iniciando descarga de {len(solicitudes)} audios en Genesys...", "info", progress=0.1)
        bot = GenesysBrowserAutomation()
        res = bot.procesar_solicitudes(solicitudes)
        send_progress_update("🎉 ¡Proceso de descarga de audios completado!", "success", progress=1.0)
    except Exception as e:
        logger.error(f"Error en descarga de audios: {e}")
        send_progress_update(f"❌ Error en proceso de audios: {e}", "error")
    finally:
        process_state["running"] = False
        process_state["current_process"] = None

@app.post("/api/audios/download")
def start_audios_download(req: AudioRequest, background_tasks: BackgroundTasks):
    if process_state["running"]:
        raise HTTPException(status_code=400, detail=f"Ya hay un proceso en ejecución: {process_state['current_process']}")

    background_tasks.add_task(_run_audios_task, req)
    return {"status": "started", "solicitudes_count": len(req.solicitudes)}

# --- INGESTA A TERADATA ---
@app.post("/api/upload/preview")
async def preview_file(
    file: UploadFile = File(...),
    file_type: str = Form("Excel"),
    selected_template: str = Form("Ninguno")
):
    try:
        templates = load_templates()
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        if file_type == "Excel":
            df = read_excel_file(tmp_path, selected_template=selected_template, templates=templates)
        elif file_type == "CSV":
            df = read_csv_file(tmp_path)
        else:
            df = read_unicode_text_file(tmp_path)

        os.remove(tmp_path)

        # Sugerir tipos de datos
        columns_info = []
        template_config = templates.get(selected_template, {})
        
        for col in df.columns:
            suggested = suggest_sql_type(df[col])
            columns_info.append({
                "original_name": col,
                "new_name": sanitize_identifier(col),
                "datatype": suggested,
                "selected": True,
                "convert_nulls": False
            })

        preview_rows = df.head(10).to_dicts()

        return {
            "status": "ok",
            "filename": file.filename,
            "total_rows": len(df),
            "total_cols": len(df.columns),
            "columns": columns_info,
            "preview": preview_rows
        }
    except Exception as e:
        logger.error(f"Error procesando archivo para vista previa: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})

# Servir Frontend
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return "<h2>Uploader V2 Backend activo. Frontend no encontrado.</h2>"
