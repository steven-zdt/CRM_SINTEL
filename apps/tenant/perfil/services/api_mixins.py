"""
API Mixins para Perfil - DEPRECATED.

WARNING: La implementacion real de PerfilServiceMixin esta en api/mixins.py.
Este archivo NO realiza re-exports para evitar importacion circular.

Importar directamente:
  from apps.tenant.perfil.api.mixins import PerfilServiceMixin
"""
# Archivo vacio intencionalmente para evitar importacion circular:
# services/__init__.py -> services/api_mixins.py -> api/mixins.py
#                     -> services/business_service.py -> services/__init__.py (circular)

__all__ = []
