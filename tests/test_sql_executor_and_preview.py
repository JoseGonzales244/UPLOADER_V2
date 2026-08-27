"""
Unit Tests for Level 1 (SQL Executor & Tokenizer) and Level 2 (FilePreviewService).
"""
import unittest
import io
import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.database.sql_executor import (
    get_period_params,
    get_quality_period_params,
    get_cierre_period_params,
    inject_variables,
    parse_statements,
    split_sql_statements
)
from infrastructure.parsers.preview_service import FilePreviewService


class TestSqlExecutorAndPreview(unittest.TestCase):

    def test_get_period_params_standard(self):
        params = get_period_params("202607")
        self.assertEqual(params["periodo"], "202607")
        self.assertEqual(params["periodo_num"], 202607)
        self.assertEqual(params["periodo_prev"], "202606")
        self.assertEqual(params["PERIODO"], "202607")
        self.assertEqual(params["PERIODO_ANTERIOR"], "202606")
        self.assertEqual(params["anio"], 2026)
        self.assertEqual(params["mes"], 7)
        self.assertEqual(params["fec_inicio_mes"], "20260701")

    def test_get_period_params_january_rollover(self):
        params = get_period_params("202601")
        self.assertEqual(params["periodo_prev"], "202512")
        self.assertEqual(params["PERIODO_ANTERIOR"], "202512")

    def test_get_period_params_invalid(self):
        with self.assertRaises(ValueError):
            get_period_params("20267")
        with self.assertRaises(ValueError):
            get_period_params("INVALID")

    def test_inject_variables(self):
        raw_sql = "SELECT * FROM DB.TABLE WHERE PERIODO = '{PERIODO}' AND PREV = '{periodo_anterior}'"
        context = {"PERIODO": "202608", "periodo_anterior": "202607"}
        result = inject_variables(raw_sql, context)
        self.assertEqual(result, "SELECT * FROM DB.TABLE WHERE PERIODO = '202608' AND PREV = '202607'")

    def test_parse_statements_complex(self):
        complex_sql = """
        -- Comentario de línea inicial
        /* Comentario de bloque
           multilínea con ; adentro */
        SELECT 'Texto con ; punto y coma' AS col1, "Otro con ;" AS col2
        FROM TABLA_A;

        -- Segundo comentario
        INSERT INTO TABLA_B VALUES (1, 'valor');
        """
        stmts = parse_statements(complex_sql)
        self.assertEqual(len(stmts), 2)
        self.assertIn("SELECT 'Texto con ; punto y coma'", stmts[0])
        self.assertIn("INSERT INTO TABLA_B", stmts[1])

    def test_split_sql_statements_alias(self):
        sql = "SELECT 1; SELECT 2;"
        self.assertEqual(len(split_sql_statements(sql)), 2)

    def test_file_preview_service_csv(self):
        csv_content = b"DNI,NOMBRE,MONTO\n12345678,JUAN PEREZ,1500.50\n87654321,MARIA LOPEZ,2300.00\n"
        preview = FilePreviewService.generate_preview(
            file_source=csv_content,
            filename="test_leads.csv",
            file_type="CSV",
            selected_template="Ninguno"
        )
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["filename"], "test_leads.csv")
        self.assertEqual(preview["total_rows"], 2)
        self.assertEqual(preview["total_cols"], 3)
        self.assertEqual(len(preview["columns"]), 3)
        self.assertEqual(len(preview["preview"]), 2)

    def test_file_preview_service_prepare_upload_data(self):
        df_in = pl.DataFrame({
            "DNI": ["12345678"],
            "MONTO": [100.0]
        })
        selections = [
            {"name": "DNI", "new_name": "DNI_CLIENTE", "datatype": "VARCHAR(20)", "selected": True, "convert_nulls": False},
            {"name": "MONTO", "new_name": "MONTO_VENTA", "datatype": "DECIMAL(18,2)", "selected": True, "convert_nulls": False}
        ]
        # Test cleaning with prepared selections
        from infrastructure.parsers.cleaners import clean_dataframe
        df_clean = clean_dataframe(df_in, selections=selections)
        self.assertIn("DNI_CLIENTE", df_clean.columns)
        self.assertIn("MONTO_VENTA", df_clean.columns)


if __name__ == "__main__":
    unittest.main()
