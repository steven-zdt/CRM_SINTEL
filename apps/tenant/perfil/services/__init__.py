"""
Servicios internos del dominio Perfil.

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Perfil.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
"""
from .perfil_service import (
    get_or_create_profile,
    read_profile,
    update_profile,
    update_profile_config,
)

__all__ = [
    'get_or_create_profile',
    'read_profile',
    'update_profile',
    'update_profile_config',
]
