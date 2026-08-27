"""
Contratos abstractos para repositorios y operaciones de Base de Datos (Teradata y Speech SQL Server).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Callable


class ITeradataRepository(ABC):
    """Contrato abstracto para interacción con Teradata."""

    @abstractmethod
    def extract_interactions(
        self,
        plantilla: str = "Exp. Compra - TC",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Extrae interacciones de calidad desde la tabla correspondiente en Teradata."""
        pass

    @abstractmethod
    def execute_script(
        self,
        sql_text: str,
        params: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> bool:
        """Ejecuta una serie de sentencias SQL en Teradata con soporte para callbacks."""
        pass


class ISpeechDbRepository(ABC):
    """Contrato abstracto para persistencia en SQL Server DB_SPEECH."""

    @abstractmethod
    def ensure_speech_table(self, table_name: str = "TRANSCRIPCION") -> None:
        """Verifica o crea la tabla destino en SQL Server si no existe."""
        pass

    @abstractmethod
    def upsert_transcripts(
        self,
        records: List[Tuple[str, str, str, str, str, str, str]],
        batch_size: int = 200
    ) -> int:
        """
        Inserta o actualiza un lote de transcripciones consolidadas.
        Retorna la cantidad de registros sincronizados exitosamente.
        """
        pass
