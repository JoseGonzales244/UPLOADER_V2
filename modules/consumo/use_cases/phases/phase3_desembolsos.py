"""
Fase 3 — Consumo: Extracción de Desembolsos desde SQL Server.

Extrae BN_DESEMBOLSOS_GENERAL desde SQL Server, transforma con Polars
y carga en DLAB_GEC.T_VENTAS_BPE_MARKET en Teradata.
"""
from __future__ import annotations

import os
import logging
import polars as pl

from infrastructure.database.database import load_to_teradata

logger = logging.getLogger(__name__)


def run_phase3(ctx) -> bool:
    """
    Fase 3 Consumo: Extracción de desembolsos de SQL Server e ingesta en Teradata.
    Omite silenciosamente si SQLSERVER_SERVER no está configurado en .env.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    sql_server = os.getenv("SQLSERVER_SERVER")
    if not sql_server or sql_server == "tu_servidor_sql":
        msg_skip = "ℹ️ Fase 3: Credenciales de SQL Server no configuradas en .env. Omitiendo extracción de desembolsos."
        logger.info(msg_skip)
        log(msg_skip, "info")
        return True

    log("📡 Fase 3: Obteniendo información de desembolsos y ventas...", "info")

    try:
        import pyodbc

        sql_database = os.getenv("SQLSERVER_DATABASE")
        sql_user = os.getenv("SQLSERVER_USER")
        sql_password = os.getenv("SQLSERVER_PASSWORD")
        sql_driver = os.getenv("SQLSERVER_DRIVER", "{ODBC Driver 17 for SQL Server}")

        if sql_user and sql_password and sql_user != "tu_usuario":
            conn_str = f"DRIVER={sql_driver};SERVER={sql_server};DATABASE={sql_database};UID={sql_user};PWD={sql_password}"
        else:
            conn_str = f"DRIVER={sql_driver};SERVER={sql_server};DATABASE={sql_database};Trusted_Connection=yes;"

        sql_conn = pyodbc.connect(conn_str)
        periodo_num = int(ctx.period_str)
        query = f"SELECT * FROM BN_DESEMBOLSOS_GENERAL WHERE periodo >= {periodo_num}"

        df_desemb = pl.read_database(query=query, connection=sql_conn)
        sql_conn.close()
        logger.info(f"Extracted {len(df_desemb)} records from SQL Server.")
        log(f"📥 Se obtuvieron {len(df_desemb):,} registros de desembolsos.", "info")

        df_desemb_clean = df_desemb.with_columns([
            pl.col("COD_DOC").alias("CODDOC"),
            pl.col("CLIENTE").alias("REPRESENTANTE_LEGAL"),
            pl.col("CAMPANA_VPC").alias("CAMPANA_N2"),
            pl.col("REG_EJECUTIVO").str.slice(0, 8).alias("REGISTRO"),
            pl.when(pl.col("NUM_RUC").cast(pl.Utf8).str.strip_chars().str.len_chars() == 8).then(pl.lit("PN"))
            .when(pl.col("NUM_RUC").cast(pl.Utf8).str.strip_chars().str.len_chars() == 11).then(pl.lit("PJ"))
            .otherwise(pl.lit("DESCONOCIDO"))
            .alias("TIPO_PERSONA")
        ]).select([
            "FECHA_DESEMBOLSADO", "COD_UNICO", "CODDOC", "REPRESENTANTE_LEGAL",
            "TIPO_PERSONA", "CANAL", "REGISTRO", "NOM_EJECUTIVO",
            "COLOCACION_NETA", "CAMPANA_N2"
        ])

        selections_desemb = [
            {
                "name": col, "selected": True, "convert_nulls": False,
                "datatype": "VARCHAR(50)" if col in ("REGISTRO", "TIPO_PERSONA") else "VARCHAR(255)",
                "new_name": col
            }
            for col in df_desemb_clean.columns
        ]

        load_to_teradata(
            con=ctx.td_con, table_name="DLAB_GEC.T_VENTAS_BPE_MARKET",
            df=df_desemb_clean, selected_columns_config=selections_desemb,
            clear_table=True, progress_callback=ctx.progress_callback
        )

        with ctx.td_con.cursor() as cursor:
            cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET SET EVALUADO = 'NO'")
            cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET FROM DLAB_GEC.M_EXP_DOCUMENTOS_EVALUADOS B SET EVALUADO = 'SI' WHERE CODDOC = B.DOCUMENTO")
            cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET SET FECHA_UPDATE = CURRENT_TIMESTAMP(0)")

        logger.info("Updated EVALUADO and FECHA_UPDATE flags in T_VENTAS_BPE_MARKET.")
        log("✅ Fase 3 completada exitosamente.", "success")

    except Exception as desemb_err:
        logger.error(f"Error extracting desembolsos from SQL Server: {desemb_err}")
        log(f"⚠️ No se pudo obtener desembolsos de SQL Server: {desemb_err}", "warning")

    return True
