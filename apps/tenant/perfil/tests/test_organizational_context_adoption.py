"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 2/14: adopcion de OrganizationalContextMixin por PerfilViewSet/DepartamentoViewSet.

Mismo hallazgo que en empresa (app 1/14), confirmado de nuevo aqui de forma
independiente: PerfilServiceMixin._resolve_empresa_id() (y el codigo inline
identico en varios metodos de PerfilViewSet/DepartamentoViewSet) resuelve la
empresa via Empresa.objects.only('id').first() - el singleton del schema,
sin exigir TenantProfile - mientras OrganizationalContext.resolve() para el
mismo request exige TenantProfile y lanza OrganizationalContextError si no
existe. Por eso get_queryset()/list()/etc. no fueron migrados en esta fase.
"""
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.perfil.api.viewsets import PerfilViewSet
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.perfil.services.selectors import PerfilSelector
from tests.tenant.base_test import SintelTenantTestCase


class PerfilOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Perfil", nit="900000998", direccion="Calle 1",
        )

    def test_perfilviewset_exposes_get_organizational_context_with_a_real_profile(self):
        """Caso comun: el usuario tiene TenantProfile - la nueva capacidad
        resuelve un contexto correcto y coincide con context.filter(TenantProfile)."""
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.authentication import JWTAuthentication

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = PerfilViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)

        # Paridad: context.filter(TenantProfile) contra la misma empresa
        # devuelve lo mismo que el PerfilSelector que get_qs_list() ya usa hoy.
        ids_context = set(context.filter(TenantProfile).values_list("id", flat=True))
        ids_selector = set(PerfilSelector.get_list(self.empresa.id).values_list("id", flat=True))
        self.assertEqual(ids_context, ids_selector)

    def test_resolve_empresa_inline_and_organizational_context_diverge_without_a_profile(self):
        """Hallazgo real de esta fase (confirmado independientemente del de
        empresa/app 1/14): sin TenantProfile, el patron
        Empresa.objects.only('id').first() usado hoy por PerfilViewSet/
        DepartamentoViewSet/PerfilServiceMixin sigue resolviendo la empresa
        (singleton del schema), mientras OrganizationalContext.resolve()
        para el MISMO request falla. Razon documentada por la que
        get_queryset()/list()/etc. no fueron migrados en esta fase."""
        from django.contrib.sessions.backends.db import SessionStore
        from django.test import RequestFactory

        from apps.tenant.empresa.models import Empresa

        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        request.session = SessionStore()

        # Sin TenantProfile: el patron usado por perfil SI resuelve (singleton).
        empresa_resuelta = Empresa.objects.only("id").first()
        self.assertIsNotNone(empresa_resuelta)
        self.assertEqual(empresa_resuelta.id, self.empresa.id)

        # El mismo request, sin TenantProfile: OrganizationalContext.resolve() falla.
        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)
