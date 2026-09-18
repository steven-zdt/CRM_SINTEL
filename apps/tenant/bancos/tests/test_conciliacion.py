"""
BAN-08 (.agent/AUDITORIA_FLUJO_COMPLETO.md §10): cobertura basica del vinculo
legado 1:1 (PATCH /transacciones/{uuid}/conciliar/, crud_service.py::
conciliar_transaccion()) para los 3 escenarios documentados que no tenian un
test dedicado: INGRESO->Cliente, EGRESO->Proveedor, quitar vinculo.

No duplica lo ya cubierto por test_conciliacion_dispara_abono_cartera.py
(sincronizacion con Cartera) ni por test_remediation_p1_04_fecha_pago_vs_documento.py
(validacion de fecha) -- este archivo cubre el contrato basico del endpoint.
"""
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ConciliacionTransaccionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa BAN-08", nit="900000811", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta BAN-08", banco="Banco Test",
            tipo="AHORROS", numero="BAN08-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=6, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900555111", razon_social="Cliente BAN-08",
            regimen_tributario="ORDINARIO", activo=True,
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900555222", razon_social="Proveedor BAN-08",
            regimen_tributario="ORDINARIO", activo=True,
        )

    def _crear_transaccion(self, valor):
        return TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 6, 20),
            descripcion="Movimiento BAN-08", valor=valor, saldo=valor,
        )

    def test_conciliar_ingreso_con_cliente(self):
        """INGRESO (valor >= 0) -> vinculo con cliente_uuid marca conciliado=True."""
        transaccion = self._crear_transaccion(Decimal("100000"))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"cliente_uuid": str(self.cliente.uuid)}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        transaccion.refresh_from_db()
        self.assertEqual(transaccion.cliente_uuid, self.cliente.uuid)
        self.assertIsNone(transaccion.proveedor_uuid)
        self.assertTrue(transaccion.conciliado)

    def test_conciliar_egreso_con_proveedor(self):
        """EGRESO (valor < 0) -> vinculo con proveedor_uuid marca conciliado=True."""
        transaccion = self._crear_transaccion(Decimal("-50000"))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"proveedor_uuid": str(self.proveedor.uuid)}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        transaccion.refresh_from_db()
        self.assertEqual(transaccion.proveedor_uuid, self.proveedor.uuid)
        self.assertIsNone(transaccion.cliente_uuid)
        self.assertTrue(transaccion.conciliado)

    def test_quitar_vinculo(self):
        """Enviar todos los campos en null + conciliado=false limpia el vinculo previo."""
        transaccion = self._crear_transaccion(Decimal("100000"))
        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {"cliente_uuid": str(self.cliente.uuid)}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        resp = self.api_client.patch(
            f"/api/v1/bancos/transacciones/{transaccion.uuid}/conciliar/",
            {
                "factura_uuid": None, "proveedor_uuid": None,
                "cliente_uuid": None, "conciliado": False,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        transaccion.refresh_from_db()
        self.assertIsNone(transaccion.factura_uuid)
        self.assertIsNone(transaccion.proveedor_uuid)
        self.assertIsNone(transaccion.cliente_uuid)
        self.assertFalse(transaccion.conciliado)
