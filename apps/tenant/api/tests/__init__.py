"""
Shim package for `apps.tenant.api.tests` used by some test imports.

Re-exports the central `SintelTenantTestCase` so imports like
`from apps.tenant.api.tests.base import SintelTenantTestCase` succeed.
"""
try:
    from tests.tenant.base_test import SintelTenantTestCase, TenantTestCase
except Exception:
    from django_tenants.test.cases import TenantTestCase as TenantTestCase

    class SintelTenantTestCase(TenantTestCase):
        pass

__all__ = ["SintelTenantTestCase", "TenantTestCase"]
