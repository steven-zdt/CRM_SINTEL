"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 5/14: adopcion de OrganizationalContextMixin por BaseViewSet (y por
herencia, sus 6 subclases: CategoriaItemViewSet, ProductoViewSet,
ServicioViewSet, ActivoFijoViewSet, MovimientoInventarioViewSet,
HistorialServicioViewSet).

Mismo hallazgo de fondo que en empresa/perfil: `inv_services.
get_empresa_singleton()` (Empresa.objects.only('id').first()) no exige
TenantProfile, mientras OrganizationalContext.resolve() si lo exige - un
QUINTO mecanismo de resolucion de empresa, distinto del de las apps ya
auditadas, con el mismo comportamiento de fondo.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.inventario.api.viewsets import ProductoViewSet
from apps.tenant.inventario.models import Producto
from apps.tenant.inventario.services.selectors import ProductoSelector
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class InventarioOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Inventario", nit="900000995", direccion="Calle 1",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, codigo="SKU-F9", nombre="Producto Fase9",
        )

    def test_productoviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = ProductoViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Producto).values_list("id", flat=True))
        ids_selector = set(ProductoSelector.get_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.producto.id, ids_context)

    def test_get_empresa_singleton_and_organizational_context_diverge_without_a_profile(self):
        from django.contrib.sessions.backends.db import SessionStore
        from django.test import RequestFactory

        from apps.tenant.inventario.services.selectors import get_empresa_singleton

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        request.session = SessionStore()

        empresa_resuelta = get_empresa_singleton()
        self.assertIsNotNone(empresa_resuelta)
        self.assertEqual(empresa_resuelta.id, self.empresa.id)

        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
