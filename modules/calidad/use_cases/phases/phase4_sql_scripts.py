"""
Fase 4 — Calidad: Ejecución del Pipeline SQL de Calidad.

Valida tablas origen, verifica preguntas sin mapear, ingesta TELEVENTAS_EJECUTIVOS_GROUPED
y ejecuta la secuencia de scripts SQL definida en config.json.
Al finalizar con éxito actualiza el timestamp de Power BI (conector_calidad.txt).
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from infrastructure.database.database import connect_teradata
from infrastructure.database.sql_executor import (
    get_friendly_script_name,
    inject_variables,
    parse_statements,
    SQLScriptExecutionError
)
from infrastructure.system.powerbi_connector import write_powerbi_timestamp
from modules.calidad.televentas.use_cases.grouped_orchestrator import ensure_grouped_data_for_period

logger = logging.getLogger(__name__)


def _validate_source_tables(cursor, config: dict, context: dict, progress_callback=None) -> None:
    log = progress_callback or (lambda msg, lvl="info": None)
    periodo = context.get("PERIODO")
    corte_inicio = context.get("corte_dia_inicio_1")
    corte_fin = context.get("corte_dia_fin_2")

    log(f"🔍 Verificando tablas de origen para el período: {periodo} (Corte: Días {corte_inicio} al {corte_fin})", "info")

    validation_settings = config.get("quality_validation_settings", {})
    tables_to_check = validation_settings.get("source_tables_to_check", [])

    if not tables_to_check:
        log("⚠️ No se configuraron tablas de origen para validación en config.json.", "warning")
        return

    empty_tables = []
    for item in tables_to_check:
        table_name = item.get("table_name")
        prepared_query = inject_variables(item.get("query", ""), context)
        try:
            cursor.execute(prepared_query)
            row = cursor.fetchone()
            count = row[0] if row else 0
            if count == 0:
                empty_tables.append(table_name)
                log(f"❌ Tabla vacía o sin registros: {table_name}", "error")
            else:
                log(f"✅ Tabla {table_name}: {count:,} registros", "info")
        except Exception as err:
            empty_tables.append(table_name)
            log(f"❌ Error al consultar la tabla {table_name}: {err}", "error")

    if empty_tables:
        log(
            f"⚠️ ADVERTENCIA: Tablas de origen vacías o fallidas: {', '.join(empty_tables)}. "
            "Continuando con el procesamiento SQL...", "warning"
        )
    else:
        log("✅ Verificación completada. Todas las tablas origen contienen registros.", "success")


def _check_unmapped_questions(cursor, progress_callback=None) -> None:
    log = progress_callback or (lambda msg, lvl="info": None)
    log("🔍 Verificando preguntas de Pure Cloud sin mapear en la maestra...", "info")

    query = """
        SELECT DISTINCT RAW_PREGUNTA_CLEAN, MAP_PREGUNTA, PLANTILLA, RAW_GRUPO
        FROM (
            SELECT
                UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(questionText, CHR(13), ''), CHR(10), ''))) AS RAW_PREGUNTA_CLEAN,
                OREPLACE(OREPLACE(questionGroupName, CHR(13), ''), CHR(10), '') AS RAW_GRUPO,
                OREPLACE(OREPLACE(evaluationFormName, CHR(13), ''), CHR(10), '') AS PLANTILLA,
                COALESCE(p.TARGET, UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(r.questionText, CHR(13), ''), CHR(10), '')))) AS MAP_PREGUNTA
            FROM DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE r
            LEFT JOIN DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_PREGUNTA p ON UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(r.questionText, CHR(13), ''), CHR(10), ''))) = p.ORIGINAL
        ) r
        WHERE NOT EXISTS (
            SELECT 1 FROM (
                SELECT
                    b.PLANTILLA,
                    COALESCE(g.TARGET, b.GRUPO_PREGUNTAS) AS MAP_GRUPO,
                    COALESCE(p.TARGET, b.PREGUNTA) AS MAP_PREGUNTA
                FROM DLAB_GEC.M_EXP_CALIDAD_MAESTRA_GRUPO_PREGUNTAS_PCLOUD b
                LEFT JOIN DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_GRUPO g
                    ON UPPER(TRIM(BOTH ' ' FROM b.GRUPO_PREGUNTAS)) = g.ORIGINAL
                LEFT JOIN DLAB_GEC.M_EXP_CALIDAD_HOMOLOGA_PREGUNTA p
                    ON UPPER(TRIM(BOTH ' ' FROM b.PREGUNTA)) = p.ORIGINAL
            ) b
            WHERE UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(r.PLANTILLA, CHR(13), ''), CHR(10), ''))) = UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(b.PLANTILLA, CHR(13), ''), CHR(10), '')))
              AND UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(r.RAW_GRUPO, CHR(13), ''), CHR(10), ''))) = UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(b.MAP_GRUPO, CHR(13), ''), CHR(10), '')))
              AND UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(r.MAP_PREGUNTA, CHR(13), ''), CHR(10), ''))) = UPPER(TRIM(BOTH ' ' FROM OREPLACE(OREPLACE(b.MAP_PREGUNTA, CHR(13), ''), CHR(10), '')))
        )
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows:
            log(f"⚠️ Se encontraron {len(rows)} preguntas sin mapear en la maestra.", "warning")
            for row in rows[:10]:
                raw_q, map_q, template, group = row
                log(f"   - Pregunta: '{raw_q}' (Mapeada: '{map_q}') | Plantilla: {template} | Grupo: {group}", "warning")
            if len(rows) > 10:
                log("   ... (más preguntas omitidas en el log rápido)", "warning")
        else:
            log("✅ Todas las preguntas crudas de Pure Cloud están homologadas correctamente.", "success")
    except Exception as err:
        log(f"⚠️ Error al verificar preguntas sin mapear: {err}", "warning")


