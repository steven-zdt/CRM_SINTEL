"""
Servicios de negocio para clientes.

Service Layer: lógica de negocio sin presentación.
Validaciones y reglas mínimas.
"""
from __future__ import annotations
from django.db import transaction
from ..models import Cliente, VentaCliente


@transaction.atomic
def upsert_cliente(data: dict) -> Cliente:
    """
    Crea/actualiza cliente por (tipo_documento, numero_documento).
    """
    lookup = {
        "tipo_documento": data["tipo_documento"],
        "numero_documento": data["numero_documento"]
    }
    obj, _ = Cliente.objects.update_or_create(defaults=data, **lookup)
    return obj


@transaction.atomic
def registrar_venta_cliente(cliente_id: int, factura_id: int) -> VentaCliente:
    """
    Registra la asociación Cliente–Factura (venta). Idempotente por unique_together.
    """
    obj, _ = VentaCliente.objects.get_or_create(cliente_id=cliente_id, factura_id=factura_id)
    return obj
