from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import (
    ActivoFijoViewSet,
    CategoriaItemViewSet,
    HistorialServicioViewSet,
    MovimientoInventarioViewSet,
    ProductoViewSet,
    ServicioViewSet,
)

# Configuración del Router
router = DefaultRouter()

# 1. Categorías (Maestras)
router.register(r'categorias', CategoriaItemViewSet, basename='inv-categorias')

# 2. Catálogo Comercial (Separado)
router.register(r'productos', ProductoViewSet, basename='inv-productos')
router.register(r'servicios', ServicioViewSet, basename='inv-servicios')

# 3. Activos Fijos (Internos)
router.register(r'activos', ActivoFijoViewSet, basename='inv-activos')

# 4. Trazabilidad y Movimientos
router.register(r'movimientos', MovimientoInventarioViewSet, basename='inv-movimientos')
router.register(r'historial-servicios', HistorialServicioViewSet, basename='inv-historial-servicios')

# Registro de URLs
urlpatterns = [
    path('', include(router.urls)),
]

# NOTA DE ARQUITECTURA v2.40:
# ---------------------------
# - Se eliminó el endpoint unificado 'catalogo/' en favor de 'productos/' y 'servicios/'.
# - Se eliminó 'vinculos/item-catalogo' ya que ahora usamos referencias desacopladas (strings).
#
# ENDPOINTS PRINCIPALES (Tabulator Factory v2.40):
# -------------------------------------------------
# GET /api/v1/inventario/categorias/          - Lista de categorías (DataTables client-side)
# GET /api/v1/inventario/productos/          - Lista paginada de productos (Tabulator)
# GET /api/v1/inventario/servicios/          - Lista paginada de servicios (Tabulator)
# GET /api/v1/inventario/activos/             - Lista paginada de activos fijos (Tabulator)
# GET /api/v1/inventario/movimientos/        - Lista paginada de movimientos/Kardex (Tabulator)
#
# Todos los endpoints principales soportan:
# - Paginación estándar DRF: ?page=1&page_size=10
# - Búsqueda: ?search=texto
# - Filtrado por empresa (automático, SSoT)
#
# El frontend Tabulator Factory consume directamente los endpoints GET estándar.