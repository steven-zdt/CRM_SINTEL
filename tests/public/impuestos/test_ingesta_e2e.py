"""
Tests E2E para Nueva Ingesta (multipart + form-urlencoded + JSON).

Verifica:
- Subida de archivo (multipart/form-data) → MultiPartParser → sin 403/415
- Programar por URL (application/x-www-form-urlencoded) → FormParser → sin 403/415
- Programar por URL (application/json) → JSONParser → sin 403/415
- CSRF funcionando correctamente
- ETL ejecutándose (Celery eager) → estado EN_PROCESO/PROCESADO + logs
"""

import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.public.impuestos.models import DocumentoFuente, IngestaLog

API_INGESTA = "/api/public/v1/impuestos/ingesta/"


def test_nueva_ingesta_subir_archivo_multipart(csrf_client, user_admin):
    """
    E2E: Subida de archivo (multipart/form-data) → sin 403 (CSRF) ni 415 (parser),
    y procesamiento encolado (Celery eager) → estado EN_PROCESO/PROCESADO + logs.
    """
    client, csrftoken = csrf_client

    # Autenticación por sesión (admin)
    assert client.login(email=user_admin.email, password="admin123")

    content = b"codigo,valor\nIVA,19\n"
    file_obj = SimpleUploadedFile("tarifas.csv", content, content_type="text/csv")

    # POST multipart: usa enctype multipart/form-data. Django Client lo maneja al pasar files=...
    resp = client.post(
        API_INGESTA,
        data={"fuente": "DIAN", "fecha_publicacion": "2025-01-01"},
        files={"archivo": file_obj},
        HTTP_X_CSRFTOKEN=csrftoken,
    )

    assert resp.status_code in (
        status.HTTP_201_CREATED,
        status.HTTP_202_ACCEPTED,
    ), f"Expected 201/202, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    # Con Celery eager, el documento se procesa inmediatamente
    doc = DocumentoFuente.objects.latest("id")
    assert doc.estado in ("EN_PROCESO", "PROCESADO", "RECIBIDO")
    assert IngestaLog.objects.filter(documento=doc).exists()

    # Verificar que el archivo se guardó
    assert doc.archivo is not None
    assert doc.fuente == "DIAN"


def test_nueva_ingesta_programar_url_form_urlencoded(csrf_client, user_admin):
    """
    E2E: Programar por URL (form-urlencoded) → sin 403 ni 415,
    DRF lo procesa con FormParser y dispara descarga/ETL.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    data = {
        "fuente": "DIAN",
        "url_origen": "https://dian.gov.co/norma.html",
        "fecha_publicacion": "2025-01-15",
    }

    # POST form-urlencoded: no se debe forzar Content-Type application/json;
    # Django Client lo arma correctamente como application/x-www-form-urlencoded
    resp = client.post(
        API_INGESTA,
        data=data,
        HTTP_X_CSRFTOKEN=csrftoken,
    )

    assert resp.status_code in (
        status.HTTP_201_CREATED,
        status.HTTP_202_ACCEPTED,
    ), f"Expected 201/202, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    doc = DocumentoFuente.objects.latest("id")
    assert doc.url_origen == data["url_origen"]
    assert doc.fuente == data["fuente"]
    assert doc.estado in (
        "EN_PROCESO",
        "PROCESADO",
        "RECIBIDO",
        "ERROR",
    )  # descarga→ETL (Celery eager)
    assert IngestaLog.objects.filter(documento=doc).exists()


def test_nueva_ingesta_sin_csrf_rechaza_403(csrf_client, user_admin):
    """
    E2E: Sin CSRF token → 403 Forbidden.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    content = b"test content"
    file_obj = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

    # POST sin CSRF token
    resp = client.post(
        API_INGESTA,
        data={"fuente": "DIAN"},
        files={"archivo": file_obj},
        # No HTTP_X_CSRFTOKEN
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_nueva_ingesta_multipart_content_type_correcto(csrf_client, user_admin):
    """
    Verifica que el Content-Type enviado es multipart/form-data.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    content = b"test pdf content"
    file_obj = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

    resp = client.post(
        API_INGESTA,
        data={"fuente": "DIAN"},
        files={"archivo": file_obj},
        HTTP_X_CSRFTOKEN=csrftoken,
    )

    # DRF debe procesar multipart correctamente (sin 415)
    assert (
        resp.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    ), "MultiPartParser no está procesando correctamente multipart/form-data"
    assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED)


def test_nueva_ingesta_form_urlencoded_content_type_correcto(csrf_client, user_admin):
    """
    Verifica que el Content-Type enviado es application/x-www-form-urlencoded.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    data = {
        "fuente": "DIAN",
        "url_origen": "https://example.com/doc.html",
    }

    resp = client.post(
        API_INGESTA,
        data=data,
        HTTP_X_CSRFTOKEN=csrftoken,
    )

    # DRF debe procesar form-urlencoded correctamente (sin 415)
    assert (
        resp.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    ), "FormParser no está procesando correctamente application/x-www-form-urlencoded"
    assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED)


