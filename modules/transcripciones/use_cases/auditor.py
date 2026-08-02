"""
Caso de Uso: Pipeline de Auditoría de Transcripciones para Canales Escritos con Gemini.
Evalúa estrictamente 3 ejes: Gramática, Trato con el cliente y Cumplimiento del protocolo.
"""
import json
import logging
from typing import List, Dict, Any, Optional

from infrastructure.llm.gemini_client import GeminiClient

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
        Evalúa estrictamente los 3 ejes: Gramática, Trato con el cliente y Cumplimiento del protocolo.
        Ahorra 75% de llamadas y cuota de tokens por minuto (TPM/RPM).
        """
        prompt = f"""
Eres el Auditor Principal de Calidad de Canales Escritos de Interbank. Tu rol es auditar la siguiente transcripción escrita para evaluar el desempeño del ejecutivo estrictamente en 3 ejes principales: Gramática, Trato con el cliente y Cumplimiento del protocolo.

<eje_gramatica>
Busca cualquier error en los mensajes del ejecutivo:
1. Ortografía y gramática (ej. tildes omitidas, errores de tipeo, concordancia de género/número).
2. Puntuación (ausencia de signos de apertura '¿' o '¡', uso excesivo o incorrecto de comas/puntos).
3. Modismos, jerga, informalidades o muletillas escritas no profesionales.
Asigna a estos hallazgos el eje "Gramática".
</eje_gramatica>

<eje_trato_cliente>
Evalúa el comportamiento hacia el cliente:
1. Cordialidad y amabilidad (saludos, despedidas, cortesía).
2. Empatía y tono profesional (disposición de ayuda, paciencia, respeto verbal).
3. Fluidez y claridad en las respuestas escritas.
Asigna a estos hallazgos el eje "Trato con el cliente".
</eje_trato_cliente>

<eje_protocolo>
1. Compara las intervenciones del ejecutivo con las plantillas y mensajes normativos autorizados.
2. Identifica si el ejecutivo usó correctamente las plantillas estipuladas, si las parafraseó, las omitió o si improvisó respuestas personales no autorizadas.
Asigna a estos hallazgos el eje "Cumplimiento del protocolo".
</eje_protocolo>

