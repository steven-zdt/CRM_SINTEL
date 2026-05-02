"""
Servicios de negocio para devengos (desprendibles de pago).

Service Layer: lógica de negocio sin presentación.
"""
from django.db import transaction

from ..models import Devengo


@transaction.atomic
def upsert_devengo(data: dict) -> Devengo:
    """
    Crea o actualiza un devengo por (empleado, periodo_inicio, periodo_fin).
    Los totales se calculan en .save() del modelo (server-side).
    """
    obj, _ = Devengo.objects.update_or_create(
        empleado_id=data["empleado"],
        periodo_inicio=data["periodo_inicio"],
        periodo_fin=data["periodo_fin"],
        defaults=data
    )
    obj.save()  # dispara cálculo de totales
    return obj
