"""
Core Service Adapter para Empresa.

⚠️ v2.30: Core API como orquestador único de la UI privada.
- Este adapter consume el Service Layer del dominio Empresa (apps/tenant/empresa/services)
- Compone el DTO final incluyendo branding
- NO reimplementa lógica del dominio; solo orquesta y compone respuestas

Uso:
    from apps.tenant.core.services.empresa_adapter import (
        core_empresa_get,
        core_empresa_update,
        core_mailbox_list,
        core_mailbox_create,
        core_mailbox_update,
        core_mailbox_delete,
    )
"""
from typing import Dict, Any, Optional
from django.core.files.uploadedfile import UploadedFile


def core_empresa_get() -> Optional[Dict[str, Any]]:
    """
    Lee la empresa del tenant y retorna un DTO completo (incluyendo branding).
    
    ⚠️ v2.30: Core API - Compone el DTO final para consumo de la UI.
    Incluye branding dinámico.
    
    Returns:
        dict: DTO completo con empresa + branding o None si no existe
    """
    from apps.tenant.empresa.impl.empresa_service import get_empresa
    
    empresa_dto = get_empresa()
    if not empresa_dto:
        return None
    
    # Construir URL relativa del logo si existe
    logo_url = None
    if empresa_dto.get('logo'):
        try:
            from django.conf import settings
            logo_path = empresa_dto['logo']
            if hasattr(settings, 'MEDIA_URL'):
                media_url = settings.MEDIA_URL.rstrip('/')
                logo_path_clean = logo_path.lstrip('/')
                # Nota: URL absoluta se construye en la vista usando request.build_absolute_uri
                logo_url = f"{media_url}/{logo_path_clean}"
        except Exception:
            pass
    
    dto = {
        **empresa_dto,
        'logo_url': logo_url,  # URL relativa (la vista construye absoluta)
        # branding se agrega en la vista usando get_tenant_branding(request)
    }
    
    return dto


def core_empresa_update(data: Dict[str, Any], files: Optional[Dict[str, UploadedFile]] = None) -> Dict[str, Any]:
    """
    Actualiza la empresa del tenant y retorna un DTO completo.
    
    ⚠️ v2.30: Core API - Orquesta la actualización usando el Service Layer del dominio.
    Soporta actualización de campos básicos y logo (multipart).
    
    Args:
        data: Diccionario con campos a actualizar
        files: Diccionario con archivos (opcional, para logo)
    
    Returns:
        dict: DTO completo con empresa actualizada + branding
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.empresa.impl.empresa_service import update_empresa
    
    # Manejar logo si se proporciona
    if files and 'logo' in files:
        data['logo'] = files['logo']
    
    # Actualizar empresa usando el Service Layer
    empresa_dto = update_empresa(data)
    
    # Construir URL relativa del logo si existe
    logo_url = None
    if empresa_dto.get('logo'):
        try:
            from django.conf import settings
            logo_path = empresa_dto['logo']
            if hasattr(settings, 'MEDIA_URL'):
                media_url = settings.MEDIA_URL.rstrip('/')
                logo_path_clean = logo_path.lstrip('/')
                logo_url = f"{media_url}/{logo_path_clean}"
        except Exception:
            pass
    
    dto = {
        **empresa_dto,
        'logo_url': logo_url,  # URL relativa (la vista construye absoluta)
        # branding se agrega en la vista usando get_tenant_branding(request)
    }
    
    return dto


def core_mailbox_list(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    Lista configuraciones de buzones de correo (paginado).
    
    ⚠️ v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.empresa.impl.mailbox_service import list_mailbox_configs
    
    return list_mailbox_configs(page=page, page_size=page_size)


def core_mailbox_create(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una configuración de buzón de correo.
    
    ⚠️ v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        data: Diccionario con datos de la configuración
    
    Returns:
        dict: DTO con datos de la configuración creada
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.empresa.impl.mailbox_service import create_mailbox_config
    
    return create_mailbox_config(data)


def core_mailbox_update(config_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza una configuración de buzón de correo.
    
    ⚠️ v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        config_id: ID de la configuración
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos de la configuración actualizada
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.empresa.impl.mailbox_service import update_mailbox_config
    
    return update_mailbox_config(config_id, data)


def core_mailbox_delete(config_id: int) -> None:
    """
    Elimina una configuración de buzón de correo.
    
    ⚠️ v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        config_id: ID de la configuración
    
    Raises:
        MailInboxConfig.DoesNotExist: Si la configuración no existe
    """
    from apps.tenant.empresa.impl.mailbox_service import delete_mailbox_config
    
    delete_mailbox_config(config_id)
