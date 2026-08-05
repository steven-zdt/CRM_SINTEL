"""
Pruebas de humo para el flujo completo de APIs de empresa (API-First).

Verifica que todos los endpoints necesarios para la página de empresa funcionan correctamente.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.tenant.core.tests import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa

User = get_user_model()


class EmpresaAPIFlowSmokeTestCase(SintelTenantTestCase):
    """Pruebas de humo para el flujo completo de APIs de empresa."""

    def setUp(self):
        """Configurar datos de prueba."""
        super().setUp()

        # Crear usuario y membresía en el tenant
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", is_active=True
        )

        # Crear tenant de prueba
        self.tenant = TenantClient.objects.create(
            schema_name="test_tenant", nombre="Test Tenant", auto_create_schema=True
        )

        # Crear dominio para el tenant
        self.domain = Domain.objects.create(
            domain="test-tenant.sintel.net.co", tenant=self.tenant, is_primary=True
        )

        # Crear membresía
        TenantMembership.objects.create(
            client=self.tenant, user=self.user, role="admin", is_active=True
        )

        # Cliente de prueba con el dominio del tenant
        self.client = Client(HTTP_HOST="test-tenant.sintel.net.co")
        self.client.force_login(self.user)

    def test_mi_empresa_endpoint_returns_json(self):
        """Verifica que GET /api/v1/empresas/mi-empresa/ retorna JSON."""
        url = "/api/v1/empresas/mi-empresa/"
        response = self.client.get(url, HTTP_HOST="test-tenant.sintel.net.co")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content)
        # Puede retornar {"empresa": null} o {"empresa": {...}}
        self.assertIn("empresa", data)

    def test_form_metadata_endpoint_returns_json(self):
        """Verifica que GET /api/v1/empresa/form-metadata/ retorna JSON con estructura esperada."""
        url = "/api/v1/empresa/form-metadata/"
        response = self.client.get(url, HTTP_HOST="test-tenant.sintel.net.co")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content)
        # Verificar estructura esperada
        self.assertIn("tipo_contribuyente", data)
        self.assertIn("regimenes_renta", data)
        self.assertIn("responsabilidades_rut", data)

        # Verificar estructura de tipo_contribuyente
        self.assertIn("clases", data["tipo_contribuyente"])
        self.assertIn("segmentos", data["tipo_contribuyente"])
        self.assertIn("PN", data["tipo_contribuyente"]["segmentos"])
        self.assertIn("PJ", data["tipo_contribuyente"]["segmentos"])

    def test_actividades_lookup_endpoint_returns_json(self):
        """Verifica que GET /api/v1/empresa/actividades-lookup/ retorna JSON."""
        url = "/api/v1/empresa/actividades-lookup/?q=SERV&limit=3"
        response = self.client.get(url, HTTP_HOST="test-tenant.sintel.net.co")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content)
        # Debe ser una lista
        self.assertIsInstance(data, list)
        # Si hay resultados, deben tener codigo y nombre
        if data:
            self.assertIn("codigo", data[0])
            self.assertIn("nombre", data[0])
        # No debe exceder el límite
        self.assertLessEqual(len(data), 3)

    def test_patch_empresa_persists_changes(self):
        """Verifica que PATCH /api/v1/empresas/{id}/ persiste cambios correctamente."""
        # Crear empresa de prueba
        empresa = Empresa.objects.create(
            razon_social="Test Empresa S.A.",
            nit="900123456",
            dv="1",
            direccion="Calle 123",
            telefono="6012345678",
            email_contacto="test@example.com",
            actividad_economica="6201",  # CIIU code
        )

        # Obtener CSRF token
        csrf_token = self.client.get(
            "/empresa/", HTTP_HOST="test-tenant.sintel.net.co"
        ).cookies.get("csrftoken")

        # PATCH con cambios
        url = f"/api/v1/empresas/{empresa.id}/"
        data = {
            "razon_social": "Test Empresa Actualizada S.A.",
            "actividad_economica": "6202",  # Cambiar CIIU
        }

        response = self.client.patch(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_HOST="test-tenant.sintel.net.co",
            HTTP_X_CSRFTOKEN=csrf_token.value if csrf_token else "",
        )

        # Debe retornar 200
        self.assertIn(response.status_code, [200, 204])

        # Verificar que los cambios se persistieron
        empresa.refresh_from_db()
        self.assertEqual(empresa.razon_social, "Test Empresa Actualizada S.A.")
        self.assertEqual(empresa.actividad_economica, "6202")

        # Verificar que GET refleja los cambios
        get_url = "/api/v1/empresas/mi-empresa/"
        get_response = self.client.get(get_url, HTTP_HOST="test-tenant.sintel.net.co")
        get_data = json.loads(get_response.content)

        if get_data.get("empresa"):
            self.assertEqual(
                get_data["empresa"]["razon_social"], "Test Empresa Actualizada S.A."
            )
            self.assertEqual(get_data["empresa"]["actividad_economica"], "6202")
