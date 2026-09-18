"""
Conversion de un monto en COP a su representacion en letras (espanol).

Sin dependencias externas (num2words no esta en requirements -- agregar una
dependencia nueva requiere autorizacion explicita, no se hizo aqui). Servicio
puro, sin estado, sin I/O -- consumido por los serializers de detalle de
Factura/Cotizacion (SerializerMethodField) para mostrar "Valor en Letras"
(FST-375 seccion 7/27): la fuente de verdad es SIEMPRE el monto Decimal ya
validado por backend, nunca un calculo hecho en el frontend.
"""
import re
from decimal import ROUND_HALF_UP, Decimal

_UNIDADES = (
    '', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
    'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciseis', 'diecisiete',
    'dieciocho', 'diecinueve', 'veinte',
)
_VEINTIS = (
    'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
    'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve',
)
_DECENAS = ('', '', '', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
_CENTENAS = (
    '', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos',
    'seiscientos', 'setecientos', 'ochocientos', 'novecientos',
)


def _hasta_999(n: int) -> str:
    """Convierte un entero 0-999 a palabras, sin el nombre de la escala (mil/millones)."""
    if n == 0:
        return ''
    if n < 21:
        return _UNIDADES[n]
    if n < 30:
        return _VEINTIS[n - 21]
    if n < 100:
        decena, resto = divmod(n, 10)
        palabra = _DECENAS[decena]
        return f'{palabra} y {_UNIDADES[resto]}' if resto else palabra
    centena, resto = divmod(n, 100)
    if centena == 1 and resto == 0:
        return 'cien'
    palabra = _CENTENAS[centena]
    return f'{palabra} {_hasta_999(resto)}' if resto else palabra


def _apocope_masculino(texto: str) -> str:
    """
    'uno'/'veintiuno' pierden la 'o' final (apocope) justo antes del sustantivo
    que acompanan (mil/millones/pesos) -- 'un peso', 'veintiun millones', nunca
    'uno peso'. Solo aplica al final de la cadena (la unica posicion donde el
    numero queda pegado al sustantivo siguiente).
    """
    texto = re.sub(r'\buno$', 'un', texto)
    texto = re.sub(r'\bveintiuno$', 'veintiun', texto)
    return texto


def _entero_a_letras(n: int) -> str:
    """Convierte un entero no negativo (sin parte decimal) a palabras completas."""
    if n == 0:
        return 'cero'

    miles_millones, resto = divmod(n, 1_000_000_000)
    millones, resto = divmod(resto, 1_000_000)
    miles, unidades = divmod(resto, 1000)

    partes = []

    if miles_millones:
        texto = _apocope_masculino(_hasta_999(miles_millones))
        sufijo = 'mil millones' if miles_millones != 1 else 'mil millones'
        # "un mil millones" no es uso comun -- se dice simplemente "mil millones".
        if miles_millones == 1:
            partes.append('mil millones')
        else:
            partes.append(f'{texto} mil millones')

    if millones:
        texto = _apocope_masculino(_hasta_999(millones))
        partes.append(f'{texto} millon' if millones == 1 else f'{texto} millones')

    if miles:
        if miles == 1:
            partes.append('mil')
        else:
            texto = _apocope_masculino(_hasta_999(miles))
            partes.append(f'{texto} mil')

    if unidades:
        partes.append(_hasta_999(unidades))

    return ' '.join(p for p in partes if p)


def monto_a_letras(valor: Decimal, moneda: str = 'COP') -> str:
    """
    Convierte un monto Decimal a su representacion en letras, en espanol,
    con la unidad monetaria y los centavos explicitos.

    Ejemplo: Decimal('5139915.83') -> "Cinco millones ciento treinta y nueve
    mil novecientos quince pesos M/CTE con ochenta y tres centavos".

    Args:
        valor: monto, cualquier signo (los negativos se prefijan "menos").
        moneda: codigo ISO de 3 letras. Solo COP tiene traduccion a "pesos" --
            cualquier otra moneda se etiqueta con su propio codigo (no se
            inventa la palabra en espanol de una moneda no soportada).
    """
    valor = Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    negativo = valor < 0
    valor = abs(valor)

    entero = int(valor)
    centavos = int((valor - entero) * 100)

    texto_entero = _apocope_masculino(_entero_a_letras(entero))
    unidad = 'peso' if entero == 1 else 'pesos'
    etiqueta_moneda = f'{unidad} M/CTE' if moneda == 'COP' else f'{unidad} {moneda}'

    resultado = f'{texto_entero} {etiqueta_moneda}'
    if centavos:
        texto_centavos = _apocope_masculino(_hasta_999(centavos))
        sufijo_centavos = 'centavo' if centavos == 1 else 'centavos'
        resultado += f' con {texto_centavos} {sufijo_centavos}'

    if negativo:
        resultado = f'menos {resultado}'

    return resultado[0].upper() + resultado[1:]
