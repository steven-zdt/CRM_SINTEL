"""Core API v1 - Clientes serializers facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app clientes.
- # WARNING: v2.61: Alineado con patrón de cotizaciones y contabilidad.
"""

from apps.tenant.clientes.api.serializers import (
    ClienteDetailSerializer,
    ClienteListSerializer,
    ContactoClienteSerializer,
)


class ClienteWorkspaceListSerializer(ClienteListSerializer):
    """
    Serializer para lista de clientes en workspace.
    
    Hereda de ClienteListSerializer (optimizado para Tabulator):
    - Campos mínimos necesarios para la tabla
    - Campos display para choices (tipo_documento_display, etc.)
    - Read-only fields apropiados
    """
    class Meta(ClienteListSerializer.Meta):
        pass


class ClienteWorkspaceDetailSerializer(ClienteDetailSerializer):
    """
    Serializer para detalle/edición de clientes en workspace.
    
    Hereda de ClienteDetailSerializer:
    - Todos los campos del modelo
    - Soporte para contactos anidados
    - Validaciones de negocio
    """
    class Meta(ClienteDetailSerializer.Meta):
        pass


class ContactoClienteWorkspaceSerializer(ContactoClienteSerializer):
    """
    Serializer para contactos de cliente en workspace.
    
    Hereda de ContactoClienteSerializer:
    - Campos del contacto
    - Campos de lectura del cliente (cliente_nombre, cliente_documento)
    - Validación unique_together (cliente + email)
    """
    class Meta(ContactoClienteSerializer.Meta):
        pass
