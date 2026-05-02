"""
Permisos para la app accounts.

Por defecto, usa los permisos globales de apps.config.api.permissions.
"""

from apps.config.api.permissions import DEFAULT_VIEWSET_PERMISSIONS

# Permisos por defecto para esta app
# Se puede sobrescribir por ViewSet
DEFAULT_PERMISSIONS = DEFAULT_VIEWSET_PERMISSIONS
