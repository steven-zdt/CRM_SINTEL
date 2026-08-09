"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 8/14: adopcion de OrganizationalContextMixin por FacturaViewSet/
ItemFacturaViewSet/NotaCreditoViewSet.

Mismo hallazgo de fondo que en empresa/clientes/proveedores/inventario/
ventas: resolve_empresa_id_from_request() (facturas/api/viewsets.py) intenta
perfil primero, pero cae al singleton Empresa.objects.only('id').first()
sin exigir TenantProfile, mientras OrganizationalContext.resolve() si lo
exige.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.facturas.api.viewsets import FacturaViewSet
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.selectors import FacturaSelectors
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Facturas", nit="900000992", direccion="Calle 1",
        )
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="FA-F9-TEST", consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit="900000992", emisor_razon_social="Empresa Test OCF Fase9 Facturas",
            receptor_nit="123", receptor_razon_social="Cliente Fase9",
        )

    def test_facturaviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = FacturaViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Factura).values_list("id", flat=True))
        ids_selector = set(FacturaSelectors.qs_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.factura.id, ids_context)

    def test_resolve_empresa_id_from_request_and_organizational_context_diverge_without_a_profile(self):
        from django.contrib.sessions.backends.db import SessionStore
        from django.test import RequestFactory

        from apps.tenant.facturas.api.viewsets import resolve_empresa_id_from_request

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        request.session = SessionStore()

        empresa_id_resuelto = resolve_empresa_id_from_request(request)
        self.assertEqual(empresa_id_resuelto, self.empresa.id)

        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
