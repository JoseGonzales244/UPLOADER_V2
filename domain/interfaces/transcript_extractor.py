"""
Core Interface: ITranscriptExtractor
Abstracción pura para extractores de transcripciones (docx, Genesys, Verint, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ITranscriptExtractor(ABC):
    @abstractmethod
    def extract_single_docx(self, docx_path: str) -> Dict[str, Any]:
        """Extrae y estructura los datos de una transcripción específica."""
        pass

    @abstractmethod
    def get_all_transcripts(self) -> List[Dict[str, Any]]:
        """Extrae todas las transcripciones disponibles en la ruta origen."""
        pass
