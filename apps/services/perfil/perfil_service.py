"""
Servicio de gestión de perfiles de colaboradores.

Este servicio centraliza la lógica de negocio para la gestión de perfiles
de colaboradores dentro de tenants, siguiendo el principio de Service Layer Pattern.

⚠️ v2.30: API-First + SSoT - Toda la lógica de negocio está aquí.
- Cero Signals: Toda la lógica es explícita
- Service Layer Pattern: Lógica de negocio separada de modelos y vistas
- Tenant Isolation: Operaciones dentro del contexto del tenant
- Transaccional: Todas las operaciones son atómicas

Uso:
    from apps.services.perfil.perfil_service import (
        obtener_o_crear_perfil,
        actualizar_perfil,
        actualizar_configuracion_ui,
        actualizar_avatar
    )
    
    # Obtener o crear perfil
    perfil = obtener_o_crear_perfil(user)
    
    # Actualizar perfil
    perfil = actualizar_perfil(user, {'cargo': 'Nuevo cargo', 'departamento': 'IT'})
    
    # Actualizar configuración de UI
    perfil = actualizar_configuracion_ui(user, {'modo_oscuro': True}, merge=True)
    
    # Actualizar avatar
    perfil = actualizar_avatar(user, archivo)
"""
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile

User = get_user_model()


