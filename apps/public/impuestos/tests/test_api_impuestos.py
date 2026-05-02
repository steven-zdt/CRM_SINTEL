"""
Tests de API para la app impuestos.

Verifica:
- ReadOnly para todos los modelos (TipoImpuesto, TarifaIVA, etc.)
- 405 en POST/PUT/DELETE
- Paginación y filtros
"""

from django.utils import timezone
from rest_framework import status

from apps.config.tests.base_public import PublicAPITestCase
from apps.public.impuestos.models import (
    ActividadEconomica,
    CodigoTributario,
    ConceptoRetencion,
    TarifaIVA,
    TipoImpuesto,
)


class TipoImpuestoViewSetTests(PublicAPITestCase):
    """Tests para TipoImpuestoViewSet (ReadOnly)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.tipo = TipoImpuesto.objects.create(
            codigo="01",
            nombre="IVA",
            descripcion="Impuesto al Valor Agregado",
            activo=True,
            fecha_vigencia=timezone.now().date(),
        )

    def test_list_tipos(self):
        """Test: GET /api/v1/impuestos/tipos/ devuelve lista paginada."""
        response = self.json("get", "/api/v1/impuestos/tipos/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)

    def test_detail_tipo(self):
        """Test: GET /api/v1/impuestos/tipos/{id}/ devuelve detalle."""
        response = self.json("get", f"/api/v1/impuestos/tipos/{self.tipo.id}/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["codigo"], "01")

    def test_create_tipo_405(self):
        """Test: POST devuelve 405 (ReadOnly)."""
        data = {"codigo": "02", "nombre": "Test"}
        response = self.json("post", "/api/v1/impuestos/tipos/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_by_activo(self):
        """Test: Filtrar por activo."""
        response = self.json("get", "/api/v1/impuestos/tipos/?activo=true")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        for result in response.data["results"]:
            self.assertTrue(result["activo"])


class TarifaIVAViewSetTests(PublicAPITestCase):
    """Tests para TarifaIVAViewSet (ReadOnly)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.tarifa = TarifaIVA.objects.create(
            codigo="01",
            nombre="IVA 19%",
            porcentaje=19.0,
            tipo_tarifa="GENERAL",
            activo=True,
            fecha_vigencia=timezone.now().date(),
        )

    def test_list_tarifas(self):
        """Test: GET /api/v1/impuestos/tarifas-iva/ devuelve lista paginada."""
        response = self.json("get", "/api/v1/impuestos/tarifas-iva/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)

    def test_create_tarifa_405(self):
        """Test: POST devuelve 405 (ReadOnly)."""
        data = {"codigo": "02", "nombre": "Test", "porcentaje": 5.0}
        response = self.json("post", "/api/v1/impuestos/tarifas-iva/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ConceptoRetencionViewSetTests(PublicAPITestCase):
    """Tests para ConceptoRetencionViewSet (ReadOnly)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.concepto = ConceptoRetencion.objects.create(
            codigo="01",
            nombre="Retención en la Fuente",
            tipo_retencion="RENTA",
            porcentaje=10.0,
            activo=True,
            fecha_vigencia=timezone.now().date(),
        )

    def test_list_conceptos(self):
        """Test: GET /api/v1/impuestos/conceptos-retencion/ devuelve lista paginada."""
        response = self.json("get", "/api/v1/impuestos/conceptos-retencion/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)

    def test_create_concepto_405(self):
        """Test: POST devuelve 405 (ReadOnly)."""
        data = {"codigo": "02", "nombre": "Test"}
        response = self.json("post", "/api/v1/impuestos/conceptos-retencion/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class CodigoTributarioViewSetTests(PublicAPITestCase):
    """Tests para CodigoTributarioViewSet (ReadOnly)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.codigo = CodigoTributario.objects.create(
            codigo="01",
            nombre="Código Test",
            tipo="IMPUESTO",
            activo=True,
            fecha_vigencia=timezone.now().date(),
        )

    def test_list_codigos(self):
        """Test: GET /api/v1/impuestos/codigos-tributarios/ devuelve lista paginada."""
        response = self.json("get", "/api/v1/impuestos/codigos-tributarios/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)

    def test_create_codigo_405(self):
        """Test: POST devuelve 405 (ReadOnly)."""
        data = {"codigo": "02", "nombre": "Test"}
        response = self.json("post", "/api/v1/impuestos/codigos-tributarios/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ActividadEconomicaViewSetTests(PublicAPITestCase):
    """Tests para ActividadEconomicaViewSet (ReadOnly)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        self.actividad = ActividadEconomica.objects.create(
            codigo="1234",
            nombre="Actividad Test",
            descripcion="Descripción test",
            activo=True,
        )

    def test_list_actividades(self):
        """Test: GET /api/v1/impuestos/actividades-economicas/ devuelve lista paginada."""
        response = self.json("get", "/api/v1/impuestos/actividades-economicas/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)

    def test_create_actividad_405(self):
        """Test: POST devuelve 405 (ReadOnly)."""
        data = {"codigo": "5678", "nombre": "Test"}
        response = self.json("post", "/api/v1/impuestos/actividades-economicas/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
