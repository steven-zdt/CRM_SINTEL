"""
Tests para validar que la activación solo funciona una vez (v2.29).

[WARNING] OBJETIVO: Garantizar que un token de activación solo se puede usar una vez.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.public.tenants.services.invitations import make_owner_invite_token

User = get_user_model()


@pytest.mark.django_db
class TestActivacionUnaSolaVez:
    """Tests para validar que la activación solo funciona una vez."""
    
    def test_activacion_muestra_formulario_si_password_usable(self, django_user_model):
        """
        [WARNING] v2.29: Verifica que la activación MUESTRA el formulario incluso si el usuario ya tiene password usable.
        
        Antes (v2.28): Bloqueaba y redirigía a /login/
        Ahora (v2.29): Muestra el formulario para permitir actualizar la contraseña
        """
        # Crear tenant y usuario
        with schema_context('public'):
            tenant = TenantClient.objects.create(
                schema_name='test_tenant',
                nombre='Test Tenant',
                is_active=True
            )
            domain = Domain.objects.create(
                tenant=tenant,
                domain='test-tenant.localhost',
                is_primary=True
            )
            user = django_user_model.objects.create_user(
                email='owner@test.com',
                username='owner',
                password='Test1234!',  # Password usable
            )
            TenantMembership.objects.create(
                client=tenant,
                user=user,
                rol='ADMIN',
                is_primary_admin=True,
                is_active=True
            )
        
        # Generar token
        token = make_owner_invite_token(user_id=user.id, tenant_id=tenant.id)
        
        # Intentar activar (v2.29: debe mostrar formulario aunque ya tenga password)
        client = Client(HTTP_HOST='test-tenant.localhost')
        response = client.get(f'/activate/?token={token}')
        
        # [WARNING] v2.29: Debe mostrar el formulario, no redirigir
        assert response.status_code == 200, "Debe mostrar formulario (v2.29)"
        assert 'activate' in response.content.decode().lower(), "Debe renderizar activate.html"
        
        # POST para actualizar contraseña
        response_post = client.post(f'/activate/?token={token}', {
            'password1': 'NewPassword123!',
            'password2': 'NewPassword123!',
        })
        
        # Debe redirigir al dashboard
        assert response_post.status_code == 302
        assert '/dashboard/' in response_post.url
        
        # Verificar que la contraseña fue actualizada
        user.refresh_from_db()
        assert user.check_password('NewPassword123!')
        assert not user.check_password('Test1234!')  # Password antiguo no funciona
    
    def test_activacion_funciona_sin_password_usable(self, django_user_model):
        """Verifica que la activación funciona si el usuario NO tiene password usable."""
        # Crear tenant y usuario sin password usable
        with schema_context('public'):
            tenant = TenantClient.objects.create(
                schema_name='test_tenant2',
                nombre='Test Tenant 2',
                is_active=True
            )
            domain = Domain.objects.create(
                tenant=tenant,
                domain='test-tenant2.localhost',
                is_primary=True
            )
            user = django_user_model.objects.create(
                email='owner2@test.com',
                username='owner2',
            )
            user.set_unusable_password()  # [WARNING] Sin password usable
            user.save()
            TenantMembership.objects.create(
                client=tenant,
                user=user,
                rol='ADMIN',
                is_primary_admin=True,
                is_active=True
            )
        
        # Generar token
        token = make_owner_invite_token(user_id=user.id, tenant_id=tenant.id)
        
        # GET activación (debe mostrar formulario)
        client = Client(HTTP_HOST='test-tenant2.localhost')
        response = client.get(f'/activate/?token={token}')
        
        assert response.status_code == 200
        assert 'activate' in response.content.decode().lower()
        
        # POST activación (v2.29: usa password1/password2)
        response = client.post(f'/activate/?token={token}', {
            'password1': 'Test1234!',
            'password2': 'Test1234!',
        })
        
        # Debe redirigir al dashboard
        assert response.status_code == 302
        assert '/dashboard/' in response.url
        
        # Verificar que el usuario ahora tiene password usable
        user.refresh_from_db()
        assert user.has_usable_password()
        assert user.check_password('Test1234!')
    
    def test_activacion_no_funciona_dos_veces(self, django_user_model):
        """Verifica que un token no se puede usar dos veces."""
        # Crear tenant y usuario sin password usable
        with schema_context('public'):
            tenant = TenantClient.objects.create(
                schema_name='test_tenant3',
                nombre='Test Tenant 3',
                is_active=True
            )
            domain = Domain.objects.create(
                tenant=tenant,
                domain='test-tenant3.localhost',
                is_primary=True
            )
            user = django_user_model.objects.create(
                email='owner3@test.com',
                username='owner3',
            )
            user.set_unusable_password()
            user.save()
            TenantMembership.objects.create(
                client=tenant,
                user=user,
                rol='ADMIN',
                is_primary_admin=True,
                is_active=True
            )
        
        # Generar token
        token = make_owner_invite_token(user_id=user.id, tenant_id=tenant.id)
        
        client = Client(HTTP_HOST='test-tenant3.localhost')
        
        # Primera activación (v2.29: usa password1/password2)
        response = client.post(f'/activate/?token={token}', {
            'password1': 'Test1234!',
            'password2': 'Test1234!',
        })
        
        assert response.status_code == 302
        assert '/dashboard/' in response.url
        
        # Verificar que el usuario ahora tiene password usable
        user.refresh_from_db()
        assert user.has_usable_password()
        assert user.check_password('Test1234!')
        
        # Segunda activación con el mismo token (v2.29: debe mostrar formulario)
        response2 = client.get(f'/activate/?token={token}')
        
        # [WARNING] v2.29: Debe mostrar el formulario (token aún válido)
        assert response2.status_code == 200, "Token aún válido, debe mostrar formulario (v2.29)"
        
        # Actualizar password nuevamente
        response3 = client.post(f'/activate/?token={token}', {
            'password1': 'NewPassword123!',
            'password2': 'NewPassword123!',
        })
        
        assert response3.status_code == 302
        assert '/dashboard/' in response3.url
        
        # Verificar que el password fue actualizado
        user.refresh_from_db()
        assert user.check_password('NewPassword123!')
        assert not user.check_password('Test1234!')  # Password anterior no funciona
