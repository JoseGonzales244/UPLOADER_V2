"""
Infrastructure Parsers Module: FilePreviewService
Proporciona lógica desacoplada para lectura de archivos (Excel/CSV/TXT),
inferencia de esquema SQL, aplicación de plantillas y previsualización de datos.
Cumple con Single Responsibility Principle (SRP) desacoplando la capa de transporte API.
"""
import io
import os
import polars as pl
from typing import List, Dict, Any, Optional, Tuple, Union

from infrastructure.parsers.readers import read_excel_file, read_csv_file, read_unicode_text_file
from infrastructure.parsers.cleaners import clean_dataframe, sanitize_identifier, suggest_sql_type
from ui.components import load_templates


class FilePreviewService:
    @staticmethod
    def read_dataframe(
        file_source: Union[str, bytes, io.BytesIO],
        file_type: str = "Excel",
        selected_template: str = "Ninguno",
        templates: Optional[Dict[str, Any]] = None
    ) -> pl.DataFrame:
        """
        Lee el archivo desde ruta o buffer binario según el tipo especificado.
        """
        if templates is None:
            templates = load_templates()

        if isinstance(file_source, bytes):
            file_source = io.BytesIO(file_source)

        if file_type == "Excel":
            return read_excel_file(file_source, selected_template=selected_template, templates=templates)
        elif file_type == "CSV":
            return read_csv_file(file_source)
        else:
            return read_unicode_text_file(file_source)

    @staticmethod
    def build_column_selections(
        df: pl.DataFrame,
        selected_template: str = "Ninguno",
        templates: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calcula las definiciones de columnas y tipos SQL sugeridos cruzando con la plantilla.
        """
        if templates is None:
            templates = load_templates()

        columns_info = []
        template_config = templates.get(selected_template, {})

        for col in df.columns:
            suggested = suggest_sql_type(df[col].dtype)

            if not template_config:
                selected = True
                new_name = sanitize_identifier(col)
                convert_nulls = False
                datatype = suggested
            elif col in template_config:
                selected = template_config[col].get("Añadir", True)
                new_name = sanitize_identifier(template_config[col].get("Nuevo nombre", col))
                convert_nulls = template_config[col].get("Null:0/No Null:1", False)
                datatype = template_config[col].get("Tipo de dato", suggested)
            else:
                selected = False
                new_name = sanitize_identifier(col)
                convert_nulls = False
                datatype = suggested

            columns_info.append({
                "original_name": col,
                "name": col,
                "new_name": new_name,
                "datatype": datatype,
                "selected": selected,
                "convert_nulls": convert_nulls
            })

        return columns_info

    @classmethod
    def generate_preview(
        cls,
        file_source: Union[str, bytes, io.BytesIO],
        filename: str,
        file_type: str = "Excel",
        selected_template: str = "Ninguno",
        templates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera la estructura de metadatos, columnas y las primeras 10 filas limpias para la vista previa.
        """
        if templates is None:
            templates = load_templates()

        df = cls.read_dataframe(file_source, file_type, selected_template, templates)
        columns_info = cls.build_column_selections(df, selected_template, templates)

        df_transformed = clean_dataframe(
            df,
            selections=columns_info,
            convertir_sin_acentos=True,
            transformar_varchar_latin=False,
            max_len_varchar=3000
        )
        preview_rows = df_transformed.head(10).to_dicts()

        return {
            "status": "ok",
            "filename": filename,
            "total_rows": len(df),
            "total_cols": len(df_transformed.columns),
            "columns": columns_info,
            "preview": preview_rows
        }

    @classmethod
    def prepare_upload_data(
        cls,
        file_path: str,
        file_type: str,
        selected_template: str,
        selections: Optional[List[Dict[str, Any]]] = None,
        convertir_sin_acentos: bool = True,
        transformar_varchar_latin: bool = False,
        max_len_varchar: int = 3000,
        templates: Optional[Dict[str, Any]] = None
    ) -> Tuple[pl.DataFrame, List[Dict[str, Any]]]:
        """
        Lee el archivo temporal, asegura la lista de columnas/tipos y aplica la limpieza para carga a Teradata.
        """
        if templates is None:
            templates = load_templates()

        df = cls.read_dataframe(file_path, file_type, selected_template, templates)

        if not selections:
            selections = cls.build_column_selections(df, selected_template, templates)

        df_clean = clean_dataframe(
            df,
            selections=selections,
            convertir_sin_acentos=convertir_sin_acentos,
            transformar_varchar_latin=transformar_varchar_latin,
            max_len_varchar=max_len_varchar
        )

        return df_clean, selections
