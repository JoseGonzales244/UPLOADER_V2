"""
Fase 5 — Calidad: Proceso NTD (Not To Do).

Valida M_EXP_CALIDAD_PURECLOUD_PRE y M_EXP_NTD_OBSERVACIONES_PRE,
ejecuta 06_carga_ntd.sql y hace commit.
"""
from __future__ import annotations

import os
import re
import logging

from infrastructure.database.database import connect_teradata
from infrastructure.database.sql_executor import (
    get_friendly_script_name,
    inject_variables,
    parse_statements,
    SQLScriptExecutionError
)

logger = logging.getLogger(__name__)


def run_phase5(ctx) -> bool:
    """
    Fase 5: Ejecución del proceso NTD (06_carga_ntd.sql) con validaciones previas.
    """
    log = ctx.progress_callback or (lambda msg, lvl="info": None)

    log("🚀 Fase 5 iniciando: Ejecución de Proceso NTD (Not To Do)...", "info")

    con = connect_teradata(ctx.td_user, ctx.td_password, host=ctx.host, logmech=ctx.logmech)
    con.autocommit = True
    cursor = con.cursor()

    try:
        # 5.1 Validar M_EXP_CALIDAD_PURECLOUD_PRE
        log("🔍 Validando tabla de entrada de Evaluaciones (M_EXP_CALIDAD_PURECLOUD_PRE)...", "info")
        cursor.execute("SELECT COUNT(*) FROM DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE")
        count_pre = (cursor.fetchone() or [0])[0]
        if count_pre == 0:
            raise ValueError("La tabla DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE está vacía. Proceso abortado.")

        cursor.execute("SELECT MAX(conversationStartTime) FROM DLAB_GEC.M_EXP_CALIDAD_PURECLOUD_PRE")
        max_date = (cursor.fetchone() or [None])[0]
        if not max_date:
            raise ValueError("No se pudo obtener la fecha máxima de M_EXP_CALIDAD_PURECLOUD_PRE.")

        if hasattr(max_date, "strftime"):
            max_period = max_date.strftime("%Y%m")
        else:
            match = re.search(r"(\d{4})-(\d{2})", str(max_date))
            max_period = match.group(1) + match.group(2) if match else None

        if max_period and max_period != ctx.period_str:
            raise ValueError(
                f"La fecha máxima de M_EXP_CALIDAD_PURECLOUD_PRE ({max_period}) "
                f"no corresponde al mes parametrizado ({ctx.period_str}). Proceso abortado."
            )

        # 5.2 Validar M_EXP_NTD_OBSERVACIONES_PRE
        log("🔍 Validando tabla de entrada de Observaciones (M_EXP_NTD_OBSERVACIONES_PRE)...", "info")
        cursor.execute("SELECT COUNT(*) FROM DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE")
        count_obs = (cursor.fetchone() or [0])[0]
        if count_obs == 0:
            raise ValueError("La tabla DLAB_GEC.M_EXP_NTD_OBSERVACIONES_PRE está vacía. Proceso abortado.")

        # 5.3 Ejecutar 06_carga_ntd.sql
        script_ntd_path = os.path.join(os.getcwd(), "modules", "calidad", "sql", "06_carga_ntd.sql")
        if not os.path.exists(script_ntd_path):
            raise FileNotFoundError(f"Archivo de script SQL no encontrado: {script_ntd_path}")

        friendly_name = get_friendly_script_name(script_ntd_path)
        log(f"⚙️ Procesando: **{friendly_name}**...", "info")

        with open(script_ntd_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        prepared_sql = inject_variables(raw_sql, ctx.context)
        statements = parse_statements(prepared_sql)

        for idx, stmt in enumerate(statements, 1):
            stmt_str = stmt.strip()
            if not stmt_str:
                continue
            try:
                cursor.execute(stmt_str)
            except Exception as stmt_err:
                raise SQLScriptExecutionError(os.path.basename(script_ntd_path), idx, stmt_str, stmt_err)

        log(f"✅ Completado: **{friendly_name}**", "success")

        con.commit()
        log("💾 Procesamiento SQL de NTD ejecutado exitosamente. Transacciones confirmadas (Commit).", "info")
        log("🏁 Fase 5 concluida exitosamente: Proceso NTD finalizado.", "success")
        return True

    except Exception as e:
        log(f"❌ Fallo crítico en el procesamiento SQL de NTD. Revirtiendo cambios (Rollback)... Error: {e}", "error")
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
