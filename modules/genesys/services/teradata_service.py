from datetime import datetime
from typing import List

from modules.genesys.config import (
    TERADATA_HOST,
    TERADATA_LOGMECH,
    TERADATA_PASSWORD,
    TERADATA_USER,
)
from modules.genesys.logger import get_logger
from modules.genesys.models import SolicitudAudio
from modules.genesys.storage.phone_cache_store import PhoneCacheStore

logger = get_logger("TeradataService")


class TeradataService:
    def __init__(self, cache_store: PhoneCacheStore = None):
        self.cache_store = cache_store or PhoneCacheStore()

    def enriquecer_solicitudes(self, solicitudes: List[SolicitudAudio]) -> List[SolicitudAudio]:
        if not solicitudes:
            return []

        # Cargar el caché y purgar cualquier entrada vacía previa
        raw_cache = self.cache_store.cargar()
        cache = {k: v for k, v in raw_cache.items() if v}

        dnis_pedidos = [sol.dni for sol in solicitudes]
        dnis_faltantes = [d for d in dnis_pedidos if not cache.get(str(d).strip()) and not cache.get(str(d).strip().zfill(8))]

        if dnis_faltantes:
            if not TERADATA_USER or not TERADATA_PASSWORD:
                logger.warning("Faltan credenciales Teradata en .env. Usando únicamente el caché local disponible.")
            else:
                try:
                    import teradatasql
                    logger.info(f"Consultando Teradata para {len(dnis_faltantes)} DNI(s) faltantes...")

                    for dni in dnis_faltantes:
                        dni_zero = str(dni).strip().zfill(8)

                        query = f"""
                            SELECT DISTINCT NUMTELEFONO
                            FROM E_DW_VIEWS.V_CONT_TELEFONO_APICLIENTE
                            WHERE CODDOC = '{dni_zero}'
                              AND NUMTELEFONO IS NOT NULL
                        """

                        try:
                            with teradatasql.connect(
                                host=TERADATA_HOST,
                                user=TERADATA_USER,
                                password=TERADATA_PASSWORD,
                                logmech=TERADATA_LOGMECH,
                            ) as con:
                                cur = con.cursor()
                                cur.execute(query)
                                raw_rows = cur.fetchall()

                                telefonos = []
                                for r in raw_rows:
                                    if r[0]:
                                        clean_num = re.sub(r"\D", "", str(r[0]))
                                        if len(clean_num) >= 7:
                                            telefonos.append(clean_num)

                                if telefonos:
                                    telefonos = list(dict.fromkeys(telefonos))
                                    cache[str(dni).strip()] = telefonos
                                    cache[dni_zero] = telefonos
                        except Exception as e:
                            logger.error(f"Error consultando Teradata para DNI {dni}: {e}")

                    self.cache_store.guardar(cache)
                    logger.info(f"Caché de teléfonos actualizado atómicamente.")
                except ImportError:
                    logger.error("La librería 'teradatasql' no está instalada. No se pudo consultar Teradata.")

        enriquecidas: List[SolicitudAudio] = []
        for sol in solicitudes:
            sol_dni_str = str(sol.dni).strip()
            telefonos = cache.get(sol_dni_str) or cache.get(sol_dni_str.zfill(8)) or []
            if telefonos:
                sol.telefonos = telefonos
                enriquecidas.append(sol)
            else:
                logger.info(f"[SKIP] {sol.reg_ev} | DNI {sol.dni} sin teléfonos en caché/Teradata.")

        logger.info(f"Solicitudes listas con teléfono: {len(enriquecidas)} de {len(solicitudes)}")
        return enriquecidas
