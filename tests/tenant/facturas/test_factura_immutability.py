"""
Tests de inmutabilidad para Facturas API.

Valida que:
- POST está bloqueado (405) - solo importación vía upload-ubl
- PUT/PATCH están bloqueados (405)
- DELETE funciona siempre (rollback de error de carga)
- GET list/retrieve funcionan correctamente
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from tests.tenant.base_test import SintelTenantTestCase


class TestFacturaImmutability(SintelTenantTestCase):
    """
    Tests de inmutabilidad para Facturas API.
    """

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test", nit="900123456", dv="7", moneda="COP"
        )

    def test_factura_list_ok(self):
        """
        GET /api/v1/facturas/ → 200 OK
        """
        # Crear factura de prueba
        factura = Factura.objects.create(
            numero="FST-001",
            prefijo="FST",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente A",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-list")
        resp = self.api_client.get(url)

        assert resp.status_code == 200
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        assert len(results) > 0

    def test_factura_detail_ok(self):
        """
        GET /api/v1/facturas/{id}/ → 200 OK
        """
        factura = Factura.objects.create(
            numero="FST-002",
            prefijo="FST",
            consecutivo=2,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente B",
            moneda="COP",
            subtotal=Decimal("200000.00"),
            impuestos=Decimal("38000.00"),
            total=Decimal("238000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.get(url)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("id") == factura.id
        assert data.get("numero") == "FST-002"

    def test_factura_update_forbidden_put(self):
        """
        PUT /api/v1/facturas/{id}/ → 405 Method Not Allowed
        """
        factura = Factura.objects.create(
            numero="FST-003",
            prefijo="FST",
            consecutivo=3,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente C",
            moneda="COP",
            subtotal=Decimal("300000.00"),
            impuestos=Decimal("57000.00"),
            total=Decimal("357000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.put(
            url, {"numero": "FST-003-MODIFIED", "estado": "ENVIADA"}
        )

        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert "inmutables" in resp.json().get("detail", "").lower()

    def test_factura_update_forbidden_patch(self):
        """
        PATCH /api/v1/facturas/{id}/ → 405 Method Not Allowed
        """
        factura = Factura.objects.create(
            numero="FST-004",
            prefijo="FST",
            consecutivo=4,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente D",
            moneda="COP",
            subtotal=Decimal("400000.00"),
            impuestos=Decimal("76000.00"),
            total=Decimal("476000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.patch(url, {"estado": "ENVIADA"})

        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert "inmutables" in resp.json().get("detail", "").lower()

    def test_factura_delete_success(self):
        """
        DELETE /api/v1/facturas/{id}/ → 204 No Content (siempre permitido, rollback de error de carga)
        """
        factura = Factura.objects.create(
            numero="FST-005",
            prefijo="FST",
            consecutivo=5,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente E",
            moneda="COP",
            subtotal=Decimal("500000.00"),
            impuestos=Decimal("95000.00"),
            total=Decimal("595000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.delete(url)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Verificar que la factura fue eliminada
        assert not Factura.objects.filter(id=factura.id).exists()

    def test_factura_delete_success_aceptada(self):
        """
        DELETE /api/v1/facturas/{id}/ → 204 No Content (independiente del estado)
        """
        factura = Factura.objects.create(
            numero="FST-006",
            prefijo="FST",
            consecutivo=6,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,  # Estado no afecta eliminación
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente F",
            moneda="COP",
            subtotal=Decimal("600000.00"),
            impuestos=Decimal("114000.00"),
            total=Decimal("714000.00"),
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.delete(url)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Verificar que la factura fue eliminada
        assert not Factura.objects.filter(id=factura.id).exists()

    def test_factura_delete_success_with_cufe(self):
        """
        DELETE /api/v1/facturas/{id}/ → 204 No Content (independiente de CUFE)
        """
        factura = Factura.objects.create(
            numero="FST-007",
            prefijo="FST",
            consecutivo=7,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ENVIADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente G",
            moneda="COP",
            subtotal=Decimal("700000.00"),
            impuestos=Decimal("133000.00"),
            total=Decimal("833000.00"),
            cufe="abc123def456",  # Con CUFE (no afecta eliminación)
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-detail", kwargs={"pk": factura.id})
        resp = self.api_client.delete(url)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Verificar que la factura fue eliminada
        assert not Factura.objects.filter(id=factura.id).exists()

    def test_factura_create_forbidden(self):
        """
        POST /api/v1/facturas/ → 405 Method Not Allowed (solo importación vía upload-ubl)
        """
        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-list")
        resp = self.api_client.post(
            url,
            {
                "numero": "FST-MANUAL",
                "prefijo": "FST",
                "consecutivo": 999,
                "tipo": "FE",
                "estado": "BORRADOR",
                "naturaleza": "VENTA",
                "fecha_emision": "2024-01-15T10:00:00Z",
                "emisor_nit": "900123456",
                "emisor_razon_social": "Empresa Test",
                "receptor_nit": "900999888",
                "receptor_razon_social": "Cliente Manual",
                "moneda": "COP",
                "subtotal": "100000.00",
                "impuestos": "19000.00",
                "total": "119000.00",
            },
        )

        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert (
            "upload-ubl" in resp.json().get("detail", "").lower()
            or "import" in resp.json().get("detail", "").lower()
        )

    def test_factura_xml_endpoint_ok(self):
        """
        GET /api/v1/facturas/{id}/xml/ → 200 OK
        """
        factura = Factura.objects.create(
            numero="FST-008",
            prefijo="FST",
            consecutivo=8,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente H",
            moneda="COP",
            subtotal=Decimal("800000.00"),
            impuestos=Decimal("152000.00"),
            total=Decimal("952000.00"),
            xml_content="<Invoice>Test XML</Invoice>",
        )

        self.api_client.force_authenticate(user=self.user)
        url = reverse("factura-xml", kwargs={"pk": factura.id})
        resp = self.api_client.get(url)

        assert resp.status_code == 200
        data = resp.json()
        assert "xml" in data
        assert data["xml"] == "<Invoice>Test XML</Invoice>"
