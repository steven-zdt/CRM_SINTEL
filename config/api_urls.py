"""
URLs de APIs REST (por tenant).

WARNING: IMPORTANTE: 
- Estas URLs están disponibles solo cuando se accede a un tenant
- django-tenants maneja automáticamente el aislamiento por esquema
- El TenantMainMiddleware establece el esquema antes de procesar la request
- NO es necesario filtrar manualmente por tenant_id

Arquitectura API-First:
- Cada app tiene su carpeta api/ con serializers, viewsets, urls
- Los routers se registran automáticamente desde cada app
- Referencia: https://www.django-rest-framework.org/api-guide/routers/

WARNING: RESILIENCIA: Este módulo está blindado contra ImportError.
Si una app falla al importar, solo esa app queda fuera; las demás siguen funcionando.

WARNING: SHIMS DE COMPATIBILIDAD: Si algún helper cambió de módulo/nombre,
usa shim de compatibilidad o lazy import para no bloquear el router.
"""
import logging

from django.urls import include, path
from rest_framework.routers import DefaultRouter

logger = logging.getLogger("config.api_urls")

# Router principal para APIs REST (por tenant)
router = DefaultRouter()

# WARNING: HARDENED: Usar include() en lugar de importar urlpatterns directamente
# Esto evita problemas de carga circular y errores de importación en tiempo de módulo
# WARNING: RESILIENCIA: Cada include está en su propio try/except para que un fallo no bloquee las demás apps
# WARNING: SHIMS: Si algún helper cambió de módulo/nombre, usa shim de compatibilidad

def _safe_import_get_empresa_emisor_data():
    """
    Shim de compatibilidad para get_empresa_emisor_data.
    
    Intenta importar desde services; si falla, retorna None (no bloquea el router).
    """
    try:
        from apps.tenant.empresa.services import get_empresa_emisor_data  # noqa
        return get_empresa_emisor_data
    except Exception as e:
        logger.warning(
            "WARNING: get_empresa_emisor_data no disponible (se usa shim). error=%s", e
        )
        return None

# Cargar shim (no crítico para el armado de rutas)
GET_EMPRESA_EMISOR_DATA = _safe_import_get_empresa_emisor_data()

urlpatterns = []

# Redirección de compatibilidad: /api/v1/empresa/ → /api/v1/empresas/
try:
    from apps.tenant.empresa.api.redirects import empresa_singular_redirect
    urlpatterns.append(
        path('empresa/', empresa_singular_redirect, name='empresa-singular-redirect')
    )
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudo cargar redirección de empresa: {e}")

# Apps de tenant (cada una en su propio try/except para resiliencia)
# WARNING: PREFIJO PLURAL: Empresa usa /api/v1/empresas/ (coherente con /api/v1/empresas/mi-empresa/)
try:
    urlpatterns.append(path('empresas/', include('apps.tenant.empresa.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudieron cargar URLs de empresa: {e}")

# Facturas en modo degradado controlado si falta dependencia opcional
try:
    urlpatterns.append(path('facturas/', include('apps.tenant.facturas.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning("[facturas:routes] URLs deshabilitadas por dependencia no disponible: %s", e)

# WARNING: v2.61: Contabilidad expuesta directamente bajo /api/v1/contabilidad/
try:
    urlpatterns.append(path('contabilidad/', include('apps.tenant.contabilidad.api.urls')))
    logger.info("OK: URLs de contabilidad registradas correctamente: /api/v1/contabilidad/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de contabilidad: {e}", exc_info=True)
    # WARNING: v2.61: Re-raise para que el error sea visible y no se silencie
    raise
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de contabilidad: {e}", exc_info=True)
    raise

try:
    urlpatterns.append(path('inventario/', include('apps.tenant.inventario.api.urls')))
    logger.info("OK: URLs de inventario registradas correctamente: /api/v1/inventario/")
    logger.info("   - Categorías: GET /api/v1/inventario/categorias/ (DataTables client-side)")
    logger.info("   - Productos: GET /api/v1/inventario/productos/ (Tabulator v2.40)")
    logger.info("   - Servicios: GET /api/v1/inventario/servicios/ (Tabulator v2.40)")
    logger.info("   - Activos: GET /api/v1/inventario/activos/ (Tabulator v2.40)")
    logger.info("   - Movimientos: GET /api/v1/inventario/movimientos/ (Tabulator v2.40)")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de inventario: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de inventario: {e}", exc_info=True)

try:
    urlpatterns.append(path('perfil/', include('apps.tenant.perfil.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudieron cargar URLs de perfil: {e}")

try:
    urlpatterns.append(path('dashboard/', include('apps.tenant.dashboard.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudieron cargar URLs de dashboard: {e}")

try:
    urlpatterns.append(path('core/', include('apps.tenant.core.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudieron cargar URLs de core: {e}")

try:
    urlpatterns.append(path('empleados/', include('apps.tenant.empleados.api.urls')))
    logger.info("OK: URLs de empleados registradas correctamente: /api/v1/empleados/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de empleados: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de empleados: {e}", exc_info=True)

try:
    urlpatterns.append(path('gastos/', include('apps.tenant.gastos.api.urls')))
    logger.info("OK: URLs de gastos registradas correctamente: /api/v1/gastos/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de gastos: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de gastos: {e}", exc_info=True)


try:
    urlpatterns.append(path('bancos/', include('apps.tenant.bancos.api.urls')))
    logger.info("OK: URLs de bancos registradas correctamente: /api/v1/bancos/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de bancos: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de bancos: {e}", exc_info=True)



try:
    urlpatterns.append(path('proveedores/', include('apps.tenant.proveedores.api.urls')))
    logger.info("OK: URLs de proveedores registradas correctamente: /api/v1/proveedores/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de proveedores: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de proveedores: {e}", exc_info=True)

try:
    urlpatterns.append(path('clientes/', include('apps.tenant.clientes.api.urls')))
    logger.info("OK: URLs de clientes registradas correctamente: /api/v1/clientes/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de clientes: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de clientes: {e}", exc_info=True)

# WARNING: v2.60: Módulo de Cotizaciones - APIs REST
# WARNING: NOTA: Las URLs UI están en config/urls_tenant.py bajo /cotizaciones/
try:
    urlpatterns.append(path('cotizaciones/', include('apps.tenant.cotizaciones.api.urls')))
    logger.info("OK: URLs API de cotizaciones registradas correctamente: /api/v1/cotizaciones/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs API de cotizaciones: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs API de cotizaciones: {e}", exc_info=True)

try:
    urlpatterns.append(path('proyectos/', include('apps.tenant.proyectos.api.urls')))
    logger.info("OK: URLs de proyectos registradas correctamente: /api/v1/proyectos/")
except (ImportError, AttributeError) as e:
    logger.error(f"ERROR: ERROR: No se pudieron cargar URLs de proyectos: {e}", exc_info=True)
except Exception as e:
    logger.error(f"ERROR: ERROR INESPERADO cargando URLs de proyectos: {e}", exc_info=True)

try:
    urlpatterns.append(path('', include('apps.public.impuestos.api.urls')))
except (ImportError, AttributeError) as e:
    logger.warning(f"WARNING: No se pudieron cargar URLs de impuestos: {e}")

# Incluir también el router principal para API Root
urlpatterns += [
    path('', include(router.urls)),
]
