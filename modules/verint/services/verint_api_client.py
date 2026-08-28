import os
import time
import json
import logging
import datetime
import random
import uuid
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

        # Cargar configuración no sensible desde config.json
        verint_cfg = {}
        try:
            cfg_file = Path(__file__).resolve().parents[3] / "config" / "config.json"
            if cfg_file.exists():
                with open(cfg_file, "r", encoding="utf-8") as f:
                    verint_cfg = json.load(f).get("verint_settings", {})
        except Exception:
            pass

        self.instance_id = int(os.getenv("VERINT_INSTANCE_ID") or verint_cfg.get("instance_id", 247115))
        self.app_id = str(os.getenv("VERINT_APP_ID") or verint_cfg.get("app_id", "e9cf0296-0580-4e22-c88d-1de0258fb48b"))
        self.speech_session_id = None
        
        # --- Auto Cookie & Token Harvester (Playwright SSO headless si caché expiró) ---
        raw_cookie = os.getenv("VERINT_COOKIES") or os.getenv("VERINT_COOKIE") or os.getenv("VERINT_JSESSIONID")
        if raw_cookie:
            logger.info("🔑 Cookie manual detectada en .env. Asignando directamente...")
            for item in raw_cookie.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    k_str, v_str = k.strip(), v.strip()
                    self.session.cookies.set(k_str, v_str)
                    if k_str.lower() in ["impact360authtoken", "xsrftoken"]:
                        self.impact360_token = v_str
                        self.xsrf_token = v_str
                        self.session.headers["Impact360AuthToken"] = v_str
                        self.session.headers["impact360authtoken"] = v_str
                        self.session.headers["xsrfToken"] = v_str
                        self.session.headers["Referer"] = f"{self.base_url}/wfo/ui/"
                        self.session.headers["Origin"] = self.base_url
            self.is_authenticated = True
        elif self.username:
            try:
                harvested_cookies, token = get_verint_session(self.username, self.password or "", self.base_url)
                for name, value in harvested_cookies.items():
                    self.session.cookies.set(name, value)
                
                token = token or harvested_cookies.get("Impact360AuthToken") or harvested_cookies.get("impact360authtoken")
                if token:
                    self.impact360_token = token
                    self.xsrf_token = token
                    self.session.headers["Impact360AuthToken"] = token
                    self.session.headers["impact360authtoken"] = token
                    self.session.headers["xsrfToken"] = token
                    self.session.headers["Referer"] = f"{self.base_url}/wfo/ui/"
                    self.session.headers["Origin"] = self.base_url
                    logger.info(f"🔑 Impact360AuthToken inyectado en cabeceras: {token}")

                self.is_authenticated = True
                logger.info(f"🍪 {len(harvested_cookies)} cookies de sesión inyectadas en el cliente API.")
            except Exception as e:
                logger.warning(f"Cookie/Token Harvester falló: {e}. Se intentará login directo luego.")

    def login(self, force_refresh: bool = False) -> bool:
        """
        Garantiza que la sesión esté autenticada con cookies y token SSO validos.
        """
        if self.is_authenticated and not force_refresh:
            return True

        if not self.username:
            raise ValueError("VERINT_USER no configurado.")

        logger.info(f"Autenticando usuario SSO '{self.username}' en Verint WFO vía Harvester...")
        try:
            harvested_cookies, token = get_verint_session(self.username, self.password or "", self.base_url, force_refresh=True)
            for name, value in harvested_cookies.items():
                self.session.cookies.set(name, value)
            
            token = token or harvested_cookies.get("Impact360AuthToken") or harvested_cookies.get("impact360authtoken")
            if token:
                self.impact360_token = token
                self.xsrf_token = token
                self.session.headers["Impact360AuthToken"] = token
                self.session.headers["impact360authtoken"] = token
                self.session.headers["xsrfToken"] = token
                self.session.headers["Referer"] = f"{self.base_url}/wfo/ui/"
                self.session.headers["Origin"] = self.base_url
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
            "id": "SpeechAnalytics.model.session.ApplicationSession-2",
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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            headers["impact360authtoken"] = self.xsrf_token
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
        Aplica streaming HTTP, normalización de rutas y validación rigurosa de integridad ZIP (PK\\x03\\x04 + EOCD).
        """
        import tempfile
        import zipfile
        import urllib.parse

        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        
        report_name = report_item.get("Name", "")
        rel_url = str(report_item.get("URL", "")).strip()
        if not rel_url or rel_url.lower() in ["none", "null", ""]:
            logger.warning(f"⚠️ El reporte '{report_name}' aún no posee URL de descarga asignada ({rel_url}). Esperando a que finalice...")
            return False

        report_format = report_item.get("Format", 4)
        token = random.randint(10000, 99999)
        
        # Normalizar separadores de ruta en el parámetro url (\\ a /)
        clean_rel_url = rel_url.replace("\\", "/")
        
        params = {
            "instanceId": instance_id,
            "baseDirectory": "DataExports",
            "name": report_name,
            "reportFormat": report_format,
            "url": clean_rel_url,
            "sessionId": self.speech_session_id or "",
            "SA_downloadReportToken": token
        }
        
        download_endpoint = f"{self.base_url}/SpeechAnalytics/Handlers/Reports/DownloadReports.ashx"
        
        # Crear archivo temporal para descarga segura
        target_dir = os.path.dirname(output_filepath) or "."
        temp_fd, temp_path = tempfile.mkstemp(suffix=".tmp", dir=target_dir)
        os.close(temp_fd)

        try:
            logger.info(f"Descargando reporte '{report_name}' por API HTTP con streaming desde {download_endpoint}...")
            
            # Descarga con streaming y timeout de lectura ampliado (300s)
            with self.session.stream("GET", download_endpoint, params=params, timeout=300.0) as resp:
                if resp.status_code != 200:
                    logger.error(f"Error HTTP al descargar reporte '{report_name}' (Status {resp.status_code})")
                    return False
                
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            
            file_size = os.path.getsize(temp_path)
            if file_size < 1000:
                logger.warning(f"⚠️ Descarga de '{report_name}' retornó tamaño insuficiente ({file_size} bytes). El worker de Verint aún está escribiendo el archivo.")
                return False

            # 1. Validar Magic Bytes de Excel (.xlsx / ZIP o .xls OLE2)
            with open(temp_path, "rb") as fp:
                header = fp.read(8)
            if not (header.startswith(b"PK\x03\x04") or header.startswith(b"\xd0\xcf\x11\xe0")):
                if header.startswith(b"<!DOC") or header.startswith(b"<html") or header.startswith(b"<?xml"):
                    logger.warning(f"⚠️ El servidor de Verint devolvió una respuesta HTML/XML en lugar del Excel. Sesión expirada o archivo no listo.")
                else:
                    logger.warning(f"⚠️ El archivo descargado no posee firma binaria de Excel válida (cabecera: {header[:4]}).")
                return False

            # 2. Validar estructura completa ZIP y EOCD (End of Central Directory)
            if header.startswith(b"PK\x03\x04"):
                try:
                    with zipfile.ZipFile(temp_path, "r") as zf:
                        corrupted_file = zf.testzip()
                        if corrupted_file is not None:
                            logger.warning(f"⚠️ Archivo ZIP internamente corrupto en '{corrupted_file}'. El servidor aún no terminó de cerrarlo.")
                            return False
                except Exception as zip_err:
                    logger.warning(f"⚠️ El archivo Excel descargado está truncado o incompleto ({zip_err}). El worker de Verint todavía está escribiendo en disco. Reintentando...")
                    return False

            # 3. Todo OK: Reemplazo atómico del archivo final
            if os.path.exists(output_filepath):
                try:
                    os.remove(output_filepath)
                except Exception:
                    pass
            os.replace(temp_path, output_filepath)
            final_size = os.path.getsize(output_filepath)
            logger.info(f"✅ Archivo Excel 100% íntegro guardado exitosamente en: {output_filepath} ({final_size} bytes)")
            return True

        except Exception as dl_err:
            logger.error(f"Error durante el streaming de descarga de '{report_name}': {dl_err}")
            return False
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

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
            file_id = ""
            if res.text and res.text.strip():
                try:
                    data = res.json()
                    file_id = data.get("id", "") if isinstance(data, dict) else str(data)
                except Exception as _je:
                    logger.debug(f"UploadFileList.ashx retornó respuesta no JSON: '{res.text[:100]}'")
                    file_id = res.text.strip()
            if not file_id:
                file_id = desc_name
            logger.info(f"✅ CSV '{path_obj.name}' cargado exitosamente por HTTP. FileId: {file_id}")
            return file_id, desc_str
        logger.error(f"Error al cargar CSV por HTTP (HTTP {res.status_code}): {res.text[:500]}")
        return "", desc_str

    def set_filter_as_search(self, qdi_xml: str, instance_id: int = 247115) -> bool:
        """
        Activa y vincula el filtro QDI como la búsqueda activa en el servidor de Verint.
        """
        if not self.speech_session_id:
            self.init_speech_session(instance_id=instance_id)

        url = f"{self.base_url}/SpeechAnalytics/Services/Filter/FilterService.svc/SetFilterAsSearch"
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-requested-with": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            headers["impact360authtoken"] = self.xsrf_token
            
        payload = {
            "session": self._get_speech_session_payload(),
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
                all_parts_ready = all(
                    bool(r.get("URL")) and str(r.get("URL")).strip().lower() not in ["", "none", "null"]
                    for r in matching_reports
                )
                if all_parts_ready:
                    logger.info(f"🎯 Reporte '{report_name}' ({len(matching_reports)} parte(s)) disponible con URL en Verint. Intentando descarga e inspección de integridad...")
                    downloaded_parts = []
                    all_success = True
                    for r in matching_reports:
                        part_name = str(r.get("Name", ""))
                        out_path = Path(output_dir) / f"{part_name}.xlsx"
                        if self.download_report(r, str(out_path), instance_id=247115):
                            downloaded_parts.append(str(out_path))
                        else:
                            all_success = False
                            break
                    
                    if all_success and downloaded_parts:
                        logger.info(f"🏆 ¡Reporte '{report_name}' descargado e íntegro al 100% ({len(downloaded_parts)} parte(s))!")
                        return downloaded_parts[0] if len(downloaded_parts) == 1 else ",".join(downloaded_parts)
                    else:
                        logger.info(f"⏳ El reporte aún se está consolidando en Verint Cloud. Reintentando en {poll_interval_seconds}s...")
                else:
                    statuses = [f"{r.get('Name')}: Status={r.get('Status')}, URL={r.get('URL')}" for r in matching_reports]
                    logger.info(f"⏳ Esperando generación del reporte en Verint Cloud... Estado actual: {statuses}")
                        
            time.sleep(poll_interval_seconds)
            
        raise RuntimeError(f"Timeout de {timeout_minutes} minutos agotado esperando el reporte '{report_name}' en Verint.")
            
    def convert_to_qdi_by_call_id(self, call_id: str, days: int = 365) -> str:
        """
        Construye el XML QDI apuntando a CUSTOM_DATA_STRING (FieldID 5 / Custom Data String 5),
        donde Genesys y la ingesta de Interbank indexan el CONID / UUID de la llamada.
        """
        clean_id = str(call_id).strip()
        guid_str = str(uuid.uuid4())
        now_iso = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.0000000+00:00")
        
        return f"""<QDI xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <GUID>{guid_str}</GUID>
  <creationTime>{now_iso}</creationTime>
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
    <NumberOfReturnedRows>100</NumberOfReturnedRows>
    <TimeZone>UserTime</TimeZone>
    <AdditionalEvalInfo>NOTHING</AdditionalEvalInfo>
  </UserPreferences>
  <OrderDef>
    <From>2026-01-01T00:00:00.0000000+00:00</From>
    <To>2026-12-31T23:59:59.0000000+00:00</To>
    <OrderDefType>GREATER_LESS_EQUAL</OrderDefType>
    <RangeInDays>{days}</RangeInDays>
    <FieldRelation>Segment</FieldRelation>
    <TimeOfDayID>-1</TimeOfDayID>
  </OrderDef>
  <Fields>
    <Field xsi:type="QDIFieldExtended">
      <Values>
        <Value>{clean_id}</Value>
      </Values>
      <SessionName>
        <FieldID>5</FieldID>
        <Name>CUSTOM_DATA_STRING</Name>
      </SessionName>
      <Operator>contains</Operator>
      <FieldRelation>Segment</FieldRelation>
      <IsExtendedCustomData>true</IsExtendedCustomData>
    </Field>
  </Fields>
