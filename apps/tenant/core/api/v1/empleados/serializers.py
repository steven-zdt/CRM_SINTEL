"""Core API v1 - Empleados serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app empleados.
"""

from apps.tenant.empleados.api.serializers import (
    EmpleadoListSerializer,
    EmpleadoDetailSerializer,
    ContratoNestedSerializer,
    DevengoSerializer,
)


class EmpleadoWorkspaceListSerializer(EmpleadoListSerializer):
    class Meta(EmpleadoListSerializer.Meta):
        pass


class EmpleadoWorkspaceDetailSerializer(EmpleadoDetailSerializer):
    class Meta(EmpleadoDetailSerializer.Meta):
        pass


class ContratoWorkspaceSerializer(ContratoNestedSerializer):
    class Meta(ContratoNestedSerializer.Meta):
        pass


class DevengoWorkspaceSerializer(DevengoSerializer):
    class Meta(DevengoSerializer.Meta):
        pass
