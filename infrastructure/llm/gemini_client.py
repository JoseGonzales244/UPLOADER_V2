"""
Infrastructure LLM Module: Client wrapper for Google Gemini API using official google-genai SDK.
Usa estrictamente gemini-3.1-flash-lite sin ningún fallback silencioso.
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger("infrastructure.llm.gemini_client")

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-3.1-flash-lite"):
        self.default_model = default_model
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip()
            os.environ["GOOGLE_API_KEY"] = self.api_key
            if genai:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = None
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY no encontrada en las variables de entorno.")

    def generate_content_with_retry(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        response_json: bool = True,
        max_retries: int = 6,
        initial_delay: float = 6.0
    ) -> str:
        if not genai or not self.client:
            raise RuntimeError("La librería 'google-genai' no está instalada. Instálala vía: pip install google-genai")

        target_model = model_name or self.default_model
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json" if response_json else "text/plain"
                )
                res = self.client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config
                )
                if res and res.text:
                    return res.text
                else:
                    raise RuntimeError(f"Respuesta vacía recibida desde la API de Gemini para el modelo {target_model}")

            except Exception as e:
                err_str = str(e)
                # Reintento únicamente si es Rate Limit 429 / Cuota superada
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    logger.warning(f"[Rate Limit 429] Reintentando en {delay}s (Intento {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    # CERO FALLBACKS: Elevar la excepción inmediatamente si el modelo o la llamada falla
                    logger.error(f"Error en Gemini API ({target_model}): {e}")
                    raise e

        raise RuntimeError(f"Error en Gemini API ({target_model}): Superado el máximo de {max_retries} reintentos por 429 Rate Limit.")
