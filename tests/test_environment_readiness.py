import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz del proyecto
load_dotenv(PROJECT_ROOT / ".env")


class TestEnvironmentReadiness(unittest.TestCase):
    """Suite de validación de preparación y accesos para nuevos operadores y relevos técnicos."""

    REQUIRED_DIRS = [
        "data/downloads/audios",
        "data/input/auditorias_wsp",
        "data/input/base_consumo",
        "data/input/proceso_calidad",
        "data/input/verint",
        "data/reports",
        "data/runtime",
        "data/transcripciones",
    ]

    REQUIRED_ENV_GROUPS = {
        "Teradata Operativo (DLAB_GEC)": [
            "TERADATA_HOST",
            "TERADATA_USER",
            "TERADATA_PASSWORD",
            "TERADATA_LOGMECH",
        ],
        "Teradata Consulta (Select)": [
            "TERADATA_HOST_SELECT",
            "TERADATA_USER_SELECT",
            "TERADATA_PASSWORD_SELECT",
            "TERADATA_LOGMECH_SELECT",
        ],
        "SQL Server General": [
            "SQLSERVER_SERVER",
            "SQLSERVER_DATABASE",
            "SQLSERVER_USER",
            "SQLSERVER_PASSWORD",
            "SQLSERVER_DRIVER",
        ],
        "SQL Server Speech (sofIA)": [
            "SPEECH_SQLSERVER_SERVER",
            "SPEECH_SQLSERVER_DATABASE",
            "SPEECH_SQLSERVER_USER",
            "SPEECH_SQLSERVER_PASSWORD",
            "SPEECH_SQLSERVER_DRIVER",
        ],
        "Insight PureCloud": [
            "USERNAME_INSIGHT",
            "PASSWORD_INSIGHT",
        ],
        "Verint WFO": [
            "VERINT_USER",
            "VERINT_PASS",
            "VERINT_COOKIES",
        ],
        "Inteligencia Artificial": [
            "GEMINI_API_KEY",
        ],
    }

    def test_01_dotenv_file_presence(self):
        """Verifica que el archivo .env exista en la raíz del proyecto."""
        env_path = PROJECT_ROOT / ".env"
        self.assertTrue(
            env_path.is_file(),
            f"Falta el archivo .env en {env_path}. Solicita las credenciales al equipo o crea una copia desde .env.example."
        )

    def test_02_environment_variables_configured(self):
        """Verifica que todas las variables requeridas por grupo estén definidas y no vacías."""
        missing = {}
        for group_name, vars_list in self.REQUIRED_ENV_GROUPS.items():
            group_missing = [v for v in vars_list if not os.getenv(v)]
            if group_missing:
                missing[group_name] = group_missing

        self.assertEqual(
            missing,
            {},
            f"Variables de entorno faltantes o vacías por grupo: {missing}"
        )

    def test_03_filesystem_required_directories_exist(self):
        """Verifica que la estructura de carpetas locales en data/ esté completa."""
        missing_dirs = []
        for rel_dir in self.REQUIRED_DIRS:
            target = PROJECT_ROOT / rel_dir
            if not target.is_dir():
                # Intentar crearla automáticamente si no existe para asistir al nuevo usuario
                target.mkdir(parents=True, exist_ok=True)
                if not target.is_dir():
                    missing_dirs.append(rel_dir)

        self.assertEqual(
            missing_dirs,
            [],
            f"Las siguientes carpetas requeridas no existen y no pudieron ser creadas: {missing_dirs}"
        )

    def test_04_filesystem_read_write_permissions(self):
        """Verifica permisos efectivos de lectura y escritura en carpetas críticas."""
        critical_targets = ["data/runtime", "data/reports", "data/transcripciones"]
        for rel_path in critical_targets:
            folder = PROJECT_ROOT / rel_path
            test_file = folder / ".write_test_probe.tmp"
            try:
                test_file.write_text("ok_probe", encoding="utf-8")
                content = test_file.read_text(encoding="utf-8")
                self.assertEqual(content, "ok_probe")
            finally:
                if test_file.exists():
                    test_file.unlink()

    def test_05_database_drivers_availability(self):
        """Verifica que los conectores de base de datos estén instalados y disponibles."""
        try:
            import teradatasql
            self.assertIsNotNone(teradatasql)
        except ImportError:
            self.fail("El paquete 'teradatasql' no está instalado en el entorno virtual.")

        try:
            import pyodbc
            drivers = pyodbc.drivers()
            self.assertTrue(
                len(drivers) > 0,
                "pyodbc está instalado pero no se detectaron drivers ODBC en el sistema operativo Windows."
            )
            sql_server_drivers = [d for d in drivers if "SQL Server" in d]
            self.assertTrue(
                len(sql_server_drivers) > 0,
                f"No se encontró un driver ODBC para SQL Server instalado. Drivers detectados: {drivers}. "
                "Se recomienda instalar 'ODBC Driver 17 for SQL Server' u 'ODBC Driver 18 for SQL Server'."
            )
        except ImportError:
            self.fail("El paquete 'pyodbc' no está instalado en el entorno virtual.")

    def test_06_core_python_dependencies(self):
        """Verifica que las librerías fundamentales de la plataforma estén instaladas."""
        core_modules = ["fastapi", "pydantic", "openpyxl", "requests", "uvicorn"]
        for mod in core_modules:
            with self.subTest(module=mod):
                try:
                    __import__(mod)
                except ImportError:
                    self.fail(f"Dependencia esencial faltante: '{mod}'. Ejecuta 'pip install -r requirements.txt'.")


