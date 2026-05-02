"""
Compat layer for test helpers expected under `apps.tenant.core.tests`.

This module re-exports the project test base `SintelTenantTestCase` so older
imports like `from apps.tenant.core.tests import SintelTenantTestCase`
continue to work after refactors.
"""
try:
    # Preferred source: central tests helper
    from tests.tenant.base_test import SintelTenantTestCase, TenantTestCase
except Exception:
    # Fallback: use django-tenants' TenantTestCase as a minimal substitute
    from django_tenants.test.cases import TenantTestCase as TenantTestCase

    class SintelTenantTestCase(TenantTestCase):
        """Minimal shim for environments where project test helpers are missing."""
        pass

__all__ = ["SintelTenantTestCase", "TenantTestCase"]
