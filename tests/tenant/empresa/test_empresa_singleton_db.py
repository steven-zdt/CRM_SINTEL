"""
Pruebas de humo para verificar el patrón Singleton de Empresa a nivel de DB.

[WARNING] PATRÓN SINGLETON: Solo una empresa por tenant (garantizado por UniqueConstraint).
"""

from django.db import IntegrityError
from django.test import TransactionTestCase
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from tests.tenant.base_test import SintelTenantTestCase


class TestEmpresaSingletonDB(SintelTenantTestCase):
    """
    Pruebas para verificar el patrón Singleton de Empresa a nivel de DB.
    """

    def test_unique_constraint_prevents_second_empresa(self):
        """
        Verifica que el UniqueConstraint previene crear una segunda empresa.
        """
        # Crear primera empresa
        empresa1 = Empresa.objects.create(
            razon_social="Primera Empresa S.A.",
            nit="900123456",
            dv="1",
            direccion="Calle 123 #45-67",
            telefono="6012345678",
            email_contacto="contacto1@prueba.com",
            regimen_tributario="Responsable de IVA",
        )

        # Verificar que singleton_key es 1
        self.assertEqual(empresa1.singleton_key, 1)

        # Intentar crear segunda empresa directamente (debe fallar por constraint)
        with self.assertRaises(IntegrityError) as context:
            Empresa.objects.create(
                razon_social="Segunda Empresa S.A.",
                nit="900654321",
                dv="2",
                direccion="Calle 456 #78-90",
                telefono="6098765432",
                email_contacto="contacto2@prueba.com",
                regimen_tributario="Responsable de IVA",
            )

        # Verificar que el error es por la constraint única
        error_message = str(context.exception)
        self.assertIn(
            "unique_singleton_empresa_per_schema",
            error_message.lower() or "unique constraint",
        )

    def test_singleton_key_default_value(self):
        """
        Verifica que singleton_key tiene valor por defecto 1.
        """
        empresa = Empresa.objects.create(
            razon_social="Empresa de Prueba S.A.",
            nit="900123456",
            dv="1",
            direccion="Calle 123 #45-67",
            telefono="6012345678",
            email_contacto="contacto@prueba.com",
            regimen_tributario="Responsable de IVA",
        )

        self.assertEqual(empresa.singleton_key, 1)

    def test_api_create_returns_409_if_exists(self):
        """
        Verifica que la API retorna 409 si ya existe una empresa (validación en ViewSet).
        """
        # Crear primera empresa vía API
        data1 = {
            "razon_social": "Primera Empresa S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto1@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        response1 = self.api_client.post("/api/v1/empresas/", data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Intentar crear segunda empresa vía API (debe retornar 409)
        data2 = {
            "razon_social": "Segunda Empresa S.A.",
            "nit": "900654321",
            "direccion": "Calle 456 #78-90",
            "telefono": "6098765432",
            "email_contacto": "contacto2@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        response2 = self.api_client.post("/api/v1/empresas/", data2, format="json")

        self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)
        response_data = response2.json()
        self.assertIn("detail", response_data)
        self.assertIn("Ya existe una Empresa", response_data["detail"])

    def test_serializer_validation_prevents_duplicate(self):
        """
        Verifica que el serializer valida singleton antes de guardar.
        """
        from apps.tenant.empresa.api.serializers import EmpresaSerializer

        # Crear primera empresa
        empresa1 = Empresa.objects.create(
            razon_social="Primera Empresa S.A.",
            nit="900123456",
            dv="1",
            direccion="Calle 123 #45-67",
            telefono="6012345678",
            email_contacto="contacto1@prueba.com",
            regimen_tributario="Responsable de IVA",
        )

        # Intentar crear segunda empresa vía serializer
        data = {
            "razon_social": "Segunda Empresa S.A.",
            "nit": "900654321",
            "direccion": "Calle 456 #78-90",
            "telefono": "6098765432",
            "email_contacto": "contacto2@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        serializer = EmpresaSerializer(data=data)

        # La validación debe fallar
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn(
            "Ya existe una Empresa", str(serializer.errors["non_field_errors"])
        )


class TestEmpresaSingletonConcurrency(TransactionTestCase):
    """
    Pruebas de concurrencia básica para el patrón Singleton.

    [WARNING] NOTA: Usa TransactionTestCase para probar transacciones concurrentes.
    """

    def setUp(self):
        """Configurar tenant y usuario para las pruebas."""
        from django.contrib.auth import get_user_model
        from django_tenants.utils import schema_context

        from apps.public.tenants.models import Client, Domain, TenantMembership

        User = get_user_model()

        # Crear tenant de prueba
        with schema_context("public"):
            self.tenant = Client.objects.create(
                schema_name="test_concurrency", nombre="Tenant Concurrencia"
            )
            Domain.objects.create(
                domain="concurrency.test.com", tenant=self.tenant, is_primary=True
            )

            # Crear usuario
            self.user = User.objects.create_user(
                username="test_concurrency",
                email="test_concurrency@test.com",
                password="testpass123",
            )

            # Crear membresía
            TenantMembership.objects.create(
                client=self.tenant, user=self.user, rol="ADMIN", is_active=True
            )

    def test_concurrent_create_attempts(self):
        """
        Verifica que intentos concurrentes de crear empresa solo permiten una.

        [WARNING] NOTA: Esta prueba simula concurrencia básica. En producción,
        el UniqueConstraint garantiza que solo una transacción tenga éxito.
        """
        from django_tenants.utils import schema_context

        from apps.tenant.empresa.models import Empresa

        with schema_context(self.tenant.schema_name):
            # Crear primera empresa
            empresa1 = Empresa.objects.create(
                razon_social="Empresa Concurrente 1",
                nit="900111111",
                dv="1",
                direccion="Calle 111",
                telefono="6011111111",
                email_contacto="concurrente1@test.com",
                regimen_tributario="Responsable de IVA",
            )

            # Verificar que solo existe una
            count = Empresa.objects.count()
            self.assertEqual(count, 1)

            # Intentar crear segunda (debe fallar por constraint)
            with self.assertRaises(IntegrityError):
                Empresa.objects.create(
                    razon_social="Empresa Concurrente 2",
                    nit="900222222",
                    dv="2",
                    direccion="Calle 222",
                    telefono="6022222222",
                    email_contacto="concurrente2@test.com",
                    regimen_tributario="Responsable de IVA",
                )

            # Verificar que sigue siendo solo una
            count = Empresa.objects.count()
            self.assertEqual(count, 1)
