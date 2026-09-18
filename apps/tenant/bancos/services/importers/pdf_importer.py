"""
Importador PDF (mision BANCOS_PDF_APLICACIONES_01, Fases 28-41).

Reutiliza pdfminer.six -- YA esta en requirements.txt y ya se usa en
apps/public/impuestos/services/etl/parse_pdf.py y
apps/services/document_parser/normalizers.py (extraccion de texto de
facturas PDF). No se agrega una dependencia nueva (Fase 31).

Estrategia (Fase 32) -- por linea de texto extraida:
    1. Buscar una fecha (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY) en la linea.
    2. Extraer los montos (parse_money) que aparecen DESPUES de la fecha.
    3. Si aparecen exactamente 2 montos: el ultimo es el saldo, el primero
       es el valor del movimiento (ya firmado -- mismo contrato de una sola
       columna "valor" que usan los importadores XLSX/CSV existentes; un
       layout de columnas separadas debito/credito no esta soportado en
       esta pasada, ver STATUS "Deferred").
    4. Cualquier otra cantidad de montos en la linea (0, 1, 3+) se descarta
       como ruido/encabezado/resumen -- se registra en advertencias, nunca
       bloquea el archivo completo (Fase 26, Fase 39).

Multi-pagina (Fase 36): pdfminer.extract_text() concatena el texto de
TODAS las paginas por defecto -- el parser de lineas ya es multi-pagina
sin cambios adicionales. Encabezados repetidos por pagina se filtran solo
por no tener el conteo de montos esperado (no producen falsos movimientos).

NO declara soporte universal de todos los bancos colombianos (Fase 44) --
es un parser generico best-effort para PDFs con texto extraible en
layout de una columna de valor + una de saldo por fila.
"""
import contextlib
import datetime
import hashlib
import io
import re

from apps.tenant.bancos.services.importers.base import (
    BankStatementImporter,
    NormalizedBankStatement,
    NormalizedBankTransaction,
    StatementParsingError,
)
from apps.tenant.bancos.services.parsing.money import parse_money

try:
    from pdfminer.high_level import extract_text as _pdf_extract_text
    HAS_PDFMINER = True
except ImportError:  # pragma: no cover - pdfminer.six ya es dependencia obligatoria del proyecto
    HAS_PDFMINER = False

