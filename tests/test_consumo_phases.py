"""
Tests unitarios (mock) para las 5 fases del Pipeline de Consumo.
"""
import unittest
from unittest.mock import MagicMock, patch
import os


def _make_consumo_ctx(**kwargs):
    """Crea un ConsumoPipelineContext mock para tests."""
    from modules.consumo.use_cases.consumo_orchestrator import ConsumoPipelineContext
    return ConsumoPipelineContext(
        period_str=kwargs.get("period_str", "202608"),
        insight_user=kwargs.get("insight_user", "test_user"),
        insight_password=kwargs.get("insight_password", "test_pass"),
        td_user=kwargs.get("td_user", "td_user"),
        td_password=kwargs.get("td_password", "td_pass"),
        host="dummy_host",
        logmech="TD2",
        input_dir=kwargs.get("input_dir", "/tmp/base_consumo"),
        clear_consent=False,
        progress_callback=None,
        insumos_config=kwargs.get("insumos_config", {}),
        td_con=kwargs.get("td_con", MagicMock())
    )


class TestConsumoPhase4(unittest.TestCase):

    @patch("modules.consumo.use_cases.phases.phase4_sql_scripts.write_powerbi_timestamp")
    @patch("modules.consumo.use_cases.phases.phase4_sql_scripts.run_post_load_transformations")
    def test_phase4_calls_powerbi_on_success(self, mock_sql, mock_powerbi):
        """Fase 4 Consumo llama write_powerbi_timestamp con conector_base_consumo.txt."""
        from modules.consumo.use_cases.phases.phase4_sql_scripts import run_phase4

        ctx = _make_consumo_ctx()
        result = run_phase4(ctx)

        self.assertTrue(result)
        mock_powerbi.assert_called_once_with("conector_base_consumo.txt")
        mock_sql.assert_called_once()

    @patch("modules.consumo.use_cases.phases.phase4_sql_scripts.write_powerbi_timestamp")
    @patch("modules.consumo.use_cases.phases.phase4_sql_scripts.run_post_load_transformations")
    def test_phase4_does_not_call_powerbi_on_error(self, mock_sql, mock_powerbi):
        """Fase 4 Consumo NO llama write_powerbi_timestamp si hay excepción."""
        from modules.consumo.use_cases.phases.phase4_sql_scripts import run_phase4

        mock_sql.side_effect = RuntimeError("SQL fallido")
        ctx = _make_consumo_ctx()

        with self.assertRaises(RuntimeError):
            run_phase4(ctx)

        mock_powerbi.assert_not_called()


class TestConsumoPhase5(unittest.TestCase):

    @patch("modules.consumo.use_cases.phases.phase5_selection.run_selection_transformation")
    def test_phase5_calls_selection_transformation(self, mock_selection):
        """Fase 5 Consumo invoca run_selection_transformation."""
        from modules.consumo.use_cases.phases.phase5_selection import run_phase5

        ctx = _make_consumo_ctx()
        result = run_phase5(ctx)

        self.assertTrue(result)
        mock_selection.assert_called_once_with(
            period_str="202608",
            progress_callback=None
        )


class TestConsumoPhase3(unittest.TestCase):

    def test_phase3_skips_if_no_server_configured(self):
        """Fase 3 Consumo omite silenciosamente si SQL Server no está en .env."""
        from modules.consumo.use_cases.phases.phase3_desembolsos import run_phase3

        ctx = _make_consumo_ctx()

        with patch.dict(os.environ, {"SQLSERVER_SERVER": "tu_servidor_sql"}):
            result = run_phase3(ctx)

        self.assertTrue(result)  # No debe fallar, solo omitir


class TestConsumoOrchestratorFacade(unittest.TestCase):

    @patch("modules.consumo.use_cases.consumo_orchestrator.connect_teradata")
    @patch("modules.consumo.use_cases.consumo_orchestrator.load_credentials")
    def test_orchestrator_creates_context_and_calls_phases(self, mock_creds, mock_connect):
        """El orquestador de consumo crea el contexto e invoca fases."""
        mock_creds.return_value = {"teradata_host": "IBKTD", "teradata_logmech": "TD2"}
        mock_con = MagicMock()
        mock_connect.return_value = mock_con

        import json
        config = {
            "consumo_insumos_config": {},
            "business_vars": {}
        }

        with patch("modules.consumo.use_cases.phases.phase1_insight_ingest.run_phase1") as p1, \
             patch("modules.consumo.use_cases.phases.phase2_cd40k.run_phase2") as p2, \
             patch("modules.consumo.use_cases.phases.phase3_desembolsos.run_phase3") as p3, \
             patch("modules.consumo.use_cases.phases.phase4_sql_scripts.run_phase4") as p4, \
             patch("modules.consumo.use_cases.phases.phase5_selection.run_phase5") as p5, \
             patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config))), \
             patch("os.path.join", return_value="/fake/path"), \
             patch("os.makedirs"):
            from modules.consumo.use_cases.consumo_orchestrator import run_orchestration_flow
            try:
                run_orchestration_flow(
                    insight_user="u", insight_password="p",
                    td_user="td", td_password="tdp",
                    period_str="202608"
                )
            except Exception:
                pass

            p1.assert_called_once()
            p2.assert_called_once()
            p3.assert_called_once()
            p4.assert_called_once()
            p5.assert_called_once()

    @patch("modules.consumo.use_cases.consumo_orchestrator.connect_teradata")
    @patch("modules.consumo.use_cases.consumo_orchestrator.load_credentials")
    def test_orchestrator_skips_disabled_phases(self, mock_creds, mock_connect):
        """El orquestador omite fases deshabilitadas."""
        mock_creds.return_value = {"teradata_host": "IBKTD", "teradata_logmech": "TD2"}
        mock_connect.return_value = MagicMock()

        import json
        config = {"consumo_insumos_config": {}, "business_vars": {}}

        with patch("modules.consumo.use_cases.phases.phase1_insight_ingest.run_phase1") as p1, \
             patch("modules.consumo.use_cases.phases.phase2_cd40k.run_phase2") as p2, \
             patch("modules.consumo.use_cases.phases.phase3_desembolsos.run_phase3") as p3, \
             patch("modules.consumo.use_cases.phases.phase4_sql_scripts.run_phase4") as p4, \
             patch("modules.consumo.use_cases.phases.phase5_selection.run_phase5") as p5, \
             patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config))), \
             patch("os.path.join", return_value="/fake/path"), \
             patch("os.makedirs"):
            from modules.consumo.use_cases.consumo_orchestrator import run_orchestration_flow
            try:
                run_orchestration_flow(
                    insight_user="u", insight_password="p",
                    td_user="td", td_password="tdp",
                    period_str="202608",
                    run_phase1=False, run_phase2=False
                )
            except Exception:
                pass

            p1.assert_not_called()
            p2.assert_not_called()
            p3.assert_called_once()


if __name__ == "__main__":
    unittest.main()
