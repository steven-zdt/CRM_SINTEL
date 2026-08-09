"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 3/14: adopcion de OrganizationalContextMixin por ClienteViewSet/
ContactoClienteViewSet/CarteraViewSet.

Mismo hallazgo que en empresa (app 1/14): estos ViewSets resuelven la
empresa via resolve_tenant_empresa() (apps/tenant/api/utils.py), que no
exige TenantProfile, mientras OrganizationalContext.resolve() si lo exige.
No se repite la investigacion completa - se confirma con un test dedicado.
"""
from apps.tenant.clientes.api.viewsets import ClienteViewSet
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.selectors import ClienteSelector
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ClienteOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Clientes", nit="900000997", direccion="Calle 1",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, razon_social="Cliente Fase9", numero_documento="123",
            tipo_documento="CC", tipo_persona="NATURAL",
        )

    def test_clienteviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = ClienteViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Cliente).values_list("id", flat=True))
        ids_selector = set(ClienteSelector.get_cliente_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.cliente.id, ids_context)

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
