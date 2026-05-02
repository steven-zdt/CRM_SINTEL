"""
Parser para documentos CSV usando pandas.

Referencia: https://pandas.pydata.org/
"""

import pandas as pd


def parse_csv_catalog(file_like, sep=None) -> dict:
    """
    Parsea un archivo CSV de catálogo tributario.

    Args:
        file_like: Archivo CSV (path o file-like object)
        sep: Separador (default: ',' detectado automáticamente)

    Returns:
        dict con:
        - 'records': lista de registros como dicts
        - 'columns': lista de columnas
        - 'row_count': número de filas
    """
    try:
        # Leer CSV con pandas
        df = pd.read_csv(file_like, sep=sep or ",", encoding="utf-8-sig")

        # Normalizar nombres de columnas (minúsculas, sin espacios)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        # Reemplazar NaN con None para compatibilidad con Django
        df = df.where(pd.notnull(df), None)

        # Convertir a lista de dicts
        records = df.to_dict(orient="records")

        return {
            "records": records,
            "columns": list(df.columns),
            "row_count": len(records),
        }
    except UnicodeDecodeError:
        # Intentar con encoding diferente
        try:
            df = pd.read_csv(file_like, sep=sep or ",", encoding="latin-1")
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            df = df.where(pd.notnull(df), None)
            records = df.to_dict(orient="records")
            return {
                "records": records,
                "columns": list(df.columns),
                "row_count": len(records),
            }
        except Exception as e:
            return {
                "records": [],
                "columns": [],
                "row_count": 0,
                "error": str(e),
            }
    except Exception as e:
        # Si falla, devolver estructura vacía con error
        return {
            "records": [],
            "columns": [],
            "row_count": 0,
            "error": str(e),
        }
