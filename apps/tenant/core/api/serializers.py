"""
Serializers compuestos para Core API.

⚠️ POLÍTICA:
- Reutilizar serializers de las apps "dueñas" cuando sea posible
- Crear adapters mínimos solo cuando sea necesario
- Mantener tenant-awareness y branding dinámico
"""
from rest_framework import serializers
from apps.tenant.core.branding import get_tenant_branding


class EmpresaResumenSerializer(serializers.Serializer):
    """Serializer para resumen de empresa."""
    id = serializers.IntegerField(read_only=True)
    razon_social = serializers.CharField(read_only=True)
    nit = serializers.CharField(read_only=True)
    dv = serializers.CharField(read_only=True)
    nit_completo = serializers.CharField(read_only=True)
    logo_url = serializers.URLField(read_only=True, allow_null=True)
    website = serializers.URLField(read_only=True, allow_null=True)
    moneda = serializers.CharField(read_only=True)
    regimen_tributario = serializers.CharField(read_only=True, allow_null=True)
    email_contacto = serializers.EmailField(read_only=True, allow_null=True)
    telefono = serializers.CharField(read_only=True, allow_null=True)


class FacturasResumenSerializer(serializers.Serializer):
    """Serializer para resumen de facturas."""
    total = serializers.IntegerField(read_only=True)
    pendientes = serializers.IntegerField(read_only=True)
    aceptadas = serializers.IntegerField(read_only=True)
    rechazadas = serializers.IntegerField(read_only=True)
    mes_actual = serializers.DictField(read_only=True)
    ultimas = serializers.ListField(read_only=True)


class ContabilidadResumenSerializer(serializers.Serializer):
    """Serializer para resumen de contabilidad."""
    total_cuentas = serializers.IntegerField(read_only=True)
    total_asientos = serializers.IntegerField(read_only=True)
    mes_actual = serializers.DictField(read_only=True)
    ultimos_asientos = serializers.ListField(read_only=True)


class PerfilResumenSerializer(serializers.Serializer):
    """Serializer para resumen de perfil."""
    id = serializers.IntegerField(read_only=True, allow_null=True)
    nombre_completo = serializers.CharField(read_only=True)
    telefono = serializers.CharField(read_only=True, allow_null=True)
    cargo = serializers.CharField(read_only=True, allow_null=True)
    departamento = serializers.CharField(read_only=True, allow_null=True)
    foto_url = serializers.URLField(read_only=True, allow_null=True)


class LandingResumenSerializer(serializers.Serializer):
    """Serializer para resumen de landing."""
    nombre = serializers.CharField(read_only=True)
    schema_name = serializers.CharField(read_only=True, allow_null=True)
    domain_url = serializers.CharField(read_only=True)
    login_url = serializers.CharField(read_only=True)
    dashboard_url = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class DashboardCompletoSerializer(serializers.Serializer):
    """
    Serializer para dashboard completo (compuesto de múltiples apps).
    
    ⚠️ POLÍTICA: Incluye branding dinámico desde BD.
    """
    tenant = serializers.DictField(read_only=True)
    user = serializers.DictField(read_only=True)
    empresa = EmpresaResumenSerializer(read_only=True)
    facturas = FacturasResumenSerializer(read_only=True)
    contabilidad = ContabilidadResumenSerializer(read_only=True)
    perfil = PerfilResumenSerializer(read_only=True)
    branding = serializers.DictField(read_only=True)
    redirect_url = serializers.CharField(read_only=True)


class MiEmpresaSerializer(serializers.Serializer):
    """
    Serializer para endpoint /api/v1/core/mi-empresa/.
    
    ⚠️ POLÍTICA: Incluye branding dinámico desde BD.
    ⚠️ SETUP: Retorna setup_required=True si no existe empresa (falta crear).
    """
    empresa = EmpresaResumenSerializer(read_only=True, allow_null=True)
    branding = serializers.DictField(read_only=True)
    setup_required = serializers.BooleanField(read_only=True)


class MiPerfilSerializer(serializers.Serializer):
    """
    Serializer para endpoint /api/v1/core/mi-perfil/.
    """
    perfil = PerfilResumenSerializer(read_only=True)
    user = serializers.DictField(read_only=True)


# --- Inventario (Core) DTOs ---
class InventarioResumenSerializer(serializers.Serializer):
    conteo = serializers.DictField()
    stock_total = serializers.DecimalField(max_digits=18, decimal_places=3)
    ultimos_movimientos = serializers.ListField()