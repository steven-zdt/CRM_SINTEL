"""Core API v1 - Clientes facade.

ViewSet espejo para exponer el CRUD de `apps.tenant.clientes` bajo el namespace de Core.
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.clientes.api.viewsets import ClienteViewSet, ContactoClienteViewSet

from .serializers import ClienteWorkspaceSerializer


class ClienteCoreViewSet(ClienteViewSet):
    serializer_class = ClienteWorkspaceSerializer
    authentication_classes = [SessionAuthentication]


class ContactoClienteCoreViewSet(ContactoClienteViewSet):
    authentication_classes = [SessionAuthentication]
