"""
Servicio Provider para datos de Empresa (consumo interno entre apps).

⚠️ POLÍTICA SSoT (Single Source of Truth):
- Este servicio es la ÚNICA fuente de datos empresariales para consumo interno
- Otras TENANT_APPS deben usar este servicio en lugar de duplicar campos
- NO hacer llamadas HTTP internas; usar ORM directo para evitar latencia

⚠️ v2.37: Service Layer Pattern - Toda la lógica de negocio está aquí.
Las vistas/serializers solo orquestan las llamadas a estos servicios.

⚠️ ALINEACIÓN: Este módulo actúa como wrapper/adaptador del servicio interno (impl/).
Usa impl/empresa_service.py y impl/mailbox_provider.py para mantener consistencia.

Uso:
    from apps.tenant.empresa.services import get_empresa_data, get_empresa_emisor_data
    
    # Obtener datos de empresa del tenant actual
    empresa_data = get_empresa_data()
    if empresa_data:
        razon_social = empresa_data['razon_social']
        nit = empresa_data['nit']
        nit_completo = empresa_data['nit_completo']
        # ...
    
    # Obtener datos del emisor (SSoT para facturas)
    emisor_data = get_empresa_emisor_data()  # Lanza EmpresaNotConfiguredError si no existe
"""
from typing import Dict, Any, Optional
from django.db import connection, transaction
from apps.tenant.empresa.models import Empresa

# ⚠️ v2.37: LIST_FIELDS y DETAIL_FIELDS para alineación Serializers ↔ Services ↔ UI
# Campos canónicos alineados con el modelo refactorizado
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
    """
    QuerySet optimizado para listado (singleton, Tabulator v2.40).
    
    ⚠️ v2.40: Usa LIST_FIELDS con only().
    ⚠️ v2.40: Soporta filtrado por ?search= para Tabulator.
    ✅ Solo carga campos necesarios para la tabla
    """
    from django.db.models import Q
    
    qs = Empresa.objects.only(*LIST_FIELDS)
    
    # Aplicar filtro de búsqueda si se proporciona
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
    """
    QuerySet optimizado para detalle (retrieve).
    
    ⚠️ v2.37: Usa DETAIL_FIELDS con only().
    ✅ Solo carga campos necesarios para el detalle
    """
    return Empresa.objects.only(*DETAIL_FIELDS)


def get_empresa_data() -> Optional[Dict[str, Any]]:
    """
    Obtiene los datos de la empresa del tenant actual (singleton).
    
    ⚠️ POLÍTICA SSoT: Esta es la ÚNICA fuente de datos empresariales para consumo interno.
    Otras apps deben usar este servicio en lugar de duplicar campos.
    
    ⚠️ ALINEACIÓN: Usa campos canónicos del modelo directamente.
    
    Returns:
        Dict con datos de empresa o None si no existe:
        {
            'id': int,
            'razon_social': str,
            'nit': str,
            'dv': str | None,
            'nit_completo': str,  # "nit-dv" o "nit"
            'direccion': str,
            'telefono': str,
            'email_contacto': str | None,
            'regimen_tributario': str,  # default: "NO_RESPONDE"
            'logo': str | None,  # URL relativa del logo
            'website': str | None,
            'moneda': str,  # default: 'COP'
        }
    """
    try:
        empresa = Empresa.objects.only(*DETAIL_FIELDS).first()
        if not empresa:
            return None
        
        # Construir nit_completo
        nit_completo = f"{empresa.nit}-{empresa.dv}" if empresa.dv else str(empresa.nit)
        
        # Construir URL del logo si existe
        logo_url = None
        if empresa.logo:
            logo_url = empresa.logo.url
        
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
    except Exception:
        # Si hay error (modelo no disponible, etc.), retornar None
        return None


@transaction.atomic
def crear_empresa(data: dict):
    """
    Crea una nueva empresa para el tenant actual (singleton).
    
    ⚠️ Service Layer: Lógica para creación de empresa (Singleton).
    
    Args:
        data: Dict con datos de la empresa (contrato canónico del serializer)
    
    Returns:
        Instancia de Empresa creada
    
    Raises:
        ValueError: Si ya existe una empresa
    """
    from apps.tenant.empresa.models import Empresa
    
    # ⚠️ Zero Trust: Verificar si ya existe
    if Empresa.objects.exists():
        raise ValueError("Ya existe Empresa en este tenant.")
    
    # Crear nueva empresa
    empresa = Empresa.objects.create(**data)
    
    return empresa