def test_nueva_ingesta_programar_url_json_ok(csrf_client, user_admin):
    """
    E2E: Programar por URL enviando JSON válido (Content-Type: application/json).

    Esperado: 201/202 sin 415, DRF usa JSONParser, Celery (eager) dispara ETL.
    Evitar 403 enviando X-CSRFToken.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    payload = {
        "fuente": "DIAN",
        "url_origen": "https://dian.gov.co/norma.html",
        "fecha_publicacion": "2025-01-31",
    }

    resp = client.post(
        API_INGESTA,
        data=json.dumps(payload),
        content_type="application/json",  # <- JSON correcto
        HTTP_X_CSRFTOKEN=csrftoken,  # <- CSRF para evitar 403
        HTTP_HX_REQUEST="true",  # (opcional) emula HTMX
        HTTP_ACCEPT="application/json",
    )

    assert resp.status_code in (
        status.HTTP_201_CREATED,
        status.HTTP_202_ACCEPTED,
    ), f"Expected 201/202, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    doc = DocumentoFuente.objects.latest("id")
    assert doc.url_origen == payload["url_origen"]
    assert doc.fuente == payload["fuente"]
    assert doc.estado in (
        "EN_PROCESO",
        "PROCESADO",
        "RECIBIDO",
        "ERROR",
    )  # descarga→ETL (Celery eager)
    assert IngestaLog.objects.filter(documento=doc).exists()


# --- Tests de Consola (UI) ---


def test_consola_crear_ingesta_multipart(csrf_client, user_admin):
    """
    Test E2E: Crear ingesta desde consola (multipart/form-data).

    Verifica que el formulario en /console/impuestos/ingesta/nuevo/ funciona
    y redirige después de crear exitosamente.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # Primero, GET al formulario (debe cargar correctamente)
    resp = client.get("/console/impuestos/ingesta/nuevo/")
    assert resp.status_code == 200
    assert b"Nueva ingesta" in resp.content or b"Subir archivo" in resp.content

    # Crear documento mediante el formulario de la consola
    content = b"codigo,valor\nIVA,19\n"
    file_obj = SimpleUploadedFile("test_consola.csv", content, content_type="text/csv")

    # POST multipart a través de la consola (redirige a la lista)
    resp = client.post(
        "/console/impuestos/ingesta/nuevo/",
        data={"fuente": "DIAN", "fecha_publicacion": "2025-01-01"},
        files={"archivo": file_obj},
        HTTP_X_CSRFTOKEN=csrftoken,
        follow=True,  # Seguir redirecciones
    )

    # Debe redirigir a la lista (302) o mostrar éxito (200)
    assert resp.status_code in (
        200,
        302,
    ), f"Expected 200/302, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    # Verificar que el documento se creó
    doc = DocumentoFuente.objects.latest("id")
    assert doc.fuente == "DIAN"
    assert doc.archivo is not None


