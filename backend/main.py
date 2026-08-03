"""
FastAPI Backend Server - UPLOADER V2
Proporciona endpoints REST y WebSockets en tiempo real para orquestación de Consumo, Calidad e Ingesta a Teradata.
"""
import os
import sys
import asyncio
import logging
import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# Asegurar path raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.logging_config import setup_logging
from core.orchestrator import run_orchestration_flow
from core.quality_process_orchestrator import run_quality_process_flow
from core.notifier import notify_desktop

logger = setup_logging("backend.main", log_prefix="fastapi")

app = FastAPI(
    title="Uploader V2 - API Server",
    description="Servidor Backend para orquestación de pipelines de Consumo y Calidad Interbank",
    version="2.0.0"
)

# Permitir CORS para desarrollo y consumo local
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

# Modelos Pydantic
class ConsumoRequest(BaseModel):
    periodo: str
    run_phase1: bool = True
    run_phase2: bool = True
    run_phase3: bool = True
    run_phase4: bool = True
    run_phase5: bool = True
    clear_consent: bool = False

class CalidadRequest(BaseModel):
    periodo: str
    run_fase1: bool = True
    run_fase2: bool = True
    run_fase3: bool = True
    run_fase4: bool = True
    run_fase5: bool = True

# Estado global de ejecución
process_state = {
    "running": False,
    "current_process": None,
    "progress": 0.0,
    "message": "Sistema listo.",
    "status": "idle"
}

def send_progress_update(message: str, type_str: str = "info", progress: Optional[float] = None):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if progress is not None:
        process_state["progress"] = progress
    process_state["message"] = message
    process_state["status"] = type_str

    payload = {
        "timestamp": timestamp,
        "message": message,
        "type": type_str,
        "progress": process_state["progress"]
    }
    
    # Transmitir por WebSockets al Event Loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
    except Exception:
        pass

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "Uploader V2 API",
        "timestamp": datetime.datetime.now().isoformat(),
        "process_state": process_state
    }

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Enviar estado actual al conectarse
        await websocket.send_json({
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "message": process_state["message"],
            "type": process_state["status"],
            "progress": process_state["progress"]
        })
        while True:
            # Mantener viva la conexión WebSocket
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def _run_consumo_task(req: ConsumoRequest):
    process_state["running"] = True
    process_state["current_process"] = "Consumo"
    process_state["progress"] = 0.0
    
    try:
        # Credenciales desde .env
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
            run_phase5=req.run_phase5
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

def _run_calidad_task(req: CalidadRequest):
    process_state["running"] = True
    process_state["current_process"] = "Calidad"
    process_state["progress"] = 0.0
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        insight_user = os.getenv("INSIGHT_USER", "")
        insight_password = os.getenv("INSIGHT_PASSWORD", "")
        td_user = os.getenv("TERADATA_USER", "")
        td_password = os.getenv("TERADATA_PASSWORD", "")

        run_quality_process_flow(
            insight_user=insight_user,
            insight_password=insight_password,
            td_user=td_user,
            td_password=td_password,
            period_str=req.periodo,
            progress_callback=send_progress_update,
            run_fase1=req.run_fase1,
            run_fase2=req.run_fase2,
            run_fase3=req.run_fase3,
            run_fase4=req.run_fase4,
            run_fase5=req.run_fase5
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
