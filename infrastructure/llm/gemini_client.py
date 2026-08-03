"""
Infrastructure LLM Module: Client wrapper for Google Gemini API with exponential backoff retries.
Supports both modern google.genai SDK and legacy google.generativeai SDK.
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Intentar primero el nuevo SDK oficial google.genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_NEW = True
except ImportError:
    HAS_GENAI_NEW = False

# Intentar como fallback el SDK legacy google.generativeai
try:
    import google.generativeai as genai_legacy
    HAS_GENAI_LEGACY = True
except ImportError:
    HAS_GENAI_LEGACY = False

logger = logging.getLogger("infrastructure.llm.gemini_client")

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-2.5-flash"):
        self.default_model = default_model
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip()
            os.environ["GOOGLE_API_KEY"] = self.api_key
            if HAS_GENAI_NEW:
                self.client_new = genai.Client(api_key=self.api_key)
            else:
                self.client_new = None
                
            if HAS_GENAI_LEGACY:
                genai_legacy.configure(api_key=self.api_key)
        else:
            self.client_new = None
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
        target_model = model_name or self.default_model
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                # 1. Probar el nuevo SDK oficial (google.genai)
                if HAS_GENAI_NEW and self.client_new:
                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json" if response_json else "text/plain"
                    )
                    res = self.client_new.models.generate_content(
                        model=target_model,
                        contents=prompt,
                        config=config
                    )
                    if res and res.text:
                        return res.text
                    else:
                        raise Exception("Empty response from Gemini API (google-genai)")

                # 2. Fallback al SDK legacy (google.generativeai)
                elif HAS_GENAI_LEGACY:
                    config_legacy = {"temperature": temperature}
                    if response_json:
                        config_legacy["response_mime_type"] = "application/json"
                    model_legacy = genai_legacy.GenerativeModel(target_model, generation_config=config_legacy)
                    res_legacy = model_legacy.generate_content(prompt)
                    if res_legacy and res_legacy.text:
                        return res_legacy.text
                    else:
                        raise Exception("Empty response from Gemini API (google-generativeai)")
                else:
                    raise RuntimeError("Ningún SDK de Gemini está instalado. Instala google-genai mediante 'pip install google-genai'")

            except Exception as e:
                err_str = str(e)
                # Si el modelo no existe o se sugiere fallback
                if "404" in err_str or "not found" in err_str.lower():
                    if target_model != "gemini-1.5-flash":
                        logger.warning(f"Modelo {target_model} no encontrado. Probando fallback a gemini-1.5-flash...")
                        target_model = "gemini-1.5-flash"
                        continue
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    logger.warning(f"[Rate Limit 429] Esperando {delay}s antes del reintento (Intento {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e

        raise Exception(f"Error al generar contenido tras {max_retries} intentos debido a límites de cuota de Gemini.")
