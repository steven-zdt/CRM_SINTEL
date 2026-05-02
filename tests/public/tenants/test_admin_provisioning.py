"""
Tests para el aprovisionamiento automático de usuarios en el admin de Client.

Estos tests validan la integración entre ClientAdminForm y ClientAdmin
para garantizar que al crear un tenant desde el admin, se asigne automáticamente
el usuario propietario mediante TenantMembership.

[WARNING] IMPORTANTE: Estos tests se ejecutan en el esquema público (public)
porque el admin de Client se accede desde el esquema público.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.forms import ClientAdminForm
from apps.public.tenants.admin import ClientAdmin

User = get_user_model()


@pytest.mark.django_db
class TestAdminProvisioning:
    """
    Tests para el aprovisionamiento automático de usuarios en el admin.
    
    [WARNING] IMPORTANTE: Estos tests se ejecutan en el esquema público (public)
    porque el admin de Client se accede desde el esquema público.
    """
    
    def test_admin_save_model_creates_membership(self):
        """
        Test de Lógica de Negocio: Verifica que save_model crea TenantMembership.
        
        Este test simula lo que hace Django Admin cuando se guarda un formulario:
        - Crea un usuario global
        - Instancia un Client (aún no guardado)
        - Instancia el ClientAdminForm con admin_user seleccionado
        - Llama a save_model del ClientAdmin
        - Verifica que se creó la TenantMembership correctamente
        """
        # Setup: Crear usuario global
        owner = User.objects.create_user(
            username='owner_test',
            email='owner@test.com',
            password='test_password',
            is_active=True
        )
        
        # Setup: Instanciar Client (aún no guardado)
        client = Client(
            schema_name='test_provisioning',
            nombre='Test Provisioning Tenant',
            is_active=True,
            on_trial=True
        )
        
        # Setup: Instanciar ClientAdminForm con datos válidos
        form_data = {
            'nombre': 'Test Provisioning Tenant',
            'schema_name': 'test_provisioning',
            'is_active': True,
            'on_trial': True,
            'admin_user': owner.id
        }
        form = ClientAdminForm(data=form_data, instance=client)
        
        # Validar el formulario para que cleaned_data esté disponible
        assert form.is_valid(), f"Formulario inválido: {form.errors}"
        
        # Setup: Instanciar ClientAdmin
        admin_instance = ClientAdmin(Client, site)
        
        # Setup: Crear mock request
        factory = RequestFactory()
        request = factory.get('/admin/')
        
        # Acción: Llamar a save_model manualmente
        # change=False indica que es una creación nueva
        admin_instance.save_model(
            request=request,
            obj=client,
            form=form,
            change=False
        )
        
        # Asserts: Verificar que el Client se guardó en la BD
        assert client.pk is not None, "El Client no se guardó en la BD"
        saved_client = Client.objects.get(pk=client.pk)
        assert saved_client.schema_name == 'test_provisioning'
        assert saved_client.nombre == 'Test Provisioning Tenant'
        
        # Asserts: Verificar que se creó una TenantMembership
        membership = TenantMembership.objects.filter(
            client=client,
            is_primary_admin=True
        ).first()
        
        assert membership is not None, "No se creó la TenantMembership"
        
        # Asserts: Verificar propiedades de la membresía
        assert membership.user == owner, "El usuario de la membresía no coincide"
        assert membership.client == client, "El cliente de la membresía no coincide"
        assert membership.rol == 'ADMIN', f"El rol debe ser 'ADMIN', pero es '{membership.rol}'"
        assert membership.is_primary_admin is True, "is_primary_admin debe ser True"
        
        # Limpieza: Eliminar el tenant de prueba
        Domain.objects.filter(tenant=client).delete()
        TenantMembership.objects.filter(client=client).delete()
        client.delete()
    
    def test_form_requires_user_on_create(self):
        """
        Test de Validación de Formulario: Verifica que el formulario requiere usuario en creación.
        
        Este test verifica que el formulario lance error si falta el usuario
        al crear un nuevo tenant.
        """
        # Setup: Instanciar Client (aún no guardado - creación nueva)
        client = Client(
            schema_name='test_validation',
            nombre='Test Validation Tenant',
            is_active=True,
            on_trial=True
        )
        
        # Acción: Instanciar ClientAdminForm sin admin_user
        form_data = {
            'nombre': 'Test Validation Tenant',
            'schema_name': 'test_validation',
            'is_active': True,
            'on_trial': True,
            # admin_user NO se incluye (debe fallar)
        }
        form = ClientAdminForm(data=form_data, instance=client)
        
        # Acción: Llamar a is_valid()
        is_valid = form.is_valid()
        
        # Asserts: El formulario debe ser inválido
        assert is_valid is False, "El formulario debería ser inválido sin admin_user en creación"
        
        # Asserts: Debe tener error en el campo admin_user
        assert 'admin_user' in form.errors, "Debe haber error en el campo admin_user"
        
        # Asserts: El mensaje de error debe ser el esperado
        error_messages = form.errors['admin_user']
        assert len(error_messages) > 0, "Debe haber al menos un mensaje de error"
        
        expected_message = "Debe asignar un usuario propietario al crear un nuevo tenant."
        assert expected_message in error_messages, (
            f"El mensaje de error esperado no se encontró. "
            f"Errores encontrados: {error_messages}"
        )
    
    def test_edit_does_not_require_user(self):
        """
        Test de Edición: Verifica que al editar un tenant existente, el campo admin_user es opcional.
        
        Este test verifica que:
        - Al editar un tenant existente, el campo admin_user puede quedar vacío
        - El formulario es válido sin admin_user en edición
        - No se lanza ValidationError
        """
        # Setup: Crear un tenant existente con usuario propietario
        owner = User.objects.create_user(
            username='owner_edit',
            email='owner_edit@test.com',
            password='test_password',
            is_active=True
        )
        
        # Crear tenant en el esquema público
        with schema_context(get_public_schema_name()):
            client = Client.objects.create(
                schema_name='test_edit',
                nombre='Test Edit Tenant',
                is_active=True,
                on_trial=True
            )
            
            # Crear TenantMembership existente
            TenantMembership.objects.create(
                client=client,
                user=owner,
                rol='ADMIN',
                is_primary_admin=True
            )
        
        # Acción: Instanciar ClientAdminForm para edición (sin admin_user)
        form_data = {
            'nombre': 'Test Edit Tenant Updated',
            'schema_name': 'test_edit',
            'is_active': True,
            'on_trial': False,  # Cambiar on_trial
            # admin_user NO se incluye (debe ser válido en edición)
        }
        form = ClientAdminForm(data=form_data, instance=client)
        
        # Acción: Llamar a is_valid()
        is_valid = form.is_valid()
        
        # Asserts: El formulario debe ser válido (admin_user es opcional en edición)
        assert is_valid is True, (
            f"El formulario debería ser válido sin admin_user en edición. "
            f"Errores: {form.errors}"
        )
        
        # Asserts: No debe haber error en admin_user
        assert 'admin_user' not in form.errors, (
            f"No debe haber error en admin_user al editar. "
            f"Errores encontrados: {form.errors.get('admin_user', [])}"
        )
        
        # Limpieza
        with schema_context(get_public_schema_name()):
            Domain.objects.filter(tenant=client).delete()
            TenantMembership.objects.filter(client=client).delete()
            client.delete()
    
    def test_save_model_updates_existing_membership(self):
        """
        Test adicional: Verifica que save_model actualiza la membresía existente.
        
        Este test verifica que si se cambia el admin_user en una edición,
        se actualiza correctamente la TenantMembership.
        """
        # Setup: Crear dos usuarios
        owner1 = User.objects.create_user(
            username='owner1',
            email='owner1@test.com',
            password='test_password',
            is_active=True
        )
        
        owner2 = User.objects.create_user(
            username='owner2',
            email='owner2@test.com',
            password='test_password',
            is_active=True
        )
        
        # Setup: Crear tenant con owner1
        with schema_context(get_public_schema_name()):
            client = Client.objects.create(
                schema_name='test_update',
                nombre='Test Update Tenant',
                is_active=True,
                on_trial=True
            )
            
            # Crear TenantMembership con owner1
            TenantMembership.objects.create(
                client=client,
                user=owner1,
                rol='ADMIN',
                is_primary_admin=True
            )
        
        # Setup: Formulario de edición con nuevo admin_user (owner2)
        form_data = {
            'nombre': 'Test Update Tenant',
            'schema_name': 'test_update',
            'is_active': True,
            'on_trial': True,
            'admin_user': owner2.id  # Cambiar a owner2
        }
        form = ClientAdminForm(data=form_data, instance=client)
        assert form.is_valid(), f"Formulario inválido: {form.errors}"
        
        # Setup: Instanciar ClientAdmin
        admin_instance = ClientAdmin(Client, site)
        factory = RequestFactory()
        request = factory.get('/admin/')
        
        # Acción: Llamar a save_model (change=True porque es edición)
        admin_instance.save_model(
            request=request,
            obj=client,
            form=form,
            change=True
        )
        
        # Asserts: Verificar que la membresía se actualizó a owner2
        membership = TenantMembership.objects.filter(
            client=client,
            is_primary_admin=True
        ).first()
        
        assert membership is not None, "No se encontró la TenantMembership"
        assert membership.user == owner2, "El usuario de la membresía debería ser owner2"
        assert membership.rol == 'ADMIN', "El rol debe ser 'ADMIN'"
        
        # Asserts: Verificar que owner1 ya no es primary_admin
        owner1_membership = TenantMembership.objects.filter(
            client=client,
            user=owner1,
            is_primary_admin=True
        ).first()
        assert owner1_membership is None, "owner1 no debería ser primary_admin"
        
        # Limpieza
        with schema_context(get_public_schema_name()):
            Domain.objects.filter(tenant=client).delete()
            TenantMembership.objects.filter(client=client).delete()
            client.delete()
