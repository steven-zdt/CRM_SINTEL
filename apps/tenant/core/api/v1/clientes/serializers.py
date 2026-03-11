"""Core API v1 - Clientes serializers.

Placeholder para serializers compuestos destinados a la IU de Core.
"""

from apps.tenant.clientes.api.serializers import ClienteDetailSerializer


class ClienteWorkspaceSerializer(ClienteDetailSerializer):
    class Meta(ClienteDetailSerializer.Meta):
        fields = ClienteDetailSerializer.Meta.fields
