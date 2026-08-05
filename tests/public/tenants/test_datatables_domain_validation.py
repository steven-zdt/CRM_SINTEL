"""
Tests para validar que el dominio mostrado en DataTables corresponde al de la BD.

Valida que el serializer TenantListSerializer retorna el dominio correcto
que está almacenado en la base de datos.
"""

import pytest
from django.db import connection
from rest_framework.test import APIClient

# Imports dentro de funciones para evitar problemas de configuración de Django


@pytest.mark.django_db
class TestDataTablesDomainValidation:
    """
    Tests para validar correspondencia entre dominio en BD y dominio en DataTables.
    """

    def test_datatables_returns_correct_domain_from_db(self, admin_user):
        """Test: Verificar que DataTables retorna el dominio correcto de la BD."""
        from rest_framework.test import APIClient

        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant con dominio específico
        tenant = ClientFactory(
            nombre="Empresa Validación", schema_name="validacion_test", is_active=True
        )

        # Crear dominio específico en BD
        expected_domain = "validacion-test.sintel.net.co"
        domain = DomainFactory(tenant=tenant, domain=expected_domain, is_primary=True)

        # Verificar en BD que el dominio existe y es primary
        domain_from_db = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        assert domain_from_db is not None, "El dominio debe existir en la BD"
        assert (
            domain_from_db.domain == expected_domain
        ), f"El dominio en BD debe ser '{expected_domain}', pero es '{domain_from_db.domain}'"

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Llamar al endpoint de DataTables
        from django.urls import reverse

        url = reverse("admin-dt-tenants")
        response = api_client.post(
            url, {"draw": 1, "start": 0, "length": 10}, format="json"
        )

        # Verificar que la respuesta es exitosa
        assert (
            response.status_code == 200
        ), f"DataTables debe retornar 200, no {response.status_code}. Data: {response.data}"

        # Obtener datos de la respuesta
        data = response.data
        assert "data" in data, "La respuesta debe contener 'data'"

        # Buscar el tenant en los datos retornados
        tenant_found = False
        for row in data["data"]:
            # Formato: [id, schema_name, nombre, domain, admin_email, created_on, on_trial, paid_until, is_active]
            row_id = row[0]
            row_schema = row[1]
            row_domain = row[3]  # Columna 3 es el dominio

            if row_id == tenant.id:
                tenant_found = True
                # Verificar que el dominio retornado corresponde al de la BD
                assert row_domain == expected_domain, (
                    f"El dominio retornado por DataTables ('{row_domain}') debe corresponder "
                    f"al dominio en BD ('{expected_domain}') para tenant ID {tenant.id}"
                )
                break

        assert (
            tenant_found
        ), f"El tenant con ID {tenant.id} debe estar en los datos retornados por DataTables"

    def test_datatables_handles_multiple_domains_correctly(self, admin_user):
        """Test: Verificar que DataTables retorna el dominio primary cuando hay múltiples dominios."""
        from rest_framework.test import APIClient

        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant
        tenant = ClientFactory(
            nombre="Empresa Múltiples Dominios",
            schema_name="multi_domain",
            is_active=True,
        )

        # Crear múltiples dominios (uno primary, otros no)
        primary_domain = DomainFactory(
            tenant=tenant, domain="primary.sintel.net.co", is_primary=True
        )

        secondary_domain = DomainFactory(
            tenant=tenant, domain="secondary.sintel.net.co", is_primary=False
        )

        tertiary_domain = DomainFactory(
            tenant=tenant, domain="tertiary.sintel.net.co", is_primary=False
        )

        # Verificar en BD que hay 3 dominios y solo uno es primary
        domains_from_db = Domain.objects.filter(tenant=tenant)
        assert domains_from_db.count() == 3, "Debe haber 3 dominios en BD"
        primary_count = domains_from_db.filter(is_primary=True).count()
        assert primary_count == 1, "Debe haber exactamente 1 dominio primary"

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Llamar al endpoint de DataTables
        from django.urls import reverse

        url = reverse("admin-dt-tenants")
        response = api_client.post(
            url, {"draw": 1, "start": 0, "length": 10}, format="json"
        )

        # Verificar respuesta
        assert response.status_code == 200

        # Buscar el tenant y verificar que retorna el dominio primary
        data = response.data["data"]
        tenant_found = False
        for row in data:
            if row[0] == tenant.id:
                tenant_found = True
                row_domain = row[3]  # Columna dominio
                # Debe retornar el dominio primary, no los secundarios
                assert row_domain == primary_domain.domain, (
                    f"DataTables debe retornar el dominio primary ('{primary_domain.domain}'), "
                    f"no '{row_domain}'"
                )
                assert (
                    row_domain != secondary_domain.domain
                ), "DataTables NO debe retornar el dominio secundario"
                assert (
                    row_domain != tertiary_domain.domain
                ), "DataTables NO debe retornar el dominio terciario"
                break

        assert tenant_found, "El tenant debe estar en los datos retornados"

    def test_datatables_handles_tenant_without_domain(self, admin_user):
        """Test: Verificar que DataTables retorna '-' cuando un tenant no tiene dominio."""
        from rest_framework.test import APIClient

        from apps.public.tenants.models import Client as TenantClient
        from apps.public.tenants.models import Domain
        from tests.public.tenants.factories import ClientFactory

        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        # Crear tenant SIN dominio (caso edge)
        tenant = ClientFactory(
            nombre="Empresa Sin Dominio", schema_name="sin_dominio", is_active=True
        )

        # Verificar que NO tiene dominios
        domains_count = Domain.objects.filter(tenant=tenant).count()
        assert domains_count == 0, "El tenant no debe tener dominios"

        # Crear APIClient autenticado
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)

        # Llamar al endpoint de DataTables
        from django.urls import reverse

        url = reverse("admin-dt-tenants")
        response = api_client.post(
            url, {"draw": 1, "start": 0, "length": 10}, format="json"
        )

        # Verificar respuesta
        assert response.status_code == 200

        # Buscar el tenant y verificar que retorna '-'
        data = response.data["data"]
        tenant_found = False
        for row in data:
            if row[0] == tenant.id:
                tenant_found = True
                row_domain = row[3]  # Columna dominio
                # Debe retornar '-' cuando no hay dominio
                assert (
                    row_domain == "-"
                ), f"DataTables debe retornar '-' cuando no hay dominio, no '{row_domain}'"
                break

        assert tenant_found, "El tenant debe estar en los datos retornados"
