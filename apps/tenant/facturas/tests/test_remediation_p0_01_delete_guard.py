"""
REM P0-01 (docs/remediation/REM-P0-01.md): FacturaViewSet.destroy() permitia
hard-delete incondicional de cualquier Factura, incluso ACEPTADA con CUFE ya
reconocido por la DIAN, dejando huerfano el AsientoContable ya extraido por
Contabilidad. Corregido: FacturaBusinessService.eliminar_factura() bloquea
el DELETE fuera de BORRADOR -- la via sancionada para el resto es anulacion
(cambiar_estado -> ANULADA), no DELETE fisico.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaDeleteGuardP0_01Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test P0-01", nit="900000790", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

    def _crear_factura(self, numero, estado):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente P0-01",
            estado=estado,
        )

    def test_delete_factura_borrador_es_permitido(self):
        factura = self._crear_factura("FA-P001-BOR", Factura.Estado.BORRADOR)
        resp = self.api_client.delete(f"/api/v1/facturas/{factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(Factura.objects.filter(id=factura.id).exists())

    def test_delete_factura_enviada_es_rechazado(self):
        factura = self._crear_factura("FA-P001-ENV", Factura.Estado.ENVIADA)
        resp = self.api_client.delete(f"/api/v1/facturas/{factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())

    def test_delete_factura_aceptada_es_rechazado(self):
        """Caso central del hallazgo: una factura con CUFE ya aceptado por la DIAN."""
        factura = self._crear_factura("FA-P001-ACE", Factura.Estado.ACEPTADA)
        resp = self.api_client.delete(f"/api/v1/facturas/{factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())

    def test_delete_factura_rechazada_es_rechazado(self):
        factura = self._crear_factura("FA-P001-RCH", Factura.Estado.RECHAZADA)
        resp = self.api_client.delete(f"/api/v1/facturas/{factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())

    def test_delete_factura_anulada_es_rechazado(self):
        """Una factura ya anulada tampoco se borra fisicamente -- el registro persiste."""
        factura = self._crear_factura("FA-P001-ANU", Factura.Estado.ANULADA)
        resp = self.api_client.delete(f"/api/v1/facturas/{factura.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())

    def test_anulacion_sigue_disponible_para_factura_aceptada(self):
        """La via sancionada (cambiar_estado -> ANULADA) sigue funcionando."""
        factura = self._crear_factura("FA-P001-ANULA-VIA", Factura.Estado.ACEPTADA)
        resp = self.api_client.post(
            f"/api/v1/facturas/{factura.uuid}/cambiar-estado/",
            {"estado": "ANULADA"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ANULADA)
