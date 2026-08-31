"""
Presenter Layer: TranscriptExcelPresenter
Exporta los reportes de auditoría de transcripciones en formato Excel gerencial (2 Pestañas).
Implementa IReportPresenter.
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from domain.interfaces.report_presenter import IReportPresenter

logger = logging.getLogger("modules.transcripciones.presenters.excel_presenter")


class TranscriptExcelPresenter(IReportPresenter):
    def __init__(self, default_output_dir: str = os.path.join("data", "reports")):
        self.default_output_dir = default_output_dir

    def generate_report(
        self,
        audit_summary: List[Dict[str, Any]],
        all_hallazgos: List[Dict[str, Any]],
        output_dir: Optional[str] = None
    ) -> str:
        """
        Genera el reporte de auditoría gerencial con 2 pestañas:
          1. Resumen_Evaluaciones
          2. Detalle_Hallazgos
        Devuelve la ruta absoluta del archivo Excel generado.
        """
        target_dir = output_dir or os.path.join(os.getcwd(), self.default_output_dir)
        os.makedirs(target_dir, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"Reporte_Auditoria_WhatsApp_{timestamp_str}.xlsx"
        excel_path = os.path.join(target_dir, excel_filename)

        df_summary = pd.DataFrame(audit_summary)
        df_hallazgos = pd.DataFrame(all_hallazgos)

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="Resumen_Evaluaciones", index=False)
            if not df_hallazgos.empty:
                df_hallazgos.to_excel(writer, sheet_name="Detalle_Hallazgos", index=False)
            else:
                pd.DataFrame(columns=[
                    "ID Conversación", "Ejecutivo", "Sub-equipo", "Eje", "Gravedad",
                    "Mensaje del Ejecutivo", "Hallazgo/Error Detectado", "Sugerencia de Corrección"
                ]).to_excel(writer, sheet_name="Detalle_Hallazgos", index=False)

        logger.info(f"Reporte Excel Gerencial exportado exitosamente en: {excel_path}")
        return excel_path
