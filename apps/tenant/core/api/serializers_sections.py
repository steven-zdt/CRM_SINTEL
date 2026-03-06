"""
Serializers para secciones del dashboard (Core API).

⚠️ POLÍTICA:
- Serializers de read-model para presentación
- Orden requerido: empresas → facturas → contabilidad → perfil
- Sin hardcodes de marca
"""
from rest_framework import serializers


class EmpresasSectionSerializer(serializers.Serializer):
    """Serializer para sección de empresas."""
    empresas = serializers.ListField(child=serializers.DictField())


class FacturasSectionSerializer(serializers.Serializer):
    """Serializer para sección de facturas."""
    total = serializers.IntegerField()
    por_estado = serializers.ListField(child=serializers.DictField())
    mes_actual = serializers.DictField()
    recientes = serializers.ListField(child=serializers.DictField())


class ContabilidadSectionSerializer(serializers.Serializer):
    """Serializer para sección de contabilidad."""
    total_cuentas = serializers.IntegerField()
    total_asientos = serializers.IntegerField()
    mes_actual = serializers.DictField()
    asientos_recientes = serializers.ListField(child=serializers.DictField())


class PerfilSectionSerializer(serializers.Serializer):
    """Serializer para sección de perfil."""
    me = serializers.DictField(allow_null=True)


class DashboardSectionsSerializer(serializers.Serializer):
    """
    Serializer para todas las secciones del dashboard.
    
    ⚠️ ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
    ⚠️ POLÍTICA API-First: Incluye user, tenant, branding y KPIs para evitar múltiples requests
    """
    # Información de usuario y tenant (para header/branding)
    user = serializers.DictField()
    tenant = serializers.DictField()
    branding = serializers.DictField()
    kpis = serializers.DictField()
    
    # Secciones en orden requerido
    empresas = EmpresasSectionSerializer()
    facturas = FacturasSectionSerializer()
    contabilidad = ContabilidadSectionSerializer()
    perfil = PerfilSectionSerializer()
