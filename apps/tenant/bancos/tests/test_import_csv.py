"""Fase 2 y Fase 33 (mision Bancos v3.0): importador CSV -- separadores,
BOM, decimales colombianos/americanos, fechas con y sin año."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ImportCSVTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa CSV", nit="900000901", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta CSV", banco="Banco Test",
            tipo="AHORROS", numero="CSV-1",
        )

    def _crear_extracto(self, mes=1, anio=2026):
        resp = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {"cuenta": str(self.cuenta.uuid), "mes": mes, "anio": anio},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        return resp.data["uuid"]

    def _procesar(self, extracto_uuid, contenido_bytes, nombre="mov.csv"):
        archivo = SimpleUploadedFile(nombre, contenido_bytes, content_type="text/csv")
        extracto = ExtractoBancario.objects.get(uuid=extracto_uuid)
        extracto.archivo_s3.save(nombre, archivo, save=True)
        return self.api_client.post(f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/")

    def test_import_csv_semicolon_decimal_colombiano(self):
        extracto_uuid = self._crear_extracto()
        contenido = (
            "FECHA;DESCRIPCION;VALOR;SALDO\n"
            "05/01/2026;Saldo inicial ajuste;100.000,00;100.000,00\n"
            "06/01/2026;Pago cliente;50.000,00;150.000,00\n"
            "07/01/2026;Pago proveedor;-30.000,00;120.000,00\n"
        ).encode("utf-8-sig")
        resp = self._procesar(extracto_uuid, contenido)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["transacciones_importadas"], 3)
        self.assertEqual(resp.data["formato"], "CSV")

        tx = TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).order_by("fecha")
        self.assertEqual(list(tx.values_list("valor", flat=True)), [
            Decimal("100000.00"), Decimal("50000.00"), Decimal("-30000.00"),
        ])

    def test_import_csv_comma_decimal_americano(self):
        extracto_uuid = self._crear_extracto(mes=2)
        contenido = (
            b"FECHA,DESCRIPCION,VALOR,SALDO\n"
            b"01/02/2026,Deposito,1000.50,1000.50\n"
            b"02/02/2026,Retiro,-200.00,800.50\n"
        )
        resp = self._procesar(extracto_uuid, contenido)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["transacciones_importadas"], 2)

    def test_import_csv_formato_no_reconocido_no_rompe_con_500(self):
        extracto_uuid = self._crear_extracto(mes=3)
        resp = self._procesar(extracto_uuid, b"esto no es un csv de banco valido", "raro.csv")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

    def test_import_xml_sin_adapter_responde_error_controlado_no_500(self):
        extracto_uuid = self._crear_extracto(mes=4)
        resp = self._procesar(extracto_uuid, b"<extracto></extracto>", "extracto.xml")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        self.assertIn("UNSUPPORTED_FORMAT", str(resp.data))
