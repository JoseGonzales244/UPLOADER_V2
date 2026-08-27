import os
import time
import logging
from typing import List, Dict, Optional
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("InsightLeadService")



class InsightLeadService:
    """
    Servicio para calcular dinámicamente el TIPO_LEAD de interacciones
    consultando el backend de Insight (Genesys session_summary).
    """
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        load_dotenv()
        self.username = username or os.getenv("USERNAME_INSIGHT")
        self.password = password or os.getenv("PASSWORD_INSIGHT")
        self.base_url = "https://s425vp01/Insight"
        self.session = requests.Session()

    def _login(self) -> bool:
        if not self.username or not self.password:
            raise ValueError("Credenciales de Insight faltantes (USERNAME_INSIGHT / PASSWORD_INSIGHT).")

        logger.info(f"Iniciando sesión en Insight ({self.base_url}) para usuario '{self.username}'...")
        resp = self.session.post(
            self.base_url,
            data={"registro": self.username, "password": self.password},
            verify=False,
            timeout=30
        )
        if resp.status_code == 200:
            logger.info("✓ Sesión iniciada exitosamente en Insight.")
            return True
        else:
            raise RuntimeError(f"Error al iniciar sesión en Insight: Status {resp.status_code}")

    def _build_query_sql(self, conversation_ids: List[str], min_date: str = "2026-07-01") -> str:
        """Construye el SQL dinámico de #BASE y #HISTORICO para calcular TIPO_LEAD."""
        formatted_ids = ", ".join(f"'{cid.strip()}'" for cid in conversation_ids if cid.strip())

        query_sql = f"""
-- BASE POR ID
SELECT *
INTO #BASE
FROM session_summary WITH(NOLOCK)
WHERE purpose = 'AGENT'
  AND queueName LIKE 'TLV_%'
  AND conversationID IN ({formatted_ids});

-- BÚSQUEDA HISTÓRICA POR NRO DE TELÉFONO
SELECT *
INTO #HISTORICO
FROM session_summary WITH(NOLOCK)
WHERE purpose = 'AGENT'
  AND sessionIndex <> '1'
  AND queueName LIKE 'TLV_%'
  AND originatingDnis IN (
      SELECT DISTINCT originatingDnis
      FROM #BASE
      WHERE sessionIndex = '1'
        AND ISNULL(originatingDnis, '') <> ''
  )
  AND sessionStartTime >= '{min_date}';

-- CRUCE FINAL
SELECT 
    s.conversationID,
    CASE 
        WHEN s.sessionIndex = '1' THEN 
            CASE 
                WHEN prev.queueName IN ('TLV_TC','TLV_TC2') THEN 'MANUAL_OUTBOUND'
                WHEN prev.queueName LIKE 'TLV_RESCATE_%' THEN 'MANUAL_RESCATE_DIGITAL'
                WHEN prev.queueName LIKE 'TLV_DERIVA_%' THEN 'MANUAL_INBOUND'
                ELSE 'MANUAL_NO_MAPEADO'
            END
        WHEN s.sessionIndex <> '1' AND s.queueName IN ('TLV_TC','TLV_TC2') THEN 'OUTBOUND'
        WHEN s.sessionIndex <> '1' AND s.queueName LIKE 'TLV_RESCATE_%' THEN 'RESCATE_DIGITAL'
        WHEN s.sessionIndex <> '1' AND s.queueName LIKE 'TLV_DERIVA_%' THEN 'INBOUND'
        ELSE 'NO_MAPEADO'
    END AS TIPO_LEAD
FROM #BASE s
OUTER APPLY(
    SELECT TOP 1 h.queueName
    FROM #HISTORICO h
    WHERE h.originatingDnis = s.originatingDnis
      AND h.sessionStartTime < s.sessionStartTime
    ORDER BY h.sessionStartTime DESC
) prev;
"""
        return query_sql

    def get_tipos_lead_batch(
        self,
        conversation_ids: List[str],
        min_date: str = "2026-07-01",
        chunk_size: int = 500
    ) -> Dict[str, str]:
        """
        Ejecuta la consulta por lotes en Insight y retorna un diccionario {conversationID: TIPO_LEAD}.
        """
        if not conversation_ids:
            return {}

        self._login()
        lead_mapping: Dict[str, str] = {}

        unique_ids = list(dict.fromkeys(conversation_ids))
        total_batches = (len(unique_ids) + chunk_size - 1) // chunk_size

        for i in range(0, len(unique_ids), chunk_size):
            batch_ids = unique_ids[i:i + chunk_size]
            batch_num = (i // chunk_size) + 1
            logger.info(f"Procesando lote {batch_num}/{total_batches} ({len(batch_ids)} IDs) en Insight...")

            query_sql = self._build_query_sql(batch_ids, min_date=min_date)

            # 1. Enviar consulta para ejecución asíncrona
            exec_url = f"{self.base_url}/api/Insight/executeQuery"
            payload = {
                "queryDelimiter": "\t",
                "query": query_sql,
                "areaId": "GCI_PRD_Insight_TLVentas"
            }

            resp_exec = self.session.post(exec_url, json=payload, verify=False, timeout=60)
            if resp_exec.status_code != 200:
                logger.error(f"Error enviando consulta a Insight: {resp_exec.status_code} - {resp_exec.text[:300]}")
                continue

            data_json = resp_exec.json()
            file_id = data_json.get("data", {}).get("nomArchivo")
            if not file_id:
                logger.error(f"Insight no retornó 'nomArchivo': {data_json}")
                continue

            # 2. Polling hasta que el archivo esté listo
            export_url = f"{self.base_url}/api/Insight/exportData?fileId={file_id}"
            file_url = None
            for attempt in range(25):
                resp_export = self.session.get(export_url, verify=False, timeout=30)
                if resp_export.status_code == 200:
                    exp_data = resp_export.json()
                    if exp_data.get("data") and exp_data["data"].get("fileSource"):
                        file_url = exp_data["data"]["fileSource"]
                        break
                time.sleep(3)

            if not file_url:
                logger.error(f"Tiempo de espera agotado esperando archivo {file_id} en Insight.")
                continue

            # 3. Descargar y parsear el TSV de resultados
            resp_file = self.session.get(file_url, verify=False, timeout=60)
            if resp_file.status_code != 200:
                logger.error(f"Error descargando TSV desde {file_url}: {resp_file.status_code}")
                continue

            lines = resp_file.text.splitlines()
            if len(lines) <= 1:
                logger.warning(f"Lote {batch_num} retornó 0 filas de datos.")
                continue

            # Parsear cabecera y filas (separado por tabulación)
            header = [h.strip() for h in lines[0].split("\t")]
            try:
                idx_conv = header.index("conversationID") if "conversationID" in header else 0
                idx_lead = header.index("TIPO_LEAD") if "TIPO_LEAD" in header else 1
            except ValueError:
                idx_conv, idx_lead = 0, 1

            batch_count = 0
            for line in lines[1:]:
                parts = line.split("\t")
                if len(parts) > max(idx_conv, idx_lead):
                    c_id = parts[idx_conv].strip()
                    t_lead = parts[idx_lead].strip()
                    if c_id:
                        lead_mapping[c_id] = t_lead
                        batch_count += 1

            logger.info(f"✓ Lote {batch_num}/{total_batches}: {batch_count} tipos de lead obtenidos.")

        logger.info(f"✅ Total TIPO_LEAD mapeados desde Insight: {len(lead_mapping)}/{len(unique_ids)}")
        return lead_mapping
