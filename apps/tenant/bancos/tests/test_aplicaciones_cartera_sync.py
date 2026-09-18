"""
BANCOS_PDF_APLICACIONES_01 (Fases 07, 09, 12): sincronizacion de
aplicaciones FACTURA_VENTA con Cartera (SSoT real de saldo de cliente) y
validacion de saldo antes de aplicar. Tambien cubre anticipo sin factura
(Escenario E) y combinaciones factura + anticipo (Escenario D).
"""
import uuid as uuid_module
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.clientes.models import Cartera, Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class AplicacionesCarteraSyncTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Cartera Sync", nit="900000905", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Sync", banco="Banco Test",
            tipo="AHORROS", numero="SYNC-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=1, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900111333", razon_social="Cliente Cartera SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )

    def _tx(self, valor):
        return TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 1, 10),
            descripcion="Pago cliente", valor=Decimal(valor), saldo=Decimal(valor),
        )

    def _cartera(self, valor_total, valor_pagado="0", factura_uuid=None):
        return Cartera.objects.create(
            empresa=self.empresa, cliente=self.cliente,
            numero_factura=f"FST-{Cartera.objects.count() + 1}",
            factura_uuid=factura_uuid or uuid_module.uuid4(),
            fecha_emision=date(2026, 1, 1), fecha_vencimiento=date(2026, 2, 1),
            valor_total=Decimal(valor_total), valor_pagado=Decimal(valor_pagado),
        )

    def _aplicar(self, tx, tipo_referencia, monto, referencia_uuid=None, tercero_tipo=None, tercero_uuid=None):
        payload = {
            "tipo_referencia": tipo_referencia, "monto_aplicado": str(monto),
            "fecha_aplicacion": "2026-01-10",
        }
        if referencia_uuid is not None:
            payload["referencia_uuid"] = str(referencia_uuid)
        if tercero_tipo is not None:
            payload["tercero_tipo"] = tercero_tipo
        if tercero_uuid is not None:
            payload["tercero_uuid"] = str(tercero_uuid)
        return self.api_client.post(
            f"/api/v1/bancos/transacciones/{tx.uuid}/aplicaciones/", payload, format="json",
        )

    def test_aplicar_factura_venta_sincroniza_abono_en_cartera(self):
        cartera = self._cartera(valor_total="1000000.00")
        tx = self._tx("500000.00")

        resp = self._aplicar(tx, "FACTURA_VENTA", "500000.00", referencia_uuid=cartera.factura_uuid)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("500000.00"))
        self.assertEqual(cartera.saldo, Decimal("500000.00"))
        self.assertEqual(cartera.estado_pago, "PARCIAL")

    def test_rechaza_aplicacion_que_excede_saldo_cartera(self):
        cartera = self._cartera(valor_total="300000.00")
        tx = self._tx("500000.00")

        resp = self._aplicar(tx, "FACTURA_VENTA", "400000.00", referencia_uuid=cartera.factura_uuid)
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("0.00"))

    def test_aplicacion_sin_cartera_existente_no_bloquea(self):
        tx = self._tx("250000.00")
        resp = self._aplicar(tx, "FACTURA_VENTA", "250000.00", referencia_uuid=uuid_module.uuid4())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

    def test_anticipo_sin_factura_no_crea_factura_ficticia(self):
        tx = self._tx("500000.00")
        resp = self._aplicar(
            tx, "ANTICIPO", "500000.00", tercero_tipo="CLIENTE", tercero_uuid=self.cliente.uuid,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertIsNone(resp.data["referencia_uuid"])
        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 0)

        tx.refresh_from_db()
        self.assertTrue(tx.conciliado)

    def test_movimiento_dividido_factura_mas_anticipo(self):
        """Escenario D: Pago $1.500.000 = Factura A $1.000.000 + Anticipo $500.000."""
        cartera = self._cartera(valor_total="1000000.00")
        tx = self._tx("1500000.00")

        resp1 = self._aplicar(tx, "FACTURA_VENTA", "1000000.00", referencia_uuid=cartera.factura_uuid)
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED, resp1.content)
        resp2 = self._aplicar(tx, "ANTICIPO", "500000.00", tercero_tipo="CLIENTE", tercero_uuid=self.cliente.uuid)
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED, resp2.content)

        tx.refresh_from_db()
        self.assertTrue(tx.conciliado)
        cartera.refresh_from_db()
        self.assertEqual(cartera.estado_pago, "PAGADA")
        self.assertEqual(cartera.saldo, Decimal("0.00"))

    def test_movimiento_dividido_multiples_facturas(self):
        """Escenario B: Pago $2.000.000 repartido entre 3 facturas + anticipo."""
        cartera_a = self._cartera(valor_total="500000.00")
        cartera_b = self._cartera(valor_total="700000.00")
        cartera_c = self._cartera(valor_total="400000.00")
        tx = self._tx("2000000.00")

        for cartera, monto in ((cartera_a, "500000.00"), (cartera_b, "700000.00"), (cartera_c, "400000.00")):
            resp = self._aplicar(tx, "FACTURA_VENTA", monto, referencia_uuid=cartera.factura_uuid)
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        resp_anticipo = self._aplicar(tx, "ANTICIPO", "400000.00", tercero_tipo="CLIENTE", tercero_uuid=self.cliente.uuid)
        self.assertEqual(resp_anticipo.status_code, status.HTTP_201_CREATED, resp_anticipo.content)

        tx.refresh_from_db()
        self.assertTrue(tx.conciliado)
        for cartera in (cartera_a, cartera_b, cartera_c):
            cartera.refresh_from_db()
            self.assertEqual(cartera.estado_pago, "PAGADA")

    def test_editar_aplicacion_incrementa_abono_misma_factura(self):
        cartera = self._cartera(valor_total="1000000.00")
        tx = self._tx("500000.00")
        resp = self._aplicar(tx, "FACTURA_VENTA", "300000.00", referencia_uuid=cartera.factura_uuid)
        aplicacion_uuid = resp.data["uuid"]
        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("300000.00"))

        resp_patch = self.api_client.patch(
            f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/", {"monto_aplicado": "500000.00"}, format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK, resp_patch.content)

        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("500000.00"))

    def test_editar_aplicacion_no_permite_exceder_saldo_cartera(self):
        cartera = self._cartera(valor_total="400000.00")
        tx = self._tx("500000.00")
        resp = self._aplicar(tx, "FACTURA_VENTA", "300000.00", referencia_uuid=cartera.factura_uuid)
        aplicacion_uuid = resp.data["uuid"]

        resp_patch = self.api_client.patch(
            f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/", {"monto_aplicado": "500000.00"}, format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp_patch.content)

    def test_editar_aplicacion_decremento_no_revierte_cartera(self):
        """Limitacion conocida y documentada: Cartera no revierte abonos ya
        aplicados (mismo criterio que el vinculo legado 1:1)."""
        cartera = self._cartera(valor_total="1000000.00")
        tx = self._tx("500000.00")
        resp = self._aplicar(tx, "FACTURA_VENTA", "500000.00", referencia_uuid=cartera.factura_uuid)
        aplicacion_uuid = resp.data["uuid"]
        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("500000.00"))

        resp_patch = self.api_client.patch(
            f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/", {"monto_aplicado": "200000.00"}, format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK, resp_patch.content)

        cartera.refresh_from_db()
        self.assertEqual(cartera.valor_pagado, Decimal("500000.00"))
