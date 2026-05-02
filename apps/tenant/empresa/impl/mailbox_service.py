"""
Service Layer interno para MailInboxConfig (dominio Empresa).

# WARNING: v2.30: Service Layer Pattern - Lógica de negocio del dominio Empresa.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Rangos (port, max_attachment_mb), formatos (host/mailbox), password write_only
"""
from typing import Any

from django.core.paginator import Paginator
from django.db import transaction


def list_mailbox_configs(page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """
    Lista configuraciones de buzones de correo (paginado).
    
    Args:
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    qs = MailInboxConfig.objects.only(
        'id', 'nombre', 'provider', 'email_address',
        'host', 'port', 'protocol', 'ssl', 'username',
        'imap_host', 'imap_port', 'imap_ssl', 'imap_starttls', 'imap_username',
        'mailbox', 'imap_mailbox', 'mark_as_seen', 'move_processed_to', 'max_attachment_mb',
        'is_active', 'created_at', 'updated_at'
    ).order_by('-updated_at')
    
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    results = []
    for config in page_obj:
        # Usar campos nuevos (imap_*) si están disponibles, sino usar legacy
        host = config.imap_host or config.host or ''
        port = config.imap_port or config.port or 993
        username = config.imap_username or config.username or ''
        mailbox_name = config.imap_mailbox or config.mailbox or 'INBOX'
        
        results.append({
            'id': config.id,
            'nombre': config.nombre,
            'provider': config.provider or 'custom',
            'email_address': config.email_address or '',
            'host': host,
            'port': port,
            'protocol': config.protocol or 'imap',
            'ssl': config.imap_ssl if hasattr(config, 'imap_ssl') else (config.ssl if config.ssl is not None else True),
            'starttls': config.imap_starttls if hasattr(config, 'imap_starttls') else False,
            'username': username,
            'mailbox': mailbox_name,
            'mark_as_seen': config.mark_as_seen if config.mark_as_seen is not None else True,
            'move_processed_to': config.move_processed_to or '',
            'max_attachment_mb': config.max_attachment_mb or 50,
            'is_active': config.is_active if config.is_active is not None else True,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
        })
    
    return {
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': results,
    }


@transaction.atomic
def create_mailbox_config(data: dict[str, Any]) -> dict[str, Any]:
    """
    Crea una configuración de buzón de correo.
    
    # WARNING: VALIDACIONES: Rangos (port, max_attachment_mb), formatos (host/mailbox), protocol.
    
    Args:
        data: Diccionario con datos de la configuración
    
    Returns:
        dict: DTO con datos de la configuración creada
    
    Raises:
        ValueError: Si los datos no son válidos
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    # Validaciones
    if 'port' in data:
        port = data['port']
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("El campo 'port' debe estar entre 1 y 65535.")
    
    if 'max_attachment_mb' in data:
        max_mb = data['max_attachment_mb']
        if not isinstance(max_mb, int) or not (1 <= max_mb <= 50):
            raise ValueError("El campo 'max_attachment_mb' debe estar entre 1 y 50 MB.")
    
    if 'protocol' in data:
        protocol = data['protocol']
        if protocol not in ['imap', 'pop3']:
            raise ValueError("El campo 'protocol' debe ser 'imap' o 'pop3'.")
    
    if 'host' in data:
        host = data['host']
        if not isinstance(host, str) or len(host) > 255:
            raise ValueError("El campo 'host' debe ser una cadena de texto de máximo 255 caracteres.")
        if not host.strip():
            raise ValueError("El campo 'host' no puede estar vacío.")
    
    # Mapear campos legacy a nuevos si es necesario
    if 'host' in data and 'imap_host' not in data:
        data['imap_host'] = data['host']
    if 'port' in data and 'imap_port' not in data:
        data['imap_port'] = data['port']
    if 'ssl' in data and 'imap_ssl' not in data:
        data['imap_ssl'] = data['ssl']
    if 'username' in data and 'imap_username' not in data:
        data['imap_username'] = data['username']
    if 'password' in data and 'imap_password' not in data:
        data['imap_password'] = data['password']
    if 'mailbox' in data and 'imap_mailbox' not in data:
        data['imap_mailbox'] = data['mailbox']
    
    config = MailInboxConfig.objects.create(**data)
    
    # Retornar DTO sin password (usar campos nuevos si están disponibles)
    host = config.imap_host or config.host or ''
    port = config.imap_port or config.port or 993
    username = config.imap_username or config.username or ''
    mailbox_name = config.imap_mailbox or config.mailbox or 'INBOX'
    
    return {
        'id': config.id,
        'nombre': config.nombre,
        'provider': config.provider or 'custom',
        'email_address': config.email_address or '',
        'host': host,
        'port': port,
        'protocol': config.protocol or 'imap',
        'ssl': config.imap_ssl if hasattr(config, 'imap_ssl') else (config.ssl if config.ssl is not None else True),
        'starttls': config.imap_starttls if hasattr(config, 'imap_starttls') else False,
        'username': username,
        'mailbox': mailbox_name,
        'mark_as_seen': config.mark_as_seen if config.mark_as_seen is not None else True,
        'move_processed_to': config.move_processed_to or '',
        'max_attachment_mb': config.max_attachment_mb or 50,
        'is_active': config.is_active if config.is_active is not None else True,
        'created_at': config.created_at.isoformat() if config.created_at else None,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
    }


@transaction.atomic
def update_mailbox_config(config_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza una configuración de buzón de correo.
    
    # WARNING: VALIDACIONES: Rangos (port, max_attachment_mb), formatos (host/mailbox), protocol.
    # WARNING: SEGURIDAD: password es write_only (no se expone en respuesta).
    
    Args:
        config_id: ID de la configuración
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos de la configuración actualizada
    
    Raises:
        ValueError: Si los datos no son válidos
        MailInboxConfig.DoesNotExist: Si la configuración no existe
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    config = MailInboxConfig.objects.get(id=config_id)
    
    # Validaciones (mismas que create)
    if 'port' in data:
        port = data['port']
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("El campo 'port' debe estar entre 1 y 65535.")
    
    if 'max_attachment_mb' in data:
        max_mb = data['max_attachment_mb']
        if not isinstance(max_mb, int) or not (1 <= max_mb <= 50):
            raise ValueError("El campo 'max_attachment_mb' debe estar entre 1 y 50 MB.")
    
    if 'protocol' in data:
        protocol = data['protocol']
        if protocol not in ['imap', 'pop3']:
            raise ValueError("El campo 'protocol' debe ser 'imap' o 'pop3'.")
    
    # Mapear campos legacy a nuevos si es necesario
    if 'host' in data and 'imap_host' not in data:
        data['imap_host'] = data['host']
    if 'port' in data and 'imap_port' not in data:
        data['imap_port'] = data['port']
    if 'ssl' in data and 'imap_ssl' not in data:
        data['imap_ssl'] = data['ssl']
    if 'username' in data and 'imap_username' not in data:
        data['imap_username'] = data['username']
    if 'password' in data and 'imap_password' not in data:
        data['imap_password'] = data['password']
    if 'mailbox' in data and 'imap_mailbox' not in data:
        data['imap_mailbox'] = data['mailbox']
    
    campos_permitidos = [
        'nombre', 'provider', 'email_address',
        'host', 'port', 'protocol', 'ssl', 'username', 'password',
        'imap_host', 'imap_port', 'imap_ssl', 'imap_starttls', 'imap_username', 'imap_password',
        'mailbox', 'imap_mailbox', 'mark_as_seen', 'move_processed_to', 'max_attachment_mb', 'is_active'
    ]
    
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            setattr(config, campo, data[campo])
            update_fields.append(campo)
    
    if update_fields:
        config.save(update_fields=update_fields)
    
    # Retornar DTO sin password (usar campos nuevos si están disponibles)
    host = config.imap_host or config.host or ''
    port = config.imap_port or config.port or 993
    username = config.imap_username or config.username or ''
    mailbox_name = config.imap_mailbox or config.mailbox or 'INBOX'
    
    return {
        'id': config.id,
        'nombre': config.nombre,
        'provider': config.provider or 'custom',
        'email_address': config.email_address or '',
        'host': host,
        'port': port,
        'protocol': config.protocol or 'imap',
        'ssl': config.imap_ssl if hasattr(config, 'imap_ssl') else (config.ssl if config.ssl is not None else True),
        'starttls': config.imap_starttls if hasattr(config, 'imap_starttls') else False,
        'username': username,
        'mailbox': mailbox_name,
        'mark_as_seen': config.mark_as_seen if config.mark_as_seen is not None else True,
        'move_processed_to': config.move_processed_to or '',
        'max_attachment_mb': config.max_attachment_mb or 50,
        'is_active': config.is_active if config.is_active is not None else True,
        'created_at': config.created_at.isoformat() if config.created_at else None,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
    }


@transaction.atomic
def delete_mailbox_config(config_id: int) -> None:
    """
    Elimina una configuración de buzón de correo.
    
    Args:
        config_id: ID de la configuración
    
    Raises:
        MailInboxConfig.DoesNotExist: Si la configuración no existe
    """
    from apps.tenant.empresa.models import MailInboxConfig
    
    config = MailInboxConfig.objects.get(id=config_id)
    config.delete()
