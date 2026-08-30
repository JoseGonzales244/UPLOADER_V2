"""
Módulo de componentes y utilidades compartidas de configuración.
"""
import os
import json
from typing import Dict, Any


def load_templates() -> Dict[str, Any]:
    """
    Carga las plantillas de mapping Excel -> Teradata desde config/plantillas.json.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(base_dir, "config", "plantillas.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Archivo de plantillas no encontrado: '{path}'. "
            "Asegúrate de que 'config/plantillas.json' existe en la raíz del proyecto."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
