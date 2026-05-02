"""
Service Layer interno del dominio Perfil.

WARNING: v2.30: Service Layer Pattern - Lógica de negocio del dominio Perfil.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Tipos, longitud, MIME, tamaño de archivos

Este módulo contiene la lógica de negocio pura del dominio Perfil.
No debe tener dependencias de HTTP, vistas o serializers.
"""
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

User = get_user_model()


def get_or_create_profile(user: User, defaults: dict[str, Any] | None = None) -> 'TenantProfile':
    """
    Obtiene o crea el perfil del usuario en el tenant actual.
    
    WARNING: TENANT ISOLATION: django-tenants maneja automáticamente el aislamiento
    por esquema, así que el perfil se crea/obtiene del esquema del tenant actual.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        defaults: Valores por defecto para crear el perfil si no existe
    
    Returns:
        TenantProfile: Perfil del usuario en el tenant actual
    """
    from apps.tenant.perfil.models import TenantProfile
    
    # Valores por defecto si no se proporcionan
    if defaults is None:
        defaults = {
            'cargo': 'Colaborador',
            'departamento': '',
            'configuracion': {}
        }
    
    # Intentar obtener el perfil existente
    try:
        perfil = TenantProfile.objects.filter(user=user).only(
            "id",
            "user_id",
            "empresa_id",
            "cargo",
            "departamento",
            "telefono_corporativo",
            "avatar",
            "configuracion",
            "created_at",
            "updated_at",
        ).get()
        return perfil
    except TenantProfile.DoesNotExist:
        # Crear el perfil con valores por defecto
        perfil = TenantProfile.objects.create(
            user=user,
            **defaults
        )
        return perfil


def read_profile(user: User) -> dict[str, Any]:
    """
    Lee el perfil del usuario y retorna un DTO (dict).
    
    WARNING: v2.30: Retorna un diccionario con todos los campos del perfil,
    incluyendo campos calculados (no incluye campos del User global; eso lo hace el adapter).
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
    
    Returns:
        dict: DTO con los datos del perfil
    """
    perfil = get_or_create_profile(user)
    
    return {
        'id': perfil.id,
        'cargo': perfil.cargo,
        'departamento': perfil.departamento or '',
        'telefono_corporativo': perfil.telefono_corporativo or '',
        'avatar': perfil.avatar.name if perfil.avatar else None,
        'configuracion': perfil.configuracion or {},
        'created_at': perfil.created_at.isoformat() if perfil.created_at else None,
        'updated_at': perfil.updated_at.isoformat() if perfil.updated_at else None,
    }


