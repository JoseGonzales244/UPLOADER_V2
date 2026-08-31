"""
Caso de Uso: Pipeline de Auditoría de Transcripciones de WhatsApp con Gemini 3.1 Flash Lite.
Evalúa los mensajes del ejecutivo en 3 ejes con clasificación directa de gravedad por eje:
  - Gramática -> Leve
  - Cumplimiento del protocolo -> Medio
  - Trato con el cliente -> Grave
Prompt 100% universal con Regla General de DNI Reciente Previo (si el cliente ya dio su DNI antes del asesor, no se sanciona).
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz

from domain.interfaces.llm_provider import ILLMProvider
from infrastructure.llm.gemini_client import GeminiClient

logger = logging.getLogger("modules.transcripciones.use_cases.auditor")


SEVERITY_BY_AXIS = {
    "Gramática": "Leve",
    "Cumplimiento del protocolo": "Medio",
    "Trato con el cliente": "Grave"
}


# FEW-SHOT PURAMENTE ESTRUCTURAL Y 100% GENÉRICO
FEW_SHOT_EXAMPLE = """
EJEMPLO DE REFERENCIA ESTRUCTURAL (FEW-SHOT):
Entrada:
<raw_transcript>
Cliente (Cliente Ejemplo) [20 de julio de 2026 9:41:08]: Hola
Ejecutivo Evaluado [EJECUTIVO EJEMPLO] [20 de julio de 2026 9:43:43]: Hola, te saluda el asesor de atención. ¿En qué puedo ayudarte?
Cliente (Cliente Ejemplo) [20 de julio de 2026 9:44:16]: Información sobre el producto
Ejecutivo Evaluado [EJECUTIVO EJEMPLO] [20 de julio de 2026 9:47:05]: Actualmente estas son las condiciones de la campaña vigente...
</raw_transcript>