def check_external_paths():
    """Valida la accesibilidad de carpetas y archivos externos (OneDrive, SharePoint, Power BI)."""
    from modules.dotacion.dotacion_config import DotacionConfig
    from infrastructure.system.powerbi_connector import get_powerbi_dir
    from modules.calidad.televentas.use_cases.grouped_orchestrator import ONEDRIVE_DIRS

    cfg = DotacionConfig()
    results = []

    # 1. Insumos Excel locales
    cd40k_path = PROJECT_ROOT / "data/input/base_consumo/CD40K_NEW.xlsx"
    cd40k_alt = PROJECT_ROOT / "data/input/base_consumo/CD40K.xlsx"
    cd40k_ok = cd40k_path.is_file() or cd40k_alt.is_file()
    results.append({
        "name": "Plantilla CD40K (Consumo)",
        "path": str(cd40k_path if cd40k_path.is_file() else cd40k_alt),
        "status": "[OK]" if cd40k_ok else "[FAIL]",
        "detail": "Archivo presente" if cd40k_ok else "Falta CD40K_NEW.xlsx en data/input/base_consumo/ (ejecuta git pull)"
    })

    acc_path = PROJECT_ROOT / "data/input/proceso_calidad/ACCION_TOMADA.xlsx"
    acc_ok = acc_path.is_file()
    results.append({
        "name": "Plantilla ACCION_TOMADA (Calidad)",
        "path": str(acc_path),
        "status": "[OK]" if acc_ok else "[FAIL]",
        "detail": "Archivo presente" if acc_ok else "Falta ACCION_TOMADA.xlsx en data/input/proceso_calidad/ (ejecuta git pull)"
    })

    # 2. Base OneDrive
    onedrive_exists = os.path.isdir(cfg.base_onedrive)
    results.append({
        "name": "Carpeta Base OneDrive / Interbank",
        "path": cfg.base_onedrive,
        "status": "[OK]" if onedrive_exists else "[WARN]",
        "detail": "Detectada correctamente" if onedrive_exists else "No detectada. Configurar ONEDRIVE_DIR en .env si está en otra ruta"
    })

    # 3. 1. EXPERIENCIA DE COMPRA
    exp_dir = os.path.dirname(cfg.dir_equipo_ventas)
    exp_exists = os.path.isdir(exp_dir) or os.path.isdir(cfg.dir_equipo_ventas)
    results.append({
        "name": "1. EXPERIENCIA DE COMPRA",
        "path": exp_dir,
        "status": "[OK]" if exp_exists else "[WARN]",
        "detail": "Acceso disponible" if exp_exists else "Solicitar acceso a Janesy Lopez y agregar acceso directo en OneDrive"
    })

    # 4. Equipo de Ventas (Año actual)
    eq_exists = os.path.isdir(cfg.dir_equipo_ventas)
    input_wb_exists = os.path.isfile(cfg.INPUT_WORKBOOK)
    results.append({
        "name": f"EQUIPO DE VENTAS {cfg.year}",
        "path": cfg.dir_equipo_ventas,
        "status": "[OK]" if eq_exists else "[WARN]",
        "detail": f"Libro base ({cfg.input_base}): {'[OK]' if input_wb_exists else '[FALTA ARCHIVO]'}" if eq_exists else "Carpeta del año no encontrada"
    })

    # 5. Dotación & Licencias
    lic_exists = os.path.isfile(cfg.LICENCIAS_FILE)
    results.append({
        "name": f"LICENCIAS_SA_{cfg.year}.xlsx",
        "path": cfg.LICENCIAS_FILE,
        "status": "[OK]" if lic_exists else "[WARN]",
        "detail": "Archivo maestro presente" if lic_exists else f"Falta archivo {cfg.licencias_base} en GESTIÓN/DOTACION"
    })

    # 6. Vacaciones
    vac_exists = os.path.isfile(cfg.VACACIONES_FILE)
    results.append({
        "name": f"Vacaciones y Horarios {cfg.year}",
        "path": cfg.VACACIONES_FILE,
        "status": "[OK]" if vac_exists else "[WARN]",
        "detail": "Archivo presente" if vac_exists else f"Falta archivo {cfg.vacaciones_base} en GESTIÓN/VACACIONES"
    })

    # 7. Dotación {year}
    dot_exists = os.path.isdir(cfg.base_dotacion)
    results.append({
        "name": f"Dotación {cfg.year}",
        "path": cfg.base_dotacion,
        "status": "[OK]" if dot_exists else "[WARN]",
        "detail": "Acceso disponible" if dot_exists else "Solicitar acceso a Jacqueline y agregar acceso directo en OneDrive"
    })

    # 8. POWER BI
    pbi_dir = get_powerbi_dir()
    pbi_exists = pbi_dir.exists()
    results.append({
        "name": "Directorio POWER BI",
        "path": str(pbi_dir),
        "status": "[OK]" if pbi_exists else "[WARN]",
        "detail": "Directorio conector encontrado" if pbi_exists else "Crear carpeta 'Televentas/POWER BI' en OneDrive o definir POWER_BI_DIR en .env"
    })

    # 9. Televentas (P021)
    televentas_found = any(os.path.isdir(d) for d in ONEDRIVE_DIRS)
    active_tv = next((d for d in ONEDRIVE_DIRS if os.path.isdir(d)), ONEDRIVE_DIRS[0] if ONEDRIVE_DIRS else "N/A")
    results.append({
        "name": "Directorio Televentas (P021)",
        "path": active_tv,
        "status": "[OK]" if televentas_found else "[WARN]",
        "detail": "Directorio encontrado" if televentas_found else "Crear carpeta 'Televentas' en OneDrive para insumos P021"
    })

    return results


