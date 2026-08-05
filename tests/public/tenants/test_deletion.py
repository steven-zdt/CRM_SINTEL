"""
Tests para el borrado completo y limpio de tenants.

Estos tests validan que al eliminar un Client:
1. Se elimina el objeto Client de la BD
2. Se eliminan automáticamente los Domain asociados (CASCADE)
3. Se eliminan automáticamente las TenantMembership asociadas (CASCADE)
4. Se elimina el esquema PostgreSQL (auto_drop_schema=True)
5. El tenant 'public' está protegido y no se puede eliminar
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_tenants.utils import get_public_schema_name, schema_context, schema_exists

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_tenant

User = get_user_model()


@pytest.mark.django_db
class TestTenantDeletion:
    """
    Tests para el borrado completo de tenants.

    [WARNING] IMPORTANTE: Estos tests se ejecutan en el esquema público (public)
    porque los modelos Client, Domain y TenantMembership están en SHARED_APPS.
    """

    def test_tenant_hard_delete(self):
        """
        Test crítico: Verifica que el borrado de un tenant elimina TODO.

        Este test:
        1. Crea un tenant "borrame"
        2. Verifica que su esquema existe
        3. Ejecuta client.delete()
        4. Verifica que TODO fue eliminado
        """
        # Setup: Crear usuario para el tenant
        owner = User.objects.create_user(
            username="owner_delete",
            email="owner_delete@test.com",
            password="test_password",
            is_active=True,
        )

        schema_name = "borrame"
        nombre = "Tenant Para Borrar"

        # 1. Crear tenant usando el servicio
        client, domain, login_url = crear_tenant(
            nombre=nombre, admin_user_id=owner.id, schema_name=schema_name
        )

        # Verificar que el tenant se creó correctamente
        assert client.pk is not None, "El Client no se creó"
        assert domain.pk is not None, "El Domain no se creó"

        # Verificar que existe TenantMembership
        membership = TenantMembership.objects.filter(
            client=client, is_primary_admin=True
        ).first()
        assert membership is not None, "No se creó la TenantMembership"

        # 2. Verificar que el esquema existe en PostgreSQL
        assert schema_exists(
            schema_name
        ), f"El esquema '{schema_name}' no existe después de crear el tenant"

        # 3. Ejecutar client.delete()
        client.delete()

        # 4. Verificar que el objeto Client ya no existe
        with pytest.raises(Client.DoesNotExist):
            Client.objects.get(schema_name=schema_name)
        assert not Client.objects.filter(
            schema_name=schema_name
        ).exists(), "El Client aún existe"

        # 5. Verificar que el objeto Domain ya no existe (CASCADE)
        assert not Domain.objects.filter(
            domain=domain.domain
        ).exists(), "El Domain aún existe"

        # 6. Verificar que la TenantMembership ya no existe (CASCADE)
        assert not TenantMembership.objects.filter(
            client=client
        ).exists(), "La TenantMembership aún existe"

        # 7. Verificar que el esquema YA NO existe en PostgreSQL
        assert not schema_exists(
            schema_name
        ), f"El esquema '{schema_name}' aún existe en PostgreSQL"

        # 8. Verificar que el usuario global NO fue eliminado (debe seguir existiendo)
        assert User.objects.filter(
            pk=owner.pk
        ).exists(), "El usuario global fue eliminado (no debería)"

    def test_public_tenant_protection(self):
        """
        Test de protección: Verifica que es IMPOSIBLE borrar el tenant 'public'.

        Este test:
        1. Intenta obtener el tenant 'public'
        2. Intenta borrarlo
        3. Verifica que lanza ValueError con mensaje apropiado
        """
        public_schema = get_public_schema_name()

        # Obtener el tenant público
        try:
            public_client = Client.objects.get(schema_name=public_schema)
        except Client.DoesNotExist:
            pytest.skip(
                f"El tenant '{public_schema}' no existe. Ejecuta primero: python manage.py setup_public_tenant"
            )

        # Intentar borrar el tenant público debe lanzar ValueError
        with pytest.raises(ValueError) as exc_info:
            public_client.delete()

        # Verificar que el mensaje de error es el esperado
        error_message = str(exc_info.value)
        assert (
            "No se puede eliminar el tenant público" in error_message
            or "núcleo del sistema" in error_message
        ), f"El mensaje de error no es el esperado. Mensaje: {error_message}"

        # Verificar que el tenant público sigue existiendo
        assert Client.objects.filter(
            schema_name=public_schema
        ).exists(), "El tenant público fue eliminado (no debería)"

    def test_delete_cascades_to_domain(self):
        """
        Test de cascada: Verifica que al eliminar Client, se eliminan los Domain.
        """
        owner = User.objects.create_user(
            username="owner_cascade",
            email="owner_cascade@test.com",
            password="test_password",
            is_active=True,
        )

        schema_name = "test_cascade"
        client, domain, _ = crear_tenant(
            nombre="Test Cascade", admin_user_id=owner.id, schema_name=schema_name
        )

        domain_id = domain.pk
        domain_domain = domain.domain

        # Eliminar el Client
        client.delete()

        # Verificar que el Domain fue eliminado (CASCADE)
        assert not Domain.objects.filter(
            pk=domain_id
        ).exists(), "El Domain no fue eliminado por CASCADE"
        assert not Domain.objects.filter(
            domain=domain_domain
        ).exists(), "El Domain no fue eliminado por CASCADE"

    def test_delete_cascades_to_membership(self):
        """
        Test de cascada: Verifica que al eliminar Client, se eliminan las TenantMembership.
        """
        owner = User.objects.create_user(
            username="owner_membership",
            email="owner_membership@test.com",
            password="test_password",
            is_active=True,
        )

        schema_name = "test_membership"
        client, _, _ = crear_tenant(
            nombre="Test Membership", admin_user_id=owner.id, schema_name=schema_name
        )

        # Verificar que existe la membresía
        membership = TenantMembership.objects.filter(client=client).first()
        assert membership is not None, "No se creó la TenantMembership"
        membership_id = membership.pk

        # Eliminar el Client
        client.delete()

        # Verificar que la TenantMembership fue eliminada (CASCADE)
        assert not TenantMembership.objects.filter(
            pk=membership_id
        ).exists(), "La TenantMembership no fue eliminada por CASCADE"

        # Verificar que el usuario global NO fue eliminado
        assert User.objects.filter(
            pk=owner.pk
        ).exists(), "El usuario global fue eliminado (no debería)"

    def test_delete_removes_schema_from_postgresql(self):
        """
        Test crítico: Verifica que el esquema PostgreSQL se elimina automáticamente.

        Este test verifica que con auto_drop_schema=True, django-tenants
        elimina el esquema automáticamente al borrar el Client.
        """
        owner = User.objects.create_user(
            username="owner_schema",
            email="owner_schema@test.com",
            password="test_password",
            is_active=True,
        )

        schema_name = "test_schema_drop"
        client, _, _ = crear_tenant(
            nombre="Test Schema Drop", admin_user_id=owner.id, schema_name=schema_name
        )

        # Verificar que el esquema existe
        assert schema_exists(schema_name), f"El esquema '{schema_name}' no existe"

        # Eliminar el Client
        client.delete()

        # Verificar que el esquema fue eliminado
        assert not schema_exists(
            schema_name
        ), f"El esquema '{schema_name}' aún existe después de eliminar el Client"

    def test_delete_preserves_global_users(self):
        """
        Test de preservación: Verifica que los usuarios globales NO se eliminan.

        Este test verifica que al eliminar un tenant, los usuarios globales
        que pertenecían a ese tenant siguen existiendo (pueden pertenecer a otros tenants).
        """
        owner = User.objects.create_user(
            username="owner_preserve",
            email="owner_preserve@test.com",
            password="test_password",
            is_active=True,
        )

        schema_name = "test_preserve"
        client, _, _ = crear_tenant(
            nombre="Test Preserve", admin_user_id=owner.id, schema_name=schema_name
        )

        owner_id = owner.pk

        # Verificar que existe la membresía
        membership = TenantMembership.objects.filter(client=client, user=owner).first()
        assert membership is not None, "No se creó la TenantMembership"

        # Eliminar el Client
        client.delete()

        # Verificar que el usuario global sigue existiendo
        assert User.objects.filter(
            pk=owner_id
        ).exists(), "El usuario global fue eliminado (no debería)"

        # Verificar que el usuario puede ser usado en otro tenant
        owner2 = User.objects.get(pk=owner_id)
        assert (
            owner2.email == "owner_preserve@test.com"
        ), "El usuario global fue modificado"