def obtener_o_crear_perfil(user: User, defaults: Optional[Dict[str, Any]] = None) -> 'TenantProfile':
    """
    Obtiene o crea el perfil del usuario en el tenant actual.
    
    ⚠️ IMPORTANTE: Este método reemplaza el uso de señales post_save.
    La lógica es explícita y se ejecuta solo cuando se necesita.
    
    ⚠️ TENANT ISOLATION: Este método debe ejecutarse dentro del contexto
    del tenant correcto. django-tenants maneja automáticamente el aislamiento
    por esquema, así que el perfil se crea en el esquema del tenant actual.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        defaults: Valores por defecto para crear el perfil si no existe
    
    Returns:
        TenantProfile: Perfil del usuario en el tenant actual
    
    Example:
        from apps.services.perfil.perfil_service import obtener_o_crear_perfil
        
        perfil = obtener_o_crear_perfil(
            user=request.user,
            defaults={
                'cargo': 'Colaborador',
                'departamento': 'General'
            }
        )
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
        perfil = TenantProfile.objects.get(user=user)
        return perfil
    except TenantProfile.DoesNotExist:
        # Crear el perfil con valores por defecto
        perfil = TenantProfile.objects.create(
            user=user,
            **defaults
        )
        return perfil


@transaction.atomic
def actualizar_perfil(user: User, data: Dict[str, Any]) -> 'TenantProfile':
    """
    Actualiza el perfil del usuario con los datos proporcionados.
    
    ⚠️ v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    ⚠️ IMPORTANTE: Normaliza configuracion=None a {} antes de guardar.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        data: Diccionario con campos a actualizar (cargo, departamento, telefono_corporativo, configuracion)
    
    Returns:
        TenantProfile: Perfil actualizado
    
    Example:
        from apps.services.perfil.perfil_service import actualizar_perfil
        
        perfil = actualizar_perfil(user, {
            'cargo': 'Contador Senior',
            'departamento': 'Finanzas',
            'telefono_corporativo': '3001234567',
            'configuracion': {'modo_oscuro': True}  # o None (se normaliza a {})
        })
    """
    from apps.tenant.perfil.models import TenantProfile
    
    # Obtener o crear el perfil
    perfil = obtener_o_crear_perfil(user)
    
    # Campos permitidos para actualizar
    campos_permitidos = ['cargo', 'departamento', 'telefono_corporativo', 'configuracion']
    update_fields = []
    
    for campo in campos_permitidos:
        if campo in data:
            valor = data[campo]
            # ⚠️ v2.30: Normalizar configuracion=None a {} (nunca propagar None al modelo)
            if campo == 'configuracion' and valor is None:
                valor = {}
            setattr(perfil, campo, valor)
            update_fields.append(campo)
    
    if update_fields:
        update_fields.append('updated_at')
        perfil.save(update_fields=update_fields)
    
    return perfil


@transaction.atomic
def actualizar_configuracion_ui(
    user: User,
    configuracion_dict: Dict[str, Any],
    merge: bool = True
) -> 'TenantProfile':
    """
    Actualiza la configuración de UI del perfil de forma segura.
    
    ⚠️ v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    ⚠️ IMPORTANTE: Este método actualiza el campo JSONField `configuracion`
    de forma segura, preservando los valores existentes si `merge=True`.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        configuracion_dict: Diccionario con la configuración a actualizar
        merge: Si True, hace merge profundo preservando valores existentes. Si False, reemplaza toda la configuración.
    
    Returns:
        TenantProfile: Perfil actualizado
    
    Example:
        from apps.services.perfil.perfil_service import actualizar_configuracion_ui
        
        # Merge (preserva valores existentes)
        perfil = actualizar_configuracion_ui(user, {'modo_oscuro': True}, merge=True)
        
        # Reemplazar toda la configuración
        perfil = actualizar_configuracion_ui(
            user,
            {'modo_oscuro': True, 'densidad_tablas': 'compacta'},
            merge=False
        )
    """
    from apps.tenant.perfil.models import TenantProfile
    
    # Obtener o crear el perfil
    perfil = obtener_o_crear_perfil(user)
    
    # ⚠️ v2.30: Normalizar None a {} (nunca propagar None)
    if configuracion_dict is None:
        configuracion_dict = {}
    
    # Validar que configuracion_dict sea un diccionario
    if not isinstance(configuracion_dict, dict):
        raise ValueError("La configuración debe ser un diccionario válido.")
    
    # Actualizar la configuración
    if merge:
        # Merge profundo: preservar valores existentes
        configuracion_actual = perfil.configuracion.copy() if perfil.configuracion else {}
        configuracion_actual.update(configuracion_dict)
        perfil.configuracion = configuracion_actual
    else:
        # Reemplazar toda la configuración
        perfil.configuracion = configuracion_dict
    
    perfil.save(update_fields=['configuracion', 'updated_at'])
    return perfil


@transaction.atomic
def actualizar_avatar(user: User, archivo: UploadedFile) -> 'TenantProfile':
    """
    Actualiza el avatar del perfil del usuario.
    
    ⚠️ v2.30: Service Layer Pattern - Lógica de negocio centralizada.
    ⚠️ SEGURIDAD: Valida tipo de archivo y tamaño.
    
    Args:
        user: Usuario global (AUTH_USER_MODEL)
        archivo: Archivo de imagen subido (UploadedFile)
    
    Returns:
        TenantProfile: Perfil actualizado
    
    Raises:
        ValueError: Si el archivo no es una imagen válida o excede el tamaño máximo
    
    Example:
        from apps.services.perfil.perfil_service import actualizar_avatar
        
        perfil = actualizar_avatar(user, request.FILES['avatar'])
    """
    from apps.tenant.perfil.models import TenantProfile
    from django.core.exceptions import ValidationError
    
    # Validar tipo de archivo (solo imágenes)
    content_types_permitidos = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if archivo.content_type not in content_types_permitidos:
        raise ValueError(f"Tipo de archivo no permitido. Solo se aceptan: {', '.join(content_types_permitidos)}")
    
    # Validar tamaño (máximo 5MB)
    tamaño_maximo = 5 * 1024 * 1024  # 5MB
    if archivo.size > tamaño_maximo:
        raise ValueError(f"El archivo excede el tamaño máximo permitido (5MB). Tamaño actual: {archivo.size / 1024 / 1024:.2f}MB")
    
    # Obtener o crear el perfil
    perfil = obtener_o_crear_perfil(user)
    
    # Eliminar avatar anterior si existe
    if perfil.avatar:
        perfil.avatar.delete(save=False)
    
    # Asignar nuevo avatar
    perfil.avatar = archivo
    perfil.save(update_fields=['avatar', 'updated_at'])
    
    return perfil
