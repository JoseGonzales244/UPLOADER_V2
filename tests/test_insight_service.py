import unittest
from unittest.mock import MagicMock, patch
from modules.speech.services.insight_lead_service import InsightLeadService

class TestInsightLeadService(unittest.TestCase):
    def setUp(self):
        self.service = InsightLeadService(username="test_user", password="test_password")

    def test_build_query_sql(self):
        cids = ["id-1234", "id-5678"]
        sql = self.service._build_query_sql(cids, min_date="2026-07-01")
        self.assertIn("'id-1234', 'id-5678'", sql)
        self.assertIn("sessionStartTime >= '2026-07-01'", sql)
        self.assertIn("TIPO_LEAD", sql)

    @patch("requests.Session.post")
    @patch("requests.Session.get")
    def test_get_tipos_lead_batch_mock(self, mock_get, mock_post):
        # Mock login response
        mock_login_resp = MagicMock()
        mock_login_resp.status_code = 200
        
        # Mock executeQuery response
        mock_exec_resp = MagicMock()
        mock_exec_resp.status_code = 200
        mock_exec_resp.json.return_value = {"data": {"nomArchivo": "test_file_123"}}

        # Mock exportData polling response
        mock_export_resp = MagicMock()
        mock_export_resp.status_code = 200
        mock_export_resp.json.return_value = {
            "data": {"fileSource": "https://s425vp01/files/test_file_123.tsv"}
        }

        # Mock file download TSV response
        mock_file_resp = MagicMock()
        mock_file_resp.status_code = 200
        mock_file_resp.text = "conversationID\tTIPO_LEAD\nid-1234\tOUTBOUND\nid-5678\tRESCATE_DIGITAL\n"

        mock_post.side_effect = [mock_login_resp, mock_exec_resp]
        mock_get.side_effect = [mock_export_resp, mock_file_resp]

        result = self.service.get_tipos_lead_batch(["id-1234", "id-5678"])

        self.assertEqual(result.get("id-1234"), "OUTBOUND")
        self.assertEqual(result.get("id-5678"), "RESCATE_DIGITAL")

if __name__ == "__main__":
    unittest.main()
