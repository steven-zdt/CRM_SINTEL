"""
DEUDA-C03 "Clientes + Cartera" (decision del usuario, 2026-09-11): al
conciliar una TransaccionBancaria contra una Factura de VENTA, Bancos debe
disparar automaticamente un abono en la Cartera asociada -- Cartera queda
como la UNICA fuente de verdad real de pagos, no un enum aislado en
Factura. Ver apps/tenant/bancos/services/crud_service.py::conciliar_transaccion()
y apps/tenant/clientes/services/business_service.py::
CarteraBusinessService.registrar_abono_desde_conciliacion_bancaria().
"""
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ConciliacionDisparaAbonoCarteraTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa DEUDA-C03", nit="900000799", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta C03", banco="Banco Test",
            tipo="AHORROS", numero="C03-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=6, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900444555", razon_social="Cliente DEUDA-C03",
            regimen_tributario="ORDINARIO", activo=True,
        )
        self.factura_venta = Factura.objects.create(
            empresa=self.empresa, numero="FE-C03-1", consecutivo=1,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-01T00:00:00Z", payment_due_date="2026-07-01",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit=self.cliente.numero_documento, receptor_razon_social=self.cliente.razon_social,
            cliente_uuid=self.cliente.uuid,
            subtotal=Decimal("500000.00"), total=Decimal("500000.00"),
        )

    def _crear_transaccion(self, valor):
        return TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 6, 20),
            descripcion="Pago cliente C03", valor=valor, saldo=valor,
        )

    def test_conciliar_transaccion_crea_cartera_y_registra_abono(self):
        transaccion = self._crear_transaccion(Decimal("300000.00"))
        assert not Cartera.objects.filter(factura_uuid=self.factura_venta.uuid).exists()

        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(self.factura_venta.uuid), "conciliado": True}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        cartera = Cartera.objects.get(factura_uuid=self.factura_venta.uuid)
        self.assertEqual(cartera.valor_total, Decimal("500000.00"))
        self.assertEqual(cartera.valor_pagado, Decimal("300000.00"))
        self.assertEqual(cartera.saldo, Decimal("200000.00"))
        self.assertEqual(cartera.estado_pago, "PARCIAL")

    def test_reguardar_conciliacion_sin_cambiar_flag_no_duplica_abono(self):
        """Editar notas_conciliacion sobre una transaccion YA conciliada no
        debe volver a disparar un abono (guard conciliado_previo)."""
        transaccion = self._crear_transaccion(Decimal("300000.00"))
        self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(self.factura_venta.uuid), "conciliado": True}, format="json",
        )
        cartera = Cartera.objects.get(factura_uuid=self.factura_venta.uuid)
        self.assertEqual(cartera.valor_pagado, Decimal("300000.00"))

        resp2 = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"notas_conciliacion": "Confirmado por el banco"}, format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)

        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("300000.00"))  # sin cambio

    def test_conciliar_factura_de_compra_no_crea_cartera(self):
        """Cartera es CxC (Ventas), nunca CxP (Compras) -- una Factura
        COMPRA conciliada no debe generar ninguna Cartera."""
        factura_compra = Factura.objects.create(
            empresa=self.empresa, numero="FC-C03-1", consecutivo=2,
            naturaleza=Factura.Naturaleza.COMPRA,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit="900999888", emisor_razon_social="Proveedor Externo",
            receptor_nit=self.empresa.nit, receptor_razon_social=self.empresa.razon_social,
            subtotal=Decimal("100000.00"), total=Decimal("100000.00"),
        )
        transaccion = self._crear_transaccion(Decimal("-100000.00"))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(factura_compra.uuid), "conciliado": True}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertFalse(Cartera.objects.filter(factura_uuid=factura_compra.uuid).exists())

    def test_monto_bancario_mayor_al_saldo_se_acota_sin_error(self):
        """Un monto bancario que excede el saldo pendiente no debe romper
        la conciliacion -- se acota al saldo disponible (nunca sobrepago)."""
        transaccion = self._crear_transaccion(Decimal("999999999.00"))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"factura_uuid": str(self.factura_venta.uuid), "conciliado": True}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        cartera = Cartera.objects.get(factura_uuid=self.factura_venta.uuid)
        self.assertEqual(cartera.valor_pagado, Decimal("500000.00"))
        self.assertEqual(cartera.estado_pago, "PAGADA")
