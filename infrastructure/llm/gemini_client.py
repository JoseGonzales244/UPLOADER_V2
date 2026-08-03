"""
Infrastructure LLM Module: Modern client wrapper for Google Gemini API using official google-genai SDK.
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
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-2.5-flash"):
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
            logger.warning("GEMINI_API_KEY environment variable not set in .env file.")

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
                    raise Exception("Respuesta vacía de la API de Gemini")

            except Exception as e:
                err_str = str(e)
                # Fallback de modelo si el nombre no existe
                if "404" in err_str or "not found" in err_str.lower():
                    if target_model != "gemini-1.5-flash":
                        logger.warning(f"Modelo {target_model} no disponible. Reintentando con gemini-1.5-flash...")
                        target_model = "gemini-1.5-flash"
                        continue
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    logger.warning(f"[Rate Limit 429] Esperando {delay}s antes del reintento (Intento {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e

        raise Exception(f"Error al generar contenido tras {max_retries} intentos debido a límites de cuota.")
