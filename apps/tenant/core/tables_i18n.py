"""
F33.6: wording compartido para el `empty_text` de django-tables2.

F33_SHARED_UI_INVENTORY.md §3a encontro 4 frases distintas para el mismo
mensaje semantico (lista vacia) entre apps, incluso dentro de un mismo
archivo (`empleados/tables.py`). No es un componente -- es una constante
de texto reutilizable, para que las tablas nuevas no reinventen el
wording. No se migran las tablas existentes en esta pasada (seria
refactor masivo sin valor real, el wording actual no esta roto).
"""


def empty_text(entidad_plural: str, genero: str = "o") -> str:
    """
    Genera el texto estandar para listas vacias.

    Args:
        entidad_plural: sustantivo plural en minuscula, ej. "facturas".
        genero: "o" (registrados) o "a" (registradas), segun concordancia.

    Ejemplo:
        empty_text("facturas", "a")  -> "Sin facturas registradas"
        empty_text("clientes")       -> "Sin clientes registrados"
    """
    return f"Sin {entidad_plural} registrad{genero}s"