</QDI>"""

    def convert_to_qdi_by_switch_id(self, call_id: str, days: int = 365) -> Optional[str]:
        """
        Fallback: Invoca el endpoint oficial /Ultra/api/SearchServices/ConvertToQDI de Verint
        con el elemento SwitchCallID para PBX/Conmutador.
        """
        url = f"{self.base_url}/Ultra/api/SearchServices/ConvertToQDI"
        headers = {
            "Accept": "text/xml",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["Impact360AuthToken"] = self.xsrf_token
            headers["xsrfToken"] = self.xsrf_token

        payload = {
            "RootElements": [
                {"Id": "SearchType", "Params": {"Type": "Interactions"}},
                {"Id": "InteractionTypes", "Params": {"Calls": True, "Emails": True, "Chats": True}}
            ],
            "Sections": [
                {
                    "Id": "Metadata",
                    "Categories": [
                        {
                            "Id": "DateRange",
                            "Elements": [
                                {"Id": "DateRangeCalls", "Params": {"Type": "TheLast", "Days": days}}
                            ]
                        },
                        {
                            "Id": "Switches",
                            "Elements": [
                                {
                                    "Id": "SwitchCallID",
                                    "Params": {
                                        "Value": str(call_id).strip(),
                                        "EnableFileList": "true"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ],
            "Name": "SASearchServices"
        }

        try:
            res = self.session.post(url, json=payload, headers=headers)
            if res.status_code == 200 and res.text:
                return res.text
            logger.debug(f"ConvertToQDI SwitchCallID retornó HTTP {res.status_code}")
        except Exception as e:
            logger.debug(f"Error en ConvertToQDI SwitchCallID: {e}")
        return None

    def get_current_result_set_docs_amount(self) -> int:
        """
        Invoca ContactsService.svc/GetCurrentResultSetDocsAmount para forzar
        a Verint a compilar y contar el result set del filtro activo.
        """
        url = f"{self.base_url}/SpeechAnalytics/Services/Contacts/ContactsService.svc/GetCurrentResultSetDocsAmount"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            headers["impact360authtoken"] = self.xsrf_token

        payload = {"session": self._get_speech_session_payload()}
        try:
            res = self.session.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                res_obj = data.get("GetCurrentResultSetDocsAmountResult") or {}
                total = res_obj.get("TotalCount", 0)
                logger.info(f"   [Verint DocsAmount] Total llamadas halladas: {total}")
                return total
        except Exception as e:
            logger.error(f"Error en GetCurrentResultSetDocsAmount: {e}")
        return 0

    def select_televentas_project(self) -> bool:
        """
        Selecciona y activa el proyecto 'Televentas' en Verint llamando a ConvertToLDFO
        (Paso 1 exacto de la interfaz web).
        """
        url = f"{self.base_url}/Ultra/api/SearchServices/ConvertToLDFO?templateName=SALeftPaneFacadeOldIFA"
        headers = {
            "Accept": "*/*",
            "Content-Type": "text/plain",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["xsrfToken"] = self.xsrf_token
            headers["impact360authtoken"] = self.xsrf_token

        qdi_xml = """<QDI xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <GUID>00000000-0000-0000-0000-000000000000</GUID>
  <creationTime>2026-08-20T04:02:00.0000000+00:00</creationTime>
  <MajorVersion>0</MajorVersion>
  <MinorVersion>0</MinorVersion>
  <QueryType>Session</QueryType>
  <DataSource>CentralContact</DataSource>
  <Direction>Relative_range</Direction>
  <Security>
    <UserId>2</UserId>
    <IsAgentQuery>false</IsAgentQuery>
    <World>IFind</World>
  </Security>
  <UserPreferences>
    <NumberOfReturnedRows>100</NumberOfReturnedRows>
    <TimeZone>UserTime</TimeZone>
    <AdditionalEvalInfo>NOTHING</AdditionalEvalInfo>
  </UserPreferences>
  <OrderDef>
    <From>0001-01-01T00:00:00.0000000+00:00</From>
    <To>0001-01-01T00:00:00.0000000+00:00</To>
    <RefFrom>0001-01-01T00:00:00.0000000-00:00</RefFrom>
    <RefTo>0001-01-01T00:00:00.0000000-00:00</RefTo>
    <OrderDefType>GREATER_LESS_EQUAL</OrderDefType>
    <RangeInDays>180</RangeInDays>
    <FieldRelation>Segment</FieldRelation>
    <TimeOfDayID>-1</TimeOfDayID>
  </OrderDef>
  <Fields />
  <ComplexFields />
  <Random>
    <IsRandom>false</IsRandom>
    <PickRowOutOfEvery>10</PickRowOutOfEvery>
  </Random>
