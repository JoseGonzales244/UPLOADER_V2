import os
import re
import datetime
import logging
from pathlib import Path
import polars as pl

from infrastructure.database.database import (
    load_credentials,
    load_desnegret_credentials,
    connect_teradata,
    load_to_teradata
)
from infrastructure.database.sql_executor import split_sql_statements
from infrastructure.parsers.cleaners import clean_dataframe, sanitize_identifier
from ui.components import load_templates

logger = logging.getLogger(__name__)

SQL_DDL_PATH = Path(__file__).parent.parent / "sql" / "00_ddl_tcad_tables_views.sql"
SQL_DML_PATH = Path(__file__).parent.parent / "sql" / "01_dml_tcad_monthly_ingest.sql"


def calculate_period_date_range(period_str: str = None) -> tuple:
    """
    Dada una cadena de periodo YYYYMM (ej: '202608'), retorna
    (fecha_inicio, fecha_fin) en formato ISO string.
    Si no se especifica, toma el periodo del mes actual.
    """
    if not period_str:
        period_str = datetime.datetime.now().strftime("%Y%m")
        
    period_clean = period_str.strip()
    year = int(period_clean[:4])
    month = int(period_clean[4:6])

    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_date = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_date = datetime.datetime(year, month + 1, 1, 0, 0, 0)

    return (
        start_date.strftime("%Y-%m-%d %H:%M:%S"),
        end_date.strftime("%Y-%m-%d %H:%M:%S"),
    )


def get_selections_from_template(df: pl.DataFrame, template_config: dict) -> list:
    """Mapea las columnas del DataFrame según la plantilla de configuración."""
    selections = []
    for col in df.columns:
        if col in template_config:
            selections.append({
                "name": col,
                "selected": template_config[col].get('Añadir', True),
                "convert_nulls": template_config[col].get('Null:0/No Null:1', False),
                "datatype": template_config[col].get('Tipo de dato', 'VARCHAR(255)'),
                "new_name": sanitize_identifier(template_config[col].get('Nuevo nombre', col))
            })
        else:
            selections.append({
                "name": col,
                "selected": False,
                "convert_nulls": False,
                "datatype": 'VARCHAR(255)',
                "new_name": sanitize_identifier(col)
            })
    return selections


