from dataclasses import dataclass, field
from typing import Optional
from modules.dotacion.domain.exceptions import InvalidEmployeeDataException


@dataclass(frozen=True)
class Employee:
    code: str
    full_name: str
    document_id: Optional[str] = None
    situation: str = "ACTIVO"
    team: Optional[str] = None
    leader: Optional[str] = None

    def __post_init__(self):
        if not self.code or not str(self.code).strip():
            raise InvalidEmployeeDataException("Employee code cannot be empty.")
        if not self.full_name or not str(self.full_name).strip():
            raise InvalidEmployeeDataException("Employee name cannot be empty.")

    @property
    def formatted_name_reversed(self) -> str:
        """
        Formatea el nombre del ejecutivo de 'Nombre Apellido' a 'Apellido Nombre'.
        Soporta conectores comunes en apellidos (DE, DEL, LA).
        """
        words = self.full_name.strip().split()
        if len(words) >= 4 and words[-3].upper() in ["DE", "DEL", "LA"]:
            last_names = " ".join(words[-3:])
            first_names = " ".join(words[:-3])
            return f"{last_names} {first_names}"
        elif len(words) >= 3:
            last_names = " ".join(words[-2:])
            first_names = " ".join(words[:-2])
            return f"{last_names} {first_names}"
        elif len(words) == 2:
            return f"{words[1]} {words[0]}"
        return " ".join(words)
