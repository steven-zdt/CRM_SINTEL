"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 9/14: adopcion de OrganizationalContextMixin por CuentaBancariaViewSet/
ExtractoBancarioViewSet/TransaccionBancariaViewSet.

Caso de PARIDAD (no divergencia), igual que compras: bancos SI hereda
SintelDSVMixin - la misma SSoT que OrganizationalContext.resolve() duplica
(Fase 2). get_queryset() sigue sin migrarse porque get_qs_list() usa el
selector con sus propios .only(), que el context.filter() generico no
replica.
"""
from apps.tenant.bancos.api.viewsets import CuentaBancariaViewSet
from apps.tenant.bancos.models import CuentaBancaria
from apps.tenant.bancos.services.selectors import CuentaBancariaSelector
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class BancosOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Bancos", nit="900000991", direccion="Calle 1",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Fase9", banco="BANCOLOMBIA", tipo="AHORROS", numero="123456",
        )

    def test_cuentabancariaviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = CuentaBancariaViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        # Paridad directa contra la SSoT que este ViewSet ya usaba:
        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(CuentaBancaria).values_list("id", flat=True))
        ids_selector = set(
            CuentaBancariaSelector.get_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.cuenta.id, ids_context)
