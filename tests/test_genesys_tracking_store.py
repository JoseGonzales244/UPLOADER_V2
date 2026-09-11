import os
import tempfile
import unittest
from pathlib import Path

from modules.genesys.models import EstadoRegistro, RegistroTracking, SolicitudAudio
from modules.genesys.storage.tracking_store import TrackingStore


class TestGenesysTrackingStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tracking_file = Path(self.temp_dir.name) / "test_tracking.json"
        self.csv_file = Path(self.temp_dir.name) / "test_no_encontrados.csv"
        self.store = TrackingStore(tracking_file=self.tracking_file, csv_file=self.csv_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_marcar_como_procesado_guarda_telefonos(self):
        telefonos_mock = ["987654321", "912345678"]
        self.store.marcar_como_procesado(
            reg_ev="EV123",
            dni="12345678",
            estado=EstadoRegistro.DESCARGADO,
            telefonos=telefonos_mock
        )

        tracking = self.store.cargar()
        clave = "EV123|12345678"
        self.assertIn(clave, tracking)
        reg = tracking[clave]
        self.assertEqual(reg.reg_ev, "EV123")
        self.assertEqual(reg.dni, "12345678")
        self.assertEqual(reg.estado, EstadoRegistro.DESCARGADO)
        self.assertEqual(reg.telefonos, telefonos_mock)

    def test_marcar_sin_telefonos_mantiene_lista_vacia(self):
        self.store.marcar_como_procesado(
            reg_ev="EV999",
            dni="87654321",
            estado=EstadoRegistro.NO_ENCONTRADO
        )

        tracking = self.store.cargar()
        clave = "EV999|87654321"
        self.assertIn(clave, tracking)
        self.assertEqual(tracking[clave].telefonos, [])

    def test_registro_tracking_serialization_roundtrip(self):
        reg = RegistroTracking(
            reg_ev="EV001",
            dni="44556677",
            estado=EstadoRegistro.DESCARGADO,
            timestamp="2026-09-11T12:00:00",
            telefonos=["999888777"]
        )
        d = reg.to_dict()
        self.assertEqual(d["telefonos"], ["999888777"])

        restored = RegistroTracking.from_dict(d)
        self.assertEqual(restored.telefonos, ["999888777"])
        self.assertEqual(restored.reg_ev, "EV001")


if __name__ == "__main__":
    unittest.main()
