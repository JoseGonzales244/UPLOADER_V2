"""
Módulo Orquestador de Consumo:
Orquesta las 5 Fases del Proceso de Consumo (Insight, CD40K, SQL Server, Pipelines SQL Teradata y Selección).
Registra el detalle técnico completo en logs/app.log y emite mensajes ejecutivos amigables para el usuario en la UI.
"""
import os
import re
import shutil
import datetime
import logging
import subprocess
import glob
import polars as pl
from pathlib import Path
from core.Insight_downloader import download_insight_data
from core.cleaners import clean_dataframe, sanitize_identifier
from core.database import load_credentials, connect_teradata, load_to_teradata, check_table_exists
from core.logging_config import setup_logging
from ui.components import load_templates

# Configurar logger técnico para el proceso de Consumo
logger = setup_logging("core.orchestrator", log_prefix="consumo")

# Insumos configuration mapping
INSUMOS_CONFIG = {
    "TRAFICO_GENESYS": {
        "query_name": "TRAFICO_GENESYS",
        "template_key": "P009-INSIGHT_01_TRAFICO_GENESYS",
        "tables": ["DLAB_GEC.M_EXP_TRAFICO_GENESIS"],
        "nombre_ejecutivo": "Tráfico Genesys"
    },
    "CONV_ATTRIBUTES": {
        "query_name": "CONV_ATTRIBUTES",
        "template_key": "P010-INSIGHT_02_CONV_ATTRIBUTES",
        "tables": ["DLAB_GEC.M_EXP_BT_CONVERSATIONS_ATTRIBUTES"],
        "nombre_ejecutivo": "Atributos de Conversaciones"
    },
    "DERIVA_BT": {
        "query_name": "DERIVA_BT",
        "template_key": "P011-INSIGHT_03_DERIVA_BT",
        "tables": ["DLAB_GEC.M_EXP_DERIVA_BT_TIEMPOS"],
        "nombre_ejecutivo": "Tiempos de Derivación"
    },
    "CLOUD_MARCA_TRANSF": {
        "query_name": "CLOUD_MARCA_TRANSF",
        "template_key": "P012-INSIGHT_04_CLOUD_MARCA_TRANSF",
        "tables": ["DLAB_GEC.M_EXP_CO_CLOUD_MARCA_TRASNFERENCIA_PRE"],
        "nombre_ejecutivo": "Marcas de Transferencia"
    },
    "BT_TRANSFERENCIA": {
        "query_name": "BT_TRANSFERENCIA",
        "template_key": "P013-INSIGHT_05_BT_TRANSFERENCIA",
        "tables": ["DLAB_GEC.M_DERIVA_BT_EV_TRANSFERENCIA"],
        "nombre_ejecutivo": "Evaluación de Transferencias"
    },
    "IVR_VENTAS": {
        "query_name": "IVR_VENTAS",
        "template_key": "P014-INSIGHT_06_IVR_VENTAS",
        "tables": ["DLAB_GEC.M_EXP_IVR_VENTAS_2022"],
        "nombre_ejecutivo": "Ventas IVR"
    },
    "EVALUATIONS": {
        "query_name": "EVALUATIONS",
        "template_key": "P008-INSIGHT_07_EVALUATIONS",
        "tables": ["DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE"],
        "nombre_ejecutivo": "Evaluaciones de Calidad"
    }
}

def get_selections_from_template(df, template_config):
    """Maps DataFrame columns using the template configuration."""
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

