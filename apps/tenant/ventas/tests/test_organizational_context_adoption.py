"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 6/14: adopcion de OrganizationalContextMixin por VentaViewSet/
ResolucionFacturacionViewSet.

Mismo hallazgo de fondo que en empresa/clientes/proveedores/inventario:
VentaServiceMixin hereda BaseServiceMixin pero NO SintelDSVMixin, asi que
_get_empresa_id_seguro() nunca llega a intentar el perfil - cae directo al
singleton Empresa.objects.only('id').first() via _get_empresa(), sin exigir
TenantProfile, mientras OrganizationalContext.resolve() si lo exige.
"""
from apps.tenant.clientes.models import Cliente
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.ventas.api.viewsets import VentaViewSet
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.selectors import VentaSelector
from tests.tenant.base_test import SintelTenantTestCase


class VentaOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Ventas", nit="900000994", direccion="Calle 1",
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="9201", razon_social="Cliente Fase9 Ventas", regimen_tributario="ORDINARIO",
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="VENTA-F9-TEST", subtotal="100.00", total_neto="100.00",
        )

    def test_ventaviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = VentaViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Venta).values_list("id", flat=True))
        ids_selector = set(VentaSelector.get_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.venta.id, ids_context)

    def test_get_empresa_singleton_fallback_and_organizational_context_diverge_without_a_profile(self):
        from django.contrib.sessions.backends.db import SessionStore
        from django.test import RequestFactory

        from apps.tenant.empresa.models import Empresa

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        request.session = SessionStore()

        empresa_resuelta = Empresa.objects.only("id").first()
        self.assertIsNotNone(empresa_resuelta)
        self.assertEqual(empresa_resuelta.id, self.empresa.id)

        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
