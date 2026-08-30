"""
Configuración dinámica y resolución de rutas para el Módulo de Dotación y Licencias SA.
"""
import os
import datetime
import unicodedata
from typing import Optional, Dict, List

ANALYSTS = ["CAROLINA", "CARMEN", "JANE", "KARIN"]
DAILY_TARGETS = {
    "CAROLINA": 8,
    "CARMEN": 8,
    "JANE": 5,
    "KARIN": 8
}

MONTH_NAMES_UPPER = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SETIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

MONTH_NAMES_CAP = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Setiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


class DotacionConfig:
    def __init__(
        self,
        target_period: str = "AUTO",
        base_dir_override: Optional[str] = None
    ):
        if str(target_period).strip().upper() == "AUTO" or not target_period:
            now = datetime.datetime.now()
            self.target_period = f"{now.year}-{now.month:02d}"
        else:
            clean_p = str(target_period).strip().replace("/", "-")
            if len(clean_p) == 6 and clean_p.isdigit():
                self.target_period = f"{clean_p[:4]}-{clean_p[4:]}"
            else:
                self.target_period = clean_p

        self.year, self.month = map(int, self.target_period.split("-"))
        self.prev_month = self.month - 1 if self.month > 1 else 12
        self.prev_year = self.year if self.month > 1 else self.year - 1

        self.month_name_upper = MONTH_NAMES_UPPER[self.month]
        self.prev_month_name_upper = MONTH_NAMES_UPPER[self.prev_month]
        self.month_name_cap = MONTH_NAMES_CAP[self.month]
        self.year_short = str(self.year)[2:]

        # Analistas y Metas Diarias
        self.analysts = ANALYSTS
        self.daily_targets = DAILY_TARGETS

        # Resolución de OneDrive
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "OneDrive - Interbank"),
            os.path.join(home, "OneDrive")
        ]
        self.base_onedrive = base_dir_override or next((c for c in candidates if os.path.exists(c)), candidates[0])

        self.dir_equipo_ventas = os.path.join(self.base_onedrive, rf"1. EXPERIENCIA DE COMPRA\EQUIPO DE VENTAS {self.year}")
        self.dir_licencias = os.path.join(self.base_onedrive, rf"1. EXPERIENCIA DE COMPRA\GESTIÓN {self.year}\DOTACION")
        self.dir_televentas = os.path.join(self.base_onedrive, rf"1. EXPERIENCIA DE COMPRA\GESTIÓN {self.year}\DOTACION\TERADATA")
        self.dir_vacaciones = os.path.join(self.base_onedrive, rf"1. EXPERIENCIA DE COMPRA\GESTIÓN {self.year}\VACACIONES")
        self.base_dotacion = os.path.join(self.base_onedrive, rf"Dotación {self.year}")

        self.dir_consolidado = os.path.join(self.base_dotacion, f"Dotación {self.year}{self.month:02d}")
        self.dir_select = os.path.join(self.dir_consolidado, "Equipo Select")

        # Nombres de archivo dinámicos por periodo
        self.input_base = f"{self.prev_month} EQUIPO DE VENTAS {self.prev_month_name_upper} {self.prev_year}.xlsx"
        self.output_base = f"{self.month} EQUIPO DE VENTAS {self.month_name_upper} {self.year}_PRELIMINAR.xlsx"
        self.consolidado_base = f"Consolidado Planilla ausentismo {self.year}{self.month:02d}.xlsx"
        self.select_dot_base = f"Dotacion_Ausencias_Select_{self.month_name_cap}{self.year_short}.xlsx"
        self.prev_exec_base = f"{self.prev_month} {self.prev_month_name_upper}_TELEVENTAS_EJECUTIVOS.xlsx"
        self.curr_exec_base = f"{self.month} {self.month_name_upper}_TELEVENTAS_EJECUTIVOS_PRELIMINAR.xlsx"
        self.licencias_base = f"LICENCIAS_SA_{self.year}.xlsx"
        self.vacaciones_base = f"Gestión de Vacaciones y Horarios {self.year}.xlsx"

        # Rutas finales
        self.INPUT_WORKBOOK = self._resolve_filepath(self.dir_equipo_ventas, self.input_base)
        self.OUTPUT_WORKBOOK = self._resolve_output_filepath(self.dir_equipo_ventas, self.output_base)
        self.CONSOLIDADO_FILE = self._resolve_filepath(self.dir_consolidado, self.consolidado_base)
        self.SELECT_DOTACION_FILE = self._resolve_filepath(self.dir_select, self.select_dot_base)
        self.PREV_EXEC_FILE = self._resolve_filepath(self.dir_televentas, self.prev_exec_base)
        self.CURR_EXEC_FILE = self._resolve_output_filepath(self.dir_televentas, self.curr_exec_base)
        self.LICENCIAS_FILE = self._resolve_filepath(self.dir_licencias, self.licencias_base)
        self.VACACIONES_FILE = self._resolve_filepath(self.dir_vacaciones, self.vacaciones_base)
        self.TARGET_PERIOD = self.target_period

    def _resolve_filepath(self, directory: str, base_filename: str) -> str:
        if os.path.exists(base_filename):
            return base_filename
        norm_base = unicodedata.normalize('NFC', base_filename).lower()
        if os.path.exists('.'):
            for fname in os.listdir('.'):
                if unicodedata.normalize('NFC', fname).lower() == norm_base:
                    return os.path.join('.', fname)
        return os.path.join(directory, base_filename)

    def _resolve_output_filepath(self, directory: str, base_filename: str) -> str:
        if not os.path.exists(directory):
            return base_filename
        return os.path.join(directory, base_filename)
