"""Core API URLConf.

⚠️ POLÍTICA:
- Endpoints de composición/orquestación para presentación.
- NO reemplazan CRUD de las apps individuales.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenant.core.api.health import HealthView
# ⚠️ v2.61: Solo importar ViewSets que existen en viewsets.py
from apps.tenant.core.api.viewsets import CoreLinksViewSet, DashboardSectionsViewSet

# Facades v1
from apps.tenant.core.api.v1.clientes.viewsets import ClienteCoreViewSet, ContactoClienteCoreViewSet
from apps.tenant.core.api.v1.cotizaciones.viewsets import (
    ConfiguracionCotizacionCoreViewSet,
    CotizacionCoreViewSet,
    CotizacionItemCoreViewSet,
)
from apps.tenant.core.api.v1.gastos.viewsets import GastoCoreViewSet
from apps.tenant.core.api.v1.inventario.viewsets import (
    CategoriaItemCoreViewSet,
    MovimientoInventarioCoreViewSet,
    ProductoCoreViewSet,
)
from apps.tenant.core.api.v1.empleados.viewsets import ContratoCoreViewSet, DevengoCoreViewSet, EmpleadoCoreViewSet
from apps.tenant.core.api.v1.contabilidad.viewsets import (
    AsientoContableCoreViewSet,
    CatalogoMaestroNIIFCoreViewSet,
    CuentaContableCoreViewSet,
    MovimientoContableCoreViewSet,
)
from apps.tenant.core.api.v1.gastos.viewsets import ResolucionDIANCoreViewSet
from apps.tenant.core.api.v1.empresa.viewsets import EmpresaCoreViewSet, MailInboxConfigCoreViewSet
from apps.tenant.core.api.v1.proyectos.viewsets import ProyectoCoreViewSet

app_name = "tenant_core_api"

# Router base (/api/v1/core/)
router = DefaultRouter()
# ⚠️ v2.61: Solo registrar ViewSets que existen
# router.register(r"routes", CoreRoutesViewSet, basename="core-routes")  # No existe
# router.register(r"dashboard", CoreDashboardViewSet, basename="core-dashboard")  # No existe
# router.register(r"landing", CoreLandingViewSet, basename="core-landing")  # No existe
# router.register(r"auth", CoreAuthViewSet, basename="core-auth")  # No existe
# router.register(r"mi-perfil", CoreMiPerfilViewSet, basename="core-mi-perfil")  # No existe
# router.register(r"facturas", CoreFacturasViewSet, basename="core-facturas")  # No existe
# router.register(r"contabilidad", CoreContabilidadViewSet, basename="core-contabilidad")  # No existe
# router.register(r"maildigester/runs", CoreMailDigesterRunsViewSet, basename="core-maildigester-runs")  # No existe
# router.register(r"maildigester/configs", CoreMailDigesterConfigsViewSet, basename="core-maildigester-configs")  # No existe
# router.register(r"maildigester/run", CoreMailDigesterRunViewSet, basename="core-maildigester-run")  # No existe
router.register(r"links", CoreLinksViewSet, basename="core-links")  # ✅ Existe
router.register(r"dashboard/sections", DashboardSectionsViewSet, basename="core-dashboard-sections")  # ✅ Existe

# Router versionado v1 (/api/v1/core/v1/)
router_v1 = DefaultRouter()

# Clientes
router_v1.register(r"workspace-clientes/contactos", ContactoClienteCoreViewSet, basename="workspace-contactos")
router_v1.register(r"workspace-clientes", ClienteCoreViewSet, basename="workspace-clientes")

# Cotizaciones
router_v1.register(
    r"cotizaciones/configuracion",
    ConfiguracionCotizacionCoreViewSet,
    basename="core-cotizaciones-configuracion",
)
router_v1.register(r"cotizaciones/items", CotizacionItemCoreViewSet, basename="core-cotizaciones-items")
router_v1.register(r"cotizaciones", CotizacionCoreViewSet, basename="core-cotizaciones")

# Empleados
router_v1.register(r"empleados/contratos", ContratoCoreViewSet, basename="core-empleados-contratos")
router_v1.register(r"empleados/devengos", DevengoCoreViewSet, basename="core-empleados-devengos")
router_v1.register(r"empleados/gestion", EmpleadoCoreViewSet, basename="core-empleados")

# Contabilidad
router_v1.register(r"contabilidad/cuentas", CuentaContableCoreViewSet, basename="core-contabilidad-cuentas")
router_v1.register(r"contabilidad/asientos", AsientoContableCoreViewSet, basename="core-contabilidad-asientos")
router_v1.register(r"contabilidad/movimientos", MovimientoContableCoreViewSet, basename="core-contabilidad-movimientos")
router_v1.register(r"contabilidad/catalogo-niif", CatalogoMaestroNIIFCoreViewSet, basename="core-contabilidad-catalogo-niif")

# Gastos
router_v1.register(r"gastos/operativos", GastoCoreViewSet, basename="core-gastos")
router_v1.register(r"gastos/resoluciones-dian", ResolucionDIANCoreViewSet, basename="core-gastos-resoluciones")

# Inventario
router_v1.register(r"inventario/categorias", CategoriaItemCoreViewSet, basename="core-inventario-categorias")
router_v1.register(r"inventario/productos", ProductoCoreViewSet, basename="core-inventario-productos")
router_v1.register(r"inventario/movimientos", MovimientoInventarioCoreViewSet, basename="core-inventario-movimientos")

# Empresa
router_v1.register(r"empresa/configuracion", EmpresaCoreViewSet, basename="core-empresa")
router_v1.register(r"empresa/mail-inbox", MailInboxConfigCoreViewSet, basename="core-empresa-mailinbox")

# Proyectos
router_v1.register(r"proyectos/gestion", ProyectoCoreViewSet, basename="core-proyectos")

urlpatterns = [
    path("health/", HealthView.as_view(), name="tenant-health"),

    # Empresa singleton — PATCH /api/v1/core/empresa/ (sin ID, singleton pattern)
    path(
        "empresa/",
        EmpresaCoreViewSet.as_view({"get": "mi_empresa", "patch": "partial_update"}),
        name="core-empresa-singleton",
    ),

    # API Core v1 - Identidad (alias unificado para workspace)
    # ⚠️ v2.61: Comentado - CoreMiPerfilViewSet no existe
    # path(
    #     "v1/usuario/mi-perfil/",
    #     CoreMiPerfilViewSet.as_view({"get": "list", "patch": "partial_update"}),
    #     name="core-v1-mi-perfil",
    # ),
    # path(
    #     "v1/usuario/mi-perfil/configuracion/",
    #     CoreMiPerfilViewSet.as_view({"patch": "configuracion"}),
    #     name="core-v1-mi-perfil-configuracion",
    # ),

    # API Core versionada (v1)
    path("v1/", include(router_v1.urls)),

    # ViewSets base
    path("", include(router.urls)),

    # Gateway a APIs de apps
    path("_apps/empresa/", include("apps.tenant.empresa.api.urls")),
    path("_apps/facturas/", include("apps.tenant.facturas.api.urls")),
    path("_apps/contabilidad/", include("apps.tenant.contabilidad.api.urls")),
    path("_apps/inventario/", include("apps.tenant.inventario.api.urls")),
    path("_apps/empleados/", include("apps.tenant.empleados.api.urls")),
    path("_apps/gastos/", include("apps.tenant.gastos.api.urls")),
    path("_apps/cotizaciones/", include("apps.tenant.cotizaciones.api.urls")),
    path("_apps/proveedores/", include("apps.tenant.proveedores.api.urls")),
    path("_apps/clientes/", include("apps.tenant.clientes.api.urls")),
    path("_apps/proyectos/", include("apps.tenant.proyectos.api.urls")),
    path("_apps/landing/", include("apps.tenant.landing.api.urls")),
    path("_apps/dashboard/", include("apps.tenant.dashboard.api.urls")),
    path("_apps/perfil/", include("apps.tenant.perfil.api.urls")),
]
