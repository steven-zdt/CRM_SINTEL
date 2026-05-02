from typing import Any
from django.db import transaction

from apps.tenant.empresa.models import Empresa

# Campos canónicos alineados con los serializers y UI
LIST_FIELDS = (
    "id",
    "razon_social",
    "nit",
    "dv",
    "direccion",
    "telefono",
    "email_contacto",
    "regimen_tributario",
    "moneda",
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "razon_social",
    "nit",
    "dv",
    "direccion",
    "telefono",
    "email_contacto",
    "regimen_tributario",
    "logo",
    "website",
    "moneda",
    "created_at",
    "updated_at",
)


def qs_list(search=None):
    from django.db.models import Q

    qs = Empresa.objects.only(*LIST_FIELDS)
    if search:
        qs = qs.filter(
            Q(razon_social__icontains=search) |
            Q(nit__icontains=search) |
            Q(email_contacto__icontains=search) |
            Q(direccion__icontains=search) |
            Q(telefono__icontains=search)
        )
    return qs


def qs_detail():
    return Empresa.objects.only(*DETAIL_FIELDS)


def get_empresa_data() -> dict[str, Any] | None:
    empresa = Empresa.objects.only(*DETAIL_FIELDS).first()
    if not empresa:
        return None

    nit_completo = f"{empresa.nit}-{empresa.dv}" if empresa.dv else str(empresa.nit)
    logo_url = empresa.logo.url if empresa.logo else None

    return {
        'id': empresa.id,
        'razon_social': empresa.razon_social,
        'nit': str(empresa.nit),
        'dv': empresa.dv or None,
        'nit_completo': nit_completo,
        'direccion': empresa.direccion or '',
        'telefono': empresa.telefono or '',
        'email_contacto': empresa.email_contacto or None,
        'regimen_tributario': empresa.regimen_tributario or 'NO_RESPONDE',
        'logo': logo_url,
        'website': empresa.website or None,
        'moneda': empresa.moneda or 'COP',
    }


@transaction.atomic
def crear_empresa_db(data: dict) -> Empresa:
    # Solo considerar conflicto si existe la instancia singleton (clave 1)
    if Empresa.objects.filter(singleton_key=1).exists():
        raise ValueError("Ya existe Empresa singleton en este tenant.")
    empresa = Empresa.objects.create(**data)
    return empresa


@transaction.atomic
def actualizar_empresa_db(data: dict) -> Empresa:
    empresa = Empresa.objects.only('id', 'razon_social', 'nit').first()
    if not empresa:
        raise Empresa.DoesNotExist("No existe empresa configurada para este tenant.")

    campos_permitidos = [
        'razon_social', 'nit', 'dv', 'direccion', 'telefono',
        'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda'
    ]
    for campo, valor in data.items():
        if campo in campos_permitidos and hasattr(empresa, campo):
            setattr(empresa, campo, valor)

    empresa.full_clean()
    empresa.save()
    return empresa


def get_empresa_emisor_data() -> dict[str, Any]:
    empresa = (
        Empresa.objects
        .only("id", "nit", "razon_social", "dv", "direccion", "telefono", "email_contacto")
        .order_by("id")
        .first()
    )

    if not empresa:
        raise Exception("Empresa no configurada en el tenant")

    if not empresa.nit:
        raise Exception("Empresa existe pero no tiene NIT asignado")

    nit_completo = f"{empresa.nit}-{empresa.dv}" if empresa.dv else str(empresa.nit)

    return {
        'nit': str(empresa.nit),
        'razon_social': empresa.razon_social,
        'dv': empresa.dv or '',
        'nit_completo': nit_completo,
        'direccion': empresa.direccion or '',
        'telefono': empresa.telefono or '',
        'email_contacto': empresa.email_contacto or None,
    }


def get_mailbox_config(config_id: int):
    from apps.tenant.empresa.impl.mailbox_provider import get_mailbox_config as _get_mailbox_config
    return _get_mailbox_config(config_id)
