"""
Fase 1 y Fase 33 (mision Bancos v3.0): usa el extracto bancario REAL
(media/extractos/10800014844_AGO2026.xlsx) como fixture -- no un Excel
artificial. Valida el release gate exacto pedido por la mision:

    60 movimientos, 24 creditos, 36 debitos,
    creditos=8,656,342.15  debitos=9,633,350.20
    saldo_inicial=986,830.85  saldo_final=9,822.80
"""
import os
from decimal import Decimal

from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

FIXTURE_PATH = os.path.join("media", "extractos", "10800014844_AGO2026.xlsx")


class ImportXLSXFixtureRealTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Fixture Real", nit="900000900", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Fixture", banco="Banco Test",
            tipo="AHORROS", numero="10800014844",
        )

    def _crear_y_procesar_extracto(self):
        assert os.path.exists(FIXTURE_PATH), f"Fixture real no encontrado: {FIXTURE_PATH}"
        from django.core.files.uploadedfile import SimpleUploadedFile

        with open(FIXTURE_PATH, "rb") as f:
            archivo = SimpleUploadedFile(
                "10800014844_AGO2026.xlsx", f.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        resp_crear = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {"cuenta": str(self.cuenta.uuid), "mes": 8, "anio": 2026, "archivo_s3": archivo},
            format="multipart",
        )
        self.assertEqual(resp_crear.status_code, status.HTTP_201_CREATED, resp_crear.content)
        extracto_uuid = resp_crear.data["uuid"]

        resp_procesar = self.api_client.post(f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/")
        self.assertEqual(resp_procesar.status_code, status.HTTP_200_OK, resp_procesar.content)
        return extracto_uuid, resp_procesar.data

    def test_import_xlsx_real_bank_statement_release_gate(self):
        extracto_uuid, resultado = self._crear_y_procesar_extracto()

        self.assertEqual(resultado["transacciones_importadas"], 60)
        self.assertEqual(resultado["filas_omitidas"], 0)
        self.assertEqual(resultado["errores"], [])
        self.assertEqual(resultado["formato"], "XLSX")
        self.assertEqual(Decimal(resultado["saldo_inicial"]), Decimal("986830.85"))
        self.assertEqual(Decimal(resultado["saldo_final"]), Decimal("9822.80"))
        self.assertEqual(Decimal(resultado["total_creditos"]), Decimal("8656342.15"))
        self.assertEqual(Decimal(resultado["total_debitos"]), Decimal("9633350.20"))

        extracto = ExtractoBancario.objects.get(uuid=extracto_uuid)
        self.assertTrue(extracto.procesado)
        self.assertEqual(extracto.saldo_inicial, Decimal("986830.85"))
        self.assertEqual(extracto.saldo_final, Decimal("9822.80"))

        transacciones = TransaccionBancaria.objects.filter(extracto=extracto)
        self.assertEqual(transacciones.count(), 60)

        creditos = transacciones.filter(valor__gte=0)
        debitos = transacciones.filter(valor__lt=0)
        self.assertEqual(creditos.count(), 24)
        self.assertEqual(debitos.count(), 36)

        primero = transacciones.order_by("fecha", "id").first()
        self.assertEqual(primero.fecha.isoformat(), "2026-08-03")
        self.assertEqual(primero.descripcion, "ABONO INTERESES AHORROS")
        self.assertEqual(primero.valor, Decimal("4.05"))

        ultimo = transacciones.order_by("fecha", "id").last()
        self.assertEqual(ultimo.fecha.isoformat(), "2026-08-31")
        self.assertEqual(ultimo.saldo, Decimal("9822.80"))

    def test_reprocesar_extracto_no_conciliado_es_idempotente(self):
        extracto_uuid, _ = self._crear_y_procesar_extracto()
        resp2 = self.api_client.post(f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)
        self.assertEqual(
            TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).count(), 60
        )

    def test_reprocesar_extracto_con_conciliaciones_bloquea_sin_forzar(self):
        extracto_uuid, _ = self._crear_y_procesar_extracto()
        tx = TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).first()
        tx.conciliado = True
        tx.save(update_fields=["conciliado"])

        resp = self.api_client.post(f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        self.assertEqual(TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).count(), 60)

    def test_render_offcanvas_detalle_incluye_kpis_fase19(self):
        """Fase 19: el offcanvas de detalle debe renderizar sin error y
        exponer el resumen KPI (ingresos/egresos/neto/pendientes/conciliados)."""
        extracto_uuid, _ = self._crear_y_procesar_extracto()
        resp = self.api_client.get(f"/api/v1/bancos/extractos/{extracto_uuid}/render-offcanvas/detalle/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        contenido = resp.content.decode("utf-8")
        self.assertIn("Ingresos", contenido)
        self.assertIn("Egresos", contenido)
        self.assertIn("Pendientes", contenido)
        self.assertIn("Conciliados", contenido)

    def test_reprocesar_extracto_con_conciliaciones_forzado_reemplaza(self):
        extracto_uuid, _ = self._crear_y_procesar_extracto()
        tx = TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).first()
        tx.conciliado = True
        tx.save(update_fields=["conciliado"])

        resp = self.api_client.post(
            f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/", {"forzar": True}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # Reemplazadas -- la que se marco conciliado ya no existe (fue borrada e reinsertada).
        self.assertFalse(
            TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid, conciliado=True).exists()
        )