</QDI>"""
        try:
            res = self.session.post(url, content=qdi_xml, headers=headers)
            if res.status_code == 200:
                logger.info("✓ Proyecto 'Televentas' seleccionado en Verint.")
                return True
        except Exception as e:
            logger.error(f"Error seleccionando proyecto Televentas: {e}")
        return False

    def get_interaction_transcription_api(self, call_id: str, instance_id: int = 247115) -> Optional[Dict[str, Any]]:
        """
        Obtiene la transcripción JSON real de una llamada por su ID de llamada (SWITCH_CALL_ID / CONID)
        siguiendo el flujo 100% nativo de Verint Speech Analytics:
        1. Construye el QDI de búsqueda en Speech Analytics (CentralContact / IFind / SWITCH_CALL_ID).
        2. Aplica el filtro con ConvertToLDFO y SetFilterAsSearch en la sesión activa.
        3. Obtiene el resultado con GetContactsResultSet. Si no hay contactos, retorna None (sin duplicar).
        4. Invoca GetContactPlayerData para obtener el Channel, StartTime exacto y CategoriesIds.
        5. Invoca GetInteractionTranscription para descargar todos los turnos del diálogo.
        """
        clean_cid = str(call_id).strip()
        if not self.speech_session_id:
            if not self.init_speech_session(instance_id=instance_id):
                logger.warning(f"No se pudo inicializar sesión en Verint para call_id={clean_cid}")
                return None
            self.select_televentas_project()

        # 1. XML QDI para Speech Analytics (Televentas)
        qdi_speech = f"""<QDI xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <GUID>00000000-0000-0000-0000-000000000000</GUID>
  <creationTime>2026-08-20T04:02:00.0000000+00:00</creationTime>
  <MajorVersion>0</MajorVersion>
  <MinorVersion>0</MinorVersion>
  <QueryType>Session</QueryType>
  <DataSource>CentralContact</DataSource>
  <Direction>Relative_range</Direction>
  <Security>
    <UserId>2</UserId>
    <IsAgentQuery>false</IsAgentQuery>
    <World>IFind</World>
  </Security>
  <UserPreferences>
    <NumberOfReturnedRows>100</NumberOfReturnedRows>
    <TimeZone>UserTime</TimeZone>
    <AdditionalEvalInfo>NOTHING</AdditionalEvalInfo>
  </UserPreferences>
  <OrderDef>
    <From>0001-01-01T00:00:00.0000000+00:00</From>
    <To>0001-01-01T00:00:00.0000000+00:00</To>
    <RefFrom>0001-01-01T00:00:00.0000000-00:00</RefFrom>
    <RefTo>0001-01-01T00:00:00.0000000-00:00</RefTo>
    <OrderDefType>GREATER_LESS_EQUAL</OrderDefType>
    <RangeInDays>365</RangeInDays>
    <FieldRelation>Segment</FieldRelation>
    <TimeOfDayID>-1</TimeOfDayID>
  </OrderDef>
  <Fields>
    <Field>
      <Values>
        <Value>{clean_cid}</Value>
      </Values>
      <SessionName>
        <FieldID>0</FieldID>
        <Name>SWITCH_CALL_ID</Name>
      </SessionName>
      <Operator>equal</Operator>
      <FieldRelation>Segment</FieldRelation>
    </Field>
  </Fields>
  <ComplexFields />
  <Random>
    <IsRandom>false</IsRandom>
    <PickRowOutOfEvery>10</PickRowOutOfEvery>
  </Random>
