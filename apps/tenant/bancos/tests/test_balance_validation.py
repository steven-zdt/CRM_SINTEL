"""Fase 1 (mision Bancos v3.0): saldo_inicial + creditos - debitos debe
igualar saldo_final (tolerancia 0.01) o el importador reporta la
inconsistencia y NUNCA marca procesado=True en silencio."""

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class BalanceValidationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Balance", nit="900000902", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Balance", banco="Banco Test",
            tipo="AHORROS", numero="BAL-1",
        )
        resp = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {"cuenta": str(self.cuenta.uuid), "mes": 1, "anio": 2026},
            format="json",
        )
        self.extracto_uuid = resp.data["uuid"]

    def _procesar(self, contenido_bytes):
        archivo = SimpleUploadedFile("mov.csv", contenido_bytes, content_type="text/csv")
        extracto = ExtractoBancario.objects.get(uuid=self.extracto_uuid)
        extracto.archivo_s3.save("mov.csv", archivo, save=True)
        return self.api_client.post(f"/api/v1/bancos/extractos/{self.extracto_uuid}/procesar/")

    def test_balance_consistente_se_procesa_normalmente(self):
        contenido = (
            b"FECHA,DESCRIPCION,VALOR,SALDO\n"
            b"01/01/2026,Ingreso,1000.00,1000.00\n"
            b"02/01/2026,Egreso,-400.00,600.00\n"
        )
        resp = self._procesar(contenido)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_balance_inconsistente_bloquea_y_no_marca_procesado(self):
        contenido = (
            b"FECHA,DESCRIPCION,VALOR,SALDO\n"
            b"01/01/2026,Ingreso,1000.00,1000.00\n"
            # Saldo final declarado (9999.00) no cuadra con 1000 - 1000 = 0.
            b"02/01/2026,Egreso,-1000.00,9999.00\n"
        )
        resp = self._procesar(contenido)
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        self.assertIn("Inconsistencia de saldos", str(resp.data))

        extracto = ExtractoBancario.objects.get(uuid=self.extracto_uuid)
        self.assertFalse(extracto.procesado)
        self.assertEqual(TransaccionBancaria.objects.filter(extracto=extracto).count(), 0)
