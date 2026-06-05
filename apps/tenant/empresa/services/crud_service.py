from typing import Any

from django.db import transaction
from django.db.models import Q

from apps.tenant.empresa.impl.mailbox_provider import get_mailbox_config as _get_mailbox_config
from apps.tenant.empresa.models import Area, Empresa, Sede

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
    return _get_mailbox_config(config_id)


@transaction.atomic
def crear_sede_db(empresa_id: int, data: dict) -> Sede:
    nombre = data.get('nombre')
    if Sede.objects.filter(empresa_id=empresa_id, nombre=nombre).exists():
        raise ValueError("Ya existe una sede con este nombre en la empresa.")
    
    sede = Sede(
        empresa_id=empresa_id,
        nombre=nombre,
        direccion=data.get('direccion', ''),
        telefono=data.get('telefono', ''),
        encargado_nombre=data.get('encargado_nombre', '')
    )
    sede.full_clean()
    sede.save()
    return sede


@transaction.atomic
def actualizar_sede_db(sede: Sede, data: dict) -> Sede:
    nombre = data.get('nombre')
    if nombre and Sede.objects.filter(empresa_id=sede.empresa_id, nombre=nombre).exclude(pk=sede.pk).exists():
        raise ValueError("Ya existe otra sede con este nombre en la empresa.")
    
    if 'nombre' in data:
        sede.nombre = data['nombre']
    if 'direccion' in data:
        sede.direccion = data['direccion']
    if 'telefono' in data:
        sede.telefono = data['telefono']
    if 'encargado_nombre' in data:
        sede.encargado_nombre = data['encargado_nombre']
        
    sede.full_clean()
    sede.save()
    return sede


@transaction.atomic
def eliminar_sede_db(sede: Sede) -> None:
    if sede.areas.exists():
        raise ValueError("No se puede eliminar la sede porque tiene areas asociadas.")
    sede.delete()


@transaction.atomic
def crear_area_db(empresa_id: int, data: dict) -> Area:
    sede_id = data.get('sede')
    # Validar que sede pertenece a empresa_id (anti-IDOR / DSV)
    sede = Sede.objects.filter(empresa_id=empresa_id, pk=sede_id).first()
    if not sede:
        raise ValueError("La sede especificada no existe o no pertenece a la empresa.")
        
    nombre = data.get('nombre')
    codigo_funcionamiento = data.get('codigo_funcionamiento')
    
    if Area.objects.filter(sede=sede, nombre=nombre).exists():
        raise ValueError("Ya existe un area con este nombre en la sede especificada.")
    if Area.objects.filter(sede=sede, codigo_funcionamiento=codigo_funcionamiento).exists():
        raise ValueError("Ya existe un area con este codigo de funcionamiento en la sede especificada.")
        
    area = Area(
        empresa_id=empresa_id,
        sede=sede,
        nombre=nombre,
        codigo_funcionamiento=codigo_funcionamiento
    )
    area.full_clean()
    area.save()
    return area


@transaction.atomic
def actualizar_area_db(area: Area, data: dict) -> Area:
    if 'sede' in data:
        sede_id = data['sede']
        sede = Sede.objects.filter(empresa_id=area.empresa_id, pk=sede_id).first()
        if not sede:
            raise ValueError("La sede especificada no existe o no pertenece a la empresa.")
        area.sede = sede

    nombre = data.get('nombre', area.nombre)
    codigo_funcionamiento = data.get('codigo_funcionamiento', area.codigo_funcionamiento)
    
    if Area.objects.filter(sede=area.sede, nombre=nombre).exclude(pk=area.pk).exists():
        raise ValueError("Ya existe otra area con este nombre en la sede especificada.")
    if Area.objects.filter(sede=area.sede, codigo_funcionamiento=codigo_funcionamiento).exclude(pk=area.pk).exists():
        raise ValueError("Ya existe otra area con este codigo de funcionamiento en la sede especificada.")
        
    if 'nombre' in data:
        area.nombre = data['nombre']
    if 'codigo_funcionamiento' in data:
        area.codigo_funcionamiento = data['codigo_funcionamiento']
        
    area.full_clean()
    area.save()
    return area


@transaction.atomic
def eliminar_area_db(area: Area) -> None:
    area.delete()