def print_diagnostic_report():
    """Imprime un reporte visual rápido de preparación si se ejecuta como script."""
    print("=" * 75)
    print("DIAGNOSTICO DE PREPARACION DE ENTORNO Y ACCESOS (READINESS REPORT)")
    print("=" * 75)

    # 1. .env
    env_file = PROJECT_ROOT / ".env"
    env_status = "[OK] PRESENTE" if env_file.is_file() else "[FAIL] NO ENCONTRADO"
    print(f"\n[1] Archivo de Configuracion (.env): {env_status}")

    # 2. Variables de entorno
    print("\n[2] Variables de Entorno por Grupo:")
    for group, vars_list in TestEnvironmentReadiness.REQUIRED_ENV_GROUPS.items():
        present = sum(1 for v in vars_list if os.getenv(v))
        total = len(vars_list)
        status = "[OK]" if present == total else f"[WARN] ({present}/{total})"
        print(f"    - {group.ljust(35)}: {status}")
        if present < total:
            missing = [v for v in vars_list if not os.getenv(v)]
            print(f"      Faltantes: {', '.join(missing)}")

    # 3. Carpetas de datos locales
    print("\n[3] Carpetas de Almacenamiento Local (data/):")
    for rel_dir in TestEnvironmentReadiness.REQUIRED_DIRS:
        folder = PROJECT_ROOT / rel_dir
        status = "[OK]" if folder.is_dir() else "[FAIL] FALTANTE"
        print(f"    - {rel_dir.ljust(35)}: {status}")

    # 4. Drivers
    print("\n[4] Drivers y Conectores de BD:")
    try:
        import teradatasql
        print("    - TeradataSQL Driver                : [OK] INSTALADO")
    except ImportError:
        print("    - TeradataSQL Driver                : [FAIL] NO INSTALADO")

    try:
        import pyodbc
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if drivers:
            print(f"    - SQL Server ODBC Driver            : [OK] DETECTADO ({drivers[0]})")
        else:
            print("    - SQL Server ODBC Driver            : [WARN] NINGUNO DETECTADO")
    except ImportError:
        print("    - pyodbc                            : [FAIL] NO INSTALADO")

    # 5. Rutas Externas y Carpetas de Insumos (OneDrive / SharePoint)
    print("\n[5] Rutas Externas y Archivos de Entrada (OneDrive / Insumos):")
    try:
        ext_results = check_external_paths()
        for item in ext_results:
            tag = item["status"]
            name = item["name"].ljust(35)
            detail = item["detail"]
            print(f"    - {name}: {tag} {detail}")
            if tag != "[OK]":
                print(f"      Ruta evaluada: {item['path']}")
    except Exception as ex:
        print(f"    [WARN] No se pudo verificar rutas externas: {ex}")

    print("\n" + "=" * 75)
    print("Para correr validacion unitaria formal:")
    print("    .\\.venv\\Scripts\\python -m unittest tests/test_environment_readiness.py")
    print("=" * 75)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--report", "-r", "--paths"):
        print_diagnostic_report()
    else:
        unittest.main()

