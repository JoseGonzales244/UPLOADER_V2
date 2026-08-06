import os
import teradatasql
import polars as pl
from dotenv import load_dotenv

def load_credentials():
    """
    Loads Teradata credentials from environment variables / .env file.
    """
    load_dotenv()
    env_user = os.getenv("TERADATA_USER")
    env_password = os.getenv("TERADATA_PASSWORD")
    env_host = os.getenv("TERADATA_HOST")
    env_logmech = os.getenv("TERADATA_LOGMECH")
    
    return {
        "teradata_user": env_user or "",
        "teradata_password": env_password or "",
        "teradata_host": env_host or "IBKTD",
        "teradata_logmech": env_logmech or "LDAP"
    }

def connect_teradata(user, password, host='IBKTD', logmech='TD2'):
    """Establishes connection to the Teradata database."""
    return teradatasql.connect(
        host=host,
        user=user,
        password=password,
        logmech=logmech
    )

def _sanitize_cell(val):
    if isinstance(val, str):
        # Sanitiza caracteres que la codificación de Teradata no pueda traducir
        return val.encode('latin-1', errors='replace').decode('latin-1')
    return val

def check_table_exists(con, table_name) -> bool:
    """Checks if a table exists in Teradata."""
    cur = con.cursor()
    try:
        cur.execute(f"SELECT TOP 1 * FROM {table_name}")
        return True
    except Exception:
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass

def get_table_columns(con, table_name) -> list:
    """Gets column names of an existing table."""
    cur = con.cursor()
    try:
        cur.execute(f"SELECT TOP 1 * FROM {table_name}")
        return [desc[0] for desc in cur.description]
    except Exception:
        return []
    finally:
        try:
            cur.close()
        except Exception:
            pass

def execute_create_table(con, table_name, columns_with_types):
    """Creates a new table with sanitized column names and specified types."""
    cur = con.cursor()
    cols_defs = [f'"{col}" {dtype}' for col, dtype in columns_with_types.items()]
    create_query = f"CREATE MULTISET TABLE {table_name} (\n" + ",\n".join(cols_defs) + "\n);"
    cur.execute(create_query)
    cur.close()
    return create_query

def clear_table_data(con, table_name):
    """Deletes all records from the target table."""
    cur = con.cursor()
    cur.execute(f"DELETE FROM {table_name}")
    cur.close()

def load_to_teradata(con, table_name, df: pl.DataFrame, selected_columns_config, clear_table, progress_callback=None):
    """
    Ingests a Polars DataFrame into Teradata.
    Uses standard batch insertion with optional percentage progress updates.
    """
    cur = con.cursor()
    
    table_exists = check_table_exists(con, table_name)
    
    if table_exists:
        if clear_table:
            if progress_callback:
                progress_callback("Limpiando datos existentes en la tabla...")
            clear_table_data(con, table_name)
        columns_in_table = get_table_columns(con, table_name)
    else:
        if progress_callback:
            progress_callback("Creando tabla de destino...")
        columns_with_types = {col['new_name']: col['datatype'] for col in selected_columns_config if col['selected']}
        create_query = execute_create_table(con, table_name, columns_with_types)
        columns_in_table = list(columns_with_types.keys())
        if progress_callback:
            progress_callback("Tabla de destino creada con éxito.")

    if not columns_in_table:
        raise ValueError("No se pudo obtener ni crear la estructura de la tabla.")

    rename_mapping = {
        col['name']: col['new_name'] 
        for col in selected_columns_config 
        if col['selected'] and col['name'] in df.columns and col['name'] != col['new_name']
    }
    if rename_mapping:
        df_filtered = df.rename(rename_mapping)
    else:
        df_filtered = df
    df_filtered = df_filtered.select([col for col in columns_in_table if col in df_filtered.columns])
    
    total_rows = df_filtered.height
    batch_size = 5000
    
    placeholders = ", ".join(["?"] * len(df_filtered.columns))
    cols_str = ", ".join([f'"{c}"' for c in df_filtered.columns])
    insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
    
    raw_rows = df_filtered.rows()
    for i in range(0, total_rows, batch_size):
        batch = raw_rows[i:i + batch_size]
        batch_values = [[_sanitize_cell(val) for val in row] for row in batch]
        cur.executemany(insert_query, batch_values)
        if progress_callback:
            pct = min(100, int(((i + len(batch)) / total_rows) * 100))
            progress_callback(f"Cargando registros... {pct}% ({i + len(batch)}/{total_rows})")

    con.commit()
    cur.close()
