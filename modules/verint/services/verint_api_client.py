import os
import time
import json
import logging
import datetime
import random
from typing import Dict, Any, List, Optional
from pathlib import Path
import httpx
from dotenv import load_dotenv
from modules.verint.services.verint_cookie_harvester import get_verint_cookies, get_verint_session

load_dotenv()

logger = logging.getLogger("verint_api_client")

class VerintAPIClient:
    """
    Cliente API / HTTP directo para Verint WFO & Speech Analytics.
    Permite autenticarse mediante HTTP POST/Session cookies/SSO Microsoft, inicializar sesiones de Speech Analytics,
    aplicar filtros por fecha y agente, consultar contactos directamente, y gestionar exportaciones.
    """
    def __init__(self, base_url: str = "https://wfo.mt5.verintcloudservices.com", username: str = None, password: str = None):
        self.base_url = base_url.rstrip("/")
        self.username = username or os.getenv("VERINT_USER")
        self.password = password or os.getenv("VERINT_PASS")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Microsoft Edge";v="151", "Chromium";v="151"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }
        
        self.session = httpx.Client(
            headers=headers,
            timeout=60.0,
            follow_redirects=True,
            verify=False  # Proxy corporativo Interbank usa SSL inspection con cert propio
        )
        self.is_authenticated = False
        self.xsrf_token = None
        self.impact360_token = None
        self.instance_id = 247129
        self.app_id = "0a089067-5b54-4e8b-e34b-0420d23ce8b4"
        self.speech_session_id = None
        
        # --- Auto Cookie & Token Harvester (Playwright SSO headless si caché expiró) ---
        raw_cookie = os.getenv("VERINT_COOKIES") or os.getenv("VERINT_COOKIE") or os.getenv("VERINT_JSESSIONID")
        if raw_cookie:
            logger.info("🔑 Cookie manual detectada en .env. Asignando directamente...")
            for item in raw_cookie.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    self.session.cookies.set(k.strip(), v.strip())
            self.is_authenticated = True
        elif self.username:
            try:
                harvested_cookies, token = get_verint_session(self.username, self.password or "", self.base_url)
                for name, value in harvested_cookies.items():
                    self.session.cookies.set(name, value)
                
                if token:
                    self.impact360_token = token
                    self.xsrf_token = token
                    self.session.headers["Impact360AuthToken"] = token
                    self.session.headers["xsrfToken"] = token
                    logger.info(f"🔑 Impact360AuthToken inyectado en cabecera: {token}")

                self.is_authenticated = True
                logger.info(f"🍪 {len(harvested_cookies)} cookies de sesión inyectadas en el cliente API.")
            except Exception as e:
                logger.warning(f"Cookie/Token Harvester falló: {e}. Se intentará login directo luego.")

    def login(self) -> bool:
        """
        Garantiza que la sesión esté autenticada con cookies y token SSO validos.
        """
        if self.is_authenticated and self.impact360_token:
            return True

        if not self.username:
            raise ValueError("VERINT_USER no configurado.")

        logger.info(f"Autenticando usuario SSO '{self.username}' en Verint WFO vía Harvester...")
        try:
            harvested_cookies, token = get_verint_session(self.username, self.password or "", self.base_url, force_refresh=True)
            for name, value in harvested_cookies.items():
                self.session.cookies.set(name, value)
            
            if token:
                self.impact360_token = token
                self.xsrf_token = token
                self.session.headers["Impact360AuthToken"] = token
                self.session.headers["xsrfToken"] = token
                logger.info(f"🔑 Nuevo Impact360AuthToken inyectado: {token}")

            self.is_authenticated = True
            return True
        except Exception as e:
            logger.error(f"Fallo al autenticar vía SSO Playwright: {e}")
            return False

    def init_speech_session(self, instance_id: int = None) -> Optional[str]:
        """
        Inicializa la sesión de Speech Analytics para llamadas de WCF services (.svc).
        """
        if instance_id is not None:
            self.instance_id = instance_id
            
        if not self.is_authenticated:
            self.login()
            
        # Asegurar toque previo a /wfo/control/main para registrar sesión en servidor WFO
        try:
            self.session.get(f"{self.base_url}/wfo/control/main", timeout=15.0)
        except Exception as err_main:
            logger.debug(f"Pre-touch a /wfo/control/main: {err_main}")

        url = f"{self.base_url}/SpeechAnalytics/Services/ApplicationSession/ApplicationSessionService.svc/InitializeSession"
        payload = {
            "instanceContext": {
                "InstanceId": self.instance_id,
                "ApplicationId": self.app_id
            }
        }
        headers = {"Content-Type": "application/json"}
        
        def _do_init():
            res = self.session.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                try:
                    data = res.json()
                    init_res = data.get("InitializeSessionResult", {})
                    data_obj = init_res.get("Data", {})
                    self.speech_session_id = data_obj.get("SessionId")
                    if self.speech_session_id:
                        logger.info(f"Sesión de Speech Analytics inicializada con éxito: {self.speech_session_id}")
                        return self.speech_session_id
                except Exception as e:
                    logger.error(f"Error al deserializar InitializeSession: {e}")
            return None

        sid = _do_init()
        if sid:
            return sid
            
        # Si falló por cookies expiradas o bloqueadas, forzar renovación transparente con Cookie Harvester
        logger.warning("InitializeSession rechazado. Forzando renovación de cookies con Harvester...")
        try:
            harvested = get_verint_cookies(self.username, self.password, self.base_url, force_refresh=True)
            for name, value in harvested.items():
                self.session.cookies.set(name, value)
            self.session.get(f"{self.base_url}/wfo/control/main", timeout=15.0)
            return _do_init()
        except Exception as e_harv:
            logger.error(f"Fallo crítico al renovar cookies: {e_harv}")
            return None

    def _get_speech_session_payload(self) -> Dict[str, Any]:
        return {
            "InstanceId": self.instance_id,
            "SessionId": self.speech_session_id or "",
            "sessionConfiguration": {"IsSpeakerSeparation": True},
            "id": "SpeechAnalytics.model.session.ApplicationSession-1",
            "ApplicationId": self.app_id
        }

    def get_contacts_result_set(self, limit: int = 1000, page: int = 1) -> Dict[str, Any]:
        """
        Obtiene directamente el listado de interacciones/contactos del filtro activo.
        """
        if not self.speech_session_id:
            self.init_speech_session()
            
        url = f"{self.base_url}/SpeechAnalytics/Services/Contacts/ContactsService.svc/GetContactsResultSet"
        payload = {
            "session": self._get_speech_session_payload(),
            "page": page,
            "start": (page - 1) * limit,
            "limit": limit,
            "maxStarRank": 0,
            "sorters": None
        }
        headers = {"Content-Type": "application/json"}
        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            try:
                data = res.json()
                result = data.get("GetContactsResultSetResult", {})
                logger.info(f"Petición GetContactsResultSet exitosa (Success: {result.get('Success')})")
                return result
            except Exception as e:
                logger.error(f"Error deserializando GetContactsResultSet: {e}")
        else:
            logger.error(f"Error en GetContactsResultSet ({res.status_code}): {res.text[:200]}")
        return {}

    def export_result_set(self, export_name: str) -> Dict[str, Any]:
        """
        Encola la generación de un reporte Excel en Mis Exportaciones de Verint.
        """
        if not self.speech_session_id:
            self.init_speech_session()
            
        url = f"{self.base_url}/SpeechAnalytics/Services/Reports/ReportsService.svc/ExportResultSet"
        payload = {
            "session": self._get_speech_session_payload(),
            "reportName": export_name,
            "exportType": "Excel",
            "isAllResults": True
        }
        headers = {"Content-Type": "application/json"}
        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            try:
                data = res.json()
                logger.info(f"Respuesta de ExportResultSet: {data}")
                return data
            except Exception as e:
                logger.error(f"Error al deserializar ExportResultSet: {e}")
        else:
            logger.error(f"Error en ExportResultSet ({res.status_code}): {res.text[:200]}")
        return {}

    def get_saved_reports(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de reportes exportados en Mis Exportaciones.
        """
        if not self.speech_session_id:
            self.init_speech_session()
            
        url = f"{self.base_url}/SpeechAnalytics/Services/Reports/ReportsService.svc/GetSavedReports"
        payload = {
            "session": self._get_speech_session_payload(),
            "retriveReportDescription": True,
            "page": 1,
            "start": 0,
            "limit": 10000,
            "sortProperty": "Name",
            "sortDirection": "ASC",
            "language": "es-ES"
        }
        headers = {"Content-Type": "application/json"}
        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            try:
                data = res.json()
                get_res = data.get("GetSavedReportsResult", {})
                reports = get_res.get("Data", []) or get_res.get("Reports", []) or []
                logger.info(f"Se obtuvieron {len(reports)} reportes exportados de Verint.")
                return reports
            except Exception as e:
                logger.error(f"Error al deserializar GetSavedReports: {e}")
        else:
            logger.error(f"Error en GetSavedReports ({res.status_code}): {res.text[:200]}")
        return []

    def download_report(self, report_item: dict, output_filepath: str, instance_id: int = 247115) -> bool:
        """
        Descarga el archivo exportado de Verint Cloud dado el objeto de reporte devuelto por GetSavedReports.
        """
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        
        report_name = report_item.get("Name", "")
        rel_url = report_item.get("URL", "")
        report_format = report_item.get("Format", 4)
        token = random.randint(10000, 99999)
        
        url = (
            f"{self.base_url}/SpeechAnalytics/Handlers/Reports/DownloadReports.ashx"
            f"?instanceId={instance_id}"
            f"&baseDirectory=DataExports"
            f"&name={report_name}"
            f"&reportFormat={report_format}"
            f"&url={rel_url}"
            f"&sessionId={self.speech_session_id}"
            f"&SA_downloadReportToken={token}"
        )
        
        logger.info(f"Descargando reporte '{report_name}' por API HTTP pura desde {url}...")
        res = self.session.get(url)
        
        if res.status_code == 200 and len(res.content) > 1000:
            with open(output_filepath, "wb") as f:
                f.write(res.content)
            logger.info(f"✅ Archivo guardado exitosamente en: {output_filepath} ({len(res.content)} bytes)")
            return True
        else:
            logger.error(f"Error al descargar reporte '{report_name}' por API ({res.status_code}, Bytes: {len(res.content)})")
            return False

    def create_contacts_report(self, report_name: str, filter_qdi_xml: str, instance_caption: str = "Televentas") -> bool:
        """
        Encola un reporte de exportación directamente en el servidor de Verint por HTTP puro (100% API sin navegador).
        """
        if not self.speech_session_id:
            self.init_speech_session(instance_id=247115)

        url = f"{self.base_url}/SpeechAnalytics/Services/Reports/ReportsService.svc/CreateContactsReport"
        
        speech_session_payload = {
            "InstanceId": 247115,
            "SessionId": self.speech_session_id,
            "sessionConfiguration": {"IsSpeakerSeparation": True},
            "id": "SpeechAnalytics.model.session.ApplicationSession-2",
            "ApplicationId": self.app_id
        }
        
        payload = {
            "session": speech_session_payload,
            "instanceCaption": instance_caption,
            "instanceName": instance_caption,
            "reportName": report_name,
            "reportType": 0,
            "numberOfContacts": 0,
            "filterQDI": filter_qdi_xml,
            "language": "es-ES",
            "regionalFormat": "en-US",
            "reportCreationDate": int(datetime.datetime.now().timestamp() * 1000)
        }
        
        headers = {"Content-Type": "application/json"}
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            
        logger.info(f"Enviando CreateContactsReport ('{report_name}') por API HTTP pura...")
        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            try:
                data = res.json()
                success = data.get("CreateContactsReportResult", {}).get("Success", False)
                if success:
                    logger.info(f"✅ Reporte '{report_name}' encolado exitosamente en Verint por API pura.")
                    return True
            except Exception as e:
                logger.error(f"Error al deserializar respuesta de CreateContactsReport: {e}")
        else:
            logger.error(f"Error al encolar reporte por API ({res.status_code}): {res.text[:200]}")
        return False

    def upload_csv_file(self, csv_filepath: str, instance_id: int = 247115) -> tuple:
        """
        Suba el archivo CSV de ejecutivos por HTTP POST a UploadFileList.ashx.
        Retorna (file_id, description_str).
        """
        if not self.speech_session_id:
            self.init_speech_session(instance_id=instance_id)

        url = f"{self.base_url}/SpeechAnalytics/Handlers/FileList/UploadFileList.ashx"
        path_obj = Path(csv_filepath)
        desc_name = path_obj.stem
        desc_str = f"{desc_name} ({datetime.datetime.now().strftime('%I:%M %p %m/%d/%Y').lstrip('0')})"
        
        params = {
            "InstanceId": instance_id,
            "SessionId": self.speech_session_id,
            "fieldName": "CDStringWithList5",
            "description": desc_name
        }
        with open(csv_filepath, "rb") as f:
            files = {"file": (path_obj.name, f, "text/csv")}
            res = self.session.post(url, params=params, files=files)

        if res.status_code == 200:
            file_id = res.json().get("id", "")
            logger.info(f"✅ CSV '{path_obj.name}' cargado exitosamente por HTTP. FileId: {file_id}")
            return file_id, desc_str
        logger.error(f"Error al cargar CSV por HTTP ({res.status_code}): {res.text[:200]}")
        return "", desc_str

    def set_filter_as_search(self, qdi_xml: str, instance_id: int = 247115) -> bool:
        """
        Activa y vincula el filtro QDI como la búsqueda activa en el servidor de Verint.
        """
        if not self.speech_session_id:
            self.init_speech_session(instance_id=instance_id)

        url = f"{self.base_url}/SpeechAnalytics/Services/Filter/FilterService.svc/SetFilterAsSearch"
        headers = {"Content-Type": "application/json"}
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            
        speech_session_payload = {
            "InstanceId": instance_id,
            "SessionId": self.speech_session_id or "",
            "sessionConfiguration": {"IsSpeakerSeparation": True},
            "id": "SpeechAnalytics.model.session.ApplicationSession-2",
            "ApplicationId": "129eee08-a5b6-4e26-c00d-27d3663975ee"
        }
        
        payload = {
            "session": speech_session_payload,
            "filterQDI": qdi_xml
        }
        
        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            try:
                res_data = res.json().get("SetFilterAsSearchResult", {})
                success = res_data.get("Success", False)
                if success:
                    logger.info("✅ Búsqueda activa congelada exitosamente en el servidor de Verint.")
                    return True
                err_msg = res_data.get("ErrorMessage") or res_data.get("ErrorDescription") or str(res_data)
                logger.error(f"SetFilterAsSearch rechazado por Verint: {err_msg}")
            except Exception as e:
                logger.error(f"Error deserializando SetFilterAsSearch: {e}")
        else:
            logger.error(f"SetFilterAsSearch falló (HTTP {res.status_code}): {res.text[:200]}")
        return False

    def export_televentas_period(self, from_iso: str, to_iso: str, csv_filepath: str, output_dir: str, poll_interval_seconds: int = 60, timeout_minutes: int = 35, stop_checker: Optional[Any] = None) -> str:
        """
        Ejecuta el flujo completo 100% HTTP API de exportación para Televentas:
        Login -> InitSession -> UploadCSV -> SetFilterAsSearch -> CreateContactsReport -> Wait & Download.
        Retorna la ruta absoluta del archivo .xlsx descargado.
        """
        import uuid
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        report_name = f"Export_Calidad_{timestamp_str}"
        
        if stop_checker and stop_checker():
            raise RuntimeError("Proceso cancelado por el usuario antes de iniciar exportación Verint.")

        if not self.xsrf_token:
            if not self.login():
                raise RuntimeError("Fallo en la autenticación con Verint WFO.")
                
        self.init_speech_session(instance_id=247115)
        
        # 1. Subir CSV de Ejecutivos
        file_id, desc_str = self.upload_csv_file(csv_filepath, instance_id=247115)
        if not file_id:
            raise RuntimeError(f"No se pudo cargar el archivo CSV: {csv_filepath}")
            
        # 2. Construir XML QDI completo vinculado con GUID del FileId y rango de fechas
        guid_str = str(uuid.uuid4())
        now_iso = datetime.datetime.now().isoformat()
        from_fmt = datetime.datetime.fromisoformat(from_iso).strftime("%Y-%m-%dT%H:%M:%S.0000000+00:00")
        to_fmt = datetime.datetime.fromisoformat(to_iso).strftime("%Y-%m-%dT%H:%M:%S.0000000+00:00")

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

        # 3. Vincular Filtro como Búsqueda Activa en Servidor
        if not self.set_filter_as_search(qdi_xml, instance_id=247115):
            raise RuntimeError("Fallo al vincular la búsqueda activa en Verint.")
            
        # 4. Encolar Reporte por HTTP Pura
        if not self.create_contacts_report(report_name, qdi_xml, instance_caption="Televentas"):
            raise RuntimeError(f"Fallo al encolar el reporte '{report_name}'.")
            
        # 5. Esperar y Descargar por HTTP Pura (Soporta 1 archivo o partes 1-2, 2-2)
        logger.info(f"Monitoreando la finalización del reporte '{report_name}' por API HTTP...")
        downloaded_paths = []
        start_time = time.time()  # FIX: inicializar antes del loop de polling
        
        while (time.time() - start_time) < (timeout_minutes * 60):
            if stop_checker and stop_checker():
                logger.warning(f"🛑 Cancelación detectada durante la espera del reporte '{report_name}'. Abortando...")
                raise RuntimeError("Proceso cancelado por el usuario.")
            reports = self.get_saved_reports()
            matching_reports = [
                r for r in reports[:20]
                if (str(r.get("Name", "")) == report_name or str(r.get("Name", "")).startswith(f"{report_name} "))
            ]
            
            if matching_reports:
                all_ready = all(str(r.get("Status", "")) in ["1", "2", "4", "completed", "completado"] for r in matching_reports)
                if all_ready:
                    logger.info(f"🎯 Reporte '{report_name}' ({len(matching_reports)} parte(s)) completado en Verint Cloud! Descargando...")
                    for r in matching_reports:
                        part_name = str(r.get("Name", ""))
                        out_path = Path(output_dir) / f"{part_name}.xlsx"
                        if self.download_report(r, str(out_path), instance_id=247115):
                            downloaded_paths.append(str(out_path))
                    if downloaded_paths:
                        return downloaded_paths[0] if len(downloaded_paths) == 1 else ",".join(downloaded_paths)
                        
            time.sleep(poll_interval_seconds)
            
        raise RuntimeError(f"Timeout de {timeout_minutes} minutos agotado esperando el reporte '{report_name}' en Verint.")
            
    def get_interaction_transcription_api(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la transcripción JSON completa de una llamada por CONID (call_id) vía API REST directa.
        Retorna la estructura deserializada con WordsSequences (Hablantes Agent/Customer, Timestamps y Texto).
        """
        if not self.speech_session_id:
            self.init_speech_session(instance_id=247115)

        qdi_xml = f"""<QDI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <QueryType>Session</QueryType>
  <DataSource>Unified</DataSource>
  <Direction>Full</Direction>
  <Fields>
    <Field xsi:type="QDIFieldExtended">
      <Values>
        <Value>{call_id}</Value>
      </Values>
      <SessionName>
        <FieldID>5</FieldID>
        <Name>CUSTOM_DATA_STRING</Name>
      </SessionName>
      <Operator>contains</Operator>
      <FieldRelation>Segment</FieldRelation>
    </Field>
  </Fields>
</QDI>"""

        self.set_filter_as_search(qdi_xml, instance_id=247115)
        contacts_res = self.get_contacts_result_set(limit=5, page=1)
        data_obj = contacts_res.get("Data", {})
        contacts_list = data_obj.get("Contacts", []) if isinstance(data_obj, dict) else []

        if not contacts_list:
            logger.warning(f"No se hallaron contactos en Verint para CONID='{call_id}'")
            return None

        contact = contacts_list[0]
        db_sid = contact.get("DbsId", 247)
        sid_val = int(contact.get("Sid") or contact.get("DocumentId") or 0)
        channel_val = contact.get("Channel", 0) or contact.get("ChannelId", 0) or 258758270
        start_time_val = contact.get("StartTime") or contact.get("StartTimeUTC") or "2026-07-16T22:04:48.977Z"

        url = f"{self.base_url}/SpeechAnalytics/Services/Transcription/TranscriptionService.svc/GetInteractionTranscription"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            headers["impact360authtoken"] = self.xsrf_token

        payload = {
            "instanceContext": {
                "InstanceId": 247115,
                "ApplicationId": "c6b76d91-5291-4928-f3ec-b97a8d2921b3"
            },
            "channel": channel_val,
            "module": 999502,
            "startTime": start_time_val,
            "localDate": start_time_val[:10] + "T00:00:00.000Z",
            "categoriesIds": [],
            "queryTerms": "",
            "editCategory": None,
            "language": "es-ES",
            "transactionId": "2157019040984375478048370989227333246",
            "docId": None,
            "isDocumentMarkingLayersRequeire": False,
            "isRedactionDisabled": False,
            "hideTranscriptionWrapperViewOn": False,
            "isOutOfSpeechContext": False,
            "dbSid": db_sid,
            "sid": sid_val,
            "redactionStatus": 0
        }

        res = self.session.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            return res.json()
        else:
            logger.error(f"Error HTTP {res.status_code} al consultar GetInteractionTranscription: {res.text[:200]}")
            return None

    def close(self):
        self.session.close()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
