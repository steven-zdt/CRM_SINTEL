"""Core API URLConf v2.61.2.

# WARNING: POLÍTICA:
- Endpoints de composición/orquestación para presentación.
- NO reemplazan CRUD de las apps individuales.
- Facades para workspace: /api/v1/core/v1/{modulo}/
- Gateway directo: /api/v1/core/_apps/{modulo}/ (acceso directo a apps)

# WARNING: v2.61.2: OPTIMIZACIONES FACTURAS:
- Batch processing: upload-ubl soporta files[] (múltiples archivos)
- Pre-validación de idempotencia: extrae CUFE/CUDE con regex antes del parsing completo
- Silent Success: actualiza FacturaAnexos si XML nuevo es más completo
- Transaction.atomic optimizado: solo envuelve persistencia, no parsing
"""

import logging

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenant.core.api.health import HealthView

# Facades v1
from apps.tenant.core.api.v1.clientes.viewsets import ClienteCoreViewSet, ContactoClienteCoreViewSet
from apps.tenant.core.api.v1.contabilidad.viewsets import (
    AsientoContableCoreViewSet,
    CatalogoMaestroNIIFCoreViewSet,
    CuentaContableCoreViewSet,
    MovimientoContableCoreViewSet,
    PeriodoContableCoreViewSet,  # # WARNING: v2.61
)
from apps.tenant.core.api.v1.empleados.viewsets import (
    ContratoCoreViewSet,
    DevengoCoreViewSet,
    EmpleadoCoreViewSet,
)
from apps.tenant.core.api.v1.empresa.viewsets import EmpresaCoreViewSet, MailInboxConfigCoreViewSet
from apps.tenant.core.api.v1.gastos.viewsets import GastoCoreViewSet, ResolucionDIANCoreViewSet
from apps.tenant.core.api.v1.inventario.viewsets import (
    ActivoFijoCoreViewSet,
    CategoriaItemCoreViewSet,
    MovimientoInventarioCoreViewSet,
    ProductoCoreViewSet,
    ServicioCoreViewSet,
)
from apps.tenant.core.api.v1.proyectos.viewsets import ProyectoCoreViewSet

# # WARNING: v2.61: Solo importar ViewSets que existen en viewsets.py
from apps.tenant.core.api.viewsets import (
    CoreAuthViewSet,
    CoreLinksViewSet,
    DashboardSectionsViewSet,
    TenantInfoView,
)

app_name = "tenant_core_api"
logger = logging.getLogger(__name__)

# Router base (/api/v1/core/)
router = DefaultRouter()
# # WARNING: v2.61: Solo registrar ViewSets que existen
# router.register(r"routes", CoreRoutesViewSet, basename="core-routes")  # No existe
# router.register(r"dashboard", CoreDashboardViewSet, basename="core-dashboard")  # No existe
# router.register(r"landing", CoreLandingViewSet, basename="core-landing")  # No existe
router.register(r"auth", CoreAuthViewSet, basename="core-auth")  # [OK] v2.61: Implementado
# router.register(r"mi-perfil", CoreMiPerfilViewSet, basename="core-mi-perfil")  # No existe
# router.register(r"facturas", CoreFacturasViewSet, basename="core-facturas")  # No existe
# router.register(r"contabilidad", CoreContabilidadViewSet, basename="core-contabilidad")  # No existe
# router.register(r"maildigester/runs", CoreMailDigesterRunsViewSet, basename="core-maildigester-runs")  # No existe
# router.register(r"maildigester/configs", CoreMailDigesterConfigsViewSet, basename="core-maildigester-configs")  # No existe
# router.register(r"maildigester/run", CoreMailDigesterRunViewSet, basename="core-maildigester-run")  # No existe
router.register(r"links", CoreLinksViewSet, basename="core-links")  # [OK] Existe
router.register(r"dashboard/sections", DashboardSectionsViewSet, basename="core-dashboard-sections")  # [OK] Existe

# Router versionado v1 (/api/v1/core/v1/)
router_v1 = DefaultRouter()

# Clientes
router_v1.register(r"workspace-clientes/contactos", ContactoClienteCoreViewSet, basename="workspace-contactos")
router_v1.register(r"workspace-clientes", ClienteCoreViewSet, basename="workspace-clientes")

