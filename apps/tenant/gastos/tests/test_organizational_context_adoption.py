"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 11/14: adopcion de OrganizationalContextMixin por GastoViewSet/
ResolucionDIANViewSet.

Caso de PARIDAD (no divergencia), igual que compras/bancos/contabilidad:
esta app ya hereda SintelDSVMixin - la misma SSoT que
OrganizationalContext.resolve() duplica (Fase 2).
"""
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.gastos.api.viewsets import GastoViewSet
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.selectors import DocumentoSelector
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastosOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Gastos", nit="900000989", direccion="Calle 1",
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RESF9", prefijo="GF9",
            rango_desde=1, rango_hasta=100,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Fase9 Gastos", numero_documento="654", tipo_documento="NIT",
        )
        self.documento = DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=1,
            fecha="2026-05-01", proveedor=self.proveedor, subtotal=1000, total=1000,
            descripcion="Gasto Fase9", categoria_contable="ARRENDAMIENTOS",
        )

    def test_gastoviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = GastoViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(DocumentoSoporte).values_list("id", flat=True))
        ids_selector = set(
            DocumentoSelector.get_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.documento.id, ids_context)