def run_phase4(ctx, start_from_script: Optional[str] = None) -> bool:
    """
    Fase 4: Ejecución de scripts SQL del pipeline de Calidad.
    Actualiza timestamp Power BI al finalizar.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("🚀 Fase 4 iniciando: Ejecución de Scripts SQL del Pipeline de Calidad...", "info")

    # 4.0 Validar/Ingestar automáticamente TELEVENTAS_EJECUTIVOS_GROUPED
    ensure_grouped_data_for_period(ctx.period_str, progress_callback=ctx.progress_callback)

    sequence = ctx.quality_sequence
    scripts_to_run = sequence
    if start_from_script:
        clean_start = os.path.basename(start_from_script).lower()
        matched_idx = next(
            (i for i, s in enumerate(sequence) if os.path.basename(s).lower() == clean_start or s.lower() == clean_start),
            -1
        )
        if matched_idx != -1:
            scripts_to_run = sequence[matched_idx:]
        else:
            log(f"⚠️ No se encontró el script '{start_from_script}' en la secuencia. Se ejecutarán todos.", "warning")

    con = connect_teradata(ctx.td_user, ctx.td_password, host=ctx.host, logmech=ctx.logmech)
    con.autocommit = True
    cursor = con.cursor()

    try:
        # 4.1 Validaciones previas
        _validate_source_tables(cursor, ctx.config, ctx.context, ctx.progress_callback)
        _check_unmapped_questions(cursor, ctx.progress_callback)

        # 4.2 Ejecutar secuencia de scripts SQL
        for script_rel_path in scripts_to_run:
            script_path = os.path.join(os.getcwd(), script_rel_path)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Archivo de script SQL no encontrado: {script_rel_path}")

            friendly_name = get_friendly_script_name(script_path)
            log(f"⚙️ Procesando: **{friendly_name}**...", "info")

            with open(script_path, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            prepared_sql = inject_variables(raw_sql, ctx.context)
            statements = parse_statements(prepared_sql)
            logger.info(f"Se detectaron {len(statements)} sentencias en {os.path.basename(script_path)}")

            for idx, stmt in enumerate(statements, 1):
                stmt_str = stmt.strip()
                if not stmt_str:
                    continue
                preview = stmt_str.split("\n")[0][:100]
                logger.info(f"   [{idx}/{len(statements)}] Ejecutando: {preview}")
                try:
                    log(f"⚙️ {friendly_name} — Paso {idx}/{len(statements)} ({int(idx/len(statements)*100)}%)", "info")
                except Exception:
                    pass
                try:
                    cursor.execute(stmt_str)
                except Exception as stmt_err:
                    raise SQLScriptExecutionError(os.path.basename(script_path), idx, stmt_str, stmt_err)

            log(f"✅ Completado: **{friendly_name}**", "success")

        con.commit()
        log("💾 Todo el procesamiento SQL ejecutado. Transacciones confirmadas (Commit).", "info")
        log("🎉 ¡Pipeline de Calidad Completo ejecutado exitosamente!", "success")

        # Actualizar conector Power BI al finalizar el SQL
        write_powerbi_timestamp("conector_calidad.txt")
        log("🏁 Fase 4 concluida exitosamente: Scripts SQL aplicados.", "success")
        return True

    except Exception as e:
        log(f"❌ Fallo crítico en el procesamiento SQL. Revirtiendo cambios (Rollback)... Error: {e}", "error")
        try:
            con.rollback()
        except Exception:
            pass
        raise e
    finally:
        try:
            con.close()
        except Exception:
            pass
