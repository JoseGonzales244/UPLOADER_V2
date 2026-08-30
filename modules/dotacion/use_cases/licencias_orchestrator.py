"""
Orquestador del proceso de Solicitud de Licencias Speech Analytics (Verint SA).
"""
import os
import time
from typing import Optional, Dict, Callable
from infrastructure.system.logging_config import setup_logging
from modules.dotacion.dotacion_config import DotacionConfig
from modules.dotacion.phases.fase_licencias_sa import run_licencias_sa

logger = setup_logging("modules.dotacion.licencias_orchestrator")


class LicenciasSaOrchestrator:

    def __init__(self, config: Optional[DotacionConfig] = None):
        self.config = config

    def run_licencias_pipeline(
        self,
        periodo: str = "AUTO",
        licencias_file: Optional[str] = None,
        consolidado_file: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """
        Ejecuta la sincronización mensual de licencias Verint SA.
        """
        def notify(msg: str, level: str = "info"):
            if level == "error":
                logger.error(msg)
            elif level == "warning":
                logger.warning(msg)
            else:
                logger.info(msg)
            if progress_callback:
                progress_callback(msg, level)

        start_time = time.time()
        cfg = self.config or DotacionConfig(target_period=periodo)
        
        target_p = str(periodo).strip().replace("-", "") if periodo and periodo != "AUTO" else f"{cfg.year}{cfg.month:02d}"
        lic_file = licencias_file or cfg.LICENCIAS_FILE
        cons_file = consolidado_file or cfg.CONSOLIDADO_FILE

        notify(f"🔑 Iniciando generación de Licencias Speech Analytics para {target_p}...")
        notify(f"📄 Archivo de Licencias: {lic_file}")
        notify(f"📄 Archivo Consolidado: {cons_file}")

        if not os.path.exists(lic_file):
            err = f"Archivo de Licencias no encontrado: {lic_file}"
            notify(f"❌ {err}", "error")
            raise FileNotFoundError(err)

        if not os.path.exists(cons_file):
            err = f"Archivo Consolidado ausentismo no encontrado: {cons_file}"
            notify(f"❌ {err}", "error")
            raise FileNotFoundError(err)

        notify("⚙️ Procesando exclusión de BackOffice y asignación de licencias...")
        run_licencias_sa(
            target_period=target_p,
            licencias_file=lic_file,
            consolidado_file=cons_file,
            cfg=cfg
        )

        elapsed = time.time() - start_time
        notify(f"🎉 Hoja de Licencias SA {target_p} generada con éxito en {elapsed:.2f} segundos!", "success")

        return {
            "status": "success",
            "periodo": target_p,
            "licencias_file": lic_file,
            "elapsed_seconds": round(elapsed, 2)
        }
