"""
Service Layer para Dashboard - Punto de entrada v3.5.
"""
from apps.tenant.dashboard.services.selectors import DashboardSelector
from apps.tenant.dashboard.services.crud_service import DashboardCRUDService
from apps.tenant.dashboard.services.business_service import DashboardBusinessService
from apps.tenant.dashboard.services.api_mixins import DashboardServiceMixin

# Compatibilidad legacy - re-exportar desde services.py original
import importlib.util
from pathlib import Path

services_py_path = Path(__file__).resolve().parent.parent / 'services.py'

if services_py_path.exists():
    spec = importlib.util.spec_from_file_location(
        'dashboard.services_legacy',
        services_py_path
    )
    legacy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_module)

    get_user_role_in_tenant = legacy_module.get_user_role_in_tenant
    get_dashboard_redirect_url = legacy_module.get_dashboard_redirect_url
    get_dashboard_context = legacy_module.get_dashboard_context

__all__ = [
    'DashboardSelector',
    'DashboardCRUDService',
    'DashboardBusinessService',
    'DashboardServiceMixin',
    'get_user_role_in_tenant',
    'get_dashboard_redirect_url',
    'get_dashboard_context',
]
