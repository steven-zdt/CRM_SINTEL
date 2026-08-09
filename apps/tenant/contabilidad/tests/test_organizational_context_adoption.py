"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 10/14: adopcion de OrganizationalContextMixin por los 10 ViewSets de
contabilidad (CuentaContable, AsientoContable, MovimientoContable,
CatalogoMaestroNIIF, PeriodoContable, TipoComprobante, DocumentosPendientes,
ConfiguracionRetenciones, Retencion, LibroDiario, PlantillaContable).

Caso de PARIDAD (no divergencia), igual que compras/bancos: toda la app ya
hereda SintelDSVMixin y usa self.get_empresa_id() directamente - la misma
SSoT que OrganizationalContext.resolve() duplica (Fase 2).
"""
from apps.tenant.contabilidad.api.viewsets import CuentaContableViewSet
from apps.tenant.contabilidad.models import CuentaContable
from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ContabilidadOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Contabilidad", nit="900000990", direccion="Calle 1",
        )
        self.cuenta = CuentaContable.objects.create(
            empresa=self.empresa, codigo="1105-F9", nombre="Caja Fase9", tipo="ACTIVO",
        )

    def test_cuentacontableviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = CuentaContableViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(CuentaContable).values_list("id", flat=True))
        ids_selector = set(
            CuentaContableSelector.get_qs_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.cuenta.id, ids_context)
