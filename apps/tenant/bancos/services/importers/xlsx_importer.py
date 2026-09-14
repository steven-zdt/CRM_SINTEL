"""
Importador XLSX (Fase 2, mision Bancos v3.0).

Estrategia probada contra el fixture real `10800014844_AGO2026.xlsx`
(60 movimientos, 2 bloques de encabezado repetidos a mitad de archivo):
en vez de asumir una fila de inicio fija, se escanea CADA fila del archivo
y se reconoce como movimiento cualquiera cuya primera celda matchee el
patron de fecha corta "D/M" o "DD/MM" -- esto ignora automaticamente
titulos, bloques "Informacion Cliente/General/Resumen", encabezados
repetidos y "FIN ESTADO DE CUENTA" sin necesidad de trackear posicion.

La posicion de las COLUMNAS (fecha/descripcion/sucursal/dcto/valor/saldo)
si se detecta dinamicamente buscando la fila de encabezado real
(FECHA/DESCRIPCION.../DCTO./VALOR/SALDO) -- si no se encuentra (banco con
layout distinto), se usa el layout por defecto verificado contra el
fixture real (0:fecha,1:descripcion,2:sucursal,3:dcto,4:valor,5:saldo).
"""
import contextlib
import hashlib
import re
import unicodedata

import pandas as pd

from apps.tenant.bancos.services.importers.base import (
    BankStatementImporter,
    NormalizedBankStatement,
    NormalizedBankTransaction,
    StatementParsingError,
)
from apps.tenant.bancos.services.parsing.money import parse_money

_DATE_ROW_PATTERN = re.compile(r"^\d{1,2}/\d{1,2}$")

_HEADER_ALIASES = {
    "fecha": "fecha",
    "descripcion": "descripcion",
    "sucursal": "sucursal",
    "dcto": "dcto",
    "dcto.": "dcto",
    "documento": "dcto",
    "valor": "valor",
    "saldo": "saldo",
}

_RESUMEN_ALIASES = {
    "saldo anterior": "saldo_inicial_declarado",
    "total abonos": "total_creditos_declarado",
    "total cargos": "total_debitos_declarado",
    "saldo actual": "saldo_final_declarado",
}

_DEFAULT_COLUMNS = {"fecha": 0, "descripcion": 1, "sucursal": 2, "dcto": 3, "valor": 4, "saldo": 5}


def _norm_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    texto = str(value).strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return texto


def _detectar_columnas(df) -> dict:
    """Busca la fila de encabezado real de movimientos y mapea nombre->indice.

    Fase 2: 'No asumir posicion fija'. Si no encuentra un encabezado
    reconocible, devuelve el layout por defecto (verificado contra el
    fixture real de produccion).
    """
    for _, row in df.iterrows():
        etiquetas = {_norm_text(v): idx for idx, v in enumerate(row.values)}
        if "fecha" in etiquetas and "valor" in etiquetas and "saldo" in etiquetas:
            columnas = {}
            for etiqueta, idx in etiquetas.items():
                campo = _HEADER_ALIASES.get(etiqueta)
                if campo:
                    columnas[campo] = idx
            if {"fecha", "valor", "saldo"} <= columnas.keys():
                return columnas
    return dict(_DEFAULT_COLUMNS)


def _extraer_resumen(df) -> dict:
    """Best-effort: bloque 'Resumen:' del extracto (SALDO ANTERIOR, TOTAL
    ABONOS, TOTAL CARGOS, SALDO ACTUAL). No bloquea si no se encuentra --
    la validacion de balance real (Fase 1) se deriva siempre de los propios
    movimientos, esto solo enriquece metadata quando esta disponible."""
    resultado = {}
    filas = df.values.tolist()
    for i, row in enumerate(filas):
        etiquetas = {_norm_text(v): idx for idx, v in enumerate(row)}
        encontrados = {campo: etiquetas[et] for et, campo in _RESUMEN_ALIASES.items() if et in etiquetas}
        if encontrados and i + 1 < len(filas):
            valores = filas[i + 1]
            for campo, idx in encontrados.items():
                if idx < len(valores):
                    resultado[campo] = parse_money(valores[idx])
    return resultado


class XLSXBankStatementImporter(BankStatementImporter):
    formato = "XLSX"
    extensiones = (".xlsx", ".xls")

    def importar(self, archivo, nombre_archivo: str) -> NormalizedBankStatement:
        contenido = archivo.read()
        if hasattr(archivo, "seek"):
            with contextlib.suppress(Exception):
                archivo.seek(0)

        try:
            df = pd.read_excel(pd.io.common.BytesIO(contenido), header=None)
        except Exception as exc:
            raise StatementParsingError(f"Error al leer el archivo Excel: {exc}") from exc

        if df.shape[1] < 5:
            raise StatementParsingError(
                "Estructura de archivo invalida. Se requieren al menos 5 columnas "
                "(FECHA, DESCRIPCION, DCTO., VALOR, SALDO)."
            )

        columnas = _detectar_columnas(df)
        resumen = _extraer_resumen(df)

        resultado = NormalizedBankStatement(
            source_format=self.formato,
            source_file_name=nombre_archivo or "",
            source_file_hash=hashlib.sha256(contenido).hexdigest(),
            **resumen,
        )

        fila_num = 0
        for _, row in df.iterrows():
            fila_num += 1
            resultado.filas_leidas += 1
            col_fecha = row.get(columnas["fecha"]) if columnas["fecha"] in row.index else None
            fecha_str = str(col_fecha).strip() if pd.notna(col_fecha) else ""

            if not _DATE_ROW_PATTERN.match(fecha_str):
                continue

            try:
                dia_str, mes_str = fecha_str.split("/")
                dia, mes = int(dia_str), int(mes_str)
                descripcion = _celda(row, columnas.get("descripcion"))
                sucursal = _celda(row, columnas.get("sucursal")) or None
                dcto = _celda(row, columnas.get("dcto")) or None
                valor = parse_money(row.get(columnas["valor"]))
                saldo = parse_money(row.get(columnas["saldo"]))

                transaccion = NormalizedBankTransaction(
                    fecha=None,  # sin año -- lo resuelve el business_service con el periodo del extracto
                    descripcion=descripcion,
                    sucursal=sucursal,
                    dcto=dcto,
                    valor=valor,
                    saldo=saldo,
                    source_row_number=fila_num,
                    dia_sin_anio=dia,
                    mes_sin_anio=mes,
                )
                resultado.transactions.append(transaccion)
                resultado.filas_importadas += 1
            except Exception as exc:
                resultado.filas_omitidas += 1
                resultado.errores.append(f"Fila {fila_num}: {exc}")

        if not resultado.transactions:
            raise StatementParsingError("No se encontraron transacciones validas en el archivo.")

        return resultado


def _celda(row, idx):
    if idx is None or idx not in row.index:
        return ""
    valor = row.get(idx)
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()
