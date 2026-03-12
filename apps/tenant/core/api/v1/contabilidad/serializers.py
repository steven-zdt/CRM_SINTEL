"""Core API v1 - Contabilidad serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app contabilidad.
- ⚠️ v2.61: Incluye CatalogoMaestroNIIF para el catálogo oficial NIIF Colombia.
"""

from apps.tenant.contabilidad.api.serializers import (
    CuentaContableListSerializer,
    CuentaContableDetailSerializer,
    CuentaContableListDTSerializer,
    AsientoContableListSerializer,
    AsientoContableListDTSerializer,
    AsientoContableDetailSerializer,
    MovimientoContableListSerializer,
    MovimientoContableDetailSerializer,
    PeriodoContableListSerializer,  # ⚠️ v2.61
    PeriodoContableDetailSerializer,  # ⚠️ v2.61
    CatalogoMaestroNIIFListSerializer,
    CatalogoMaestroNIIFDetailSerializer,
)


class CuentaContableWorkspaceListSerializer(CuentaContableListSerializer):
    class Meta(CuentaContableListSerializer.Meta):
        pass


class CuentaContableWorkspaceDetailSerializer(CuentaContableDetailSerializer):
    class Meta(CuentaContableDetailSerializer.Meta):
        pass


class CuentaContableWorkspaceListDTSerializer(CuentaContableListDTSerializer):
    class Meta(CuentaContableListDTSerializer.Meta):
        pass


class AsientoContableWorkspaceListSerializer(AsientoContableListSerializer):
    class Meta(AsientoContableListSerializer.Meta):
        pass


class AsientoContableWorkspaceListDTSerializer(AsientoContableListDTSerializer):
    class Meta(AsientoContableListDTSerializer.Meta):
        pass


class AsientoContableWorkspaceDetailSerializer(AsientoContableDetailSerializer):
    class Meta(AsientoContableDetailSerializer.Meta):
        pass


class MovimientoContableWorkspaceListSerializer(MovimientoContableListSerializer):
    class Meta(MovimientoContableListSerializer.Meta):
        pass


class MovimientoContableWorkspaceDetailSerializer(MovimientoContableDetailSerializer):
    class Meta(MovimientoContableDetailSerializer.Meta):
        pass


# ═══════════════════════════════════════════════════════════════
# CATÁLOGO MAESTRO NIIF - Facade Serializers (v2.61)
# ═══════════════════════════════════════════════════════════════

class CatalogoMaestroNIIFWorkspaceListSerializer(CatalogoMaestroNIIFListSerializer):
    """Facade para listado del Catálogo Maestro NIIF."""
    class Meta(CatalogoMaestroNIIFListSerializer.Meta):
        pass


class CatalogoMaestroNIIFWorkspaceDetailSerializer(CatalogoMaestroNIIFDetailSerializer):
    """Facade para detalle del Catálogo Maestro NIIF."""
    class Meta(CatalogoMaestroNIIFDetailSerializer.Meta):
        pass


# ═══════════════════════════════════════════════════════════════
# PERIODOS CONTABLES - Facade Serializers (v2.61)
# ═══════════════════════════════════════════════════════════════

class PeriodoContableWorkspaceListSerializer(PeriodoContableListSerializer):
    """Facade para listado de Periodos Contables."""
    class Meta(PeriodoContableListSerializer.Meta):
        pass


class PeriodoContableWorkspaceDetailSerializer(PeriodoContableDetailSerializer):
    """Facade para detalle de Periodo Contable."""
    class Meta(PeriodoContableDetailSerializer.Meta):
        pass
