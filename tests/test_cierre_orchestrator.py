"""
Tests unitarios (mock) para el Orquestador de Cierre Mensual.
Verifica ejecución paralela (Fan-Out), manejo de conexiones de worker e idempotencia.
"""
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os

from modules.cierre.use_cases.cierre_orchestrator import run_cierre_process_flow


class TestCierreOrchestrator(unittest.TestCase):

    @patch("modules.cierre.use_cases.cierre_orchestrator.load_credentials")
    def test_cierre_no_scripts_selected_raises_value_error(self, mock_creds):
        """Si no se selecciona ningún script de cierre, debe levantar ValueError."""
        with self.assertRaises(ValueError) as ctx:
            run_cierre_process_flow(
                period_str="202608",
                run_cierre_01=False,
                run_cierre_02=False,
                run_cierre_03=False
            )
        self.assertIn("al menos un script", str(ctx.exception))

    @patch("modules.cierre.use_cases.cierre_orchestrator.connect_teradata")
    @patch("modules.cierre.use_cases.cierre_orchestrator.load_credentials")
    def test_cierre_connection_failure_raises_runtime_error(self, mock_creds, mock_connect):
        """Fallo al conectar con Teradata levanta RuntimeError descriptivo."""
        mock_creds.return_value = {
            "teradata_user": "user",
            "teradata_password": "pass",
            "teradata_host": "IBKTD",
            "teradata_logmech": "TD2"
        }
        mock_connect.side_effect = Exception("Conexión rechazada")

        with self.assertRaises(RuntimeError) as ctx:
            run_cierre_process_flow(period_str="202608")
        self.assertIn("Error de conexión con Teradata", str(ctx.exception))

    @patch("infrastructure.system.notifier.notify_desktop")
    @patch("modules.cierre.use_cases.cierre_orchestrator.connect_teradata")
    @patch("modules.cierre.use_cases.cierre_orchestrator.load_credentials")
    @patch("os.path.exists", return_value=True)
    def test_cierre_parallel_execution_all_scripts(self, mock_exists, mock_creds, mock_connect, mock_notify):
        """Ejecuta los 3 scripts de cierre en paralelo con conexiones dedicadas."""
        mock_creds.return_value = {
            "teradata_user": "td_user",
            "teradata_password": "td_password",
            "teradata_host": "IBKTD",
            "teradata_logmech": "TD2"
        }

        mock_con = MagicMock()
        mock_cursor = MagicMock()
        mock_con.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_con

        fake_sql = "DELETE FROM DLAB_GEC.TABLE WHERE PERIODO = '{PERIODO}';\nSELECT 1;"

        with patch("builtins.open", mock_open(read_data=fake_sql)):
            result = run_cierre_process_flow(
                period_str="202608",
                run_cierre_01=True,
                run_cierre_02=True,
                run_cierre_03=True
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["periodo_base"], "202608")
        # 1 test connection + 3 worker connections = 4 connect_teradata calls
        self.assertEqual(mock_connect.call_count, 4)

    @patch("infrastructure.system.notifier.notify_desktop")
    @patch("modules.cierre.use_cases.cierre_orchestrator.connect_teradata")
    @patch("modules.cierre.use_cases.cierre_orchestrator.load_credentials")
    @patch("os.path.exists", return_value=True)
    def test_cierre_single_script_execution(self, mock_exists, mock_creds, mock_connect, mock_notify):
        """Ejecuta un solo script cuando solo uno es seleccionado."""
        mock_creds.return_value = {
            "teradata_user": "td_user",
            "teradata_password": "td_password",
            "teradata_host": "IBKTD",
            "teradata_logmech": "TD2"
        }

        mock_con = MagicMock()
        mock_cursor = MagicMock()
        mock_con.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_con

        fake_sql = "DELETE FROM DLAB_GEC.M_KRI_RESUMEN_TOTAL WHERE PERIODO = '{PERIODO}';"

        with patch("builtins.open", mock_open(read_data=fake_sql)):
            result = run_cierre_process_flow(
                period_str="202608",
                run_cierre_01=False,
                run_cierre_02=True,
                run_cierre_03=False
            )

        self.assertEqual(result["status"], "success")
        # 1 test connection + 1 worker connection = 2 connect_teradata calls
        self.assertEqual(mock_connect.call_count, 2)


if __name__ == "__main__":
    unittest.main()
