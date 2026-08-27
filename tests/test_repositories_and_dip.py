import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from domain.interfaces.database_repository import ITeradataRepository, ISpeechDbRepository
from infrastructure.database.repositories.teradata_repository import TeradataRepository
from infrastructure.database.repositories.speech_repository import SpeechDbRepository
from modules.speech.use_cases.speech_orchestrator import sync_transcripts_pipeline, extract_interactions_from_teradata
from modules.convenios.use_cases.convenios_orchestrator import run_convenios_setup, run_convenios_process_flow


class TestRepositoriesAndDIP(unittest.TestCase):

    def test_teradata_repository_extract_interactions_mock(self):
        repo = TeradataRepository(host="dummy_host", user="dummy_user", password="dummy_password")
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_con.cursor.return_value.__enter__.return_value = mock_cur
        mock_con.__enter__.return_value = mock_con

        mock_cur.description = [("CONID",), ("PRODUCTO",), ("FECHA_LLAMADA",), ("DNI",), ("REGISTRO",)]
        mock_cur.fetchall.return_value = [
            ("call-001", "TC", "2026-08-01", "12345678", "B11111"),
            ("call-002", "TC", "2026-08-02", "87654321", "B22222")
        ]

        with patch.object(repo, "_get_connection", return_value=mock_con):
            results = repo.extract_interactions(plantilla="Exp. Compra - TC", limit=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["ID_LLAMADA"], "call-001")
            self.assertEqual(results[1]["DNI"], "87654321")

    def test_teradata_repository_execute_script_mock(self):
        repo = TeradataRepository(host="dummy_host", user="dummy_user", password="dummy_password")
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_con.cursor.return_value.__enter__.return_value = mock_cur
        mock_con.__enter__.return_value = mock_con

        with patch.object(repo, "_get_connection", return_value=mock_con):
            success = repo.execute_script("SELECT 1; SELECT 2;", params={"VAR": "test"})
            self.assertTrue(success)
            self.assertEqual(mock_cur.execute.call_count, 2)

    def test_speech_repository_upsert_transcripts_mock(self):
        repo = SpeechDbRepository(server="dummy_srv", user="dummy_usr", password="dummy_pwd")
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_con.cursor.return_value.__enter__.return_value = mock_cur
        mock_con.__enter__.return_value = mock_con

        records = [
            ("call-001", "TC", "2026-08-01", "12345678", "B11111", "OUTBOUND", "Texto 1"),
            ("call-002", "TC", "2026-08-02", "87654321", "B22222", "INBOUND", "Texto 2")
        ]

        with patch.object(repo, "_get_connection", return_value=mock_con):
            count = repo.upsert_transcripts(records, batch_size=100)
            self.assertEqual(count, 2)
            self.assertTrue(mock_cur.executemany.called)
            self.assertTrue(mock_con.commit.called)

    @patch("modules.speech.use_cases.speech_orchestrator.extract_transcripts_from_verint")
    @patch("modules.speech.use_cases.speech_orchestrator.InsightLeadService")
    def test_speech_orchestrator_sync_pipeline_with_injected_repos(self, mock_insight_cls, mock_verint_extract):
        mock_insight = MagicMock()
        mock_insight.get_tipos_lead_batch.return_value = {"call-001": "OUTBOUND"}
        mock_insight_cls.return_value = mock_insight

        mock_verint_extract.return_value = {"call-001": "[00:01] Asesor: Hola"}

        mock_t_repo = MagicMock(spec=ITeradataRepository)
        mock_t_repo.extract_interactions.return_value = [{
            "ID_LLAMADA": "call-001",
            "PRODUCTO": "TC",
            "FECHA_LLAMADA": "2026-08-01",
            "DNI": "12345678",
            "REGISTRO": "B11111"
        }]

        mock_s_repo = MagicMock(spec=ISpeechDbRepository)
        mock_s_repo.upsert_transcripts.return_value = 1

        result = sync_transcripts_pipeline(
            plantilla="Exp. Compra - TC",
            teradata_repo=mock_t_repo,
            speech_repo=mock_s_repo
        )

        self.assertEqual(result["total_extraidos"], 1)
        self.assertEqual(result["total_sincronizados"], 1)
        mock_s_repo.ensure_speech_table.assert_called_once()
        mock_s_repo.upsert_transcripts.assert_called_once()

    def test_convenios_orchestrator_with_injected_repo(self):
        mock_t_repo = MagicMock(spec=ITeradataRepository)
        mock_t_repo.execute_script.return_value = True

        setup_ok = run_convenios_setup(teradata_repo=mock_t_repo)
        self.assertTrue(setup_ok)
        mock_t_repo.execute_script.assert_called_once()

        mock_t_repo.reset_mock()
        flow_ok = run_convenios_process_flow(period_str="202608", teradata_repo=mock_t_repo)
        self.assertTrue(flow_ok)
        mock_t_repo.execute_script.assert_called_once()


if __name__ == "__main__":
    unittest.main()
