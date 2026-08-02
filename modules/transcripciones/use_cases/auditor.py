"""
Caso de Uso: Pipeline de Auditoría de Transcripciones con Gemini (Modos Single Agent y Multi Agent).
"""
import json
import logging
from typing import List, Dict, Any, Optional

from infrastructure.llm.gemini_client import GeminiClient
from modules.transcripciones.domain.ntd_rules import get_ntd_rules_prompt

logger = logging.getLogger("modules.transcripciones.use_cases.auditor")

class TranscriptAuditorUseCase:
    def __init__(self, llm_client: Optional[GeminiClient] = None):
        self.llm = llm_client or GeminiClient()

    def audit_transcript_single(
        self,
        conversation_text: str,
        conv_metadata: Optional[Dict[str, Any]] = None,
        sub_equipo: str = "Televentas",
        templates_text: str = ""
    ) -> Dict[str, Any]:
        """
        MODO SINGLE AGENT (1 sola llamada a la API de Gemini):
        Evalúa los 3 ejes (Gramática, Protocolo y Trato al cliente / NTD) en una única interacción.
        Ahorra 75% de llamadas y cuota de tokens por minuto (TPM/RPM).
        """
        metadata = conv_metadata or {}
        ntd_rules = get_ntd_rules_prompt()
        
        prompt = f"""
Eres el Auditor Principal de Calidad de Interbank. Tu rol es auditar la siguiente transcripción para evaluar la atención en 3 ejes principales: Gramática, Protocolo y Trato al cliente.

<eje_gramatica>
Busca cualquier error cometido por el ejecutivo:
1. Ortografía y gramática (ej. concordancia género/número, tildes omitidas).
2. Puntuación (apertura de signos '¿' o '¡', comas excesivas/ausentes).
3. Modismos, jerga o informalidades verbales no profesionales.
Asigna a estos hallazgos el eje "Gramática" y Gravedad "N1" (u "OK").
</eje_gramatica>

<eje_protocolo>
1. Compara las intervenciones del ejecutivo con la lista de plantillas y frases normativas autorizadas.
2. Identifica si usó, parafraseó u omitió frases estipuladas por el protocolo, o si usó mensajes personalizados improvisados.
Asigna el eje "Protocolo" y Gravedad "N1" o "N2" (u "OK").
</eje_protocolo>

<eje_trato_y_ntd>
1. Cordialidad y amabilidad: Debe ser amable, educado, empático y cooperativo en todo momento.
2. Faltas éticas / Not To Do: Detecta faltas de respeto, discusiones, inducir bajas, forzar productos o dar información falsa.
Asigna el eje "Trato" y Gravedad ("N1", "N2" o "N3").
</eje_trato_y_ntd>

Debes devolver un único objeto JSON con la estructura exacta:
{{
  "hallazgos": [
    {{
      "eje": "Gramática | Protocolo | Trato",
      "nivel_ntd": "N1 | N2 | N3 | OK",
      "mensaje_ejecutivo": "Texto exacto expresado por el ejecutivo o vacío en omisiones",
      "hallazgo": "Descripción clara, concisa y profesional de la observación detectada",
      "sugerencia": "Sugerencia práctica de corrección o frase oficial esperada"
    }}
  ],
  "plantillas_checklist": [
    {{
      "codigo_plantilla": "Nombre o sección de la plantilla/protocolo evaluado",
      "estado": "Usada | Parafraseada | No Usada",
      "comentario": "Explicación breve de cumplimiento"
    }}
  ]
}}

REGLAS DE NOT TO DO Y CONDUCTA:
{ntd_rules}

PLANTILLAS Y GUIONES AUTORIZADOS:
{templates_text if templates_text else "Guion estándar de bienvenida, oferta y cierre normativo."}

TRANSCRIPCIÓN:
{conversation_text}
"""
        try:
            logger.info("Iniciando auditoría en MODO SINGLE AGENT (1 sola solicitud LLM)...")
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.1, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Single Agent Audit: {e}")
            return {"hallazgos": [], "plantillas_checklist": []}

    def run_agent_grammar(self, conversation_text: str) -> Dict[str, Any]:
        """Agente 1 (Multi-agent): Ortografía, gramática e informalidades."""
        prompt = f"""
Eres un auditor de expresión verbal, ortografía y gramática para Interbank.
Analiza la siguiente transcripción, enfocándote en las intervenciones del ejecutivo.

Devuelve un objeto JSON:
{{
  "hallazgos": [
    {{
      "mensaje_ejecutivo": "Texto exacto",
      "hallazgo": "Descripción del error o informalismo",
      "sugerencia": "Texto corregido formal"
    }}
  ]
}}

TRANSCRIPCIÓN:
{conversation_text}
"""
        try:
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.0, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Agente 1 (Gramática): {e}")
            return {"hallazgos": []}

    def run_agent_protocol(self, conversation_text: str, sub_equipo: str = "Televentas", templates_text: str = "") -> Dict[str, Any]:
        """Agente 2 (Multi-agent): Adherencia a guiones y frases de protocolo."""
        prompt = f"""
Eres un auditor de protocolo normativo para Interbank.
Analiza la transcripción del ejecutivo.

Devuelve un objeto JSON:
{{
  "plantillas_evaluadas": [
    {{
      "codigo_plantilla": "Sección del protocolo",
      "estado": "Usada | Parafraseada | No Usada",
      "comentario": "Detalle"
    }}
  ],
  "hallazgos": [
    {{
      "mensaje_ejecutivo": "Texto expresado",
      "hallazgo": "Desviación del protocolo o mensaje personalizado no autorizado",
      "sugerencia": "Frase oficial que debió usar"
    }}
  ]
}}

PLANTILLAS Y GUIONES AUTORIZADOS:
{templates_text if templates_text else "Guion estándar de bienvenida, oferta y cierre."}

TRANSCRIPCIÓN:
{conversation_text}
"""
        try:
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.1, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Agente 2 (Protocolo): {e}")
            return {"plantillas_evaluadas": [], "hallazgos": []}

    def run_agent_tone_ntd(self, conversation_text: str) -> Dict[str, Any]:
        """Agente 3 (Multi-agent): Trato al cliente y reglas Not To Do."""
        ntd_rules = get_ntd_rules_prompt()
        prompt = f"""
Eres un auditor de trato al cliente y ética para Interbank.
Evalúa amabilidad, cordialidad y violaciones Not To Do.

Devuelve un objeto JSON:
{{
  "hallazgos": [
    {{
      "mensaje_ejecutivo": "Texto expresado",
      "codigo_ntd": "Código de la regla",
      "nivel_ntd": "N1 | N2 | N3",
      "hallazgo": "Descripción del hallazgo",
      "sugerencia": "Comportamiento esperado"
    }}
  ]
}}

REGLAS DE NOT TO DO:
{ntd_rules}

TRANSCRIPCIÓN:
{conversation_text}
"""
        try:
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.0, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Agente 3 (Trato/NTD): {e}")
            return {"hallazgos": []}

    def consolidate_findings(
        self,
        metadata: Dict[str, Any],
        grammar_data: Dict[str, Any],
        protocol_data: Dict[str, Any],
        tone_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agente 4 (Multi-agent): Consolidador principal."""
        input_data = {
            "metadata": metadata,
            "grammar_findings": grammar_data.get("hallazgos", []),
            "protocol_findings": protocol_data.get("hallazgos", []),
            "protocol_checklist": protocol_data.get("plantillas_evaluadas", []),
            "tone_ntd_findings": tone_data.get("hallazgos", [])
        }
        
        prompt = f"""
Consolida los hallazgos de los 3 evaluadores.
Devuelve JSON:
{{
  "hallazgos": [
    {{
      "eje": "Gramática | Protocolo | Trato",
      "nivel_ntd": "N1 | N2 | N3 | OK",
      "mensaje_ejecutivo": "Texto exacto",
      "hallazgo": "Descripción",
      "sugerencia": "Sugerencia"
    }}
  ],
  "plantillas_checklist": [
    {{
      "codigo_plantilla": "Plantilla",
      "estado": "Usada | Parafraseada | No Usada",
      "comentario": "Detalle"
    }}
  ]
}}

DATOS:
{json.dumps(input_data, indent=2, ensure_ascii=False)}
"""
        try:
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.1, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Agente Consolidador: {e}")
            return {"hallazgos": [], "plantillas_checklist": []}

    def audit_transcript(
        self,
        conversation_text: str,
        conv_metadata: Optional[Dict[str, Any]] = None,
        sub_equipo: str = "Televentas",
        templates_text: str = "",
        mode: str = "single"
    ) -> Dict[str, Any]:
        """
        Orquesta la auditoría en el modo seleccionado:
        - mode="single": 1 solicitud a Gemini (Ahorro máximo de tokens/peticiones).
        - mode="multi": 4 solicitudes especializadas a Gemini + Consolidador.
        """
        if mode.lower() == "single":
            return self.audit_transcript_single(
                conversation_text=conversation_text,
                conv_metadata=conv_metadata,
                sub_equipo=sub_equipo,
                templates_text=templates_text
            )
        else:
            logger.info("Iniciando auditoría en MODO MULTI AGENT (4 solicitudes LLM)...")
            metadata = conv_metadata or {}
            grammar_res = self.run_agent_grammar(conversation_text)
            protocol_res = self.run_agent_protocol(conversation_text, sub_equipo, templates_text)
            tone_res = self.run_agent_tone_ntd(conversation_text)
            return self.consolidate_findings(metadata, grammar_res, protocol_res, tone_res)
