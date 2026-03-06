"""
Service Layer interno del dominio Empresa.

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Empresa.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Tipos, longitudes, formatos (NIT, email, URL), singleton
"""
from typing import Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError


def get_empresa() -> Optional[Dict[str, Any]]:
    """
    Obtiene la empresa del tenant actual (singleton).
    
    ⚠️ SINGLETON: Solo existe una empresa por tenant.
    
    Returns:
        dict: DTO con datos de la empresa o None si no existe
    """
    from apps.tenant.empresa.models import Empresa
    
    empresa = Empresa.objects.only(
        'id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
        'regimen_tributario', 'logo', 'website', 'moneda', 'created_at', 'updated_at'
    ).first()
    
    if not empresa:
        return None
    
    return {
        'id': empresa.id,
        'razon_social': empresa.razon_social,
        'nit': empresa.nit,
        'dv': empresa.dv,
        'nit_completo': f"{empresa.nit}-{empresa.dv}",
        'direccion': empresa.direccion,
        'telefono': empresa.telefono,
        'email_contacto': empresa.email_contacto or '',
        'regimen_tributario': empresa.regimen_tributario or '',
        'logo': empresa.logo.name if empresa.logo else None,
        'website': empresa.website or '',
        'moneda': empresa.moneda or 'COP',
        'created_at': empresa.created_at.isoformat() if empresa.created_at else None,
        'updated_at': empresa.updated_at.isoformat() if empresa.updated_at else None,
    }


def get_or_create_empresa(defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Obtiene o crea la empresa del tenant actual (singleton).
    
    ⚠️ SINGLETON: Solo existe una empresa por tenant.
    
    Args:
        defaults: Valores por defecto para crear la empresa si no existe
    
    Returns:
        dict: DTO con datos de la empresa
    """
    empresa_dto = get_empresa()
    if empresa_dto:
        return empresa_dto
    
    # Si no existe, crear con defaults
    if defaults is None:
        defaults = {
            'razon_social': 'Empresa',
            'nit': '000000000',
            'dv': '0',
            'direccion': '',
            'telefono': '',
            'moneda': 'COP',
        }
    
    from apps.tenant.empresa.models import Empresa
    
    empresa = Empresa.objects.create(**defaults)
    return get_empresa()


@transaction.atomic
def update_empresa(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza la empresa del tenant actual (singleton).
    
    ⚠️ v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    ⚠️ VALIDACIONES: Tipos, longitudes, formatos (NIT, email, URL), singleton.
    
    Args:
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos de la empresa actualizada
    
    Raises:
        ValueError: Si los datos no son válidos (tipo, longitud, formato)
    """
    from apps.tenant.empresa.models import Empresa
    
    empresa = Empresa.objects.first()
    if not empresa:
        raise ValueError("No existe una empresa para actualizar. Use get_or_create_empresa() primero.")
    
    # Validaciones específicas por campo (solo campos canónicos)
    campos_permitidos = [
        'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
        'regimen_tributario', 'logo', 'website', 'moneda'
    ]
    
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            valor = data[campo]
            
            # Validaciones específicas
            if campo == 'razon_social':
                if not isinstance(valor, str):
                    raise ValueError("El campo 'razon_social' debe ser una cadena de texto.")
                if len(valor) > 255:
                    raise ValueError("El campo 'razon_social' no puede exceder 255 caracteres.")
                if not valor.strip():
                    raise ValueError("El campo 'razon_social' no puede estar vacío.")
            
            elif campo == 'nit':
                if not isinstance(valor, str):
                    raise ValueError("El campo 'nit' debe ser una cadena de texto.")
                if len(valor) > 20:
                    raise ValueError("El campo 'nit' no puede exceder 20 caracteres.")
                if not valor.strip():
                    raise ValueError("El campo 'nit' no puede estar vacío.")
            
            elif campo == 'email_contacto':
                if valor and not isinstance(valor, str):
                    raise ValueError("El campo 'email_contacto' debe ser una cadena de texto o null.")
                if valor and '@' not in valor:
                    raise ValueError("El campo 'email_contacto' debe ser un email válido.")
            
            elif campo == 'website':
                if valor and not isinstance(valor, str):
                    raise ValueError("El campo 'website' debe ser una cadena de texto o null.")
                if valor and not valor.startswith(('http://', 'https://')):
                    raise ValueError("El campo 'website' debe ser una URL válida (http:// o https://).")
            
            setattr(empresa, campo, valor)
            update_fields.append(campo)
    
    if update_fields:
        empresa.save(update_fields=update_fields)
    
    return get_empresa()
