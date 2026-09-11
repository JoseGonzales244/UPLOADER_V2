from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class EstadoRegistro(str, Enum):
    NO_ENCONTRADO = "no_encontrado"
    PENDIENTE = "pendiente"
    DESCARGADO = "descargado"


@dataclass
class SolicitudAudio:
    reg_ev: str
    dni: str
    nombre_archivo: str
    telefonos: List[str] = field(default_factory=list)
    prefijo: str = "AUDIO"

    @property
    def clave_unica(self) -> str:
        return f"{self.reg_ev}|{self.dni}"


@dataclass
class RegistroTracking:
    reg_ev: str
    dni: str
    estado: EstadoRegistro
    timestamp: str
    telefonos: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reg_ev": self.reg_ev,
            "dni": self.dni,
            "estado": self.estado.value if isinstance(self.estado, EstadoRegistro) else str(self.estado),
            "timestamp": self.timestamp,
            "telefonos": self.telefonos,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistroTracking":
        return cls(
            reg_ev=data.get("reg_ev", ""),
            dni=data.get("dni", ""),
            estado=EstadoRegistro(data.get("estado", EstadoRegistro.PENDIENTE.value)),
            timestamp=data.get("timestamp", ""),
            telefonos=data.get("telefonos", []),
        )
