"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md):
adopcion de OrganizationalContextMixin por EmpresaViewSet/SedeViewSet/AreaViewSet.

Prueba dos cosas, no una sola:
  1. La capacidad nueva funciona end-to-end para un usuario CON TenantProfile
     (el caso comun).
  2. La razon documentada para NO migrar get_queryset() todavia es real, no
     teorica: resolve_tenant_empresa() (usado por estos 3 ViewSets) sigue
     funcionando para un usuario SIN TenantProfile via el fallback singleton,
     mientras OrganizationalContext.resolve() para ese mismo request lanza
     OrganizationalContextError - swapear el queryset habria roto ese caso.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.empresa.api.viewsets import SedeViewSet
from apps.tenant.empresa.models import Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class EmpresaOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9", nit="900000999", direccion="Calle 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal Fase9")

    def test_sede_viewset_exposes_get_organizational_context_with_a_real_profile(self):
        """Caso comun: el usuario tiene TenantProfile - la nueva capacidad
        resuelve un contexto correcto y coincide con context.filter(Sede)."""
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp = self.api_client.get("/api/v1/empresas/sedes/")
        self.assertEqual(resp.status_code, 200, resp.content)

        # Reconstruir un request equivalente via APIRequestFactory para
        # invocar get_organizational_context() directamente (mas simple y
        # explicito que inspeccionar el request interno de la respuesta).
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = SedeViewSet()
        view.request = request
        from rest_framework_simplejwt.authentication import JWTAuthentication
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        # Paridad: context.filter(Sede) contra la misma empresa devuelve lo
        # mismo que el SedeSelector que get_queryset() ya usa hoy.
        from apps.tenant.empresa.services.selectors import SedeSelector

        ids_context = set(context.filter(Sede).values_list("id", flat=True))
        ids_selector = set(SedeSelector.get_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.sede.id, ids_context)

    def test_resolve_tenant_empresa_and_organizational_context_diverge_without_a_profile(self):
        """Hallazgo real de esta fase, no teorico: sin TenantProfile,
        resolve_tenant_empresa() (usado hoy por SedeViewSet.get_queryset())
        sigue resolviendo la empresa via el fallback singleton, mientras
        OrganizationalContext.resolve() para el MISMO request falla. Esta es
        la razon documentada por la que get_queryset() no fue migrado en
        esta fase."""
        from django.test import RequestFactory

        from apps.tenant.api.utils import resolve_tenant_empresa

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()

        # Sin TenantProfile: resolve_tenant_empresa() SI resuelve (fallback singleton).
        empresa_resuelta = resolve_tenant_empresa(request, view_instance=None)
        self.assertIsNotNone(empresa_resuelta)
        self.assertEqual(empresa_resuelta.id, self.empresa.id)

        # El mismo request, sin TenantProfile: OrganizationalContext.resolve() falla.
        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
