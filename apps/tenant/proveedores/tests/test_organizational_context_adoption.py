"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 4/14: adopcion de OrganizationalContextMixin por ProveedorViewSet/
CuentasPagarViewSet/RepresentanteViewSet.

Mismo hallazgo que en empresa/clientes: estos ViewSets resuelven la empresa
via resolve_tenant_empresa(), que no exige TenantProfile, mientras
OrganizationalContext.resolve() si lo exige.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.api.viewsets import ProveedorViewSet
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services.selectors import ProveedorSelector
from tests.tenant.base_test import SintelTenantTestCase


class ProveedorOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Proveedores", nit="900000996", direccion="Calle 1",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Fase9", numero_documento="321", tipo_documento="NIT",
        )

    def test_proveedorviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = ProveedorViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Proveedor).values_list("id", flat=True))
        ids_selector = set(ProveedorSelector.get_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.proveedor.id, ids_context)

    def test_resolve_tenant_empresa_and_organizational_context_diverge_without_a_profile(self):
        from django.contrib.sessions.backends.db import SessionStore
        from django.test import RequestFactory

        from apps.tenant.api.utils import resolve_tenant_empresa

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        request.session = SessionStore()

        empresa_resuelta = resolve_tenant_empresa(request, view_instance=None)
        self.assertIsNotNone(empresa_resuelta)
        self.assertEqual(empresa_resuelta.id, self.empresa.id)

        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
