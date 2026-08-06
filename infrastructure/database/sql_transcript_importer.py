import os
import re
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SQLTranscriptImporter")

def parse_transcript_file(file_path: str) -> dict:
    """
    Parsea un archivo .txt de transcripción y extrae los campos necesarios para DB_SPEECH.TRANSCRIPCION.
    """
    filename = os.path.basename(file_path)
    clean_filename = filename.replace('.txt', '')
    
    # Valores por defecto desde el nombre de archivo: <FECHA>_<DNI>_<REGISTRO>_<PRODUCTO>_<ID_LLAMADA>.txt
    parts = clean_filename.split('_')
    
    fecha_raw = parts[0] if len(parts) >= 1 else ""
    dni = parts[1] if len(parts) >= 2 else ""
    registro = parts[2] if len(parts) >= 3 else ""
    producto = parts[3] if len(parts) >= 4 else "TC"
    id_llamada = "_".join(parts[4:]) if len(parts) >= 5 else clean_filename

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Separar encabezado del cuerpo de la transcripción
    if 'TRANSCRIPCIÓN:' in content:
        header_part, text_part = content.split('TRANSCRIPCIÓN:', 1)
    elif 'TRANSCRIPCION:' in content:
        header_part, text_part = content.split('TRANSCRIPCION:', 1)
    else:
        header_part, text_part = "", content

    # Extraer variables del encabezado interno si están presentes
    for line in header_part.splitlines():
        line_str = line.strip()
        if line_str.upper().startswith('ID DE LLAMADA:'):
            id_llamada = line_str.split(':', 1)[1].strip()
        elif line_str.upper().startswith('DNI CLIENTE:') or line_str.upper().startswith('DNI:'):
            dni = line_str.split(':', 1)[1].strip()
        elif line_str.upper().startswith('EJECUTIVO:') or line_str.upper().startswith('REGISTRO:'):
            registro = line_str.split(':', 1)[1].strip()
        elif line_str.upper().startswith('FECHA:'):
            fecha_raw = line_str.split(':', 1)[1].strip()
        elif line_str.upper().startswith('PRODUCTO:'):
            producto = line_str.split(':', 1)[1].strip()

    # Formatear fecha a YYYY-MM-DD
    fecha_formatted = fecha_raw
    if len(fecha_raw) == 8 and fecha_raw.isdigit():
        fecha_formatted = f"{fecha_raw[:4]}-{fecha_raw[4:6]}-{fecha_raw[6:]}"

    # Limpiar el texto de la transcripción
    transcripcion_texto = text_part.strip()

    return {
        "id_llamada": id_llamada,
        "producto": producto,
        "fecha_llamada": fecha_formatted,
        "dni": dni,
        "registro": registro,
        "transcripcion_texto": transcripcion_texto,
        "file_path": file_path
    }

def generate_sql_inserts(transcripts: list, batch_size: int = 500) -> str:
    """
    Genera sentencias SQL INSERT INTO DB_SPEECH.TRANSCRIPCION compatibles con SQL Server (T-SQL) en lotes masivos.
    """
    sql_lines = [
        "-- ==========================================================================",
        "-- SCRIPT DE INSERCIÓN MASIVA EN DB_SPEECH.TRANSCRIPCION",
        "-- Generado automáticamente por UPLOADER_V2 (Modo Batch)",
        "-- ==========================================================================\n",
        "USE DB_SPEECH;\nGO\n"
    ]

    for i in range(0, len(transcripts), batch_size):
        chunk = transcripts[i:i + batch_size]
        row_tuples = []
        for item in chunk:
            id_llamada = item['id_llamada'].replace("'", "''")
            producto = item['producto'].replace("'", "''")
            fecha_llamada = item['fecha_llamada'].replace("'", "''")
            dni = item['dni'].replace("'", "''")
            registro = item['registro'].replace("'", "''")
            texto = item['transcripcion_texto'].replace("'", "''")
            row_tuples.append(
                f"    ('{id_llamada}', '{producto}', '{fecha_llamada}', '{dni}', '{registro}', N'{texto}', GETDATE(), GETDATE())"
            )
        
        stmt = (
            "INSERT INTO DB_SPEECH.TRANSCRIPCION "
            "(ID_LLAMADA, PRODUCTO, FECHA_LLAMADA, DNI, REGISTRO, TRANSCRIPCION_TEXTO, CREATED_AT, UPDATED_AT)\nVALUES\n"
            + ",\n".join(row_tuples) + ";\nGO\n"
        )
        sql_lines.append(stmt)

    return "\n".join(sql_lines)

def process_directory(dir_path: str, output_sql: str = "insert_transcripciones.sql"):
    """
    Procesa todos los archivos .txt de una carpeta y genera el archivo SQL.
    """
    if not os.path.exists(dir_path):
        logger.error(f"La carpeta '{dir_path}' no existe.")
        return

    txt_files = [
        os.path.join(dir_path, f) for f in os.listdir(dir_path) 
        if f.endswith('.txt') and not f.startswith('requirements') and not f.startswith('ACCESOS')
    ]
    
    if not txt_files:
        logger.warning(f"No se encontraron archivos .txt en '{dir_path}'.")
        return

    logger.info(f"Procesando {len(txt_files)} archivo(s) .txt en '{dir_path}'...")
    parsed_items = []
    for fpath in txt_files:
        parsed = parse_transcript_file(fpath)
        parsed_items.append(parsed)
        logger.info(f"  - Procesado: {os.path.basename(fpath)} | ID: {parsed['id_llamada']} | Fecha: {parsed['fecha_llamada']}")

    sql_content = generate_sql_inserts(parsed_items)
    
    with open(output_sql, 'w', encoding='utf-8') as fsql:
        fsql.write(sql_content)

    logger.info(f"¡Script SQL generado con éxito!: {os.path.abspath(output_sql)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser de Transcripciones a SQL Insert")
    parser.add_argument("--dir", type=str, default="./transcripciones", help="Carpeta contenedora de archivos .txt")
    parser.add_argument("--file", type=str, help="Archivo .txt específico si se desea procesar solo uno")
    parser.add_argument("--output", type=str, default="insert_transcripciones.sql", help="Ruta del archivo .sql generado")
    args = parser.parse_args()

    if args.file and os.path.exists(args.file):
        item = parse_transcript_file(args.file)
        sql_content = generate_sql_inserts([item])
        with open(args.output, 'w', encoding='utf-8') as fsql:
            fsql.write(sql_content)
        logger.info(f"SQL generado para {args.file} en {args.output}")
    else:
        # Si la carpeta por defecto no existe pero hay archivos .txt en la raíz, buscar en la raíz o carpetas relativas
        target_dir = args.dir
        if not os.path.exists(target_dir):
            if os.path.exists("./transcripciones"):
                target_dir = "./transcripciones"
            else:
                target_dir = "."
        process_directory(target_dir, args.output)
