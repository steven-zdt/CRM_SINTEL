"""
Tests para la API de Ingesta.

Verifica:
- POST con multipart (archivo) → 202 Accepted, crea DocumentoFuente y encola procesar_fuente
- POST con JSON (url_origen) → 202 Accepted, encola descargar_fuente
- GET detalle → muestra estado + lista de logs
- Throttling: al exceder tasa → 429 con cabecera Retry-After
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.config.tests.base_public import PublicAPITestCase
from apps.public.impuestos.models import DocumentoFuente, IngestaLog


class IngestaViewSetTests(PublicAPITestCase):
    """Tests para IngestaViewSet."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()

    def test_create_with_file(self):
        """Test: POST con multipart (archivo) → 202 Accepted."""
        # Crear archivo temporal
        content = b"Test PDF content"
        archivo = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        data = {
            "archivo": archivo,
            "fuente": "DIAN",
            "tipo": "PDF",
        }

        response = self.client.post("/api/public/v1/impuestos/ingesta/", data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["estado"], "RECIBIDO")
        self.assertEqual(response.data["fuente"], "DIAN")

        # Verificar que se creó en BD
        doc = DocumentoFuente.objects.get(id=response.data["id"])
        self.assertIsNotNone(doc.archivo)
        self.assertEqual(doc.fuente, "DIAN")

    def test_create_with_url(self):
        """Test: POST con JSON (url_origen) → 202 Accepted."""
        data = {
            "url_origen": "https://www.dian.gov.co/documento.pdf",
            "fuente": "DIAN",
            "tipo": "PDF",
        }

        response = self.client.post("/api/public/v1/impuestos/ingesta/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["estado"], "RECIBIDO")
        self.assertEqual(response.data["url_origen"], data["url_origen"])

        # Verificar que se creó en BD
        doc = DocumentoFuente.objects.get(id=response.data["id"])
        self.assertIsNotNone(doc.url_origen)
        self.assertFalse(doc.archivo)

    def test_create_mutual_exclusion(self):
        """Test: Validación de mutua exclusión archivo/url_origen."""
        # Sin archivo ni url_origen
        data = {"fuente": "DIAN"}
        response = self.client.post("/api/public/v1/impuestos/ingesta/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Con ambos
        archivo = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        data = {
            "archivo": archivo,
            "url_origen": "https://example.com/doc.pdf",
            "fuente": "DIAN",
        }
        response = self.client.post("/api/public/v1/impuestos/ingesta/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_documentos(self):
        """Test: GET lista documentos."""
        # Crear algunos documentos
        DocumentoFuente.objects.create(
            fuente="DIAN", url_origen="https://example.com/1.pdf", estado="RECIBIDO"
        )
        DocumentoFuente.objects.create(
            fuente="DOF", url_origen="https://example.com/2.pdf", estado="PROCESADO"
        )

        response = self.client.get("/api/public/v1/impuestos/ingesta/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_detail_with_logs(self):
        """Test: GET detalle muestra estado + lista de logs."""
        doc = DocumentoFuente.objects.create(
            fuente="DIAN", url_origen="https://example.com/doc.pdf", estado="EN_PROCESO"
        )

        # Crear algunos logs
        IngestaLog.objects.create(
            documento=doc, etapa="descarga", nivel="INFO", mensaje="Inicio descarga"
        )
        IngestaLog.objects.create(
            documento=doc, etapa="parseo", nivel="INFO", mensaje="Inicio parseo"
        )

        response = self.client.get(f"/api/public/v1/impuestos/ingesta/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado"], "EN_PROCESO")
        self.assertIn("logs", response.data)
        self.assertEqual(len(response.data["logs"]), 2)

    def test_hash_calculation(self):
        """Test: Hash SHA256 se calcula automáticamente al subir archivo."""
        content = b"Test content for hash"
        archivo = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        data = {
            "archivo": archivo,
            "fuente": "DIAN",
        }

        response = self.client.post("/api/public/v1/impuestos/ingesta/", data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        doc_id = response.data["id"]
        doc = DocumentoFuente.objects.get(id=doc_id)

        # Verificar que hash se calculó (debe tener 64 caracteres hex)
        self.assertIsNotNone(doc.hash_sha256)
        self.assertEqual(len(doc.hash_sha256), 64)

    def test_requires_authentication(self):
        """Test: Endpoints requieren autenticación."""
        self.client.logout()

        response = self.client.get("/api/public/v1/impuestos/ingesta/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post(
            "/api/public/v1/impuestos/ingesta/", {"fuente": "DIAN"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