REGLA DE SALIDA: Analizar la transcripción delimitada y generar el reporte JSON con citas textuales exactas del ejecutivo.
"""


def clean_placeholders(text: str) -> str:
    """Limpia variables y placeholders de plantillas de Genesys/Verint para comparación de texto."""
    if not text:
        return ""
    cleaned = re.sub(r"\[\[.*?\]\]|X{2,}|<.*?>|\{.*?\}", "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def check_recent_dni_before_advisor(conversation_text: str, lookback_lines: int = 15) -> bool:
    """
    Verifica si el cliente entregó un DNI (8 dígitos) en los mensajes previos inmediatos
    antes de la conexión del asesor evaluado.
    """
    lines = [l.strip() for l in conversation_text.splitlines() if l.strip()]
    if not lines:
        return False

    first_exec_idx = len(lines)
    for idx, line in enumerate(lines):
        if "Ejecutivo Evaluado" in line or ("Interno" in line and not "Bot" in line and not "Flujo" in line):
            first_exec_idx = idx
            break

    pre_advisor_start = max(0, first_exec_idx - lookback_lines)
    pre_advisor_lines = lines[pre_advisor_start:first_exec_idx]
    pre_advisor_text = "\n".join(pre_advisor_lines).lower()

    dni_match = re.search(r"\b\d{8}\b", pre_advisor_text)
    return bool(dni_match)


def validate_and_filter_findings(
    conversation_text: str,
    hallazgos: List[Dict[str, Any]],
    min_similarity: float = 40.0
) -> List[Dict[str, Any]]:
    """
    Filtro post-procesamiento determinista y general en Python:
      - Gramática -> Leve
      - Cumplimiento del protocolo -> Medio
      - Trato con el cliente -> Grave
    """
    filtered = []
    text_lower = conversation_text.lower()

    has_recent_dni = check_recent_dni_before_advisor(conversation_text, lookback_lines=15)

    sale_acceptance_keywords = [
        "acepto", "sí quiero", "si quiero", "de acuerdo", "procede", "está bien", "esta bien",
        "conforme", "llámame para contratar", "quiero el préstamo", "quiero el prestamo",
        "quiero la tarjeta", "desembolsa", "haz la llamada"
    ]
    has_explicit_sale_acceptance = any(k in text_lower for k in sale_acceptance_keywords)

    for h in hallazgos:
        eje = (h.get("eje") or "").strip()
        cita = (h.get("mensaje_ejecutivo") or "").strip()
        sugerencia = (h.get("sugerencia") or "").strip()
        obs = (h.get("hallazgo") or "").strip().lower()
        trigger_cliente = (h.get("mensaje_desencadenante_cliente") or "").strip().lower()

        # Asignación forzosa y directa de gravedad por eje
        if "gram" in eje.lower():
            h["eje"] = "Gramática"
            h["gravedad"] = "Leve"
        elif "proto" in eje.lower():
            h["eje"] = "Cumplimiento del protocolo"
            h["gravedad"] = "Medio"
        elif "trato" in eje.lower():
            h["eje"] = "Trato con el cliente"
            h["gravedad"] = "Grave"

        # FILTRO DE DNI RECIENTE EN LA COLA PREVIA AL ASESOR:
        if has_recent_dni and h["eje"] == "Cumplimiento del protocolo":
            if any(k in obs for k in ["dni", "documento", "identidad", "identificación", "identificacion"]):
                logger.info("ℹ️ [Falso positivo de DNI filtrado] Omisión de solicitud de DNI descartada porque el cliente entregó su DNI inmediatamente antes de la conexión del asesor.")
                continue

        # FILTRO DE PLANTILLAS DE CIERRE DE VENTA (TLV_Cierre_de_Venta_*):
        if "cierre" in obs or "cierre_de_venta" in obs or "cierre" in sugerencia.lower():
            if not has_explicit_sale_acceptance:
                logger.info("ℹ️ [Falso positivo de protocolo filtrado] 'TLV_Cierre_de_Venta' descartado porque el chat es informativo y el cliente no aceptó cerrar la venta.")
                continue

        # TOLERANCIA DE PLANTILLAS GENERAL (PROGRAMÁTICA EN PYTHON)
        if h["eje"] == "Cumplimiento del protocolo" and cita and sugerencia and len(cita) > 12:
            sug_clean = clean_placeholders(sugerencia)
            cita_clean = clean_placeholders(cita)
            
            token_set_sim = fuzz.token_set_ratio(cita_clean.lower(), sug_clean.lower())
            partial_sim = fuzz.partial_ratio(cita_clean.lower(), sug_clean.lower())
            simple_ratio = fuzz.ratio(cita_clean.lower(), sug_clean.lower())
            
            max_sim = max(token_set_sim, partial_sim, simple_ratio)
            
            if max_sim >= 75:
                logger.info(f"ℹ️ [Falso positivo de protocolo filtrado] El mensaje del ejecutivo coincide en {max_sim}% (sin placeholders) con la plantilla oficial.")
                continue

        # Filtrar explicaciones ficticias de falta de data
        if "no se puede evaluar" in obs or "no existen mensajes" in obs or "imposibilitando la evaluaci" in obs:
            continue

        # FILTRO DE PLANTILLAS CONDICIONALES DE SEGURIDAD:
        if "dudas_por_seguridad" in obs or ("seguridad" in obs and "omisión" in obs):
            sec_keywords = ["segur", "estaf", "fraude", "confia", "peligro", "riesgo", "clon", "clave", "tarjeta", "robo"]
            if not any(k in text_lower for k in sec_keywords) and (trigger_cliente in ("n/a", "none", "", "sin desencadenante")):
                logger.info("ℹ️ [Falso positivo bloqueado] 'TLV_Dudas_por_seguridad' descartado porque el cliente no manifestó dudas de seguridad.")
                continue

        # Si es una omisión explícita de plantilla
        if not cita or cita.lower() in ("n/a", "none", "no aplica", "omisión", "omision", "sin cita", "null") or len(cita) < 3:
            filtered.append(h)
            continue

        cita_lower = cita.lower()

        # Búsqueda exacta rápida o fuzzy matching
        if cita_lower in text_lower or len(cita_lower) < 8:
            filtered.append(h)
            continue

        score = fuzz.partial_ratio(cita_lower, text_lower)
        if score >= min_similarity:
            filtered.append(h)
        else:
            filtered.append(h)

    return filtered


class TranscriptAuditorUseCase:
    def __init__(self, llm_client: Optional[ILLMProvider] = None):
        self.llm: ILLMProvider = llm_client or GeminiClient(default_model="gemini-3.1-flash-lite")

    def audit_transcript_single(
        self,
        conversation_text: str,
        conv_metadata: Optional[Dict[str, Any]] = None,
        sub_equipo: str = "Televentas",
        templates_text: str = ""
    ) -> Dict[str, Any]:
        """
        Evalúa los mensajes del ejecutivo asignando gravedad directa por eje.
        Prompt 100% universal con regla de contexto para DNI entregado previamente en el bot.
        """
        prompt = f"""
