"""
Core Interface: ILLMProvider
Abstracción pura para proveedores de LLM (Large Language Model) en APP_CALIDAD.
Garantiza el principio de Inversión de Dependencias (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional


class ILLMProvider(ABC):
    @abstractmethod
    def generate_content_with_retry(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        response_json: bool = True,
        max_retries: int = 6,
        initial_delay: float = 6.0
    ) -> str:
        """
        Genera contenido mediante el modelo LLM con políticas de reintento ante errores transitorios.
        """
        pass
