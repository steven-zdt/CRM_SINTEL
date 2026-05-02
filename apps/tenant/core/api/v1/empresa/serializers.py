"""Core API v1 - Empresa serializers facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app empresa.
"""

from apps.tenant.empresa.api.serializers import (
    EmpresaDetailSerializer,
    EmpresaHeaderSerializer,
    EmpresaListSerializer,
    EmpresaUpsertSerializer,
    MailInboxConfigDetailSerializer,
    MailInboxConfigListSerializer,
    MailInboxConfigTestConnectionSerializer,
)


class EmpresaWorkspaceListSerializer(EmpresaListSerializer):
    class Meta(EmpresaListSerializer.Meta):
        pass


class EmpresaWorkspaceDetailSerializer(EmpresaDetailSerializer):
    class Meta(EmpresaDetailSerializer.Meta):
        pass


class EmpresaWorkspaceUpsertSerializer(EmpresaUpsertSerializer):
    class Meta(EmpresaUpsertSerializer.Meta):
        pass


class EmpresaWorkspaceHeaderSerializer(EmpresaHeaderSerializer):
    class Meta(EmpresaHeaderSerializer.Meta):
        pass


class MailInboxConfigWorkspaceListSerializer(MailInboxConfigListSerializer):
    class Meta(MailInboxConfigListSerializer.Meta):
        pass


class MailInboxConfigWorkspaceDetailSerializer(MailInboxConfigDetailSerializer):
    class Meta(MailInboxConfigDetailSerializer.Meta):
        pass


class MailInboxConfigWorkspaceTestConnectionSerializer(MailInboxConfigTestConnectionSerializer):
    pass
