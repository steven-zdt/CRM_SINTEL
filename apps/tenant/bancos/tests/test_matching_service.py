"""Fase 8-12 y Fase 33 (mision Bancos v3.0): BankTransactionMatchingService
-- motor de sugerencias, solo lectura, nunca escribe."""
from datetime import date
from decimal import Decimal

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.bancos.services.matching_service import BankTransactionMatchingService
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class MatchingServiceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Matching", nit="900000905", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Matching", banco="Banco Test",
            tipo="AHORROS", numero="MAT-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=1, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )

    def _tx(self, valor, descripcion, fecha=date(2026, 1, 15)):
        return TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=fecha,
            descripcion=descripcion, valor=valor, saldo=valor,
        )

    def test_suggest_sale_invoice_for_credit(self):
        cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900111222", razon_social="ACME COLOMBIA SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        factura = Factura.objects.create(
            empresa=self.empresa, numero="FV-1001", consecutivo=1,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-01-14T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
            cliente_uuid=cliente.uuid,
            subtotal=Decimal("1400000.00"), total=Decimal("1400000.00"),
        )
        tx = self._tx(Decimal("1400000.00"), "PAGO INTERBANC ACME COLOMBIA SAS")

        candidatos = BankTransactionMatchingService.sugerir(tx)
        tipos = {c["tipo"] for c in candidatos}
        assert "FACTURA_VENTA" in tipos
        mejor = max((c for c in candidatos if c["tipo"] == "FACTURA_VENTA"), key=lambda c: c["score"])
        assert mejor["uuid"] == str(factura.uuid)
        assert mejor["score"] > 0.5
        assert any("monto" in r for r in mejor["reason"])

    def test_suggest_purchase_invoice_for_debit(self):
        proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900333444", razon_social="MOVISTAR COLOMBIA SA",
            regimen_tributario="ORDINARIO", activo=True,
        )
        factura = Factura.objects.create(
            empresa=self.empresa, numero="FC-2001", consecutivo=1,
            naturaleza=Factura.Naturaleza.COMPRA,
            fecha_emision="2026-01-13T00:00:00Z",
            emisor_nit=proveedor.numero_documento, emisor_razon_social=proveedor.razon_social,
            receptor_nit=self.empresa.nit, receptor_razon_social=self.empresa.razon_social,
            subtotal=Decimal("192844.00"), total=Decimal("192844.00"),
        )
        tx = self._tx(Decimal("-192844.00"), "PAGO SV MOVISTAR COLOMBIA SA")

        candidatos = BankTransactionMatchingService.sugerir(tx)
        tipos = {c["tipo"] for c in candidatos}
        assert "FACTURA_COMPRA" in tipos
        mejor = max((c for c in candidatos if c["tipo"] == "FACTURA_COMPRA"), key=lambda c: c["score"])
        assert mejor["uuid"] == str(factura.uuid)

    def test_suggest_client_for_credit(self):
        cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900555666", razon_social="FOCUS ELECTRONICA SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        tx = self._tx(Decimal("500000.00"), "PAGO INTERBANC FOCUS ELECTRONICA SAS")

        candidatos = BankTransactionMatchingService.sugerir(tx)
        clientes = [c for c in candidatos if c["tipo"] == "CLIENTE"]
        assert any(c["uuid"] == str(cliente.uuid) for c in clientes)

    def test_suggest_supplier_for_debit(self):
        proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900777888", razon_social="BODYTECH PLAZA SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        tx = self._tx(Decimal("-139800.00"), "COMPRA EN BODYTECH PLAZA SAS")

        candidatos = BankTransactionMatchingService.sugerir(tx)
        proveedores = [c for c in candidatos if c["tipo"] == "PROVEEDOR"]
        assert any(c["uuid"] == str(proveedor.uuid) for c in proveedores)

    def test_sugerencias_nunca_escriben_datos(self):
        from apps.tenant.bancos.models import MovimientoBancarioAplicacion

        tx = self._tx(Decimal("100000.00"), "TRANSFERENCIA VIRTUAL")
        BankTransactionMatchingService.sugerir(tx)
        assert not MovimientoBancarioAplicacion.objects.filter(transaccion=tx).exists()
        tx.refresh_from_db()
        assert tx.conciliado is False

    def test_sin_candidatos_no_rompe(self):
        tx = self._tx(Decimal("-9999999.99"), "MOVIMIENTO SIN NINGUNA COINCIDENCIA POSIBLE")
        candidatos = BankTransactionMatchingService.sugerir(tx)
        assert isinstance(candidatos, list)
