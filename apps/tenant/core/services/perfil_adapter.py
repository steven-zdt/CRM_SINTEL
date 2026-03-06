"""
Core Service Adapter para Perfil.

⚠️ v2.30: Core API como orquestador único de la UI privada.
- Este adapter consume el Service Layer del dominio Perfil (apps/tenant/perfil/services)
- Compone el DTO final incluyendo campos de solo lectura del User global
- NO reimplementa lógica del dominio; solo orquesta y compone respuestas

Uso:
    from apps.tenant.core.services.perfil_adapter import (
        core_me_read,
        core_me_update,
        core_me_update_config,
    )
    
    # Leer perfil
    dto = core_me_read(user)
    
    # Actualizar perfil
    dto = core_me_update(user, {'cargo': 'Nuevo cargo'}, files={'avatar': archivo})
    
    # Actualizar configuración
    dto = core_me_update_config(user, {'tema': 'oscuro'}, merge=True)
"""
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile

User = get_user_model()


def core_me_read(user: User) -> Dict[str, Any]:
    """
    Lee el perfil del usuario y retorna un DTO completo (incluyendo campos del User global).
    
    ⚠️ v2.30: Core API - Compone el DTO final para consumo de la UI.
    Incluye campos de solo lectura del User global (user_id, user_email, etc.).
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
    
    Returns:
        dict: DTO completo con perfil + campos del User global
    """
    from apps.tenant.perfil.services.perfil_service import read_profile
    
    # Obtener datos del perfil desde el Service Layer
    perfil_dto = read_profile(user)
    
    # Componer DTO final con campos del User global (solo lectura)
    dto = {
        **perfil_dto,
        # Campos de solo lectura del User global
        'user_id': user.id,
        'user_email': user.email,
        'user_username': user.username,
        'user_first_name': user.first_name or '',
        'user_last_name': user.last_name or '',
        'user_full_name': _get_user_full_name(user),
    }
    
    return dto


def core_me_update(
    user: User,
    data: Dict[str, Any],
    files: Optional[Dict[str, UploadedFile]] = None
) -> Dict[str, Any]:
    """
    Actualiza el perfil del usuario y retorna un DTO completo.
    
    ⚠️ v2.30: Core API - Orquesta la actualización usando el Service Layer del dominio.
    Soporta actualización de campos básicos y avatar (multipart).
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        data: Diccionario con campos a actualizar (cargo, departamento, telefono_corporativo, configuracion)
        files: Diccionario con archivos (opcional, para avatar)
    
    Returns:
        dict: DTO completo con perfil actualizado + campos del User global
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.perfil.services.perfil_service import update_profile
    
    # Actualizar perfil usando el Service Layer
    perfil_dto = update_profile(user, data, files=files)
    
    # Componer DTO final con campos del User global (solo lectura)
    dto = {
        **perfil_dto,
        # Campos de solo lectura del User global
        'user_id': user.id,
        'user_email': user.email,
        'user_username': user.username,
        'user_first_name': user.first_name or '',
        'user_last_name': user.last_name or '',
        'user_full_name': _get_user_full_name(user),
    }
    
    return dto


def core_me_update_config(user: User, config: Dict[str, Any], merge: bool = True) -> Dict[str, Any]:
    """
    Actualiza la configuración de UI del perfil y retorna un DTO completo.
    
    ⚠️ v2.30: Core API - Orquesta la actualización de configuración usando el Service Layer.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        config: Diccionario con la configuración a actualizar
        merge: Si True, hace merge superficial preservando valores existentes. Si False, reemplaza toda la configuración.
    
    Returns:
        dict: DTO completo con perfil actualizado + campos del User global
    
    Raises:
        ValueError: Si la configuración no es válida (propagado desde el Service Layer)
    """
    from apps.tenant.perfil.services.perfil_service import update_profile_config
    
    # Actualizar configuración usando el Service Layer
    perfil_dto = update_profile_config(user, config, merge=merge)
    
    # Componer DTO final con campos del User global (solo lectura)
    # Nota: avatar_url se construye en la vista usando request.build_absolute_uri
    dto = {
        **perfil_dto,
        # Campos de solo lectura del User global
        'user_id': user.id,
        'user_email': user.email,
        'user_username': user.username,
        'user_first_name': user.first_name or '',
        'user_last_name': user.last_name or '',
        'user_full_name': _get_user_full_name(user),
    }
    
    return dto


def _get_user_full_name(user: User) -> str:
    """
    Retorna el nombre completo del usuario (first_name + last_name).
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
    
    Returns:
        str: Nombre completo o email si no hay nombre
    """
    parts = [user.first_name, user.last_name]
    full_name = ' '.join(filter(None, parts))
    return full_name or user.email
