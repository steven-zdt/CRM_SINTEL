"""
BANCOS_PDF_APLICACIONES_01 (Fases 28-41): importador PDF de extractos.

Fixtures sinteticas generadas con xhtml2pdf (ya en requirements.txt, no se
agrega dependencia nueva) -- representativas de un layout de una columna
"valor" + una columna "saldo" por fila, NO un banco real especifico (el
plan explicitamente prohibe declarar soporte universal solo por un PDF
que funcione).
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from xhtml2pdf import pisa

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.bancos.services.importers.base import StatementParsingError
from apps.tenant.bancos.services.importers.pdf_importer import (
    PDFBankStatementImporter,
    parsear_texto_extracto,
)
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


def _pdf_desde_lineas(lineas: list) -> bytes:
    cuerpo = "\n".join(lineas)
    html = (
        '<html><body><pre style="font-family: monospace; font-size: 10pt;">\n'
        f"{cuerpo}\n"
        "</pre></body></html>"
    )
    buf = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), buf, encoding="UTF-8")
    return buf.getvalue()


def _pdf_vacio() -> bytes:
    buf = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(b"<html><body></body></html>"), buf, encoding="UTF-8")
    return buf.getvalue()


class PDFImporterUnitTests(SintelTenantTestCase):
    """Tests unitarios directos del importador (sin pasar por la API)."""

    def setUp(self):
        super().setUp()
        self.importer = PDFBankStatementImporter()

    def test_puede_procesar_extension_pdf(self):
        self.assertTrue(self.importer.puede_procesar("extracto.pdf"))
        self.assertFalse(self.importer.puede_procesar("extracto.xlsx"))

    def test_importa_movimientos_formato_colombiano(self):
        pdf_bytes = _pdf_desde_lineas([
            "01/06/2026  Saldo inicial ajuste  1.400.000,00  1.400.000,00",
            "02/06/2026  Pago cliente Acme  500.000,00  1.900.000,00",
            "03/06/2026  Retiro cajero  -100.000,00  1.800.000,00",
        ])
        resultado = self.importer.importar(io.BytesIO(pdf_bytes), "extracto.pdf")
        self.assertEqual(len(resultado.transactions), 3)
        self.assertEqual(str(resultado.transactions[1].valor), "500000.00")
        self.assertEqual(str(resultado.transactions[2].valor), "-100000.00")

    def test_multipagina_concatena_movimientos(self):
        """pdfminer.extract_text() concatena todas las paginas en un solo
        string -- se prueba el contrato real (texto multi-pagina ya
        concatenado, tal como lo entrega pdfminer) en vez de depender del
        round-trip completo de renderizado de un PDF de 2 paginas (el
        layout visual exacto que produce un motor de PDF para saltos de
        pagina no es 100% determinista entre entornos de ejecucion)."""
        texto = (
            "01/06/2026  Movimiento pagina 1  100.000,00  100.000,00\n"
            "\x0c"  # form-feed: separador de pagina real que emite pdfminer
            "02/06/2026  Movimiento pagina 2  200.000,00  300.000,00\n"
        )
        resultado = parsear_texto_extracto(texto)
        self.assertEqual(len(resultado.transactions), 2)

    def test_encabezados_repetidos_no_generan_movimientos_falsos(self):
        texto = (
            "FECHA  DESCRIPCION  VALOR  SALDO\n"
            "01/06/2026  Pago  100.000,00  100.000,00\n"
            "FECHA  DESCRIPCION  VALOR  SALDO\n"
            "02/06/2026  Pago 2  200.000,00  300.000,00\n"
        )
        resultado = parsear_texto_extracto(texto)
        self.assertEqual(len(resultado.transactions), 2)

    def test_pdf_sin_firma_binaria_valida(self):
        with self.assertRaises(StatementParsingError):
            self.importer.importar(io.BytesIO(b"esto no es un pdf"), "falso.pdf")

    def test_pdf_corrupto(self):
        with self.assertRaises(StatementParsingError):
            self.importer.importar(
                io.BytesIO(b"%PDF-1.4\nno es una estructura pdf valida"), "corrupto.pdf"
            )

    def test_pdf_vacio_sin_texto_needs_ocr(self):
        with self.assertRaises(StatementParsingError) as ctx:
            self.importer.importar(io.BytesIO(_pdf_vacio()), "escaneado.pdf")
        self.assertIn("NEEDS_OCR", str(ctx.exception))

    def test_pdf_sin_movimientos_reconocibles(self):
        pdf_bytes = _pdf_desde_lineas(["Este PDF no tiene ninguna fila con fecha y montos."])
        with self.assertRaises(StatementParsingError):
            self.importer.importar(io.BytesIO(pdf_bytes), "sin_datos.pdf")


class PDFImportEndToEndTests(SintelTenantTestCase):
    """Flujo completo via API: crear extracto -> subir PDF -> procesar."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa PDF", nit="900000904", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta PDF", banco="Banco Test",
            tipo="AHORROS", numero="PDF-1",
        )

    def _crear_extracto(self, mes=1, anio=2026):
        resp = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {"cuenta": str(self.cuenta.uuid), "mes": mes, "anio": anio},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        return resp.data["uuid"]

    def _procesar(self, extracto_uuid, contenido_bytes, nombre="extracto.pdf", forzar=False):
        archivo = SimpleUploadedFile(nombre, contenido_bytes, content_type="application/pdf")
        extracto = ExtractoBancario.objects.get(uuid=extracto_uuid)
        extracto.archivo_s3.save(nombre, archivo, save=True)
        return self.api_client.post(
            f"/api/v1/bancos/extractos/{extracto_uuid}/procesar/", {"forzar": forzar}, format="json"
        )

    def test_procesar_pdf_con_balance_cuadrado(self):
        extracto_uuid = self._crear_extracto()
        pdf_bytes = _pdf_desde_lineas([
            "01/06/2026  Deposito inicial  1.000.000,00  1.000.000,00",
            "02/06/2026  Pago cliente  500.000,00  1.500.000,00",
            "03/06/2026  Retiro  -200.000,00  1.300.000,00",
        ])
        resp = self._procesar(extracto_uuid, pdf_bytes)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["transacciones_importadas"], 3)
        self.assertEqual(resp.data["formato"], "PDF")

        tx = TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid)
        self.assertEqual(tx.count(), 3)

    def test_procesar_pdf_con_balance_descuadrado_no_marca_procesado(self):
        extracto_uuid = self._crear_extracto(mes=2)
        # saldo final de la ultima fila no cuadra con inicio + creditos - debitos
        pdf_bytes = _pdf_desde_lineas([
            "01/06/2026  Deposito  1.000.000,00  1.000.000,00",
            "02/06/2026  Pago  500.000,00  999.999.999,00",
        ])
        resp = self._procesar(extracto_uuid, pdf_bytes)
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

        extracto = ExtractoBancario.objects.get(uuid=extracto_uuid)
        self.assertFalse(extracto.procesado)
        self.assertEqual(TransaccionBancaria.objects.filter(extracto=extracto).count(), 0)

    def test_pdf_corrupto_responde_error_controlado_no_500(self):
        extracto_uuid = self._crear_extracto(mes=3)
        resp = self._procesar(extracto_uuid, b"%PDF-1.4\nbasura", nombre="corrupto.pdf")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)

    def test_pdf_escaneado_sin_texto_responde_error_controlado(self):
        extracto_uuid = self._crear_extracto(mes=4)
        resp = self._procesar(extracto_uuid, _pdf_vacio(), nombre="escaneado.pdf")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        self.assertIn("NEEDS_OCR", str(resp.data))

    def test_idempotencia_reprocesar_mismo_pdf_no_duplica(self):
        extracto_uuid = self._crear_extracto(mes=5)
        pdf_bytes = _pdf_desde_lineas([
            "01/06/2026  Deposito  1.000.000,00  1.000.000,00",
            "02/06/2026  Pago  500.000,00  1.500.000,00",
        ])
        resp1 = self._procesar(extracto_uuid, pdf_bytes)
        self.assertEqual(resp1.status_code, status.HTTP_200_OK, resp1.content)
        self.assertEqual(TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).count(), 2)

        resp2 = self._procesar(extracto_uuid, pdf_bytes, forzar=True)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)
        self.assertEqual(TransaccionBancaria.objects.filter(extracto__uuid=extracto_uuid).count(), 2)