@transaction.atomic
def actualizar_empresa(data: dict):
    """
    ⚠️ v2.60: Actualiza la empresa del tenant actual (singleton) con Zero Trust.
    
    ⚠️ Zero Trust: Valida que la empresa pertenezca al tenant actual.
    ⚠️ Service Layer: Toda la lógica de negocio está aquí.
    ⚠️ Transactional: Usa @transaction.atomic para garantizar integridad.
    
    Args:
        data: Dict con datos a actualizar (contrato canónico del serializer)
    
    Returns:
        Instancia de Empresa actualizada
    
    Raises:
        Empresa.DoesNotExist: Si no existe empresa en el tenant
        ValueError: Si hay errores de validación
    """
    from apps.tenant.empresa.models import Empresa
    
    # ⚠️ Zero Trust: Obtener empresa del tenant actual (singleton)
    empresa = Empresa.objects.only('id', 'razon_social', 'nit').first()
    if not empresa:
        raise Empresa.DoesNotExist("No existe empresa configurada para este tenant.")
    
    # ⚠️ PERFORMANCE BIBLE: Actualizar solo campos proporcionados
    campos_permitidos = [
        'razon_social', 'nit', 'dv', 'direccion', 'telefono', 
        'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda'
    ]
    
    for campo, valor in data.items():
        if campo in campos_permitidos and hasattr(empresa, campo):
            setattr(empresa, campo, valor)
    
    # Validar y guardar
    empresa.full_clean()
    empresa.save()
    
    return empresa


class EmpresaNotConfiguredError(Exception):
    """Excepción cuando no existe Empresa o carece de NIT en el tenant actual."""
    pass


def get_empresa_emisor_data() -> Dict[str, Any]:
    """
    SSoT: Devuelve el NIT de la Empresa del tenant actual.
    
    ⚠️ REQUISITO: Requiere que TenantMainMiddleware ya haya fijado el schema.
    Sin Empresa/NIT → lanza EmpresaNotConfiguredError (no retorna None).
    
    ⚠️ POLÍTICA: Facturas deben usar este servicio para obtener datos del emisor,
    NO deben duplicar campos como emisor_nit, emisor_razon_social.
    
    Returns:
        Dict con datos del emisor:
        {
            'nit': str,
            'razon_social': str,
            'dv': str | None,
            'nit_completo': str,
            'direccion': str,
            'telefono': str,
            'email_contacto': str | None,
        }
        
    Raises:
        EmpresaNotConfiguredError: Si no existe Empresa o carece de NIT
    """
    from apps.tenant.empresa.models import Empresa
    
    empresa = (
        Empresa.objects
        .only("id", "nit", "razon_social", "dv", "direccion", "telefono", "email_contacto")
        .order_by("id")
        .first()
    )
    
    if not empresa:
        raise EmpresaNotConfiguredError(
            "Empresa no configurada en el tenant: cree la Empresa y asigne NIT."
        )
    
    if not empresa.nit:
        raise EmpresaNotConfiguredError(
            f"Empresa '{empresa.razon_social}' existe pero no tiene NIT asignado."
        )
    
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


# ⚠️ RE-EXPORT: Funciones de mailbox_provider para consumo externo
# Estas funciones son parte del dominio Empresa y deben estar disponibles desde services.py
def get_mailbox_config(config_id: int):
    """
    Obtiene configuración de buzón de correo (SSoT para maildigester).
    
    ⚠️ SSoT: Este es el único lugar desde donde maildigester toma credenciales.
    ⚠️ RE-EXPORT: Wrapper de impl/mailbox_provider.get_mailbox_config()
    
    Args:
        config_id: ID de MailInboxConfig (debe estar activa)
        
    Returns:
        MailboxConfigDTO listo para usar en el pipeline de maildigester
        
    Raises:
        MailInboxConfig.DoesNotExist: Si la config no existe o no está activa
    """
    from apps.tenant.empresa.impl.mailbox_provider import get_mailbox_config as _get_mailbox_config
    return _get_mailbox_config(config_id)
