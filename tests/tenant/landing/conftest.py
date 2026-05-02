"""
Fixtures para tests de landing de tenants.
"""
import pytest
from django_tenants.utils import schema_context, get_public_schema_name
from apps.public.tenants.models import Client
from tests.public.tenants.factories import UserFactory


@pytest.fixture
def tenant_factory():
    """
    Fixture factory para crear tenants de prueba.
    
    Uso:
        tenant = tenant_factory(schema_name="acme", nombre="Acme SAS")
    """
    def _factory(**kwargs):
        # Crear tenant directamente en el esquema público
        schema_name = kwargs.pop('schema_name', None)
        if not schema_name:
            raise ValueError("schema_name es requerido")
        
        # Crear tenant en el esquema público (requerido por django-tenants)
        with schema_context(get_public_schema_name()):
            # Intentar obtener tenant existente
            tenant = Client.objects.filter(schema_name=schema_name).first()
            if tenant:
                # Actualizar campos si se proporcionan
                for key, value in kwargs.items():
                    if hasattr(tenant, key):
                        setattr(tenant, key, value)
                tenant.save()
                return tenant
            
            # Crear nuevo tenant
            tenant = Client(schema_name=schema_name, **kwargs)
            tenant.save()  # django-tenants creará el schema automáticamente
            return tenant
    return _factory


@pytest.fixture
def user_factory():
    """
    Fixture factory para crear usuarios de prueba.
    
    Uso:
        user = user_factory(email="owner@acme.com")
    """
    def _factory(**kwargs):
        return UserFactory(**kwargs)
    return _factory