@transaction.atomic
def update_profile(user: User, data: dict[str, Any], files: dict[str, UploadedFile] | None = None) -> dict[str, Any]:
    """
    Actualiza el perfil del usuario con los datos proporcionados.
    
    WARNING: v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    WARNING: VALIDACIONES: Tipos, longitud de campos, MIME y tamaño de avatar.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        data: Diccionario con campos a actualizar (cargo, departamento, telefono_corporativo, configuracion)
        files: Diccionario con archivos (opcional, para avatar)
    
    Returns:
        dict: DTO con los datos del perfil actualizado
    
    Raises:
        ValueError: Si los datos no son válidos (tipo, longitud, MIME, tamaño)
    """
    
    # Obtener o crear el perfil
    perfil = get_or_create_profile(user)

    # Double Semantic Verification: reject attempts to change tenant/user via payload
    if isinstance(data, dict):
        if "empresa_id" in data or "empresa" in data:
            incoming = data.get("empresa_id") or data.get("empresa")
            if incoming is not None and int(incoming) != int(getattr(perfil, "empresa_id", 0)):
                raise ValueError("Payload contains empresa that does not match tenant (anti-IDOR)")
        if "user_id" in data or "user" in data:
            incoming_user = data.get("user_id") or data.get("user")
            if incoming_user is not None and int(incoming_user) != int(user.id):
                raise ValueError("Payload contains user id that does not match authenticated user (anti-IDOR)")
    
    # Validar y actualizar campos básicos
    campos_permitidos = ['cargo', 'departamento', 'telefono_corporativo', 'configuracion']
    update_fields = []
    
    for campo in campos_permitidos:
        if campo in data:
            valor = data[campo]
            
            # Validaciones específicas por campo
            if campo == 'cargo':
                if not isinstance(valor, str):
                    raise ValueError("El campo 'cargo' debe ser una cadena de texto.")
                if len(valor) > 100:
                    raise ValueError("El campo 'cargo' no puede exceder 100 caracteres.")
                if not valor.strip():
                    raise ValueError("El campo 'cargo' no puede estar vacío.")
            
            elif campo == 'departamento':
                if valor is not None and not isinstance(valor, str):
                    raise ValueError("El campo 'departamento' debe ser una cadena de texto o null.")
                if valor and len(valor) > 100:
                    raise ValueError("El campo 'departamento' no puede exceder 100 caracteres.")
            
            elif campo == 'telefono_corporativo':
                if valor is not None and not isinstance(valor, str):
                    raise ValueError("El campo 'telefono_corporativo' debe ser una cadena de texto o null.")
                if valor and len(valor) > 20:
                    raise ValueError("El campo 'telefono_corporativo' no puede exceder 20 caracteres.")
            
            elif campo == 'configuracion':
                # Normalizar None a {} (nunca propagar None)
                if valor is None:
                    valor = {}
                if not isinstance(valor, dict):
                    raise ValueError("El campo 'configuracion' debe ser un diccionario JSON válido.")
            
            setattr(perfil, campo, valor)
            update_fields.append(campo)
    
    # Manejar avatar si se proporciona
    if files and 'avatar' in files:
        archivo_avatar = files['avatar']
        _validate_avatar_file(archivo_avatar)
        
        # Eliminar avatar anterior si existe
        if perfil.avatar:
            perfil.avatar.delete(save=False)
        
        # Asignar nuevo avatar
        perfil.avatar = archivo_avatar
        update_fields.append('avatar')
    
    # Guardar cambios
    if update_fields:
        update_fields.append('updated_at')
        perfil.save(update_fields=update_fields)
    
    # Retornar DTO actualizado
    return read_profile(user)


@transaction.atomic
def update_profile_config(user: User, config: dict[str, Any], merge: bool = True) -> dict[str, Any]:
    """
    Actualiza la configuración de UI del perfil de forma segura.
    
    WARNING: v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    WARNING: IMPORTANTE: Este método actualiza el campo JSONField `configuracion`
    de forma segura, preservando los valores existentes si `merge=True`.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        config: Diccionario con la configuración a actualizar
        merge: Si True, hace merge superficial preservando valores existentes. Si False, reemplaza toda la configuración.
    
    Returns:
        dict: DTO con los datos del perfil actualizado
    
    Raises:
        ValueError: Si la configuración no es un diccionario válido
    """
    
    # Validar que config sea un diccionario
    if not isinstance(config, dict):
        raise ValueError("La configuración debe ser un diccionario válido.")
    
    # Obtener o crear el perfil
    perfil = get_or_create_profile(user)
    
    # Actualizar la configuración
    if merge:
        # Merge superficial: preservar valores existentes
        configuracion_actual = perfil.configuracion.copy() if perfil.configuracion else {}
        configuracion_actual.update(config)
        perfil.configuracion = configuracion_actual
    else:
        # Reemplazar toda la configuración
        perfil.configuracion = config
    
    perfil.save(update_fields=['configuracion', 'updated_at'])
    
    # Retornar DTO actualizado
    return read_profile(user)


def _validate_avatar_file(archivo: UploadedFile) -> None:
    """
    Valida que el archivo de avatar cumpla con las políticas.
    
    Args:
        archivo: Archivo de imagen subido (UploadedFile)
    
    Raises:
        ValueError: Si el archivo no cumple con las políticas (tipo MIME, tamaño)
    """
    # Validar tipo de archivo (solo imágenes)
    content_types_permitidos = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if archivo.content_type not in content_types_permitidos:
        raise ValueError(
            f"Tipo de archivo no permitido. Solo se aceptan: {', '.join(content_types_permitidos)}. "
            f"Tipo recibido: {archivo.content_type}"
        )
    
    # Validar tamaño (máximo 5MB)
    tamaño_maximo = 5 * 1024 * 1024  # 5MB
    if archivo.size > tamaño_maximo:
        raise ValueError(
            f"El archivo excede el tamaño máximo permitido (5MB). "
            f"Tamaño actual: {archivo.size / 1024 / 1024:.2f}MB"
        )
