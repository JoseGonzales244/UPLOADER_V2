"""
Fases ordenadas y secuenciales del módulo de Dotación.
"""
from modules.dotacion.phases import fase1_limpieza
from modules.dotacion.phases import fase2_sincronizacion
from modules.dotacion.phases import fase3_distribucion
from modules.dotacion.phases import fase4_televentas
from modules.dotacion.phases import fase_licencias_sa

__all__ = [
    "fase1_limpieza",
    "fase2_sincronizacion",
    "fase3_distribucion",
    "fase4_televentas",
    "fase_licencias_sa"
]