Eres el Auditor Principal de Calidad de Canales Escritos (WhatsApp Televentas) de Interbank.
Tu misión es auditar METICULOSAMENTE cada oración enviada por el Ejecutivo Evaluado.

REGLAS GENERALES DE GRAVEDAD POR EJE:
- Eje 'Gramática' -> Gravedad 'Leve' (Cualquier error de ortografía, tildación, signos de puntuación ¿/¡, mayúsculas o tipeos en los mensajes del ejecutivo).
- Eje 'Cumplimiento del protocolo' -> Gravedad 'Medio' (Omisión o distorsión de plantillas oficiales obligatorias o condicionales aplicables).
- Eje 'Trato con el cliente' -> Gravedad 'Grave' (Lenguaje informal, trato frío, falta de amabilidad, empatía o frases confusas/deformadas dirigidas al cliente).

REGLA DE CONTEXTO DE DNI RECIENTE EN LA COLA DE ATENCIÓN:
- Si el cliente entregó su número de DNI (8 dígitos) en el tramo inmediatamente previo a la conexión del asesor evaluado (en las respuestas al Bot/Flujo ACD antes del saludo), NO SE DEBE REPORTAR como omisión la falta de solicitud de DNI por parte del ejecutivo.
- `TLV_Cierre_de_Venta_*`: SOLO se exige si el cliente aceptó expresamente la venta en el chat. En chats informativos está prohibido reportarla como omitida.

REGLAS STRICTAS DE NO MODIFICACIÓN Y EXTRACCIÓN:
1. Analiza la transcripción exactamente como aparece entre los delimitadores <raw_transcript> y </raw_transcript>.
2. Queda estrictamente prohibido resumir, sintetizar, parafrasear o eliminar marcas de tiempo, nombres de roles o mensajes.
3. Cita el mensaje del ejecutivo EXACTAMENTE palabra por palabra en 'mensaje_ejecutivo'.

{FEW_SHOT_EXAMPLE}

INSTRUCCIONES GENERALES DE AUDITORÍA:
1. GRAMÁTICA (Gravedad: Leve):
   - Revisa minuciosamente cada palabra enviada por el ejecutivo. Si existen faltas ortográficas, tildes omitidas o errores de tipeo, repórtalo en el eje 'Gramática'.
   - Revisa puntuación y signos de apertura ¿/¡. Si se omiten al inicio de preguntas o exclamaciones, repórtalo.
   - Revisa mayúsculas iniciales en oraciones y nombres propios.

2. TRATO CON EL CLIENTE (Gravedad: Grave):
   - Audita tono de voz, amabilidad, trato profesional y claridad de redacción.
   - Reporta cualquier frase confusa, inconexa o deformada dirigida al cliente, así como lenguaje informal o trato frío.

3. CUMPLIMIENTO DEL PROTOCOLO (Gravedad: Medio):
   - Audita el cumplimiento de las plantillas oficiales autorizadas.
   - No exigir DNI si el cliente ya lo entregó en el flujo previo al ejecutivo.

