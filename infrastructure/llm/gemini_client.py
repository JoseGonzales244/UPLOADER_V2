"""
Infrastructure LLM Module: Client wrapper for Google Gemini API with exponential backoff retries.
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger("infrastructure.llm.gemini_client")

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-3.1-flash-lite"):
        self.default_model = default_model
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            self.api_key = self.api_key.strip()
            if genai:
                genai.configure(api_key=self.api_key)
                os.environ["GOOGLE_API_KEY"] = self.api_key
        else:
            logger.warning("GEMINI_API_KEY environment variable not set in .env file.")

    def get_model(self, model_name: Optional[str] = None, temperature: float = 0.1, response_json: bool = True):
        if not genai:
            raise RuntimeError("google-generativeai package is not installed. Install it via pip install google-generativeai")
        target_model = model_name or self.default_model
        config: Dict[str, Any] = {"temperature": temperature}
        if response_json:
            config["response_mime_type"] = "application/json"
        return genai.GenerativeModel(target_model, generation_config=config)

    def generate_content_with_retry(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        response_json: bool = True,
        max_retries: int = 6,
        initial_delay: float = 6.0
    ):
        model = self.get_model(model_name=model_name, temperature=temperature, response_json=response_json)
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
                else:
                    raise Exception("Empty response from Gemini API")
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    logger.warning(f"[Rate Limit 429] Waiting {delay}s before retry (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
        raise Exception(f"Failed to generate content after {max_retries} attempts due to rate limiting.")