Debes devolver un único objeto JSON con la estructura exacta:
{{
  "hallazgos": [
    {{
      "eje": "Gramática | Trato con el cliente | Cumplimiento del protocolo",
      "mensaje_ejecutivo": "Texto exacto expresado por el ejecutivo en la transcripción",
      "hallazgo": "Descripción clara y profesional del error o la desviación observada",
      "sugerencia": "Sugerencia de corrección o texto/frase oficial recomendada"
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

PLANTILLAS Y GUIONES AUTORIZADOS:
{templates_text if templates_text else "Guion estándar de bienvenida, verificación, oferta de producto y cierre."}

TRANSCRIPCIÓN ESCRITA A AUDITAR:
{conversation_text}
"""
        try:
            logger.info("Iniciando auditoría en MODO SINGLE AGENT (1 llamada LLM)...")
            res_text = self.llm.generate_content_with_retry(prompt, temperature=0.1, response_json=True)
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Error en Single Agent Audit: {e}")
            return {"hallazgos": [], "plantillas_checklist": []}

    def run_agent_grammar(self, conversation_text: str) -> Dict[str, Any]:
        """Agente 1 (Multi-agent): Ortografía, gramática y expresión escrita."""
        prompt = f"""
Eres un auditor de ortografía, gramática y redacción para Interbank Canales Escritos.
Analiza la siguiente transcripción enfocándote en los mensajes del ejecutivo.

Devuelve un objeto JSON:
{{
  "hallazgos": [
    {{
      "eje": "Gramática",
      "mensaje_ejecutivo": "Texto exacto expresado por el ejecutivo",
      "hallazgo": "Descripción del error ortográfico, gramatical o informalismo",
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

    def run_agent_customer_treatment(self, conversation_text: str) -> Dict[str, Any]:
        """Agente 2 (Multi-agent): Trato al cliente, cordialidad y empatía."""
        prompt = f"""
Eres un auditor de empatía, cordialidad y trato al cliente para Interbank Canales Escritos.
Analiza la transcripción enfocándote en el respeto, amabilidad y empatía del ejecutivo.

Devuelve un objeto JSON:
{{
  "hallazgos": [
    {{
      "eje": "Trato con el cliente",
      "mensaje_ejecutivo": "Texto expresado por el ejecutivo",
      "hallazgo": "Descripción de la falta de cortesía, empatía o tono inapropiado",
      "sugerencia": "Comportamiento o respuesta empatica esperada"
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
            logger.error(f"Error en Agente 2 (Trato con el Cliente): {e}")
            return {"hallazgos": []}

    def run_agent_protocol(self, conversation_text: str, sub_equipo: str = "Televentas", templates_text: str = "") -> Dict[str, Any]:
        """Agente 3 (Multi-agent): Cumplimiento de plantillas y protocolo."""
        prompt = f"""
Eres un auditor de adherencia a plantillas y protocolo normativo para Interbank Canales Escritos.
Analiza si el ejecutivo usó las plantillas estipuladas, las omitió o usó mensajes improvisados.

Devuelve un objeto JSON:
{{
  "plantillas_evaluadas": [
    {{
      "codigo_plantilla": "Sección del protocolo",
      "estado": "Usada | Parafraseada | No Usada",
      "comentario": "Detalle de cumplimiento"
    }}
  ],
  "hallazgos": [
    {{
      "eje": "Cumplimiento del protocolo",
      "mensaje_ejecutivo": "Texto expresado",
      "hallazgo": "Desviación del protocolo o mensaje personalizado no autorizado",
      "sugerencia": "Frase/plantilla oficial que debió usar"
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
            logger.error(f"Error en Agente 3 (Protocolo): {e}")
            return {"plantillas_evaluadas": [], "hallazgos": []}

    def consolidate_findings(
        self,
        metadata: Dict[str, Any],
        grammar_data: Dict[str, Any],
        treatment_data: Dict[str, Any],
        protocol_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agente 4 (Multi-agent): Consolidador principal."""
        input_data = {
            "metadata": metadata,
            "grammar_findings": grammar_data.get("hallazgos", []),
            "treatment_findings": treatment_data.get("hallazgos", []),
            "protocol_findings": protocol_data.get("hallazgos", []),
            "protocol_checklist": protocol_data.get("plantillas_evaluadas", [])
        }
        
        prompt = f"""
Consolida los hallazgos de los 3 evaluadores en los 3 ejes: Gramática, Trato con el cliente y Cumplimiento del protocolo.
Devuelve JSON:
{{
  "hallazgos": [
    {{
      "eje": "Gramática | Trato con el cliente | Cumplimiento del protocolo",
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

DATOS A CONSOLIDAR:
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
        Orquesta la auditoría en los 3 ejes según el modo:
        - mode="single": 1 llamada LLM a Gemini.
        - mode="multi": 4 llamadas LLM especializadas.
        """
        if mode.lower() == "single":
            return self.audit_transcript_single(
                conversation_text=conversation_text,
                conv_metadata=conv_metadata,
                sub_equipo=sub_equipo,
                templates_text=templates_text
            )
        else:
            logger.info("Iniciando auditoría en MODO MULTI AGENT (4 llamadas LLM)...")
            metadata = conv_metadata or {}
            grammar_res = self.run_agent_grammar(conversation_text)
            treatment_res = self.run_agent_customer_treatment(conversation_text)
            protocol_res = self.run_agent_protocol(conversation_text, sub_equipo, templates_text)
            return self.consolidate_findings(metadata, grammar_res, treatment_res, protocol_res)