_DATE_RE = re.compile(r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d")

# Un "monto" en texto de PDF: opcional +/-, opcional parentesis, y O BIEN
# al menos un separador de miles (grupos de 3 digitos), O BIEN un separador
# decimal de exactamente 2 digitos. Un numero suelto sin separador de miles
# NI parte decimal (ej. "1", "2" -- muy comunes como numero de pagina,
# item o referencia dentro de la descripcion) NUNCA se interpreta como
# monto -- una factura/extracto real siempre muestra centavos o miles.
_MONEY_TOKEN_RE = re.compile(
    r"\(?[+-]?\$?\s?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?\)?"
    r"|"
    r"\(?[+-]?\$?\s?\d+[.,]\d{2}\)?"
)

# Lineas de ruido conocidas -- encabezados/resumen repetidos por pagina.
_HEADER_KEYWORDS = (
    "fecha", "descripcion", "descripción", "saldo", "pagina", "página",
    "extracto", "resumen", "total", "cliente", "cuenta no", "nit",
)


def _parse_fecha(texto: str):
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _es_linea_encabezado(resto_linea: str) -> bool:
    normalizado = resto_linea.strip().lower()
    if not normalizado:
        return True
    # Una linea de encabezado tipica no tiene digitos de monto reales, solo
    # palabras clave de columna.
    palabras = normalizado.split()
    return any(kw in normalizado for kw in _HEADER_KEYWORDS) and not any(c.isdigit() for c in normalizado[:3])


def parsear_texto_extracto(
    texto: str, formato: str = "PDF", nombre_archivo: str = "", source_file_hash: str = ""
) -> NormalizedBankStatement:
    """Parsea texto YA extraido de un PDF (o de cualquier fuente equivalente)
    a un NormalizedBankStatement. Separado de importar() para poder probar
    la logica de parseo de lineas con strings directos, sin depender del
    round-trip real de generacion/extraccion de un PDF binario (fragil para
    casos de borde en tests -- el layout visual exacto que produce un motor
    de renderizado de PDF no es 100% determinista entre entornos)."""
    resultado = NormalizedBankStatement(
        source_format=formato, source_file_name=nombre_archivo or "", source_file_hash=source_file_hash,
    )

    lineas = [l for l in texto.splitlines() if l.strip()]
    for fila_num, linea in enumerate(lineas, start=1):
        match_fecha = _DATE_RE.search(linea)
        if not match_fecha:
            continue  # Linea sin fecha: texto libre, encabezado o pie de pagina.

        resultado.filas_leidas += 1
        fecha = _parse_fecha(match_fecha.group(1))
        resto = linea[match_fecha.end():]

        if fecha is None:
            resultado.filas_omitidas += 1
            resultado.errores.append(f"Fila {fila_num}: fecha no reconocida ('{match_fecha.group(1)}').")
            continue

        montos_texto = _MONEY_TOKEN_RE.findall(resto)
        if len(montos_texto) != 2:
            # Encabezado repetido, fila de resumen, o layout no reconocido
            # (ej. columnas debito/credito separadas -- no soportado en
            # esta pasada). No es un error fatal del archivo completo.
            resultado.filas_omitidas += 1
            if not _es_linea_encabezado(resto):
                resultado.advertencias.append(
                    f"Fila {fila_num}: se esperaban 2 montos (valor, saldo), se "
                    f"encontraron {len(montos_texto)}. Linea omitida: '{linea.strip()[:80]}'"
                )
            continue

        valor_txt, saldo_txt = montos_texto
        descripcion = resto
        for token in montos_texto:
            descripcion = descripcion.replace(token, " ", 1)

        transaccion = NormalizedBankTransaction(
            fecha=fecha,
            descripcion=descripcion.strip(" -:|\t") or "(sin descripcion)",
            valor=parse_money(valor_txt),
            saldo=parse_money(saldo_txt),
            source_row_number=fila_num,
        )
        resultado.transactions.append(transaccion)
        resultado.filas_importadas += 1

    if not resultado.transactions:
        raise StatementParsingError(
            "No se encontraron movimientos reconocibles en el PDF (layout no soportado "
            "o extracto vacio). No se asume soporte universal de todos los formatos "
            "bancarios en PDF."
        )

    return resultado


class PDFBankStatementImporter(BankStatementImporter):
    formato = "PDF"
    extensiones = (".pdf",)

    def importar(self, archivo, nombre_archivo: str) -> NormalizedBankStatement:
        contenido_bytes = archivo.read()
        if hasattr(archivo, "seek"):
            with contextlib.suppress(Exception):
                archivo.seek(0)

        # Fase 30: nunca confiar solo en la extension -- validar firma binaria real.
        if not contenido_bytes.startswith(b"%PDF-"):
            raise StatementParsingError(
                "El archivo no es un PDF valido (firma binaria %PDF- no encontrada)."
            )

        if not HAS_PDFMINER:  # pragma: no cover
            raise StatementParsingError(
                "pdfminer.six no esta disponible en este entorno para procesar PDFs."
            )

        try:
            texto = _pdf_extract_text(io.BytesIO(contenido_bytes))
        except Exception as exc:
            # Cubre PDF corrupto, protegido/encriptado, o cualquier fallo de
            # bajo nivel de pdfminer -- nunca un 500 (Fase 26/39).
            raise StatementParsingError(
                f"No se pudo leer el archivo PDF (corrupto, protegido o formato no valido): {exc}"
            ) from exc

        if not (texto or "").strip():
            # Fase 34: PDF escaneado sin capa de texto -- no hay OCR disponible.
            raise StatementParsingError(
                "El PDF no contiene texto extraible (probablemente escaneado). "
                "NEEDS_OCR / UNSUPPORTED_FORMAT: este sistema no incluye OCR."
            )

        return parsear_texto_extracto(
            texto, formato=self.formato, nombre_archivo=nombre_archivo,
            source_file_hash=hashlib.sha256(contenido_bytes).hexdigest(),
        )