</QDI>"""

        # 2. Aplicar en Speech Analytics
        url_ldfo = f"{self.base_url}/Ultra/api/SearchServices/ConvertToLDFO?templateName=SALeftPaneFacadeOldIFA"
        headers_ldfo = {
            "Accept": "*/*",
            "Content-Type": "text/plain",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers_ldfo["Impact360AuthToken"] = self.xsrf_token
            headers_ldfo["xsrfToken"] = self.xsrf_token

        try:
            self.session.post(url_ldfo, content=qdi_speech, headers=headers_ldfo)
        except Exception as e:
            logger.debug(f"Error en ConvertToLDFO: {e}")

        if not self.set_filter_as_search(qdi_speech, instance_id=instance_id):
            logger.warning(f"No se pudo vincular la búsqueda en Verint para SWITCH_CALL_ID='{clean_cid}'")
            return None

        # 3. Obtener contactos filtrados
        c_res = self.get_contacts_result_set(limit=5, page=1)
        data_obj = c_res.get("Data") or {}
        contacts = data_obj.get("Contacts") or []

        if not contacts:
            logger.warning(f"⚠️ Verint no devolvió contactos para SWITCH_CALL_ID='{clean_cid}'.")
            return None

        contact = contacts[0]
        sid = int(contact.get("SID") or contact.get("Sid") or contact.get("DocumentId") or 0)
        dbs_id = contact.get("DbsId", 247)
        agent_name = contact.get("Agent", "Desconocido")
        local_time_str = contact.get("LocalStartTime", "")

        logger.info(f"   ✓ Interacción localizada: Asesor='{agent_name}', Fecha={local_time_str}, SID={sid}")

        # 4. Obtener metadatos de audio exactos (GetContactPlayerData)
        headers_json = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers_json["impact360authtoken"] = self.xsrf_token
            headers_json["xsrfToken"] = self.xsrf_token

        url_player = f"{self.base_url}/SpeechAnalytics/Services/Contacts/ContactsService.svc/GetContactPlayerData"
        player_payload = {
            "session": self._get_speech_session_payload(),
            "corpusId": contact.get("CorpusId", 60),
            "docId": str(contact.get("DocumentId")),
            "sid": sid,
            "dbsId": dbs_id,
            "playerContext": 0
        }
        
        try:
            res_p = self.session.post(url_player, json=player_payload, headers=headers_json)
            player_data = res_p.json().get("GetContactPlayerDataResult", {}).get("Data", {}) if res_p.status_code == 200 else {}
        except Exception:
            player_data = {}

        start_ms = player_data.get("StartTime") or contact.get("RealStartTime")
        if start_ms:
            dt = datetime.datetime.fromtimestamp(start_ms / 1000.0, datetime.timezone.utc)
            start_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            local_iso = dt.strftime("%Y-%m-%d") + "T00:00:00.000Z"
        else:
            start_iso = "2026-04-29T17:04:22.820Z"
            local_iso = "2026-04-29T00:00:00.000Z"

        channel_val = player_data.get("Channel") or contact.get("Channel") or 170909957
        cat_ids = player_data.get("CategoriesIds") or []

        # 5. Descargar transcripción (GetInteractionTranscription)
        url_trans = f"{self.base_url}/SpeechAnalytics/Services/Transcription/TranscriptionService.svc/GetInteractionTranscription"
        payload_trans = {
            "instanceContext": {
                "InstanceId": str(instance_id),
                "ApplicationId": self.app_id or "2b0890f2-2473-4954-d6a9-dd29ca588b82"
            },
            "channel": channel_val,
            "module": 999502,
            "startTime": start_iso,
            "localDate": local_iso,
            "categoriesIds": cat_ids,
            "queryTerms": "",
            "editCategory": None,
            "language": "es-ES",
            "transactionId": "2148850615328041750352251102220509445",
            "docId": None,
            "isDocumentMarkingLayersRequeire": False,
            "isRedactionDisabled": False,
            "hideTranscriptionWrapperViewOn": False,
            "isOutOfSpeechContext": False,
            "dbSid": dbs_id,
            "sid": sid,
            "redactionStatus": 0
        }

        try:
            res_t = self.session.post(url_trans, json=payload_trans, headers=headers_json)
            if res_t.status_code == 200:
                res_data = res_t.json()
                trans_res = res_data.get("GetInteractionTranscriptionResult") or {}
                if trans_res.get("Success"):
                    return res_data
                else:
                    err_msg = trans_res.get("ErrorDetails", {}).get("LocalizedMessageKey")
                    logger.warning(f"Verint GetInteractionTranscription devolvió Success=False ({err_msg}) para SID={sid}")
            else:
                logger.error(f"Error HTTP {res_t.status_code} en GetInteractionTranscription: {res_t.text[:200]}")
        except Exception as e_post:
            logger.error(f"Excepción en GetInteractionTranscription: {e_post}")
        return None

    @staticmethod
    def format_dialogue(res_data: Optional[Dict[str, Any]]) -> str:
        """
        Formatea la respuesta JSON de GetInteractionTranscription a texto con minutaje:
        [mm:ss] Asesor/Cliente: Diálogo
        """
        if not res_data or not isinstance(res_data, dict):
            return ""
        result_obj = res_data.get("GetInteractionTranscriptionResult") or {}
        data_trans = result_obj.get("Data") or {}
        sequences = data_trans.get("WordsSequences") or []
        lines = []
        for seq in sequences:
            if not isinstance(seq, dict):
                continue
            speaker_raw = seq.get("SpeakerName", "")
            speaker = "Asesor" if speaker_raw == "Agent" else ("Cliente" if speaker_raw == "Customer" else (speaker_raw or "Interlocutor"))
            start_ms = seq.get("StartTime", 0)
            total_sec = int(start_ms) // 1000
            mins = total_sec // 60
            secs = total_sec % 60
            ts_str = f"{mins:02d}:{secs:02d}"
            words = " ".join([w.get("WordText", "") for w in seq.get("Words", []) if isinstance(w, dict) and w.get("WordText")]).strip()
            if words:
                lines.append(f"[{ts_str}] {speaker}: {words}")
        return "\n".join(lines)

    def close(self):
        self.session.close()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
