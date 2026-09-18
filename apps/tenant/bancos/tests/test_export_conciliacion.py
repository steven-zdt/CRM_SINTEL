"""
BAN-12 (.agent/AUDITORIA_FLUJO_COMPLETO.md §10): exportar el reporte de
conciliacion de un extracto (periodo = cuenta + mes/anio) a CSV.
"""
import csv
import io
from datetime import date
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ExportarConciliacionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa BAN-12", nit="900000814", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta BAN-12", banco="Banco Test",
            tipo="AHORROS", numero="BAN12-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=6, anio=2026,
            procesado=True, saldo_inicial=Decimal("0"), saldo_final=Decimal("100000"),
        )
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900666777", razon_social="Cliente BAN-12",
            regimen_tributario="ORDINARIO", activo=True,
        )
        TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 6, 10),
            descripcion="Pago sin conciliar", valor=Decimal("50000"), saldo=Decimal("50000"),
        )
        TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 6, 20),
            descripcion="Pago conciliado", valor=Decimal("100000"), saldo=Decimal("150000"),
            conciliado=True, cliente_uuid=self.cliente.uuid,
        )

    def test_exportar_devuelve_csv_con_todas_las_transacciones(self):
        resp = self.api_client.get(f"/api/v1/bancos/extractos/{self.extracto.uuid}/exportar/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", resp["Content-Disposition"])

        rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
        header, *data_rows = rows
        self.assertEqual(header[0], "Fecha")
        self.assertEqual(len(data_rows), 2)

        conciliado_row = next(r for r in data_rows if r[1] == "Pago conciliado")
        self.assertEqual(conciliado_row[6], "Si")
        self.assertIn("Cliente BAN-12", conciliado_row[7])

        sin_conciliar_row = next(r for r in data_rows if r[1] == "Pago sin conciliar")
        self.assertEqual(sin_conciliar_row[6], "No")
        self.assertEqual(sin_conciliar_row[7], "")
