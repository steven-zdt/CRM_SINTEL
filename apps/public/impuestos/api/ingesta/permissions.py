"""
Permisos para la API de Ingesta.

Referencia: https://www.django-rest-framework.org/api-guide/permissions/
"""

from rest_framework import permissions


class IsAuthenticatedIngesta(permissions.IsAuthenticated):
    """
    Permiso base para endpoints de ingesta.

    Requiere autenticación para crear documentos y consultar estado.
    """
