"""
Orquestador Principal del Pipeline de Dotación Mensual (Fases 1 a 4).
"""
import os
import shutil
import time
import openpyxl
from typing import Optional, Dict, Callable
from infrastructure.system.logging_config import setup_logging
from modules.dotacion.dotacion_config import DotacionConfig
from modules.dotacion.phases import fase1_limpieza, fase2_sincronizacion, fase3_distribucion, fase4_televentas
from modules.dotacion.utils.excel import clean_broken_defined_names

logger = setup_logging("modules.dotacion.dotacion_orchestrator")


class DotacionOrchestrator:

    def __init__(self, config: Optional[DotacionConfig] = None):
        self.config = config

    def run_pipeline(
        self,
        periodo: str = "AUTO",
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, any]:
        """
        Ejecuta el pipeline completo de Dotación Mensual.
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
        
        notify(f"🚀 Iniciando Pipeline de Dotación Mensual - Periodo {cfg.TARGET_PERIOD}...")

        # 1. Pre-flight checks de insumos
        notify("🔍 Validando disponibilidad de archivos insumos...")
        missing_files = []
        for name, path in [
            ("Plantilla Mes Anterior (INPUT_WORKBOOK)", cfg.INPUT_WORKBOOK),
            ("Consolidado Planilla Ausentismo", cfg.CONSOLIDADO_FILE),
            ("Dotación Ausencias Select", cfg.SELECT_DOTACION_FILE),
            ("Televentas Ejecutivos Mes Anterior", cfg.PREV_EXEC_FILE),
            ("Gestión de Vacaciones y Horarios", cfg.VACACIONES_FILE),
        ]:
            if not os.path.exists(path):
                missing_files.append(f"{name}: '{path}'")

        if missing_files:
            err_detail = "Faltan insumos obligatorios: " + "; ".join(missing_files)
            notify(f"❌ Error Pre-flight: {err_detail}", "error")
            raise FileNotFoundError(err_detail)

        # 2. Asegurar directorio de salida
        out_dir = os.path.dirname(cfg.OUTPUT_WORKBOOK)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # 3. Copiar plantilla al archivo de salida
        notify(f"📋 Copiando plantilla base hacia: {os.path.basename(cfg.OUTPUT_WORKBOOK)}")
        shutil.copy(cfg.INPUT_WORKBOOK, cfg.OUTPUT_WORKBOOK)

        # 4. Cargar Workbook en memoria
        notify("📂 Cargando libro de trabajo en memoria...")
        wb = openpyxl.load_workbook(cfg.OUTPUT_WORKBOOK, keep_links=True, data_only=False)

        # 5. Fase 1: Limpieza y Saneamiento
        notify("🧹 Ejecutando Fase 1: Saneamiento de plantilla y carga de ausentismos...")
        fase1_limpieza.run(wb, cfg)

        # 6. Fase 2: Sincronización de Roster y Antigüedad (R0 -> R3)
        notify("👥 Ejecutando Fase 2: Sincronización de Roster, Altas/Bajas y Antigüedad...")
        fase2_sincronizacion.run(wb, cfg)

        # 7. Fase 3: Distribución de Muestras entre 4 Analistas
        notify("⚖️ Ejecutando Fase 3: Distribución de grabaciones entre 4 analistas (Cálculo automático de vacaciones)...")
        fase3_distribucion.run(wb, cfg)

        # 8. Limpieza de rangos corruptos (#REF!)
        notify("🧼 Purgando rangos corruptos (#REF!)...")
        clean_broken_defined_names(wb)

        # 9. Guardar libro final en disco
        notify("💾 Guardando libro consolidado en disco...")
        wb.save(cfg.OUTPUT_WORKBOOK)

        # 10. Validación y recálculo nativo con Excel COM si está disponible
        try:
            import win32com.client
            abs_out = os.path.abspath(cfg.OUTPUT_WORKBOOK)
            excel_app = win32com.client.Dispatch("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            wb_com = excel_app.Workbooks.Open(abs_out)
            wb_com.Save()
            wb_com.Close()
            excel_app.Quit()
            notify("✅ Estructura Excel recalculada y validada nativamente con éxito.")
        except Exception as e_com:
            logger.debug(f"Excel COM no disponible o error menor: {e_com}")

        # 12. Fase 4: Televentas Ejecutivos
        notify("👔 Ejecutando Fase 4: Reconciliación de Televentas Ejecutivos...")
        fase4_televentas.run(wb, cfg)
        wb.close()

        elapsed = time.time() - start_time
        notify(f"🎉 Pipeline de Dotación completado exitosamente en {elapsed:.2f} segundos!", "success")

        return {
            "status": "success",
            "periodo": cfg.TARGET_PERIOD,
            "output_file": cfg.OUTPUT_WORKBOOK,
            "televentas_file": cfg.CURR_EXEC_FILE,
            "elapsed_seconds": round(elapsed, 2)
        }
