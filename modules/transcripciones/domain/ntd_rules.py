"""
Módulo de Dominio: Reglas Not To Do (NTD) e Indicadores de Calidad de Interbank.
"""

NTD_RULES_TEXT = """
REGLAS CRÍTICAS DE CALIDAD Y ÉTICA (GUÍA NOT TO DO - INTERBANK)

Las siguientes conductas están penalizadas y deben ser auditadas rigurosamente:

NIVEL 3 - GRAVE / CRÍTICO (Sanciones graves):
1. [TRATO_MALTRATO] Maltratar, insultar, agredir verbalmente u ofender al cliente en la comunicación.
2. [TRATO_DISCUSION] Iniciar una discusión con el cliente ante el rechazo de la oferta, mostrar actitud grosera, insistencia hostil o comentarios pasivo-agresivos.
3. [TRATO_DISCRIMINACION] Realizar comentarios discriminatorios sobre la localidad, nivel educativo, acento, género o condición socio-económica del cliente.
4. [VENTA_SIN_ACEPTACION] Ingresar o forzar la aceptación de productos sin el consentimiento explícito y positivo del cliente (el cliente debe decir de forma clara: "Sí", "Acepto", "De acuerdo" o "Está bien" después de la simulación).
5. [SEGURO_OBLIGATORIO] Informar que el Seguro de Protección es obligatorio o necesario para acceder al Préstamo, Extracash o Tarjeta de Crédito. El seguro siempre es opcional y voluntario.

NIVEL 2 - IMPACTO CLIENTE/BANCO (Sanciones moderadas):
6. [INFO_FALSA_AMBIGUA] Brindar información falsa, incompleta o ambigua con respecto a beneficios, tasas de interés (TEA/TCEA), costo de membresía, condiciones de exoneración o características del producto.
7. [INDUCIR_BAJA] Inducir al cliente a cancelar o dar de baja cualquier producto que ya tenga activo con Interbank (a menos que sea un proceso formal de compra de deuda externa).
8. [OMISION_DATOS] No solicitar los datos obligatorios requeridos por la plataforma para el perfilamiento (DNI, situación laboral, correo, etc.).

NIVEL 1 - ERROR OPERATIVO (Sanciones leves):
9. [ERROR_SPEECH] No seguir las plantillas de manera correcta y completa (parafrasear omitiendo información clave, omitir cláusulas legales obligatorias).
10. [ENCUESTA_INDUCIDA] Inducir o pedir al cliente que responda favorablemente una encuesta de satisfacción para beneficiar al asesor.
"""

def get_ntd_rules_prompt() -> str:
    """Retorna el texto formateado de reglas NTD para inyectar en los prompts del agente evaluador."""
    return NTD_RULES_TEXT
