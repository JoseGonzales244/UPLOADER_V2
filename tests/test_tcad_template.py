import unittest
import json
import os
import polars as pl
from infrastructure.parsers.cleaners import clean_dataframe, sanitize_identifier
from infrastructure.database.sql_executor import split_sql_statements


class TestTCADTemplateAndSQL(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        plantillas_path = os.path.join(os.getcwd(), "config", "plantillas.json")
        with open(plantillas_path, "r", encoding="utf-8") as f:
            cls.templates = json.load(f)

    def test_p025_template_contains_flg_new_speech_tcad(self):
        p025 = self.templates.get("P025-SA_TCAD")
        self.assertIsNotNone(p025, "Plantilla P025-SA_TCAD no encontrada en plantillas.json")
        self.assertIn("Piloto TCAD campaña", p025, "Columna 'Piloto TCAD campaña' no configurada en P025-SA_TCAD")
        
        cfg = p025["Piloto TCAD campaña"]
        self.assertTrue(cfg.get("Añadir"))
        self.assertTrue(cfg.get("Null:0/No Null:1"))
        self.assertEqual(cfg.get("Tipo de dato"), "FLOAT")
        self.assertEqual(cfg.get("Nuevo nombre"), "FLG_NEW_SPEECH_TCAD")

    def test_clean_dataframe_with_flg_new_speech_tcad(self):
        p025 = self.templates.get("P025-SA_TCAD")
        df_dummy = pl.DataFrame({
            "Area": ["TLV TC", "TLV TC", "TLV TC"],
            "cti_BT_Numero_Dni": ["12345678", "87654321", "11223344"],
            "Piloto TCAD campaña": [1.0, None, 1.0]
        })

        selections = []
        for col in df_dummy.columns:
            if col in p025:
                selections.append({
                    "name": col,
                    "selected": p025[col].get("Añadir", True),
                    "convert_nulls": p025[col].get("Null:0/No Null:1", False),
                    "datatype": p025[col].get("Tipo de dato", "VARCHAR(255)"),
                    "new_name": sanitize_identifier(p025[col].get("Nuevo nombre", col))
                })

        df_cleaned = clean_dataframe(
            df_dummy,
            selections,
            convertir_sin_acentos=True,
            transformar_varchar_latin=False,
            max_len_varchar=3000
        )

        self.assertIn("FLG_NEW_SPEECH_TCAD", df_cleaned.columns)
        vals = df_cleaned["FLG_NEW_SPEECH_TCAD"].to_list()
        self.assertEqual(vals, [1, 0, 1], "Los nulos deben convertirse a 0 y no nulos a 1")

    def test_tcad_ddl_and_dml_sql_statements(self):
        ddl_path = os.path.join(os.getcwd(), "modules", "Piloto TCAD", "sql", "00_ddl_tcad_tables_views.sql")
        dml_path = os.path.join(os.getcwd(), "modules", "Piloto TCAD", "sql", "01_dml_tcad_monthly_ingest.sql")
        
        self.assertTrue(os.path.exists(ddl_path))
        self.assertTrue(os.path.exists(dml_path))

        with open(ddl_path, "r", encoding="utf-8") as f:
            ddl_sql = f.read()
        self.assertIn("FLG_NEW_SPEECH_TCAD", ddl_sql)
        self.assertIn("COALESCE(sa_dia.FLG_NEW_SPEECH_TCAD, 0) AS FLG_NEW_SPEECH_TCAD", ddl_sql)

        with open(dml_path, "r", encoding="utf-8") as f:
            dml_sql = f.read()
        self.assertIn("COALESCE(FLG_NEW_SPEECH_TCAD, 0) AS FLG_NEW_SPEECH_TCAD", dml_sql)


if __name__ == "__main__":
    unittest.main()
