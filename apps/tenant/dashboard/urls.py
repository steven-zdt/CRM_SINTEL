"""
URLs para el dashboard de tenants privados.

WARNING: v2.30: API-First estricto - Este archivo está deshabilitado.
Todas las rutas del dashboard deben consumir exclusivamente los endpoints API en /api/v1/dashboard/.
Si se necesita una ruta /dashboard/, debe ser manejada por el frontend (SPA) o shell estático.

Este archivo se mantiene vacío para evitar errores de importación.
No debe ser incluido en config/urls_tenant.py.
"""

app_name = 'tenant_dashboard'

# WARNING: API-First estricto: No hay rutas aquí
# Todas las rutas del dashboard están en /api/v1/dashboard/ (apps/tenant/dashboard/api/urls.py)
# Si se necesita una ruta /dashboard/, debe ser manejada por el frontend (SPA) o shell estático
urlpatterns = []
