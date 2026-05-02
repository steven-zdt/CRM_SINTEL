"""
Service Layer interno del dominio Empresa.

# WARNING: v2.30: Service Layer Pattern - Lógica de negocio del dominio Empresa.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Tipos, longitudes, formatos (NIT, email, URL), singleton
"""
from typing import Any

from django.db import transaction


def get_empresa() -> dict[str, Any] | None:
    """
    Obtiene la empresa del tenant actual (singleton).
    
    # WARNING: SINGLETON: Solo existe una empresa por tenant.
    
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


@transaction.atomic
def get_or_create_empresa(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Obtiene o crea/actualiza la empresa del tenant actual (singleton).
    
    # WARNING: SINGLETON: Solo existe una empresa por tenant.
    # WARNING: v2.60: Si la empresa existe, actualiza los campos proporcionados en `defaults`.
    
    Args:
        defaults: Valores por defecto para crear la empresa si no existe, o campos a actualizar si ya existe
    
    Returns:
        dict: DTO con datos de la empresa (creada o actualizada)
    """
    from apps.tenant.empresa.models import Empresa
    
    # # WARNING: v2.60: Intentar obtener la empresa existente primero
    empresa = Empresa.objects.first()
    
    if empresa:
        # # WARNING: v2.60: Si existe, actualizar los campos proporcionados en defaults
        if defaults:
            # Validar y actualizar solo campos permitidos
            campos_permitidos = [
                'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
                'regimen_tributario', 'logo', 'website', 'moneda'
            ]
            
            update_fields = []
            for campo, valor in defaults.items():
                if campo in campos_permitidos:
                    # # WARNING: Validaciones básicas (similares a update_empresa)
                    if campo == 'razon_social' and valor and not isinstance(valor, str):
                        raise ValueError("El campo 'razon_social' debe ser una cadena de texto.")
                    if campo == 'nit' and valor and not isinstance(valor, str):
                        raise ValueError("El campo 'nit' debe ser una cadena de texto.")
                    if campo == 'email_contacto' and valor and not isinstance(valor, str):
                        raise ValueError("El campo 'email_contacto' debe ser una cadena de texto o null.")
                    if campo == 'website' and valor and not isinstance(valor, str):
                        raise ValueError("El campo 'website' debe ser una cadena de texto o null.")
                    
                    setattr(empresa, campo, valor)
                    update_fields.append(campo)
            
            if update_fields:
                empresa.save(update_fields=update_fields)
        
        # Retornar DTO actualizado
        return get_empresa()
    
    # # WARNING: v2.60: Si no existe, crear con defaults
    if defaults is None:
        defaults = {
            'razon_social': 'Empresa',
            'nit': '000000000',
            'dv': '0',
            'direccion': '',
            'telefono': '',
            'moneda': 'COP',
        }
    
    # # WARNING: v2.60: Crear nueva empresa
    # Si el NIT ya existe (caso edge), intentar obtener y actualizar en lugar de crear
    try:
        empresa = Empresa.objects.create(**defaults)
    except Exception as e:
        # # WARNING: PROTECCIÓN: Si falla por NIT duplicado u otra constraint, intentar obtener y actualizar
        # Esto puede pasar en condiciones de carrera o si hay datos inconsistentes
        if 'nit' in str(e).lower() or 'unique' in str(e).lower():
            # Intentar obtener por NIT si está en defaults
            if 'nit' in defaults:
                empresa_existente = Empresa.objects.filter(nit=defaults['nit']).first()
                if empresa_existente:
                    # Actualizar la empresa existente con los demás campos
                    for campo, valor in defaults.items():
                        if campo != 'nit':  # No actualizar NIT si ya existe
                            setattr(empresa_existente, campo, valor)
                    empresa_existente.save()
                    return get_empresa()
        
        # Si no es un error de NIT duplicado, re-lanzar la excepción
        raise
    
    return get_empresa()


@transaction.atomic
def update_empresa(data: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza la empresa del tenant actual (singleton).
    
    # WARNING: v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    # WARNING: VALIDACIONES: Tipos, longitudes, formatos (NIT, email, URL), singleton.
    
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
