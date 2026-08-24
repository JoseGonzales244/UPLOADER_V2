import unittest
import os
import io
from infrastructure.system.friendly_errors import format_friendly_error, extract_filename
from infrastructure.parsers.readers import read_excel_file, _validate_excel_source


class TestFriendlyErrors(unittest.TestCase):

    def test_calamine_zip_error_translation(self):
        user_error = (
            "calamine error: Xlsx error: Zip error: invalid Zip archive: Could not find EOCD Context: "
            "0: Could not open workbook at C:\\Users\\b47756\\OneDrive - Interbank\\Televentas\\APP_CALIDAD\\data\\input\\proceso_calidad\\Export_Calidad_20260824094918.xlsx "
            "1: could not load excel file at C:\\Users\\b47756\\OneDrive - Interbank\\Televentas\\APP_CALIDAD\\data\\input\\proceso_calidad\\Export_Calidad_20260824094918.xlsx"
        )
        friendly = format_friendly_error(user_error)
        self.assertIn("Export_Calidad_20260824094918.xlsx", friendly)
        self.assertIn("dañado o incompleto", friendly)
        self.assertNotIn("calamine error", friendly.lower())
        self.assertNotIn("Could not find EOCD", friendly)

    def test_teradata_7547_error_translation(self):
        td_error = "[Version 20.0.0.63] [Session 45572246] [Teradata Database] [Error 7547] [SQLState HY000] Target row updated by multiple source rows. at gosqldriver/teradatasql.formatError"
        friendly = format_friendly_error(td_error)
        self.assertIn("7547", friendly)
        self.assertIn("registros duplicados", friendly)
        self.assertNotIn("gosqldriver", friendly)

    def test_teradata_3807_error_translation(self):
        td_error = "[Teradata Database] [Error 3807] [SQLState 42S02] Object 'DLAB_GEC.TABLA_NO_EXISTE' does not exist."
        friendly = format_friendly_error(td_error)
        self.assertIn("DLAB_GEC.TABLA_NO_EXISTE", friendly)
        self.assertIn("no existe", friendly)

    def test_teradata_8017_auth_error(self):
        auth_error = "[Teradata Database] [Error 8017] The UserId, Password or Account is invalid."
        friendly = format_friendly_error(auth_error)
        self.assertIn("Credenciales incorrectas", friendly)

    def test_connection_vpn_error(self):
        conn_error = "[WinError 10060] Se produjo un error durante el intento de conexión ya que la parte conectada no respondió"
        friendly = format_friendly_error(conn_error)
        self.assertIn("VPN", friendly)

    def test_permission_error(self):
        perm_error = "[Errno 13] Permission denied: 'data/input/proceso_calidad/ACCION_TOMADA.xlsx'"
        friendly = format_friendly_error(perm_error)
        self.assertIn("ACCION_TOMADA.xlsx", friendly)
        self.assertIn("bloqueado", friendly)

    def test_validate_excel_empty_file(self):
        empty_stream = io.BytesIO(b"")
        empty_stream.name = "test.xlsx"
        with self.assertRaises(ValueError) as ctx:
            _validate_excel_source(empty_stream)
        self.assertIn("vacío", str(ctx.exception))

    def test_validate_excel_html_content(self):
        html_stream = io.BytesIO(b"<!DOCTYPE html><html><body>Error 500 Server Error</body></html>")
        html_stream.name = "export.xlsx"
        with self.assertRaises(ValueError) as ctx:
            _validate_excel_source(html_stream)
        self.assertIn("no es un Excel válido", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
