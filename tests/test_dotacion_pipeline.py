"""
Pruebas unitarias para el Pipeline de Dotación Mensual y Licencias Speech Analytics.
"""
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from modules.dotacion.dotacion_config import DotacionConfig
from modules.dotacion.phases.fase2_sincronizacion import get_new_seniority
from modules.dotacion.phases.fase_licencias_sa import is_backoffice
from backend.main import app


class TestDotacionPipelineLogic(unittest.TestCase):

    def test_dotacion_config_period_resolution(self):
        """Verifica la resolución correcta de fechas y nombres de mes en DotacionConfig."""
        cfg = DotacionConfig(target_period="2026-08")
        self.assertEqual(cfg.year, 2026)
        self.assertEqual(cfg.month, 8)
        self.assertEqual(cfg.prev_year, 2026)
        self.assertEqual(cfg.prev_month, 7)
        self.assertEqual(cfg.month_name_upper, "AGOSTO")
        self.assertEqual(cfg.prev_month_name_upper, "JULIO")

    def test_seniority_progression(self):
        """Verifica la máquina de estados de antigüedad (R0 -> R1 -> R2 -> R3)."""
        self.assertEqual(get_new_seniority(None), "R0")
        self.assertEqual(get_new_seniority(""), "R0")
        self.assertEqual(get_new_seniority("R0"), "R1")
        self.assertEqual(get_new_seniority("r0"), "R1")
        self.assertEqual(get_new_seniority("R1"), "R2")
        self.assertEqual(get_new_seniority("R2"), "R3")
        self.assertEqual(get_new_seniority("R3"), "R3")
        self.assertEqual(get_new_seniority("R4"), "R3")

    def test_is_backoffice_detection(self):
        """Verifica la detección de personal BackOffice y exclusión de interinos."""
        self.assertTrue(is_backoffice("Gestion_BackOffice", "ASESOR"))
        self.assertTrue(is_backoffice("", "ASISTENTE BO"))
        self.assertTrue(is_backoffice("Backoffice regular", ""))
        # Interinos NO son excluidos
        self.assertFalse(is_backoffice("Backoffice Interino", "ASESOR"))
        self.assertFalse(is_backoffice("Normal", "ASESOR VENTAS"))

    def test_supervisor_inconsistencies_detection(self):
        """Verifica la detección de alertas cuando un supervisor tiene múltiples códigos o viceversa."""
        from modules.dotacion.core.matching import detect_supervisor_inconsistencies

        records = [
            {"super": "CATHERINE JOSEFINA ESPINOZA TIMOTEO", "reg_super": "B15241"},
            {"super": "CATHERINE JOSEFINA ESPINOZA TIMOTEO", "reg_super": "B43648"}, # Error en input
            {"super": "BRUNO MIRANDA", "reg_super": "B43648"},
            {"super": "MARIA LOPEZ", "reg_super": "B99999"}
        ]

        alerts = detect_supervisor_inconsistencies(records)
        self.assertTrue(len(alerts) >= 2)
        # Catherine con 2 códigos
        self.assertTrue(any("CATHERINE JOSEFINA ESPINOZA TIMOTEO" in a and "B15241" in a and "B43648" in a for a in alerts))
        # B43648 con 2 supervisores (Bruno y Catherine)
        self.assertTrue(any("B43648" in a and "BRUNO MIRANDA" in a for a in alerts))


class TestDotacionEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch("backend.main._run_dotacion_pipeline_task")
    def test_post_run_dotacion_pipeline_endpoint(self, mock_task):
        response = self.client.post(
            "/api/dotacion/run-pipeline",
            json={"periodo": "2026-08"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "started")
        self.assertIn("2026-08", data["message"])

    @patch("backend.main._run_licencias_pipeline_task")
    def test_post_run_licencias_endpoint(self, mock_task):
        response = self.client.post(
            "/api/dotacion/run-licencias",
            json={"periodo": "202608"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "started")


if __name__ == "__main__":
    unittest.main()