def sync_cross_tcad_from_desnegret(period_str: str = None, progress_callback=None) -> bool:
    """
    Extrae los datos de CROSS TCAD desde DLAB_DESNEGRET.TLV_TARJETAS_MATRIZ
    usando las credenciales de DESNEGRET, aplica la plantilla P026-CROSS_TCAD,
    elimina la data previa del periodo en DLAB_GEC.M_EXP_CROSS_TCAD y la carga directamente.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    if not period_str:
        period_str = datetime.datetime.now().strftime("%Y%m")

    log(f"🔄 [CROSS TCAD] Extrayendo datos de DLAB_DESNEGRET para el periodo {period_str}...", "info")
    
    con_desnegret = None
    con_gec = None
    try:
        # 1. Conexión a DESNEGRET y extracción
        creds_desnegret = load_desnegret_credentials()
        if not creds_desnegret.get("teradata_user") or not creds_desnegret.get("teradata_password"):
            log("⚠️ Credenciales de DESNEGRET no encontradas en .env (TERADATA_USER_DESNEGRET / TERADATA_PASSWORD_DESNEGRET).", "warning")
            return False

        con_desnegret = connect_teradata(
            user=creds_desnegret["teradata_user"],
            password=creds_desnegret["teradata_password"],
            host=creds_desnegret["teradata_host"],
            logmech=creds_desnegret["teradata_logmech"]
        )

        query_desnegret = f"""
        SELECT
            PERIODO,
            REG_EJECUTIVO,
            EJECUTIVO,
            INDICADOR,
            FECHA_GESTION,
            FLG_VALIDO,
            DNI
        FROM DLAB_DESNEGRET.TLV_TARJETAS_MATRIZ
        WHERE PERIODO = '{period_str}'
          AND INDICADOR IN ('TC ACTIVADA', 'CROSS TC AD')
          AND FLG_VALIDO = 1;
        """
        
        cur_d = con_desnegret.cursor()
        cur_d.execute(query_desnegret)
        columns = [desc[0] for desc in cur_d.description]
        rows = cur_d.fetchall()
        cur_d.close()

        if not rows:
            log(f"ℹ️ [CROSS TCAD] No se encontraron registros en DLAB_DESNEGRET para el periodo {period_str}.", "info")
            return True

        log(f"✓ [CROSS TCAD] {len(rows)} registros extraídos de DLAB_DESNEGRET. Procesando con plantilla P026-CROSS_TCAD...", "info")

        # 2. Convertir a Polars DataFrame y transformar con plantilla P026-CROSS_TCAD
        df_raw = pl.DataFrame(rows, schema=columns, orient="row")
        templates = load_templates()
        template_config = templates.get("P026-CROSS_TCAD", {})
        
        selections = get_selections_from_template(df_raw, template_config)
        df_clean = clean_dataframe(
            df_raw,
            selections,
            convertir_sin_acentos=True,
            transformar_varchar_latin=False,
            max_len_varchar=3000
        )

        # 3. Conexión a DLAB_GEC y Carga Idempotente
        creds_gec = load_credentials()
        con_gec = connect_teradata(
            user=creds_gec["teradata_user"],
            password=creds_gec["teradata_password"],
            host=creds_gec.get("teradata_host", "IBKTD"),
            logmech=creds_gec.get("teradata_logmech", "TD2")
        )
        con_gec.autocommit = True

        # Eliminar periodo actual en destino
        cur_g = con_gec.cursor()
        log(f"🗑️ Limpiando datos previos en DLAB_GEC.M_EXP_CROSS_TCAD para PERIODO = '{period_str}'...", "info")
        cur_g.execute(f"DELETE FROM DLAB_GEC.M_EXP_CROSS_TCAD WHERE PERIODO = '{period_str}';")
        cur_g.close()

        # Inserción en DLAB_GEC.M_EXP_CROSS_TCAD
        log(f"🚀 Insertando {len(df_clean)} registros en DLAB_GEC.M_EXP_CROSS_TCAD...", "info")
        load_to_teradata(
            con=con_gec,
            table_name="DLAB_GEC.M_EXP_CROSS_TCAD",
            df=df_clean,
            selected_columns_config=selections,
            clear_table=False,
            progress_callback=progress_callback
        )

        # Actualizar campo CODIGO
        cur_g = con_gec.cursor()
        cur_g.execute(f"""
        UPDATE DLAB_GEC.M_EXP_CROSS_TCAD
        SET CODIGO = TRIM(PERIODO) || '_' || TRIM(REG_EJECUTIVO)
        WHERE PERIODO = '{period_str}';
        """)
        cur_g.close()

        log(f"✅ [CROSS TCAD] Sincronización completada exitosamente ({len(df_clean)} registros).", "success")
        return True

    except Exception as err:
        log(f"❌ Error en sincronización de CROSS TCAD desde DESNEGRET: {err}", "error")
        logger.error(f"Error detallado en sync_cross_tcad_from_desnegret: {err}", exc_info=True)
        return False
    finally:
        if con_desnegret:
            try:
                con_desnegret.close()
            except Exception:
                pass
        if con_gec:
            try:
                con_gec.close()
            except Exception:
                pass


def run_tcad_setup(con=None, progress_callback=None) -> bool:
    """
    Ejecuta el script DDL de tablas y vistas para el reporte TCAD.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(
                user=creds["teradata_user"],
                password=creds["teradata_password"],
                host=creds.get("teradata_host", "IBKTD"),
                logmech=creds.get("teradata_logmech", "TD2")
            )
            close_con = True

        log("🚀 Ejecutando DDL de estructuras TCAD en Teradata...", "info")
        with open(SQL_DDL_PATH, "r", encoding="utf-8") as f:
            sql_text = f.read()

        statements = split_sql_statements(sql_text)
        cur = con.cursor()
        for idx, stmt in enumerate(statements, 1):
            log(f"  - Sentencia DDL {idx}/{len(statements)}", "info")
            cur.execute(stmt)
        cur.close()
        log("✅ Estructuras TCAD (tablas y vistas) creadas/actualizadas exitosamente.", "success")
        return True
    except Exception as e:
        log(f"❌ Error al ejecutar DDL TCAD: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()


def run_tcad_monthly_ingest(period_str: str = None, con=None, progress_callback=None, sync_cross: bool = True) -> bool:
    """
    Ejecuta la ingesta mensual TCAD parametrizada por el periodo (YYYYMM).
    Sincroniza automáticamente la matriz CROSS desde DESNEGRET antes de consolidar.
    """
    def log(msg, level="info"):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, level)

    if not period_str:
        period_str = datetime.datetime.now().strftime("%Y%m")

    # Paso 1: Sincronización automática de CROSS desde DLAB_DESNEGRET
    if sync_cross:
        log("⚡ Paso 1/2: Sincronizando CROSS TCAD desde DLAB_DESNEGRET...", "info")
        sync_ok = sync_cross_tcad_from_desnegret(period_str=period_str, progress_callback=progress_callback)
        if not sync_ok:
            log("⚠️ No se pudo sincronizar CROSS automáticamente. Se procederá con la data actual en tabla.", "warning")

    fecha_inicio, fecha_fin = calculate_period_date_range(period_str)
    log(f"🔄 Paso 2/2: Iniciando consolidación TCAD para periodo {period_str} [{fecha_inicio} -> {fecha_fin}]", "info")

    close_con = False
    try:
        if con is None:
            creds = load_credentials()
            con = connect_teradata(
                user=creds["teradata_user"],
                password=creds["teradata_password"],
                host=creds.get("teradata_host", "IBKTD"),
                logmech=creds.get("teradata_logmech", "TD2")
            )
            close_con = True

        with open(SQL_DML_PATH, "r", encoding="utf-8") as f:
            sql_template = f.read()

        sql_executed = sql_template.format(
            PERIODO=period_str,
            FECHA_INICIO=fecha_inicio,
            FECHA_FIN=fecha_fin,
        )

        statements = split_sql_statements(sql_executed)
        cur = con.cursor()
        for idx, stmt in enumerate(statements, 1):
            log(f"  - Sentencia DML {idx}/{len(statements)}", "info")
            cur.execute(stmt)
        cur.close()
        log(f"🎉 Ingesta y consolidación TCAD completada con éxito para el periodo {period_str}.", "success")
        return True
    except Exception as e:
        log(f"❌ Error en consolidación TCAD: {e}", "error")
        return False
    finally:
        if close_con and con:
            con.close()


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else None
    run_tcad_monthly_ingest(p)
