"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 12/14: adopcion de OrganizationalContextMixin por ProyectoViewSet/
ItemPresupuestoViewSet/TareaDiariaViewSet/TareaCortaViewSet.

Mismo hallazgo de fondo que en empresa/clientes/proveedores/inventario/
ventas/facturas: get_empresa()/_get_empresa_id() usan el singleton
Empresa.objects.only('id').first() directamente, sin exigir TenantProfile,
mientras OrganizationalContext.resolve() si lo exige.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.api.viewsets import ProyectoViewSet
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.proyectos.services import selectors as proyectos_selectors
from tests.tenant.base_test import SintelTenantTestCase


class ProyectosOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Proyectos", nit="900000986", direccion="Calle 1",
        )
        self.proyecto = Proyecto.objects.create(empresa=self.empresa, nombre="Proyecto Fase9")

    def test_proyectoviewset_exposes_get_organizational_context_with_a_real_profile(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = ProyectoViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        ids_context = set(context.filter(Proyecto).values_list("id", flat=True))
        ids_selector = set(proyectos_selectors.qs_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.proyecto.id, ids_context)

    def test_get_empresa_singleton_and_organizational_context_diverge_without_a_profile(self):
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