# # WARNING: v2.61: Cotizaciones ahora usa router dedicado (ver path("v1/cotizaciones/", ...) más abajo)
# El router dedicado expone todas las funcionalidades CRUD:
# - GET/POST /api/v1/core/v1/cotizaciones/cotizaciones/ (list, create)
# - GET/PUT/PATCH/DELETE /api/v1/core/v1/cotizaciones/cotizaciones/{uuid}/ (retrieve, update, destroy)
# - GET /api/v1/core/v1/cotizaciones/cotizaciones/render-offcanvas/crear/ (crear)
# - GET /api/v1/core/v1/cotizaciones/cotizaciones/{uuid}/render-offcanvas/editar/ (editar)
# - GET /api/v1/core/v1/cotizaciones/cotizaciones/render-offcanvas/detalle/?id={uuid} (detalle)
# - GET /api/v1/core/v1/cotizaciones/cotizaciones/{uuid}/exportar-pdf/ (exportar PDF)
# - POST /api/v1/core/v1/cotizaciones/cotizaciones/{uuid}/recalcular/ (recalcular totales)
# - GET/POST /api/v1/core/v1/cotizaciones/items/ (CRUD items)
# - GET/POST/PUT/PATCH/DELETE /api/v1/core/v1/cotizaciones/configuracion/ (CRUD configuraciones)
# Comentamos los registros en router_v1 para usar el router dedicado
# router_v1.register(
#     r"cotizaciones/configuracion",
#     ConfiguracionCotizacionCoreViewSet,
#     basename="core-cotizaciones-configuracion",
# )
# router_v1.register(r"cotizaciones/items", CotizacionItemCoreViewSet, basename="core-cotizaciones-items")
# router_v1.register(r"cotizaciones", CotizacionCoreViewSet, basename="core-cotizaciones")

# Empleados
router_v1.register(r"empleados/contratos", ContratoCoreViewSet, basename="core-empleados-contratos")
router_v1.register(r"empleados/devengos", DevengoCoreViewSet, basename="core-empleados-devengos")
router_v1.register(r"empleados/gestion", EmpleadoCoreViewSet, basename="core-empleados")

# Contabilidad
router_v1.register(r"contabilidad/cuentas", CuentaContableCoreViewSet, basename="core-contabilidad-cuentas")
router_v1.register(r"contabilidad/asientos", AsientoContableCoreViewSet, basename="core-contabilidad-asientos")
router_v1.register(r"contabilidad/movimientos", MovimientoContableCoreViewSet, basename="core-contabilidad-movimientos")
router_v1.register(r"contabilidad/periodos-contables", PeriodoContableCoreViewSet, basename="core-contabilidad-periodos")  # # WARNING: v2.61
router_v1.register(r"contabilidad/catalogo-niif", CatalogoMaestroNIIFCoreViewSet, basename="core-contabilidad-catalogo-niif")

# Gastos
router_v1.register(r"gastos/operativos", GastoCoreViewSet, basename="core-gastos")
router_v1.register(r"gastos/resoluciones-dian", ResolucionDIANCoreViewSet, basename="core-gastos-resoluciones")

# Inventario
router_v1.register(r"inventario/categorias", CategoriaItemCoreViewSet, basename="core-inventario-categorias")
router_v1.register(r"inventario/productos", ProductoCoreViewSet, basename="core-inventario-productos")
router_v1.register(r"inventario/servicios", ServicioCoreViewSet, basename="core-inventario-servicios")
router_v1.register(r"inventario/activos", ActivoFijoCoreViewSet, basename="core-inventario-activos")
router_v1.register(r"inventario/movimientos", MovimientoInventarioCoreViewSet, basename="core-inventario-movimientos")

# Empresa
router_v1.register(r"empresa/configuracion", EmpresaCoreViewSet, basename="core-empresa")
router_v1.register(r"empresa/mail-inbox", MailInboxConfigCoreViewSet, basename="core-empresa-mailinbox")

# Proyectos
router_v1.register(r"proyectos/gestion", ProyectoCoreViewSet, basename="core-proyectos")

