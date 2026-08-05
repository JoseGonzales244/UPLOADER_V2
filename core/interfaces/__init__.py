"""
Paquete de Interfaces Core para APP_CALIDAD
"""
from core.interfaces.llm_provider import ILLMProvider
from core.interfaces.transcript_extractor import ITranscriptExtractor
from core.interfaces.report_presenter import IReportPresenter

__all__ = ["ILLMProvider", "ITranscriptExtractor", "IReportPresenter"]
