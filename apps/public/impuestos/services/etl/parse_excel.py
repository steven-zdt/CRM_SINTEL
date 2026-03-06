"""
Parser para documentos Excel usando pandas y openpyxl.

Referencia: https://pandas.pydata.org/
"""
import pandas as pd
from typing import Dict, List, Any


def parse_excel_catalog(file_like, sheet=0) -> dict:
    """
    Parsea un archivo Excel de catálogo tributario.
    
    Args:
        file_like: Archivo Excel (path o file-like object)
        sheet: Índice o nombre de la hoja (default: 0)
        
    Returns:
        dict con:
        - 'records': lista de registros como dicts
        - 'columns': lista de columnas
        - 'sheet_name': nombre de la hoja procesada
    """
    try:
        # Leer Excel con pandas
        df = pd.read_excel(file_like, sheet_name=sheet, engine="openpyxl")
        
        # Normalizar nombres de columnas (minúsculas, sin espacios)
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        
        # Reemplazar NaN con None para compatibilidad con Django
        df = df.where(pd.notnull(df), None)
        
        # Convertir a lista de dicts
        records = df.to_dict(orient="records")
        
        return {
            'records': records,
            'columns': list(df.columns),
            'sheet_name': sheet if isinstance(sheet, str) else df.index.name or f"Sheet{sheet}",
            'row_count': len(records),
        }
    except Exception as e:
        # Si falla, devolver estructura vacía con error
        return {
            'records': [],
            'columns': [],
            'sheet_name': None,
            'row_count': 0,
            'error': str(e),
        }
