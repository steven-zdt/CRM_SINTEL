"""
Factories para modelos de tenants (factory_boy).

Facilitan la creación de datos de prueba.
"""
import factory
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory para User (usuario global)."""
    
    class Meta:
        model = User
        django_get_or_create = ('email',)
    
    email = factory.Sequence(lambda n: f"user{n}@test.local")
    username = factory.LazyAttribute(lambda obj: obj.email.split('@')[0])
    is_staff = False
    is_superuser = False
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class ClientFactory(factory.django.DjangoModelFactory):
    """Factory para Client (tenant)."""
    
    class Meta:
        model = Client
        django_get_or_create = ('schema_name',)
    
    nombre = factory.Sequence(lambda n: f"Empresa Test {n}")
    schema_name = factory.Sequence(lambda n: f"testcorp{n}")
    paid_until = None
    on_trial = True
    is_active = True  # ✅ Agregado: estado activo por defecto
    auto_create_schema = True
    auto_drop_schema = False


class DomainFactory(factory.django.DjangoModelFactory):
    """Factory para Domain."""
    
    class Meta:
        model = Domain
    
    tenant = factory.SubFactory(ClientFactory)
    domain = factory.LazyAttribute(lambda obj: f"{obj.tenant.schema_name}.localhost")
    is_primary = True


class TenantMembershipFactory(factory.django.DjangoModelFactory):
    """Factory para TenantMembership."""
    
    class Meta:
        model = TenantMembership
    
    client = factory.SubFactory(ClientFactory)
    user = factory.SubFactory(UserFactory)
    rol = "ADMIN"
    is_primary_admin = False
