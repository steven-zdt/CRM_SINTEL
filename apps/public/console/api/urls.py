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
    UsersDataTableView,
    UserTenantsView,
)
from .views_llm_providers import (
    LLMActivateModelView,
    LLMActiveConfigView,
    LLMAuditLogView,
    LLMConnectionSchemasView,
    LLMModelsView,
    LLMModelVerifyCapabilitiesView,
    LLMProviderDiscoverModelsView,
    LLMProvidersView,
    LLMProviderTestConnectionView,
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
    path(
        "dt/users/<int:user_id>/assign-tenant/",
        AssignTenantView.as_view(),
        name="dt_user_assign_tenant",
    ),
    # Tenants huerfanos (sin admin primario)
    path("orphan-tenants/", OrphanTenantsView.as_view(), name="orphan_tenants"),
    path("health/", ConsoleHealthView.as_view(), name="health"),
    # LLM Provider Hub (Fase 8, PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)
    path(
        "llm/connection-schemas/", LLMConnectionSchemasView.as_view(), name="llm_connection_schemas"
    ),
    path("llm/providers/", LLMProvidersView.as_view(), name="llm_providers"),
    path(
        "llm/providers/<int:provider_id>/", LLMProvidersView.as_view(), name="llm_provider_detail"
    ),
    path(
        "llm/providers/<int:provider_id>/test/",
        LLMProviderTestConnectionView.as_view(),
        name="llm_provider_test",
    ),
    path(
        "llm/providers/<int:provider_id>/discover-models/",
        LLMProviderDiscoverModelsView.as_view(),
        name="llm_provider_discover_models",
    ),
    path(
        "llm/providers/<int:provider_id>/models/",
        LLMModelsView.as_view(),
        name="llm_provider_models",
    ),
    path("llm/models/<int:model_id>/", LLMModelsView.as_view(), name="llm_model_detail"),
    path(
        "llm/models/<int:model_id>/verify/",
        LLMModelVerifyCapabilitiesView.as_view(),
        name="llm_model_verify",
    ),
    path(
        "llm/models/<int:model_id>/activate/",
        LLMActivateModelView.as_view(),
        name="llm_model_activate",
    ),
    path("llm/active/", LLMActiveConfigView.as_view(), name="llm_active"),
    path("llm/audit/", LLMAuditLogView.as_view(), name="llm_audit"),
]
