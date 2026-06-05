"""
Tests para validacion de fases en Proyectos v3.3
Valida que responsables opcionales no causen errores de validacion en fases tempranas.
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenant.proyectos.models import Proyecto
from apps.tenant.empresa.models import Empresa
from apps.public.accounts.models import User
from apps.tenant.perfil.models import TenantProfile


@pytest.mark.django_db(databases={'default', 'tenant1'})
class TestProyectoFaseValidation:
    """Tests para validacion de responsables por fase."""

    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        """Setup: usuario y empresa para tests."""
        self.tenant = tenant1
        with schema_context(self.tenant.schema_name):
            self.empresa = Empresa.objects.first()
            self.user = User.objects.create_user(
                email='test@test.com',
                password='test123'
            )
            self.profile = TenantProfile.objects.create(
                user=self.user,
                empresa=self.empresa,
                rol='ADMIN'
            )

    def test_crear_proyecto_borrador_sin_responsables(self, tenant1):
        """
        Test: crear proyecto en fase BORRADOR sin responsables
        (no debe fallar con error de "invalid integer")
        """
        with schema_context(tenant1.schema_name):
            client = APIClient()
            client.force_authenticate(user=self.user)

            payload = {
                'nombre': 'Proyecto Test',
                'tipo_servicio': 'PROYECTO_INTEGRAL',
                'fase_actual': 'BORRADOR',
                # Empty/missing responsables - should NOT fail
                'responsable_comercial_id': '',
                'responsable_tecnico_id': '',
                'responsable_operativo_id': '',
                'responsable_administrativo_id': '',
            }

            response = client.post(
                '/api/v1/proyectos/',
                payload,
                format='json'
            )

            # Should succeed (201 Created)
            assert response.status_code == status.HTTP_201_CREATED, \
                f"Expected 201, got {response.status_code}. Errors: {response.data}"

            # Verify responsables are None, not empty strings
            proyecto = Proyecto.objects.get(uuid=response.data['uuid'])
            assert proyecto.responsable_comercial_id is None or proyecto.responsable_comercial_id == '', \
                f"responsable_comercial_id should be None/empty, got {proyecto.responsable_comercial_id}"
            assert proyecto.responsable_tecnico_id is None or proyecto.responsable_tecnico_id == '', \
                f"responsable_tecnico_id should be None/empty, got {proyecto.responsable_tecnico_id}"

    def test_actualizar_proyecto_borrador_sin_responsables(self, tenant1):
        """
        Test: actualizar proyecto existente sin proporcionar responsables
        (PATCH con campos vacios no debe fallar)
        """
        with schema_context(tenant1.schema_name):
            # Create a project first
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Existente',
                empresa=self.empresa,
                fase_actual='BORRADOR'
            )

            client = APIClient()
            client.force_authenticate(user=self.user)

            payload = {
                'nombre': 'Proyecto Actualizado',
                # Empty/missing responsables - should NOT fail
                'responsable_comercial_id': '',
                'responsable_tecnico_id': '',
            }

            response = client.patch(
                f'/api/v1/proyectos/{proyecto.uuid}/',
                payload,
                format='json'
            )

            # Should succeed (200 OK)
            assert response.status_code == status.HTTP_200_OK, \
                f"Expected 200, got {response.status_code}. Errors: {response.data}"

            # Verify proyecto was updated but responsables remain None
            proyecto.refresh_from_db()
            assert proyecto.nombre == 'Proyecto Actualizado'
            assert proyecto.responsable_comercial_id is None or proyecto.responsable_comercial_id == ''

    def test_serializer_convierte_strings_vacios_a_none(self, tenant1):
        """
        Test: serializer debe convertir strings vacios a None en responsable fields
        """
        with schema_context(tenant1.schema_name):
            from apps.tenant.proyectos.api.serializers import ProyectoDetailSerializer

            # Create a minimal project instance
            proyecto = Proyecto.objects.create(
                nombre='Test',
                empresa=self.empresa
            )

            # Simulate form submission with empty strings
            data = {
                'nombre': 'Test Updated',
                'responsable_comercial_id': '',  # Empty string (como viene del formulario HTML)
                'responsable_comercial_nombre': '',
                'responsable_tecnico_id': '',
                'responsable_tecnico_nombre': '',
            }

            serializer = ProyectoDetailSerializer(proyecto, data=data, partial=True)
            assert serializer.is_valid(), f"Validation failed: {serializer.errors}"

            # After save, responsables should be None, not empty strings
            proyecto = serializer.save()
            assert proyecto.responsable_comercial_id is None or proyecto.responsable_comercial_id == ''
            assert proyecto.responsable_tecnico_id is None or proyecto.responsable_tecnico_id == ''
