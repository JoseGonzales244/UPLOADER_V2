"""
Paquete de Interfaces Core para APP_CALIDAD
"""
from domain.interfaces.llm_provider import ILLMProvider
from domain.interfaces.transcript_extractor import ITranscriptExtractor
from domain.interfaces.report_presenter import IReportPresenter

__all__ = ["ILLMProvider", "ITranscriptExtractor", "IReportPresenter"]