FORMATO DE SALIDA (ESTRICTO JSON):
{{
  "razonamiento_previo": "Análisis exhaustivo paso a paso...",
  "hallazgos": [
    {{
      "eje": "Gramática | Trato con el cliente | Cumplimiento del protocolo",
      "gravedad": "Leve | Medio | Grave",
      "mensaje_ejecutivo": "Cita textual exacta emitida por el ejecutivo (o 'N/A' si es omisión)",
      "mensaje_desencadenante_cliente": "Cita del cliente que exigía la plantilla (o 'N/A' si no aplica)",
      "hallazgo": "Descripción clara del error o falta detectada",
      "sugerencia": "Texto oficial corregido"
    }}
  ]
}}

PLANTILLAS OFICIALES WHATSAPP AUTORIZADAS:
{templates_text if templates_text else "Plantilla oficial de Saludo, Indagación, Validación LPDP, Oferta de Producto y Despedida."}

<raw_transcript>
{conversation_text}
</raw_transcript>
"""
        logger.info("Ejecutando auditoría detallada de calidad (Prompt Universal Limpio)...")
        res_text = self.llm.generate_content_with_retry(prompt, temperature=0.0, top_p=1.0, response_json=True)
        result = json.loads(res_text)
        
        raw_hallazgos = result.get("hallazgos", [])
        valid_hallazgos = validate_and_filter_findings(conversation_text, raw_hallazgos)
        result["hallazgos"] = valid_hallazgos
        
        return result

    def audit_transcript_multi(
        self,
        conversation_text: str,
        conv_metadata: Optional[Dict[str, Any]] = None,
        sub_equipo: str = "Televentas",
        templates_text: str = ""
    ) -> Dict[str, Any]:
        """
        ARQUITECTURA DE 4 AGENTES DE IA (Prompt Universal Limpio).
        """
        logger.info("🤖 [Agente Orquestador] Desplegando 3 Agentes Especializados (Prompt Universal)...")

        # ----------------------------------------------------
        # AGENTE 1: Especialista en Gramática y Ortografía
        # ----------------------------------------------------
        prompt_agente_1 = f"""
Eres el AGENTE ESPECIALISTA EN GRAMÁTICA Y ORTOGRAFÍA de Interbank.
Tu ÚNICO OBJETIVO es auditar la Ortografía, Puntuación, Tildación y Tipeos.
Gravedad: 'Leve'.

REGLAS STRICTAS DE NO MODIFICACIÓN:
1. Analiza la transcripción en <raw_transcript> y </raw_transcript>.
2. Queda estrictamente prohibido resumir o alterar citas.

{FEW_SHOT_EXAMPLE}

FORMATO JSON:
{{
  "hallazgos": [
    {{
      "eje": "Gramática",
      "gravedad": "Leve",
      "mensaje_ejecutivo": "Cita textual exacta del ejecutivo",
      "mensaje_desencadenante_cliente": "N/A",
      "hallazgo": "Descripción del error ortográfico o de tipeo",
      "sugerencia": "Texto exacto corregido"
    }}
  ]
}}

<raw_transcript>
{conversation_text}
</raw_transcript>
"""

        # ----------------------------------------------------
        # AGENTE 2: Especialista en Trato con el Cliente
        # ----------------------------------------------------
        prompt_agente_2 = f"""
Eres el AGENTE ESPECIALISTA EN TRATO Y EXPERIENCIA DEL CLIENTE de Interbank.
Tu ÚNICO OBJETIVO es auditar Tono, Cordialidad, Empatía y Claridad de Redacción al dirigirse al cliente.
Gravedad: 'Grave'.

REGLAS STRICTAS DE NO MODIFICACIÓN:
1. Analiza la transcripción en <raw_transcript> y </raw_transcript>.
2. Queda estrictamente prohibido resumir o alterar citas.

{FEW_SHOT_EXAMPLE}

FORMATO JSON:
{{
  "hallazgos": [
    {{
      "eje": "Trato con el cliente",
      "gravedad": "Grave",
      "mensaje_ejecutivo": "Cita textual exacta del ejecutivo",
      "mensaje_desencadenante_cliente": "N/A",
      "hallazgo": "Descripción de la falla de trato, frialdad o redacción confusa hacia el cliente",
      "sugerencia": "Propuesta de redacción profesional"
    }}
  ]
}}

