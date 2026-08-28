"""
REM P1-02 (docs/remediation/REM-P1-02.md): GastoViewSet.destroy() se saltaba
el guard "debe estar anulado antes de eliminar" cuando settings.DEBUG=True.
La integridad del dato no debe depender de una variable de entorno --
corregido para aplicar el guard siempre. El test fuerza DEBUG=True via
override_settings (el entorno de test real corre con DEBUG=False), que es
exactamente el escenario donde antes el bug era invisible.
"""
from decimal import Decimal

from django.test import override_settings
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class GastoDeleteDebugBypassP1_02Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa P1-02", nit="900000796", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RES-P102-1", prefijo="GP102",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor P1-02", numero_documento="P102-1",
            tipo_documento="NIT",
        )

    def _crear_documento(self, anulado=False):
        return DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, consecutivo=1,
            fecha="2026-06-01", proveedor=self.proveedor, subtotal=Decimal("1000000"),
            total=Decimal("1000000"), descripcion="Gasto P1-02", categoria_contable="ARRENDAMIENTOS",
            anulado=anulado,
        )

    @override_settings(DEBUG=True)
    def test_delete_gasto_no_anulado_es_rechazado_incluso_en_debug(self):
        documento = self._crear_documento(anulado=False)
        resp = self.api_client.delete(f"/api/v1/gastos/{documento.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(DocumentoSoporte.objects.filter(id=documento.id).exists())

    def test_delete_gasto_anulado_es_permitido(self):
        documento = self._crear_documento(anulado=True)
        resp = self.api_client.delete(f"/api/v1/gastos/{documento.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(DocumentoSoporte.objects.filter(id=documento.id).exists())
