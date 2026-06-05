"""
Paquete de servicios para la app `empresa`.
Exporta un wrapper de compatibilidad para llamadas existentes.
"""

from typing import Any

from apps.tenant.empresa.impl.mailbox_provider import get_mailbox_config as _get_mailbox_config_impl
from apps.tenant.empresa.models import Empresa
from . import business_service  # noqa: F401
from . import crud_service  # noqa: F401

from .selectors import EmpresaSelector, SedeSelector, AreaSelector
from .business_service import EmpresaService, SedeService, AreaService

__all__ = [
    'EmpresaSelector',
    'SedeSelector',
    'AreaSelector',
    'EmpresaService',
    'SedeService',
    'AreaService',
    'EmpresaNotConfiguredError',
    'get_empresa_emisor_data',
    'get_mailbox_config',
]

class EmpresaNotConfiguredError(Exception):
    """Excepción cuando no existe Empresa o carece de NIT en el tenant actual."""
    pass


def get_empresa_emisor_data() -> dict[str, Any]:
    """
    SSoT: Devuelve el NIT de la Empresa del tenant actual.
    
    # WARNING: REQUISITO: Requiere que TenantMainMiddleware ya haya fijado el schema.
    Sin Empresa/NIT → lanza EmpresaNotConfiguredError (no retorna None).
    
    # WARNING: POLÍTICA: Facturas deben usar este servicio para obtener datos del emisor,
    NO deben duplicar campos como emisor_nit, emisor_razon_social.
    
    Returns:
        Dict con datos del emisor.
    """
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


def get_mailbox_config(config_id: int):
    """
    Obtiene configuración de buzón de correo (SSoT para maildigester).
    """
    return _get_mailbox_config_impl(config_id)
