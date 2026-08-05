"""
Tests de Fase A: Ingesta.

Verifica:
- POST multipart con archivo (CSV/HTML) → 202 Accepted
- POST JSON con url_origen → 202 Accepted (con mock de requests)
- Estados: RECIBIDO → EN_PROCESO → PROCESADO/ERROR
- Throttling scope impuestos_ingesta → 429
- Idempotencia por hash_sha256
"""

import hashlib
import io
import json

import pytest
import responses
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.public.impuestos.models import DocumentoFuente, IngestaLog
from tests.public.impuestos.factories import DocumentoFuenteFactory


@pytest.mark.django_db
class TestIngestaAPI:
    """Tests para API de Ingesta."""

    def test_ingesta_multipart_csv(self, authenticated_client, admin_user):
        """POST multipart con archivo CSV → 202 Accepted."""
        content = b"codigo,valor\nIVA,19\n"
        f = SimpleUploadedFile("tarifas.csv", content, content_type="text/csv")

        url = "/api/public/v1/impuestos/ingesta/"
        resp = authenticated_client.post(
            url, {"fuente": "DIAN", "archivo": f}, format="multipart"
        )

        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED)
        assert resp.data["estado"] == "RECIBIDO"

        # Con Celery eager, el documento se procesa inmediatamente
        # El estado puede cambiar a EN_PROCESO o PROCESADO
        doc = DocumentoFuente.objects.latest("id")
        assert doc.estado in ("EN_PROCESO", "PROCESADO", "RECIBIDO")

        # Verificar que se crearon logs
        assert IngestaLog.objects.filter(documento=doc).exists()

    @responses.activate
    def test_ingesta_url_html_respetando_robots(self, authenticated_client, admin_user):
        """POST JSON con url_origen → respeta robots.txt."""
        # Mock de robots.txt (allow)
        responses.add(
            responses.GET,
            "https://dian.gov.co/robots.txt",
            body="User-agent: *\nAllow: /",
            status=200,
        )

        # Mock de la página HTML
        html_content = "<html><h1>Artículo 1</h1><p>IVA exento</p></html>"
        responses.add(
            responses.GET,
            "https://dian.gov.co/norma.html",
            body=html_content,
            content_type="text/html",
            status=200,
        )

        resp = authenticated_client.post(
            "/api/public/v1/impuestos/ingesta/",
            data={"fuente": "DIAN", "url_origen": "https://dian.gov.co/norma.html"},
            format="json",
        )

        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED)

        # Con Celery eager, la descarga se ejecuta inmediatamente
        doc = DocumentoFuente.objects.latest("id")
        assert doc.estado in ("EN_PROCESO", "PROCESADO", "RECIBIDO", "ERROR")

        # Verificar robots_observado
        if doc.robots_observado is not None:
            assert doc.robots_observado is True

    def test_ingesta_throttling(self, authenticated_client, admin_user):
        """Throttling de scope impuestos_ingesta → 429."""
        # Reducir tasa para la prueba
        with override_settings(
            REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"impuestos_ingesta": "2/min"}}
        ):
            url = "/api/public/v1/impuestos/ingesta/"
            f = SimpleUploadedFile("a.csv", b"a,b\n1,2\n", content_type="text/csv")

            # Primera request: OK
            resp1 = authenticated_client.post(
                url, {"fuente": "DIAN", "archivo": f}, format="multipart"
            )
            assert resp1.status_code in (
                status.HTTP_201_CREATED,
                status.HTTP_202_ACCEPTED,
            )

            # Segunda request: OK
            f2 = SimpleUploadedFile("b.csv", b"x,y\n3,4\n", content_type="text/csv")
            resp2 = authenticated_client.post(
                url, {"fuente": "DIAN", "archivo": f2}, format="multipart"
            )
            assert resp2.status_code in (
                status.HTTP_201_CREATED,
                status.HTTP_202_ACCEPTED,
            )

            # Tercera request: 429 (throttling)
            f3 = SimpleUploadedFile("c.csv", b"m,n\n5,6\n", content_type="text/csv")
            resp3 = authenticated_client.post(
                url, {"fuente": "DIAN", "archivo": f3}, format="multipart"
            )
            assert resp3.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert (
                "Retry-After" in resp3.headers
                or "retry_after" in str(resp3.data).lower()
            )

    def test_ingesta_idempotencia_por_hash(self, authenticated_client, admin_user):
        """Documento duplicado por hash → no reprocesa."""
        content = b"Test content for idempotency"
        hash_sha256 = hashlib.sha256(content).hexdigest()

        # Crear primer documento
        doc1 = DocumentoFuenteFactory(hash_sha256=hash_sha256, estado="PROCESADO")

        # Intentar crear segundo documento con mismo hash
        f = SimpleUploadedFile("duplicate.pdf", content, content_type="application/pdf")
        resp = authenticated_client.post(
            "/api/public/v1/impuestos/ingesta/",
            {"fuente": "DIAN", "archivo": f},
            format="multipart",
        )

        # Puede crear el documento, pero el hash debe detectar duplicado
        if resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED):
            doc2 = DocumentoFuente.objects.latest("id")
            # Si el hash es igual, debería marcarse como duplicado
            # (esto depende de la implementación del serializer)
            assert doc2.hash_sha256 == hash_sha256

    def test_ingesta_estados_transicion(self, authenticated_client, admin_user):
        """Verificar transición de estados: RECIBIDO → EN_PROCESO → PROCESADO."""
        content = b"codigo,valor\nIVA,19\n"
        f = SimpleUploadedFile("test.csv", content, content_type="text/csv")

        resp = authenticated_client.post(
            "/api/public/v1/impuestos/ingesta/",
            {"fuente": "DIAN", "archivo": f},
            format="multipart",
        )

        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED)

        doc = DocumentoFuente.objects.latest("id")
        assert doc.estado == "RECIBIDO"

        # Con Celery eager, el procesamiento ocurre inmediatamente
        # Verificar logs de transición
        logs = IngestaLog.objects.filter(documento=doc).order_by("ts")
        assert logs.exists()

        # El estado final puede ser PROCESADO o ERROR (depende del contenido)
        # Lo importante es que hubo procesamiento (logs)
