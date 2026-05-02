"""Core API v1 - Empresa facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.tenant.empresa.api.viewsets import EmpresaViewSet, MailInboxConfigViewSet

from . import serializers as ws_serializers


class EmpresaCoreViewSet(EmpresaViewSet):
    # # WARNING: CRÍTICO: Asegurar parser_classes en facade
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.EmpresaWorkspaceListSerializer
        elif self.action == 'retrieve':
            return ws_serializers.EmpresaWorkspaceDetailSerializer
        elif self.action == 'current_header':
            return ws_serializers.EmpresaWorkspaceHeaderSerializer
        else:
            return ws_serializers.EmpresaWorkspaceUpsertSerializer


class MailInboxConfigCoreViewSet(MailInboxConfigViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.MailInboxConfigWorkspaceListSerializer
        elif self.action == 'test_connection':
            return ws_serializers.MailInboxConfigWorkspaceTestConnectionSerializer
        return ws_serializers.MailInboxConfigWorkspaceDetailSerializer
