"""
Core Interface: IReportPresenter
Abstracción pura para generadores/presentadores de reportes de auditoría y calidad.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class IReportPresenter(ABC):
    @abstractmethod
    def generate_report(
        self,
        audit_summary: List[Dict[str, Any]],
        all_hallazgos: List[Dict[str, Any]],
        output_dir: Optional[str] = None
    ) -> str:
        """
        Genera y exporta el reporte final en el formato específico del presentador (Excel, PDF, CSV).
        Devuelve la ruta absoluta del archivo generado.
        """
        pass
