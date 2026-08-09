"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 14/14 (ultima app de la fase): adopcion de OrganizationalContextMixin
por DashboardViewSet.

Caso de PARIDAD, igual que compras/bancos/contabilidad/gastos/dashboard:
esta app ya hereda SintelDSVMixin - la misma SSoT que
OrganizationalContext.resolve() duplica (Fase 2). No hay Selector con
.only() que probar en paridad (list()/metricas() llaman directo al
Business Service), asi que el test se limita a confirmar que el contexto
resuelve y coincide con get_empresa_id().
"""
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.dashboard.api.viewsets import DashboardViewSet
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class DashboardOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Dashboard", nit="900000987", direccion="Calle 1",
        )

    def test_dashboardviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = DashboardViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()
        self.assertIsInstance(context, OrganizationalContext)
        self.assertEqual(context.empresa_id, self.empresa.id)
        self.assertEqual(context.empresa_id, view.get_empresa_id())
