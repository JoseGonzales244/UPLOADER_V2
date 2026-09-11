import unittest
from unittest.mock import MagicMock, patch
from modules.genesys.models import SolicitudAudio
from modules.genesys.services.genesys_browser import GenesysBrowserAutomation


class TestGenesysBrowserAPI(unittest.TestCase):
    def setUp(self):
        self.bot = GenesysBrowserAutomation()

    def test_es_conclusion_acepta(self):
        catalog = {"w1": "ACEPTA CAMPAÑA (CE)", "w2": "NO ACEPTA", "w3": "RECHAZA"}

        conv_acepta = {
            "participants": [
                {
                    "sessions": [
                        {
                            "segments": [
                                {"segmentType": "wrapup", "wrapUpCode": "w1"}
                            ]
                        }
                    ]
                }
            ]
        }
        self.assertTrue(GenesysBrowserAutomation._es_conclusion_acepta(conv_acepta, catalog))

        conv_no_acepta = {
            "participants": [
                {
                    "sessions": [
                        {
                            "segments": [
                                {"segmentType": "wrapup", "wrapUpCode": "w2"}
                            ]
                        }
                    ]
                }
            ]
        }
        self.assertFalse(GenesysBrowserAutomation._es_conclusion_acepta(conv_no_acepta, catalog))

    def test_duracion_grabacion(self):
        rec1 = {"durationMs": 45000}
        self.assertEqual(GenesysBrowserAutomation._duracion_grabacion(rec1), 45000.0)

        rec2 = {"startTime": "2026-09-04T10:00:00.000Z", "endTime": "2026-09-04T10:02:30.000Z"}
        self.assertEqual(GenesysBrowserAutomation._duracion_grabacion(rec2), 150.0)

    @patch("modules.genesys.services.genesys_browser.requests.get")
    def test_verificar_token(self, mock_get):
        mock_get.return_value.status_code = 200
        self.assertTrue(GenesysBrowserAutomation._verificar_token("token_valido_12345678901234567890"))

        mock_get.return_value.status_code = 401
        self.assertFalse(GenesysBrowserAutomation._verificar_token("token_invalido_12345678901234567890"))
        self.assertFalse(GenesysBrowserAutomation._verificar_token("short"))

    @patch("modules.genesys.services.genesys_browser.requests.post")
    def test_ejecutar_descargas_api_busqueda_dnis_y_ani(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "conversations": []
        }

        sol = SolicitudAudio(
            reg_ev="B45810",
            dni="42849559",
            nombre_archivo="AUDIO_B45810_DNI42849559_20260904",
            telefonos=["997350797"]
        )

        with patch.object(self.bot, "_obtener_catalogo_wrapups", return_value={}):
            self.bot.ejecutar_descargas_api([sol], token="dummy_token_123456789012345")

        # Verificar que el payload enviado a la API contiene predicados tanto para DNIS como para ANI
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertIn("segmentFilters", payload)
        preds = payload["segmentFilters"][0]["predicates"]

        dnis_values = [p["value"] for p in preds if p["dimension"] == "dnis"]
        ani_values = [p["value"] for p in preds if p["dimension"] == "ani"]

        self.assertIn("997350797", dnis_values)
        self.assertIn("+51997350797", dnis_values)
        self.assertIn("997350797", ani_values)
        self.assertIn("+51997350797", ani_values)
        self.assertIn("tel:997350797", ani_values)


if __name__ == "__main__":
    unittest.main()
