"""
Importador CSV (Fase 2, mision Bancos v3.0).

Soporta:
    - UTF-8 y UTF-8 con BOM
    - separadores , ; y tab (deteccion via csv.Sniffer con fallback manual)
    - decimales colombianos y americanos (via parse_money)
    - fechas comunes: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, D/M (sin año)
    - encabezados variables (alias FECHA/DESCRIPCION/VALOR/SALDO/DCTO/SUCURSAL)
"""
import contextlib
import csv
import datetime
import hashlib
import io
import re
import unicodedata

from apps.tenant.bancos.services.importers.base import (
    BankStatementImporter,
    NormalizedBankStatement,
    NormalizedBankTransaction,
    StatementParsingError,
)
from apps.tenant.bancos.services.parsing.money import parse_money

_HEADER_ALIASES = {
    "fecha": "fecha", "date": "fecha",
    "descripcion": "descripcion", "descripción": "descripcion", "detalle": "descripcion",
    "concepto": "descripcion", "description": "descripcion",
    "sucursal": "sucursal", "oficina": "sucursal", "agencia": "sucursal",
    "dcto": "dcto", "dcto.": "dcto", "documento": "dcto", "referencia": "dcto",
    "valor": "valor", "monto": "valor", "amount": "valor", "value": "valor",
    "saldo": "saldo", "balance": "saldo",
}

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d")
_SHORT_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def _norm(texto: str) -> str:
    texto = (texto or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _parse_fecha(texto: str):
    """Devuelve (date|None, dia_sin_anio|None, mes_sin_anio|None)."""
    texto = (texto or "").strip()
    m = _SHORT_DATE_RE.match(texto)
    if m:
        return None, int(m.group(1)), int(m.group(2))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(texto, fmt).date(), None, None
        except ValueError:
            continue
    return None, None, None


class CSVBankStatementImporter(BankStatementImporter):
    formato = "CSV"
    extensiones = (".csv", ".txt")

    def importar(self, archivo, nombre_archivo: str) -> NormalizedBankStatement:
        contenido_bytes = archivo.read()
        if hasattr(archivo, "seek"):
            with contextlib.suppress(Exception):
                archivo.seek(0)

        texto = contenido_bytes.decode("utf-8-sig", errors="replace")

        muestra = texto[:4096]
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
            delimitador = dialecto.delimiter
        except csv.Error:
            # Fallback manual: cuenta ocurrencias en la primera linea no vacia.
            primera_linea = next((linea for linea in texto.splitlines() if linea.strip()), "")
            conteos = {sep: primera_linea.count(sep) for sep in (",", ";", "\t")}
            delimitador = max(conteos, key=conteos.get) if any(conteos.values()) else ","

        lector = csv.reader(io.StringIO(texto), delimiter=delimitador)
        filas = [fila for fila in lector if any((c or "").strip() for c in fila)]

        if not filas:
            raise StatementParsingError("El archivo CSV esta vacio.")

        encabezado = filas[0]
        columnas = {}
        for idx, celda in enumerate(encabezado):
            campo = _HEADER_ALIASES.get(_norm(celda))
            if campo:
                columnas[campo] = idx

        if "fecha" not in columnas or "valor" not in columnas:
            raise StatementParsingError(
                "No se pudo identificar las columnas FECHA/VALOR en el encabezado del CSV. "
                f"Encabezado detectado: {encabezado}"
            )

        resultado = NormalizedBankStatement(
            source_format=self.formato,
            source_file_name=nombre_archivo or "",
            source_file_hash=hashlib.sha256(contenido_bytes).hexdigest(),
        )

        def _get(fila, campo):
            idx = columnas.get(campo)
            if idx is None or idx >= len(fila):
                return ""
            return (fila[idx] or "").strip()

        for fila_num, fila in enumerate(filas[1:], start=1):
            resultado.filas_leidas += 1
            fecha_txt = _get(fila, "fecha")
            if not fecha_txt:
                resultado.filas_omitidas += 1
                continue
            try:
                fecha, dia_sin_anio, mes_sin_anio = _parse_fecha(fecha_txt)
                if fecha is None and dia_sin_anio is None:
                    raise ValueError(f"Fecha no reconocida: '{fecha_txt}'")

                transaccion = NormalizedBankTransaction(
                    fecha=fecha,
                    descripcion=_get(fila, "descripcion"),
                    sucursal=_get(fila, "sucursal") or None,
                    dcto=_get(fila, "dcto") or None,
                    valor=parse_money(_get(fila, "valor")),
                    saldo=parse_money(_get(fila, "saldo")),
                    source_row_number=fila_num,
                    dia_sin_anio=dia_sin_anio,
                    mes_sin_anio=mes_sin_anio,
                )
                resultado.transactions.append(transaccion)
                resultado.filas_importadas += 1
            except Exception as exc:
                resultado.filas_omitidas += 1
                resultado.errores.append(f"Fila {fila_num}: {exc}")

        if not resultado.transactions:
            raise StatementParsingError("No se encontraron transacciones validas en el archivo CSV.")

        return resultado
