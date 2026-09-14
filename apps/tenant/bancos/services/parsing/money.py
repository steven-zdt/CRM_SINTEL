"""
Parser monetario robusto (Fase 3, mision Bancos v3.0).

Un unico punto de normalizacion de dinero para todo el modulo. Nunca
convierte a float para persistencia -- siempre Decimal con precision
Decimal("0.01").

Soporta:
    "1,400,000.00"   -> 1400000.00   (coma=miles, punto=decimal -- US/extracto real)
    "-1,431,900.00"  -> -1431900.00
    ".97"             -> 0.97
    "1.00"            -> 1.00
    "-100,000.00"    -> -100000.00
    "1.400.000,00"   -> 1400000.00   (punto=miles, coma=decimal -- Colombia)
    "-1.431.900,00"  -> -1431900.00
    "$ 1.400.000"    -> 1400000.00
    "(100,000.00)"   -> -100000.00   (parentesis contable = negativo)
"""
import math
from decimal import Decimal, InvalidOperation

CENTAVOS = Decimal("0.01")

_SIMBOLOS_MONEDA = ("$", "COP", "USD", "Cop", "cop")


def parse_money(valor) -> Decimal:
    """Convierte un valor crudo (str/int/float/Decimal/None) a Decimal con 2 decimales.

    Nunca lanza excepcion: valores no interpretables devuelven Decimal("0.00").
    """
    if valor is None:
        return Decimal("0.00")

    if isinstance(valor, Decimal):
        if valor.is_nan():
            return Decimal("0.00")
        return valor.quantize(CENTAVOS)

    if isinstance(valor, bool):
        return Decimal("0.00")

    if isinstance(valor, int | float):
        if isinstance(valor, float) and math.isnan(valor):
            return Decimal("0.00")
        try:
            return Decimal(str(valor)).quantize(CENTAVOS)
        except InvalidOperation:
            return Decimal("0.00")

    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "none", "-", "--"):
        return Decimal("0.00")

    for simbolo in _SIMBOLOS_MONEDA:
        texto = texto.replace(simbolo, "")
    texto = texto.strip()

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1].strip()

    if texto.startswith("-"):
        negativo = True
        texto = texto[1:].strip()
    elif texto.startswith("+"):
        texto = texto[1:].strip()
    elif texto.endswith("-"):
        negativo = True
        texto = texto[:-1].strip()

    texto = texto.replace(" ", "")
    if not texto:
        return Decimal("0.00")

    ultima_coma = texto.rfind(",")
    ultimo_punto = texto.rfind(".")

    if ultima_coma != -1 and ultimo_punto != -1:
        # Ambos separadores presentes: el que aparece MAS A LA DERECHA es el
        # decimal; el otro es separador de miles y se descarta.
        if ultima_coma > ultimo_punto:
            normalizado = texto.replace(".", "").replace(",", ".")
        else:
            normalizado = texto.replace(",", "")
    elif ultima_coma != -1:
        # Solo coma. Si hay mas de una coma, o el grupo final tiene 3
        # digitos, se interpreta como separador de miles (formato entero
        # sin centavos). Si el grupo final tiene 1-2 digitos, es decimal.
        digitos_finales = len(texto) - ultima_coma - 1
        if texto.count(",") > 1 or digitos_finales == 3:
            normalizado = texto.replace(",", "")
        else:
            normalizado = texto.replace(",", ".")
    elif ultimo_punto != -1:
        # Solo punto. Si hay mas de un punto es claramente separador de
        # miles (formato colombiano sin centavos, ej. "1.400.000"). Con un
        # unico punto se asume separador decimal (coincide con el extracto
        # bancario real usado como fixture: "1.00", ".97").
        if texto.count(".") > 1:
            normalizado = texto.replace(".", "")
        else:
            normalizado = texto
    else:
        normalizado = texto

    try:
        resultado = Decimal(normalizado)
    except InvalidOperation:
        return Decimal("0.00")

    if negativo:
        resultado = -resultado

    return resultado.quantize(CENTAVOS)
