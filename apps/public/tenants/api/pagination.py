"""
Paginación para la app tenants.

Re-exporta la paginación estándar para import limpio.
"""
from apps.config.api.pagination import StandardResultsSetPagination

__all__ = ['StandardResultsSetPagination']
