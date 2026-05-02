"""
URLs para la API de consola.

Todas las rutas están bajo /api/admin/v1/console/ y requieren IsAdminUser.
"""

from django.urls import path

from .views import (
    ConsoleHealthView,
    TenantDomainsDataTableView,
    TenantsDataTableView,
    UsersDataTableView,
)

app_name = "console_api"

urlpatterns = [
    path("dt/tenants/", TenantsDataTableView.as_view(), name="dt_tenants"),
    path("dt/tenant-domains/", TenantDomainsDataTableView.as_view(), name="dt_tenant_domains"),
    path("dt/users/", UsersDataTableView.as_view(), name="dt_users"),
    path("health/", ConsoleHealthView.as_view(), name="health"),
]