urlpatterns = [
    path("health/", HealthView.as_view(), name="tenant-health"),

    # --- Landing Info público ---
    path("landing/info/", TenantInfoView.as_view(), name="core-landing-info"),

    # Empresa singleton — PATCH /api/v1/core/empresa/ (sin ID, singleton pattern)
    path(
        "empresa/",
        EmpresaCoreViewSet.as_view({"get": "mi_empresa", "patch": "partial_update"}),
        name="core-empresa-singleton",
    ),

    # API Core v1 - Identidad (alias unificado para workspace)
    # # WARNING: v2.61: Comentado - CoreMiPerfilViewSet no existe
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
    
    # # WARNING: v2.61: Routers dedicados por módulo (patrón de contabilidad)
    # # WARNING: COTIZACIONES: Router dedicado con todas las funcionalidades CRUD
    # Endpoints disponibles:
    # - /api/v1/core/v1/cotizaciones/cotizaciones/ (CRUD principal)
    # - /api/v1/core/v1/cotizaciones/items/ (CRUD items)
    # - /api/v1/core/v1/cotizaciones/configuracion/ (CRUD configuraciones)
    # Todas las acciones @action se heredan automáticamente (render-offcanvas, exportar-pdf, recalcular)
    path("v1/cotizaciones/", include("apps.tenant.core.api.v1.cotizaciones.urls")),
    
    # # WARNING: CONTABILIDAD: Router dedicado con todas las funcionalidades CRUD
    # Endpoints disponibles:
    # - /api/v1/core/v1/contabilidad/cuentas/ (CRUD cuentas)
    # - /api/v1/core/v1/contabilidad/asientos/ (CRUD asientos)
    # - /api/v1/core/v1/contabilidad/movimientos/ (CRUD movimientos)
    # - /api/v1/core/v1/contabilidad/periodos-contables/ (CRUD periodos)
    # - /api/v1/core/v1/contabilidad/catalogo-niif/ (CRUD catálogo NIIF)
    path("v1/contabilidad/", include("apps.tenant.core.api.v1.contabilidad.urls")),
    
    # # WARNING: CLIENTES: Router dedicado con todas las funcionalidades CRUD + HTMX
    # Endpoints REST:
    # - /api/v1/clientes/ (CRUD clientes)
    # - /api/v1/clientes/contactos/ (CRUD contactos)
    # Endpoints HTMX heredados automáticamente:
    #   - /api/v1/clientes/render-offcanvas/crear/ (crear cliente)
    #   - /api/v1/clientes/{id}/render-offcanvas/editar/ (editar cliente)
    #   - /api/v1/clientes/render-offcanvas/detalle/?id={id} (ver detalle)
    #   - /api/v1/clientes/offcanvas/?id={id} (legacy - compatibilidad)
    #   - /api/v1/clientes/contactos/gestor-offcanvas/ (gestor de contactos)
    path("v1/clientes/", include("apps.tenant.core.api.v1.clientes.urls")),
    
    # # WARNING: v2.61.2: FACTURAS: Router dedicado con todas las funcionalidades CRUD
    # Endpoints disponibles:
    # - /api/v1/core/v1/facturas/facturas/ (CRUD principal - ReadOnly)
    # - /api/v1/core/v1/facturas/items-factura/ (CRUD items)
    # - /api/v1/core/v1/facturas/notas-credito/ (CRUD notas crédito)
    # Todas las acciones @action se heredan automáticamente:
    #   - importar-ubl, summary, upload-ubl (con batch processing y pre-validación v2.61.2)
    #   - upload-document, xml, gestor-offcanvas, etc.
    # # WARNING: v2.61.2: OPTIMIZACIONES:
    #   - Batch processing: upload-ubl soporta files[] (múltiples archivos)
    #   - Pre-validación de idempotencia: extrae CUFE/CUDE con regex antes del parsing completo
    #   - Delegación automática a Celery: si > 10 archivos, procesa asíncronamente (retorna 202 con task_id)
    #   - Silent Success: actualiza FacturaAnexos si XML nuevo es más completo
    #   - Transaction.atomic optimizado: solo envuelve persistencia, no parsing

    # ViewSets base
    path("", include(router.urls)),

    # Gateway a APIs de apps (acceso directo a las apps sin facades)
    # # WARNING: NOTA: Estos endpoints son para acceso directo. Para workspace, usar los facades en v1/
    path("_apps/empresa/", include("apps.tenant.empresa.api.urls")),
    # # WARNING: v2.61.2: FACTURAS: Gateway directo a /api/v1/core/_apps/facturas/
    # Expone todas las funcionalidades CRUD de apps/tenant/facturas/api/urls.py:
    # - GET /api/v1/core/_apps/facturas/ (list facturas con paginación)
    # - GET /api/v1/core/_apps/facturas/{id}/ (retrieve factura)
    # - DELETE /api/v1/core/_apps/facturas/{id}/ (delete factura)
    # - POST /api/v1/core/_apps/facturas/importar-ubl/ (importar UBL desde texto)
    # - GET /api/v1/core/_apps/facturas/summary/ (resumen de facturación neta)
    # - POST /api/v1/core/_apps/facturas/upload-ubl/ (upload UBL file - single o batch)
    #   # WARNING: v2.61.2: Soporta batch processing con files[] (múltiples archivos)
    #   # WARNING: v2.61.2: Pre-validación de idempotencia (CUFE/CUDE) antes del parsing completo
    #   # WARNING: v2.61.2: Delegación automática a Celery si > 10 archivos (retorna 202 con task_id)
    #   Returns (single): 201 Created, 200 OK (idempotente), 202 Accepted (async)
    #   Returns (batch <= 10): 200 OK con {"creados": X, "duplicados": Y, "errores": Z, "resultados": [...]}
    #   Returns (batch > 10): 202 Accepted con {"task_id": str, "status": "queued", "total_files": N}
    # - POST /api/v1/core/_apps/facturas/upload-document/ (upload documento universal - XML/PDF/XLS/CSV/TXT)
    # - GET /api/v1/core/_apps/facturas/ingest/{task_id}/status/ (estado de ingesta asíncrona)
    # - POST /api/v1/core/_apps/facturas/create-from-dto/ (crear factura desde DTO canónico)
    # - POST /api/v1/core/_apps/facturas/materialize/ (materializar factura desde resultado de pipeline)
    # - GET /api/v1/core/_apps/facturas/{id}/xml/ (obtener XML de factura)
    # - GET /api/v1/core/_apps/facturas/{id}/app-response/ (obtener ApplicationResponse XML)
    # - POST /api/v1/core/_apps/facturas/update-inbox-state/ (actualizar estado de inbox)
    # - GET /api/v1/core/_apps/facturas/gestor-offcanvas/ (renderizar offcanvas de gestor)
    # - GET/POST/DELETE /api/v1/core/_apps/facturas/items-factura/ (CRUD items de factura)
    # - GET/DELETE /api/v1/core/_apps/facturas/notas-credito/ (CRUD notas de crédito)
    # - GET /api/v1/core/_apps/facturas/notas-credito/{id}/xml/ (obtener XML de nota de crédito)
    # - POST /api/v1/core/_apps/facturas/ingesta-correo/run/ (ejecutar ingesta de correo)
    # - GET /api/v1/core/_apps/facturas/ingesta-correo/runs/ (listar ejecuciones de ingesta)
    # - POST /api/v1/core/_apps/facturas/ingesta-correo/preview/ (preview de ingesta sin persistir)
    path("_apps/contabilidad/", include("apps.tenant.contabilidad.api.urls")),
    path("_apps/inventario/", include("apps.tenant.inventario.api.urls")),
    path("_apps/empleados/", include("apps.tenant.empleados.api.urls")),
    path("_apps/gastos/", include("apps.tenant.gastos.api.urls")),
    # # WARNING: COTIZACIONES: Gateway directo a /api/v1/core/_apps/cotizaciones/
    # Expone todas las funcionalidades CRUD de apps/tenant/cotizaciones/api/urls.py:
    # - GET/POST /api/v1/core/_apps/cotizaciones/ (list, create cotizaciones)
    # - GET/PUT/PATCH/DELETE /api/v1/core/_apps/cotizaciones/{uuid}/ (retrieve, update, destroy)
    # - GET /api/v1/core/_apps/cotizaciones/render-offcanvas/crear/ (crear)
    # - GET /api/v1/core/_apps/cotizaciones/{uuid}/render-offcanvas/editar/ (editar)
    # - GET /api/v1/core/_apps/cotizaciones/render-offcanvas/detalle/?id={uuid} (detalle)
    # - GET /api/v1/core/_apps/cotizaciones/{uuid}/exportar-pdf/ (exportar PDF)
    # - POST /api/v1/core/_apps/cotizaciones/{uuid}/recalcular/ (recalcular totales)
    # - GET/POST /api/v1/core/_apps/cotizaciones/items/ (CRUD items)
    # - GET/POST/PUT/PATCH/DELETE /api/v1/core/_apps/cotizaciones/configuracion/ (CRUD configuraciones)
    path("_apps/cotizaciones/", include("apps.tenant.cotizaciones.api.urls")),
    path("_apps/proveedores/", include("apps.tenant.proveedores.api.urls")),
    path("_apps/clientes/", include("apps.tenant.clientes.api.urls")),
    path("_apps/proyectos/", include("apps.tenant.proyectos.api.urls")),
    path("_apps/landing/", include("apps.tenant.landing.api.urls")),
    path("_apps/dashboard/", include("apps.tenant.dashboard.api.urls")),
    path("_apps/perfil/", include("apps.tenant.perfil.api.urls")),
]



urlpatterns.append(path("_apps/facturas/", include("apps.tenant.facturas.api.urls")))