def run_orchestration_flow(
    insight_user, insight_password, td_user, td_password, period_str, 
    clear_consent=False, progress_callback=None,
    run_phase1=True, run_phase2=True, run_phase3=True, run_phase4=True, run_phase5=True,
    start_from_script=None
):
    """
    Ejecuta el flujo de orquestación de Consumo en 5 Fases:
    Fase 1: Descarga e Ingesta de Insumos de Insight
    Fase 2: Carga Manual CD40K
    Fase 3: Extracción de Desembolsos
    Fase 4: Consolidación SQL de Consumo
    Fase 5: Transformación de Selección
    """
    logger.info(f"=== INICIANDO PROCESO DE CONSUMO PARA EL PERÍODO {period_str} ===")
    
    templates = load_templates()
    credenciales = load_credentials()
    host = credenciales.get('teradata_host', 'IBKTD')
    logmech = credenciales.get('teradata_logmech', 'TD2')
    
    INPUT_BASE_CONSUMO_DIR = os.path.join(os.getcwd(), "data", "input", "base_consumo")
    os.makedirs(INPUT_BASE_CONSUMO_DIR, exist_ok=True)
 
    downloaded_files = {}
    
    # ----------------------------------------------------
    # FASE 1: DESCARGA DE INSIGHT
    # ----------------------------------------------------
    if run_phase1:
        msg_user = "📥 Fase 1: Descargando fuentes de información de Insight..."
        logger.info(msg_user)
        if progress_callback:
            progress_callback(msg_user, "info")
     
        for insumo_key, conf in INSUMOS_CONFIG.items():
            q_name = conf["query_name"]
            n_ejecutivo = conf["nombre_ejecutivo"]
            
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            expected_filename = f"Reporte_Insight_{q_name}_{today_str}.txt"
            expected_path = os.path.join(INPUT_BASE_CONSUMO_DIR, expected_filename)
            
            if os.path.exists(expected_path) and os.path.getsize(expected_path) > 0:
                msg_local = f"ℹ️ Archivo local encontrado para {n_ejecutivo}. Se usará la copia guardada de hoy."
                logger.info(f"Insight file exists locally: {expected_path}")
                if progress_callback:
                    progress_callback(msg_local, "info")
                downloaded_files[insumo_key] = expected_path
                continue
                
            msg_dl = f"📡 Descargando insumo: {n_ejecutivo}..."
            logger.info(f"Downloading Insight query '{q_name}'...")
            if progress_callback:
                progress_callback(msg_dl, "info")
                
            try:
                local_path = download_insight_data(
                    query_name=q_name,
                    username=insight_user,
                    password=insight_password,
                    progress_callback=progress_callback,
                    output_dir=INPUT_BASE_CONSUMO_DIR
                )
                downloaded_files[insumo_key] = local_path
                logger.info(f"Downloaded Insight insumo '{q_name}' successfully: {local_path}")
            except Exception as err:
                msg_err = f"⚠️ No se pudo descargar el insumo '{n_ejecutivo}'. Se continuará con los datos disponibles."
                logger.warning(f"Failed to download Insight insumo '{q_name}': {err}")
                if progress_callback:
                    progress_callback(msg_err, "warning")

    # Conectar a Teradata
    con = None
    if run_phase1 or run_phase2 or run_phase3 or run_phase4:
        msg_conn = "⚡ Estableciendo conexión segura con Teradata..."
        logger.info(f"Connecting to Teradata (Host: {host}, User: {td_user})...")
        if progress_callback:
            progress_callback(msg_conn, "info")
            
        try:
            con = connect_teradata(td_user, td_password, host=host, logmech=logmech)
            con.autocommit = True
            logger.info("Conexión con Teradata establecida correctamente.")
        except Exception as err:
            logger.error(f"Error crítico al conectar con Teradata: {err}")
            raise RuntimeError(f"Error de conexión con Teradata: {err}")
            
    try:
        # ----------------------------------------------------
        # FASE 1 (CONTINUACIÓN): INGESTA A TERADATA
        # ----------------------------------------------------
        if run_phase1 and con:
            for insumo_key, conf in INSUMOS_CONFIG.items():
                q_name = conf["query_name"]
                t_key = conf["template_key"]
                tables = conf["tables"]
                n_ejecutivo = conf["nombre_ejecutivo"]
                
                local_path = downloaded_files.get(insumo_key)
                if not local_path or not os.path.exists(local_path):
                    matching_files = glob.glob(os.path.join(INPUT_BASE_CONSUMO_DIR, f"Reporte_Insight_{q_name}_*.txt"))
                    if matching_files:
                        local_path = sorted(matching_files)[-1]
                    
                if not local_path or not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                    msg_warn = f"⚠️ Omitiendo la ingesta de '{n_ejecutivo}' por no contar con archivo válido."
                    logger.warning(f"Skipping table load for '{q_name}': file missing or empty.")
                    if progress_callback:
                        progress_callback(msg_warn, "warning")
                    continue
                    
                msg_clean = f"🧹 Procesando y limpiando datos de {n_ejecutivo}..."
                logger.info(f"Cleaning dataframe for '{q_name}' from path {local_path}...")
                if progress_callback:
                    progress_callback(msg_clean, "info")
                    
                df = pl.read_csv(local_path, separator='\t', infer_schema_length=0, truncate_ragged_lines=True)
                
                if df.is_empty():
                    logger.warning(f"File '{local_path}' is empty. Skipping load.")
                    continue
                
                template_config = templates.get(t_key, {})
                selections = get_selections_from_template(df, template_config)
                
                df_clean = clean_dataframe(
                    df,
                    selections,
                    convertir_sin_acentos=True,
                    transformar_varchar_latin=False,
                    max_len_varchar=3000
                )
                
                for table_name in tables:
                    msg_upload = f"🚀 Actualizando base de datos para {n_ejecutivo}..."
                    logger.info(f"Loading Polars dataframe ({len(df_clean)} rows) to Teradata table '{table_name}'...")
                    if progress_callback:
                        progress_callback(msg_upload, "info")
                    
                    load_to_teradata(
                        con=con,
                        table_name=table_name,
                        df=df_clean,
                        selected_columns_config=selections,
                        clear_table=True,
                        progress_callback=progress_callback
                    )
                    logger.info(f"Table '{table_name}' loaded successfully.")

        # ----------------------------------------------------
        # FASE 2: INGESTA CD40K MANUAL
        # ----------------------------------------------------
        if run_phase2 and con:
            cd40k_path = os.path.join(INPUT_BASE_CONSUMO_DIR, "CD40K_NEW.xlsx")
            
            if os.path.exists(cd40k_path):
                msg_f2 = "📂 Fase 2: Cargando información manual de CD40K..."
                logger.info(f"Phase 2: Processing manual CD40K Excel at {cd40k_path}")
                if progress_callback:
                    progress_callback(msg_f2, "info")
                try:
                    from core.quality_process_orchestrator import refresh_excel_sharepoint_data
                    try:
                        refresh_excel_sharepoint_data(cd40k_path, progress_callback)
                    except Exception as refresh_err:
                        logger.warning(f"SharePoint Excel refresh warning for CD40K: {refresh_err}")
    
                    df_cd40k = pl.read_excel(cd40k_path)
                    template_cd40k = templates.get("P003-CD40K", {})
                    
                    if template_cd40k:
                        selections_cd40k = get_selections_from_template(df_cd40k, template_cd40k)
                        df_cd40k_clean = clean_dataframe(
                            df_cd40k,
                            selections_cd40k,
                            convertir_sin_acentos=True,
                            transformar_varchar_latin=False,
                            max_len_varchar=3000
                        )
                        
                        logger.info(f"Uploading CD40K dataframe ({len(df_cd40k_clean)} rows) to Teradata 'DLAB_GEC.T_SP_CD40K'...")
                        load_to_teradata(
                            con=con,
                            table_name="DLAB_GEC.T_SP_CD40K",
                            df=df_cd40k_clean,
                            selected_columns_config=selections_cd40k,
                            clear_table=True,
                            progress_callback=progress_callback
                        )
                        logger.info("CD40K table loaded successfully.")
                except Exception as cd_err:
                    msg_warn = f"⚠️ Advertencia al procesar la base manual CD40K: {cd_err}. Se continuará con el flujo."
                    logger.error(f"Error processing CD40K manual Excel: {cd_err}")
                    if progress_callback:
                        progress_callback(msg_warn, "warning")

        # ----------------------------------------------------
        # FASE 3: EXTRACCIÓN DE DESEMBOLSOS (SQL SERVER)
        # ----------------------------------------------------
        if run_phase3 and con:
            sql_server = os.getenv("SQLSERVER_SERVER")
            if sql_server and sql_server != "tu_servidor_sql":
                msg_f3 = "📡 Fase 3: Obteniendo información de desembolsos y ventas..."
                logger.info(f"Phase 3: Connecting to SQL Server ({sql_server})...")
                if progress_callback:
                    progress_callback(msg_f3, "info")
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
                    periodo_num = int(period_str)
                    query = f"SELECT * FROM BN_DESEMBOLSOS_GENERAL WHERE periodo >= {periodo_num}"
                    
                    df_desemb = pl.read_database(query=query, connection=sql_conn)
                    sql_conn.close()
                    logger.info(f"Extracted {len(df_desemb)} records from SQL Server.")
                    
                    if progress_callback:
                        progress_callback(f"📥 Se obtuvieron {len(df_desemb):,} registros de desembolsos.", "info")
                    
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
                        "FECHA_DESEMBOLSADO",
                        "COD_UNICO",
                        "CODDOC",
                        "REPRESENTANTE_LEGAL",
                        "TIPO_PERSONA",
                        "CANAL",
                        "REGISTRO",
                        "NOM_EJECUTIVO",
                        "COLOCACION_NETA",
                        "CAMPANA_N2"
                    ])
                    
                    selections_desemb = [
                        {"name": col, "selected": True, "convert_nulls": False, "datatype": "VARCHAR(255)" if col not in ("REGISTRO", "TIPO_PERSONA") else "VARCHAR(50)", "new_name": col}
                        for col in df_desemb_clean.columns
                    ]
                    
                    load_to_teradata(
                        con=con,
                        table_name="DLAB_GEC.T_VENTAS_BPE_MARKET",
                        df=df_desemb_clean,
                        selected_columns_config=selections_desemb,
                        clear_table=True,
                        progress_callback=progress_callback
                    )
                    
                    with con.cursor() as cursor:
                        cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET SET EVALUADO = 'NO'")
                        cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET FROM DLAB_GEC.M_EXP_DOCUMENTOS_EVALUADOS B SET EVALUADO = 'SI' WHERE CODDOC = B.DOCUMENTO")
                        cursor.execute("UPDATE DLAB_GEC.T_VENTAS_BPE_MARKET SET FECHA_UPDATE = CURRENT_TIMESTAMP(0)")
                        
                    logger.info("Updated EVALUADO and FECHA_UPDATE flags in T_VENTAS_BPE_MARKET.")
                except Exception as desemb_err:
                    logger.error(f"Error extracting desembolsos from SQL Server: {desemb_err}")
                    if progress_callback:
                        progress_callback(f"⚠️ No se pudo obtener desembolsos de SQL Server: {desemb_err}", "warning")

        # ----------------------------------------------------
        # FASE 4: SCRIPTS SQL DE CONSUMO
        # ----------------------------------------------------
        if run_phase4 and con:
            msg_f4 = "⚡ Fase 4: Ejecutando reglas de negocio y cálculo diario de Consumo..."
            logger.info("Phase 4: Running post-load SQL transformations for Consumo...")
            if progress_callback:
                progress_callback(msg_f4, "info")
            
            from core.sql_executor import run_post_load_transformations
            run_post_load_transformations(
                con=con,
                period_str=period_str,
                clear_consent=clear_consent,
                progress_callback=progress_callback,
                start_from_script=start_from_script
            )

        # ----------------------------------------------------
        # FASE 5: TRANSFORMACIÓN DE SELECCIÓN
        # ----------------------------------------------------
        if run_phase5:
            msg_f5 = "⚡ Fase 5: Generando consolidado de selección..."
            logger.info("Phase 5: Running selection transformation with secondary connection...")
            if progress_callback:
                progress_callback(msg_f5, "info")
            
            from core.sql_executor import run_selection_transformation
            run_selection_transformation(
                period_str=period_str,
                progress_callback=progress_callback
            )
            
        msg_ok = "🎉 ¡Proceso de Consumo completado exitosamente!"
        logger.info(f"=== PROCESO DE CONSUMO COMPLETADO EXITOSAMENTE PARA EL PERÍODO {period_str} ===")
        if progress_callback:
            progress_callback(msg_ok, "success")
        
        # Enviar notificación nativa de escritorio
        try:
            from core.notifier import notify_desktop
            notify_desktop(
                title="Uploader V2 - Consumo",
                message=f"¡Proceso completado exitosamente para el período {period_str}!",
                duration_sec=5
            )
        except Exception as err:
            logger.warning(f"No se pudo enviar la notificación de escritorio: {err}")
    finally:
        if con:
            try:
                con.close()
                logger.info("Conexión de Teradata cerrada limpiamente.")
            except Exception:
                pass