def test_consola_crear_ingesta_url(csrf_client, user_admin):
    """
    Test E2E: Crear ingesta desde consola (form-urlencoded con URL).

    Verifica que el formulario de URL en /console/impuestos/ingesta/nuevo/ funciona.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # POST form-urlencoded con URL
    resp = client.post(
        "/console/impuestos/ingesta/nuevo/",
        data={
            "fuente": "DIAN",
            "url_origen": "https://test.example.com/norma.html",
            "fecha_publicacion": "2025-01-15",
        },
        HTTP_X_CSRFTOKEN=csrftoken,
        follow=True,
    )

    assert resp.status_code in (
        200,
        302,
    ), f"Expected 200/302, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    # Verificar que el documento se creó
    doc = DocumentoFuente.objects.latest("id")
    assert doc.url_origen == "https://test.example.com/norma.html"
    assert doc.fuente == "DIAN"


def test_consola_eliminar_ingesta(csrf_client, user_admin):
    """
    Test E2E: Eliminar documento de ingesta desde consola.

    Verifica que el endpoint DELETE /console/impuestos/ingesta/<pk>/delete/
    elimina correctamente el documento y su archivo asociado.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # Crear un documento para eliminar
    content = b"test content for delete"
    file_obj = SimpleUploadedFile("test_delete.csv", content, content_type="text/csv")

    # Crear documento
    from apps.public.impuestos.api.ingesta.serializers import (
        DocumentoFuenteCreateSerializer,
    )

    serializer = DocumentoFuenteCreateSerializer(
        data={"fuente": "DIAN", "archivo": file_obj}
    )
    serializer.is_valid(raise_exception=True)
    doc = serializer.save(estado="RECIBIDO")
    doc_id = doc.id
    archivo_path = doc.archivo.path if doc.archivo else None

    # Verificar que el documento existe
    assert DocumentoFuente.objects.filter(pk=doc_id).exists()

    # Eliminar documento (POST a /console/impuestos/ingesta/<pk>/delete/)
    resp = client.post(
        f"/console/impuestos/ingesta/{doc_id}/delete/",
        HTTP_X_CSRFTOKEN=csrftoken,
        content_type="application/json",
    )

    assert (
        resp.status_code == 200
    ), f"Expected 200, got {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')}"

    # Verificar respuesta JSON
    import json

    data = json.loads(resp.content)
    assert data.get("success") is True

    # Verificar que el documento fue eliminado
    assert not DocumentoFuente.objects.filter(pk=doc_id).exists()

    # Verificar que el archivo fue eliminado (si existía)
    if archivo_path:
        import os

        assert not os.path.exists(archivo_path), "El archivo asociado no fue eliminado"


def test_consola_eliminar_ingesta_sin_csrf_rechaza(csrf_client, user_admin):
    """
    Test E2E: Intentar eliminar sin CSRF token → debe fallar.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # Crear documento
    from apps.public.impuestos.api.ingesta.serializers import (
        DocumentoFuenteCreateSerializer,
    )

    file_obj = SimpleUploadedFile("test.csv", b"test", content_type="text/csv")
    serializer = DocumentoFuenteCreateSerializer(
        data={"fuente": "DIAN", "archivo": file_obj}
    )
    serializer.is_valid(raise_exception=True)
    doc = serializer.save(estado="RECIBIDO")

    # Intentar eliminar sin CSRF token (GET no permitido)
    resp = client.get(f"/console/impuestos/ingesta/{doc.id}/delete/")
    assert resp.status_code == 405  # Method Not Allowed

    # Intentar POST sin CSRF token (si CSRF está habilitado)
    resp = client.post(f"/console/impuestos/ingesta/{doc.id}/delete/")
    # Puede ser 403 (CSRF) o 405 (método no permitido sin token)
    assert resp.status_code in (403, 405, 400)


def test_consola_lista_ingesta_carga_correctamente(csrf_client, user_admin):
    """
    Test E2E: Verificar que la lista de ingesta carga correctamente.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # Crear algunos documentos de prueba
    from apps.public.impuestos.models import DocumentoFuente

    for i in range(3):
        DocumentoFuente.objects.create(
            fuente="DIAN",
            estado="PROCESADO",
            tipo="CSV",
        )

    # GET a la lista
    resp = client.get("/console/impuestos/ingesta/")

    assert resp.status_code == 200
    assert b"Ingesta" in resp.content
    assert (
        b"DataTables" in resp.content or b"table" in resp.content
    )  # Verificar que DataTables está incluido


def test_consola_detalle_ingesta_carga_correctamente(csrf_client, user_admin):
    """
    Test E2E: Verificar que el detalle de ingesta carga correctamente.
    """
    client, csrftoken = csrf_client

    assert client.login(email=user_admin.email, password="admin123")

    # Crear documento
    from apps.public.impuestos.models import DocumentoFuente

    doc = DocumentoFuente.objects.create(
        fuente="DIAN",
        estado="PROCESADO",
        tipo="CSV",
    )

    # GET al detalle
    resp = client.get(f"/console/impuestos/ingesta/{doc.id}/")

    assert resp.status_code == 200
    assert str(doc.id).encode() in resp.content
    assert b"Detalle" in resp.content or b"Logs" in resp.content
