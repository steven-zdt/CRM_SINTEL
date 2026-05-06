"""
Servicios de negocio para gastos.

Service Layer: lógica de negocio sin presentación.
Validaciones y reglas contables mínimas.
"""
from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction

from ..models import Gasto

_PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM

# Subtipos permitidos por tipo
_ALLOWED_BY_TYPE = {
    "PERSONAL": {"SALARIO", "APORTE_SALUD", "APORTE_PENSION", "APORTE_ARL", "APORTE_CAJA"},
    "OPERATIVO": {"ARRENDAMIENTO", "SERVICIOS", "VIATICOS", "INSUMOS", "MANUTENCION", "OTRO"},
    "ADMIN": {"ARRENDAMIENTO", "SERVICIOS", "VIATICOS", "INSUMOS", "MANUTENCION", "OTRO"},
    "MANUTENCION": {"MANUTENCION", "OTRO"},
}


@transaction.atomic
def crear_o_actualizar_gasto(data: dict) -> Gasto:
    """
    Crea/actualiza un gasto SIN IVA con reglas mínimas:
      - valor > 0 (sin IVA)
      - periodo = YYYY-MM
      - coherencia tipo/subtipo
      - si tipo==PERSONAL y subtipo==SALARIO -> requiere empleado o devengo
    """
    # Validaciones base
    valor = Decimal(str(data.get("valor", "0")))
    if valor <= 0:
        raise ValueError("El valor del gasto debe ser mayor a 0 y SIN IVA.")

    periodo = data.get("periodo", "")
    if not _PERIODO_RE.match(periodo):
        raise ValueError("Periodo inválido. Formato esperado: YYYY-MM (ej: 2026-01).")

    tipo = data.get("tipo")
    subtipo = data.get("subtipo")
    if not tipo or not subtipo or subtipo not in _ALLOWED_BY_TYPE.get(tipo, set()):
        raise ValueError(f"Subtipo '{subtipo}' no permitido para tipo '{tipo}'.")

    if tipo == "PERSONAL" and subtipo == "SALARIO":
        if not data.get("empleado") and not data.get("devengo"):
            raise ValueError("Gasto de salario requiere 'empleado' o 'devengo' asociado.")

    # Upsert por (fecha, periodo, tipo, subtipo, comprobante opcional)
    lookup = {
        "fecha": data["fecha"],
        "periodo": periodo,
        "tipo": tipo,
        "subtipo": subtipo,
        "comprobante": data.get("comprobante", ""),
    }

    obj, _created = Gasto.objects.update_or_create(defaults=data, **lookup)
    return obj
