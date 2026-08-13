import os
import sys
import logging
import datetime
from pathlib import Path

# Agregar raíz del proyecto al sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules.verint.services.verint_api_client import VerintAPIClient
from modules.verint.services.verint_utils import find_input_csv
from infrastructure.system.logging_config import setup_logging

# Configurar logging para consola y archivo plantilla_YYYYMMDD.log
logger = setup_logging(name="test_verint_step_by_step", log_prefix="proceso_calidad")

def run_step_by_step_test(period_str: str = "202607"):
    """
    Ejecuta un diagnóstico paso a paso del flujo API de Verint.
    Permite aislar exactamente en qué punto HTTP rechaza el servidor.
    """
    print("\n" + "="*60)
    print("🔍 INICIANDO DIAGNÓSTICO PASO A PASO DE VERINT API")
    print("="*60 + "\n")

    client = VerintAPIClient()

    # PASO 1: Autenticación SSO
    print("\n--- PASO 1: Autenticación SSO (login) ---")
    if not client.login():
        print("❌ PASO 1 FALLÓ: No se pudo autenticar en Verint WFO.")
        return False
    print(f"✅ PASO 1 OK. Impact360AuthToken: {client.impact360_token}")

    # PASO 2: Inicializar Sesión Speech Analytics
    print("\n--- PASO 2: Inicializar Sesión Speech Analytics (init_speech_session) ---")
    session_id = client.init_speech_session(instance_id=247115)
    if not session_id:
        print("❌ PASO 2 FALLÓ: No se obtuvo SessionId de Speech Analytics.")
        return False
    print(f"✅ PASO 2 OK. SessionId: {session_id}")

    # PASO 3: Ubicar y Subir CSV de Ejecutivos
    print("\n--- PASO 3: Subida de CSV de Ejecutivos (upload_csv_file) ---")
    try:
        csv_path = find_input_csv(period_str)
        print(f"📄 Archivo CSV detectado: {csv_path}")
    except Exception as e:
        print(f"⚠️ No se pudo localizar/generar el CSV para periodo {period_str}: {e}")
        print("   Creando CSV temporal sintético para pruebas de API...")
        temp_csv = PROJECT_ROOT / "data" / "input" / "proceso_calidad" / "test_execs.csv"
        temp_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write("EJECUTIVO\nTEST_USER\n")
        csv_path = str(temp_csv)

    file_id, desc_str = client.upload_csv_file(csv_path, instance_id=247115)
    print(f"Result Upload: file_id='{file_id}', desc_str='{desc_str}'")
    if not file_id:
        print("❌ PASO 3 FALLÓ: No se obtuvo un FileId válido al subir el CSV.")
        return False
    print(f"✅ PASO 3 OK. FileId asignado: {file_id}")

    # PASO 4: Construir XML QDI y Vincular Búsqueda Activa
    print("\n--- PASO 4: Vincular Búsqueda Activa (set_filter_as_search) ---")
    import uuid
    guid_str = str(uuid.uuid4())
    now_iso = datetime.datetime.now().isoformat()
    anio_p = int(period_str[:4])
    mes_p = int(period_str[4:6])
    m_next = 1 if mes_p == 12 else mes_p + 1
    y_next = anio_p + 1 if mes_p == 12 else anio_p

    from_fmt = f"{anio_p:04d}-{mes_p:02d}-01T00:00:00.0000000+00:00"
    to_fmt = f"{y_next:04d}-{m_next:02d}-01T00:00:00.0000000+00:00"

    qdi_xml = f"""<QDI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <GUID>{guid_str}</GUID>
  <creationTime>{now_iso}+00:00</creationTime>
  <MajorVersion>0</MajorVersion>
  <MinorVersion>0</MinorVersion>
  <QueryType>Session</QueryType>
  <DataSource>Unified</DataSource>
  <Direction>Full</Direction>
  <Security>
    <QDIRestrictionFlags ETMFilters="Active" MultiChannelApp="Active" PersonalTag="Inactive" />
    <IsAgentQuery>false</IsAgentQuery>
    <World>CCQ</World>
    <QueryPurpose>SEARCH</QueryPurpose>
  </Security>
  <UserPreferences>
    <NumberOfReturnedRows>2001</NumberOfReturnedRows>
    <TimeZone>UserTime</TimeZone>
    <AdditionalEvalInfo>NOTHING</AdditionalEvalInfo>
  </UserPreferences>
  <OrderDef>
    <TimeOfDateBegin>00:00:00</TimeOfDateBegin>
    <TimeOfDateEnd>00:00:00</TimeOfDateEnd>
    <From>{from_fmt}</From>
    <To>{to_fmt}</To>
    <RefFrom>0001-01-01T00:00:00.0000000+00:00</RefFrom>
    <RefTo>0001-01-01T00:00:00.0000000+00:00</RefTo>
    <OrderDefType>GREATER_LESS_EQUAL</OrderDefType>
    <RangeInDays>0</RangeInDays>
    <FieldRelation>Segment</FieldRelation>
    <TimeOfDayID>-1</TimeOfDayID>
  </OrderDef>
  <Fields>
    <Field xsi:type="QDIFieldExtended">
      <Values>
        <Value>{desc_str}</Value>
      </Values>
      <SessionName>
        <FieldID>5</FieldID>
        <Name>CUSTOM_DATA_STRING</Name>
      </SessionName>
      <Operator>file_list</Operator>
      <FieldRelation>Segment</FieldRelation>
      <GUID>{file_id}</GUID>
      <IsExtendedCustomData>true</IsExtendedCustomData>
    </Field>
  </Fields>
  <ComplexFields />
  <Random>
    <IsRandom>false</IsRandom>
    <PickRowOutOfEvery>10</PickRowOutOfEvery>
  </Random>
</QDI>"""

    filter_ok = client.set_filter_as_search(qdi_xml, instance_id=247115)
    if not filter_ok:
        print("❌ PASO 4 FALLÓ: SetFilterAsSearch fue rechazado por Verint.")
        return False
    print("✅ PASO 4 OK. Búsqueda activa vinculada correctamente.")

    # PASO 5: Consultar Reportes Exportados
    print("\n--- PASO 5: Consulta de Reportes Guardados (get_saved_reports) ---")
    reports = client.get_saved_reports()
    print(f"📊 Reportes encontrados: {len(reports)}")
    if reports:
        print(f"   Último reporte disponible: {reports[0].get('Name')}")

    print("\n" + "="*60)
    print("🎉 DIAGNÓSTICO COMPLETO FINALIZADO EXITOSAMENTE")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "202607"
    run_step_by_step_test(period)
