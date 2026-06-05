"""
URLs para la API de consola.

Todas las rutas están bajo /api/admin/v1/console/ y requieren IsAdminUser.
"""

from django.urls import path

from .views import (
    AssignTenantView,
    ConsoleHealthView,
    OrphanTenantsView,
    TenantDomainsDataTableView,
    TenantsDataTableView,
    UserTenantsView,
    UsersDataTableView,
)

app_name = "console_api"

urlpatterns = [
    path("dt/tenants/", TenantsDataTableView.as_view(), name="dt_tenants"),
    path("dt/tenant-domains/", TenantDomainsDataTableView.as_view(), name="dt_tenant_domains"),
    # CRUD Usuarios
    path("dt/users/", UsersDataTableView.as_view(), name="dt_users"),
    path("dt/users/<int:user_id>/", UsersDataTableView.as_view(), name="dt_user_detail"),
    # Tenant de usuario
    path("dt/users/<int:user_id>/tenants/", UserTenantsView.as_view(), name="dt_user_tenants"),
    path("dt/users/<int:user_id>/assign-tenant/", AssignTenantView.as_view(), name="dt_user_assign_tenant"),
    # Tenants huerfanos (sin admin primario)
    path("orphan-tenants/", OrphanTenantsView.as_view(), name="orphan_tenants"),
    path("health/", ConsoleHealthView.as_view(), name="health"),
]
