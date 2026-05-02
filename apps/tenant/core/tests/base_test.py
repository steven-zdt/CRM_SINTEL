"""
Compatibility shim: exposes `SintelTenantTestCase` under
`apps.tenant.core.tests.base_test` for legacy test imports.
"""
try:
    from tests.tenant.base_test import SintelTenantTestCase, TenantTestCase
except Exception:
    from django_tenants.test.cases import TenantTestCase as TenantTestCase

    class SintelTenantTestCase(TenantTestCase):
        pass

__all__ = ["SintelTenantTestCase", "TenantTestCase"]