<raw_transcript>
{conversation_text}
</raw_transcript>
"""

        # ----------------------------------------------------
        # AGENTE 3: Especialista en Protocolo y Plantillas
        # ----------------------------------------------------
        prompt_agente_3 = f"""
Eres el AGENTE ESPECIALISTA EN PROTOCOLO Y CUMPLIMIENTO NORMATIVO de Interbank.
Tu ÚNICO OBJETIVO es auditar las PLANTILLAS OFICIALES.
Gravedad: 'Medio'.

REGLA DE DNI PREVIO: Si el cliente ya entregó su DNI en el flujo previo o al Bot antes de la llegada del ejecutivo, NO reportar omisión de DNI.

PLANTILLAS OFICIALES:
{templates_text if templates_text else "Guion oficial de Saludo, Validación LPDP y Despedida."}

REGLAS STRICTAS DE NO MODIFICACIÓN:
1. Analiza la transcripción en <raw_transcript> y </raw_transcript>.
2. Queda estrictamente prohibido resumir o alterar citas.

{FEW_SHOT_EXAMPLE}

FORMATO JSON:
{{
  "hallazgos": [
    {{
      "eje": "Cumplimiento del protocolo",
      "gravedad": "Medio",
      "mensaje_ejecutivo": "Cita textual del ejecutivo o 'N/A' si es omisión",
      "mensaje_desencadenante_cliente": "Cita del cliente que exigía la plantilla (o 'N/A' si no aplica)",
      "hallazgo": "Descripción de la plantilla omitida",
      "sugerencia": "Plantilla oficial autorizada"
    }}
  ]
}}

<raw_transcript>
{conversation_text}
</raw_transcript>
"""

        logger.info("   • Agente 1 (Gramática -> Leve)...")
        res1_text = self.llm.generate_content_with_retry(prompt_agente_1, temperature=0.0, top_p=1.0, response_json=True)
        
        logger.info("   • Agente 2 (Trato -> Grave)...")
        res2_text = self.llm.generate_content_with_retry(prompt_agente_2, temperature=0.0, top_p=1.0, response_json=True)
        
        logger.info("   • Agente 3 (Protocolo -> Medio)...")
        res3_text = self.llm.generate_content_with_retry(prompt_agente_3, temperature=0.0, top_p=1.0, response_json=True)

        try:
            h1 = json.loads(res1_text).get("hallazgos", [])
        except Exception as e:
            logger.warning(f"Error parseando respuesta JSON del Agente 1 (Gramática): {e} | Raw: {res1_text[:100]}")
            h1 = []

        try:
            h2 = json.loads(res2_text).get("hallazgos", [])
        except Exception as e:
            logger.warning(f"Error parseando respuesta JSON del Agente 2 (Trato): {e} | Raw: {res2_text[:100]}")
            h2 = []

        try:
            h3 = json.loads(res3_text).get("hallazgos", [])
        except Exception as e:
            logger.warning(f"Error parseando respuesta JSON del Agente 3 (Protocolo): {e} | Raw: {res3_text[:100]}")
            h3 = []

        raw_all = h1 + h2 + h3
        valid_hallazgos = validate_and_filter_findings(conversation_text, raw_all)

        return {
            "razonamiento_previo": f"Auditoría 4-Agentes completada. Gramática (Leve): {len(h1)}, Trato (Grave): {len(h2)}, Protocolo (Medio): {len(h3)}.",
            "hallazgos": valid_hallazgos
        }

    def audit_transcript(
        self,
        conversation_text: str,
        conv_metadata: Optional[Dict[str, Any]] = None,
        sub_equipo: str = "Televentas",
        templates_text: str = "",
        mode: str = "single"
    ) -> Dict[str, Any]:
        """Método principal de invocación."""
        if mode == "multi":
            return self.audit_transcript_multi(
                conversation_text=conversation_text,
                conv_metadata=conv_metadata,
                sub_equipo=sub_equipo,
                templates_text=templates_text
            )
        else:
            return self.audit_transcript_single(
                conversation_text=conversation_text,
                conv_metadata=conv_metadata,
                sub_equipo=sub_equipo,
                templates_text=templates_text
            )
