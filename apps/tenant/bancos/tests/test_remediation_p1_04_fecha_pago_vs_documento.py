"""
REM P1-04 (docs/remediation/REM-P1-04.md): TransaccionBancariaConciliarSerializer/
conciliar_transaccion() no validaban que la fecha de la transaccion (pago)
fuera posterior o igual a la fecha de emision de la Factura vinculada. Se
agrego la validacion en conciliar_transaccion() (bancos), resolviendo la
Factura via FacturaInterAppAPI.get_by_id() (bridge cross-app ya sancionado,
mismo usado por el trigger de recalculo de estado_pago en este mismo metodo).
"""
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FechaPagoVsDocumentoP1_04Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa P1-04", nit="900000798", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta P1-04", banco="Banco Test",
            tipo="AHORROS", numero="P104-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=6, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.factura = Factura.objects.create(
            empresa=self.empresa, numero="FA-P104-1", consecutivo=1,
            fecha_emision="2026-06-15T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente P1-04",
        )

    def _crear_transaccion(self, fecha):
        return TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=fecha,
            descripcion="Pago P1-04", valor=Decimal("100000"), saldo=Decimal("100000"),
        )

    def test_conciliar_con_fecha_posterior_a_la_factura_es_permitido(self):
        transaccion = self._crear_transaccion(date(2026, 6, 20))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(self.factura.uuid)}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_conciliar_con_fecha_anterior_a_la_factura_es_rechazado(self):
        transaccion = self._crear_transaccion(date(2026, 6, 1))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(self.factura.uuid)}, format="json",
        )
        # NOTA: conciliar_transaccion() vive en la capa de servicio (crud_service),
        # no en el serializer -- SintelServiceMixin.handle_service_error() mapea
        # DRFValidationError levantado ahi a 422 (convencion ya establecida del
        # proyecto, distinta de los 400 que produce serializer.is_valid()).
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        transaccion.refresh_from_db()
        self.assertIsNone(transaccion.factura_uuid)

    def test_conciliar_con_factura_uuid_no_resoluble_no_bloquea(self):
        """Soft-reference sin match: no se bloquea, mismo criterio que el
        resto del proyecto (Kardex/Retenciones) para referencias blandas."""
        import uuid as uuid_mod
        transaccion = self._crear_transaccion(date(2026, 1, 1))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(uuid_mod.uuid4())}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
