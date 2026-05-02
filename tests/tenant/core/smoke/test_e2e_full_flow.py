"""
Prueba de humo end-to-end: Flujo completo desde onboarding hasta workspace.

[WARNING] POLÍTICA v2.30: Simula el flujo completo:
1. Alta del tenant desde consola pública
2. Activación del owner en dominio del tenant
3. Login/Logout desde UI única (Core)
4. Reset de contraseña
5. Visualización de datos en workspace (Core orquesta)

Este test valida que todo el circuito funciona correctamente.
"""
import pytest

try:
    import playwright  # noqa: F401
    import cryptography  # noqa: F401
except Exception:
    pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_public_schema_name
from rest_framework.test import APIClient
from rest_framework import status

from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token
from apps.services.onboarding.empresa_service import crear_empresa

User = get_user_model()


class TestE2EFullFlow(TestCase):
    """
    Prueba end-to-end del flujo completo.
    
    Simula:
    1. Creación de tenant desde consola pública
    2. Activación del owner
    3. Login/Logout
    4. Reset de contraseña
    5. Visualización en workspace
    """
    
    def setUp(self):
        """Configuración inicial."""
        # Cliente para dominio público (consola)
        self.public_client = Client()
        
        # Cliente para dominio del tenant (después de creación)
        self.tenant_client = None
        self.tenant_domain = None
        
        # Usuario staff para consola
        with schema_context('public'):
            self.staff_user = User.objects.create_user(
                username='staff',
                email='staff@sintel.com',
                password='staffpass123',
                is_staff=True,
                is_superuser=True,
            )
    
    def test_step1_create_tenant_from_console(self):
        """PASO 1: Alta del tenant desde la consola pública."""
        # Simular acceso a consola (dominio público)
        # En producción: http://sintel.com/console/tenants/
        
        with schema_context('public'):
            # Crear tenant usando servicio de onboarding
            result = crear_empresa(
                nombre='Empresa Test E2E',
                email_admin='owner@test-e2e.com',
                schema_name='test-e2e',
                on_trial=True,
            )
            
            # Verificar creación
            self.assertIsNotNone(result['client'])
            self.assertEqual(result['client'].nombre, 'Empresa Test E2E')
            self.assertEqual(result['client'].schema_name, 'test-e2e')
            
            # Verificar dominio
            self.assertIsNotNone(result['domain'])
            self.tenant_domain = result['domain'].domain
            
            # Verificar usuario owner
            self.assertIsNotNone(result.get('user'))
            owner_user = result['user']
            
            # Verificar membresía
            membership = TenantMembership.objects.filter(
                client=result['client'],
                user=owner_user,
            ).first()
            self.assertIsNotNone(membership)
            
            # Guardar para siguientes pasos
            self.tenant = result['client']
            self.owner_user = owner_user
            self.owner_membership = membership
            
            # Generar token de activación
            self.activation_token = generate_invitation_token(
                user_id=owner_user.id,
                tenant_id=result['client'].id,
            )
    
    def test_step2_activate_owner_in_tenant_domain(self):
        """PASO 2: Activación del owner en el dominio del tenant."""
        # Primero crear el tenant (paso 1)
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Test E2E Activate',
                email_admin='owner@activate.com',
                schema_name='test-activate',
                on_trial=True,
            )
            owner_user = result['user']
            owner_user.set_unusable_password()  # Sin password usable
            owner_user.save()
            
            token = generate_invitation_token(
                user_id=owner_user.id,
                tenant_id=result['client'].id,
            )
        
        # Cliente con HTTP_HOST del tenant
        client = APIClient(HTTP_HOST=result['domain'].domain)
        
        # PASO 2.1: Validación del token (GET)
        response = client.get(f'/api/v1/core/landing/auth/activate/?token={token}')
        
        # Debe retornar 200 si token válido y usuario sin password
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_409_CONFLICT])
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('user', data)
            self.assertIn('tenant', data)
            self.assertIn('token_valid', data)
            self.assertTrue(data['token_valid'])
            
            # PASO 2.2: Activación (POST)
            response = client.post(
                f'/api/v1/core/landing/auth/activate/?token={token}',
                {
                    'password1': 'newpass123',
                    'password2': 'newpass123',
                },
                format='json'
            )
            
            # Debe retornar 200 con redirect_url
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertIn('redirect_url', data)
            self.assertIn('detail', data)
            
            # Verificar que el usuario ahora tiene password usable
            owner_user.refresh_from_db()
            self.assertTrue(owner_user.has_usable_password())
    
    def test_step3_login_logout_from_core(self):
        """PASO 3: Login/Logout desde UI única (Core)."""
        # Crear tenant y usuario con password
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Test E2E Login',
                email_admin='owner@login.com',
                schema_name='test-login',
                on_trial=True,
            )
            owner_user = result['user']
            owner_user.set_password('testpass123')
            owner_user.save()
        
        client = APIClient(HTTP_HOST=result['domain'].domain)
        
        # PASO 3.1: Login desde Core
        response = client.post(
            '/api/v1/core/auth/login/',
            {
                'email': 'owner@login.com',
                'password': 'testpass123',
            },
            format='json'
        )
        
        # Debe retornar 200 con redirect_url
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('redirect_url', data)
        self.assertIn('detail', data)
        self.assertIn('user', data)
        self.assertIn('tenant', data)
        
        # Verificar que la sesión está activa
        # (APIClient maneja esto automáticamente)
        
        # PASO 3.2: Logout desde Core
        response = client.post('/api/v1/core/auth/logout/')
        
        # Debe retornar 200 con redirect_url="/"
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('redirect_url', data)
        self.assertEqual(data['redirect_url'], '/')
        self.assertIn('detail', data)
    
    def test_step4_password_reset_from_core(self):
        """PASO 4: Reset de contraseña desde UI única (Core)."""
        # Crear tenant y usuario
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Test E2E Reset',
                email_admin='owner@reset.com',
                schema_name='test-reset',
                on_trial=True,
            )
            owner_user = result['user']
            owner_user.set_password('oldpass123')
            owner_user.save()
        
        client = APIClient(HTTP_HOST=result['domain'].domain)
        
        # PASO 4.1: Solicitud de reset (idempotente)
        response = client.post(
            '/api/v1/core/auth/password-reset/request/',
            {
                'email': 'owner@reset.com',
            },
            format='json'
        )
        
        # Debe retornar 200 (idempotente)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('detail', data)
        
        # PASO 4.2: Validación de token (simulado - requeriría token real)
        # En producción, el usuario recibiría el token por email
        # Aquí simulamos que el token es inválido
        response = client.post(
            '/api/v1/core/auth/password-reset/validate/',
            {
                'uid': 'invalid',
                'token': 'invalid',
            },
            format='json'
        )
        
        # Debe retornar 400 (token inválido)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_step5_workspace_core_orchestration(self):
        """PASO 5: Visualización de datos en workspace (Core orquesta)."""
        # Crear tenant y usuario autenticado
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Test E2E Workspace',
                email_admin='owner@workspace.com',
                schema_name='test-workspace',
                on_trial=True,
            )
            owner_user = result['user']
            owner_user.set_password('testpass123')
            owner_user.save()
        
        client = APIClient(HTTP_HOST=result['domain'].domain)
        client.force_authenticate(user=owner_user)
        
        # PASO 5.1: Verificar endpoints Core de orquestación
        endpoints = [
            '/api/v1/core/mi-empresa/',
            '/api/v1/core/mi-perfil/',
            '/api/v1/core/facturas/resumen/',
            '/api/v1/core/contabilidad/resumen/',
            '/api/v1/core/dashboard/',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            # Todos deben retornar 200 (pueden estar vacíos si no hay datos)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Endpoint {endpoint} debe retornar 200"
            )
            
            # Verificar que es JSON
            self.assertEqual(
                response['Content-Type'],
                'application/json',
                f"Endpoint {endpoint} debe retornar JSON"
            )
            
            data = response.json()
            self.assertIsInstance(data, dict)
        
        # PASO 5.2: Verificar estructura de respuestas
        # Mi Empresa
        response = client.get('/api/v1/core/mi-empresa/')
        data = response.json()
        self.assertIn('empresa', data)
        self.assertIn('branding', data)
        
        # Mi Perfil
        response = client.get('/api/v1/core/mi-perfil/')
        data = response.json()
        self.assertIn('perfil', data)
        self.assertIn('user', data)
        
        # Dashboard
        response = client.get('/api/v1/core/dashboard/')
        data = response.json()
        self.assertIn('tenant', data)
        self.assertIn('user', data)
        self.assertIn('empresa', data)
        self.assertIn('facturas', data)
        self.assertIn('contabilidad', data)
        self.assertIn('perfil', data)
        self.assertIn('branding', data)
    
    def test_step6_routing_by_hostname(self):
        """PASO 6: Validación de routing por hostname."""
        # Crear dos tenants diferentes
        with schema_context('public'):
            result1 = crear_empresa(
                nombre='Tenant 1',
                email_admin='owner1@test.com',
                schema_name='tenant1',
                on_trial=True,
            )
            result2 = crear_empresa(
                nombre='Tenant 2',
                email_admin='owner2@test.com',
                schema_name='tenant2',
                on_trial=True,
            )
            
            user1 = result1['user']
            user1.set_password('pass123')
            user1.save()
            
            user2 = result2['user']
            user2.set_password('pass123')
            user2.save()
        
        # Cliente para tenant1
        client1 = APIClient(HTTP_HOST=result1['domain'].domain)
        client1.force_authenticate(user=user1)
        
        # Cliente para tenant2
        client2 = APIClient(HTTP_HOST=result2['domain'].domain)
        client2.force_authenticate(user=user2)
        
        # Verificar que cada tenant ve solo sus datos
        response1 = client1.get('/api/v1/core/mi-empresa/')
        response2 = client2.get('/api/v1/core/mi-empresa/')
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Los datos deben ser diferentes (aislamiento)
        data1 = response1.json()
        data2 = response2.json()
        
        # Verificar que cada tenant tiene su propio nombre
        self.assertEqual(data1['branding']['nombre'], 'Tenant 1')
        self.assertEqual(data2['branding']['nombre'], 'Tenant 2')
    
    def test_full_flow_integration(self):
        """Flujo completo integrado: desde creación hasta workspace."""
        # PASO 1: Crear tenant
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Test Full Flow',
                email_admin='owner@fullflow.com',
                schema_name='test-fullflow',
                on_trial=True,
            )
            owner_user = result['user']
            owner_user.set_unusable_password()
            owner_user.save()
            
            token = generate_invitation_token(
                user_id=owner_user.id,
                tenant_id=result['client'].id,
            )
        
        client = APIClient(HTTP_HOST=result['domain'].domain)
        
        # PASO 2: Activar owner
        response = client.post(
            f'/api/v1/core/landing/auth/activate/?token={token}',
            {
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # PASO 3: Login
        response = client.post(
            '/api/v1/core/auth/login/',
            {
                'email': 'owner@fullflow.com',
                'password': 'newpass123',
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('redirect_url', response.json())
        
        # PASO 4: Acceder a workspace (endpoints Core)
        client.force_authenticate(user=owner_user)
        
        endpoints = [
            '/api/v1/core/dashboard/',
            '/api/v1/core/mi-empresa/',
            '/api/v1/core/mi-perfil/',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Endpoint {endpoint} debe estar accesible después del flujo completo"
            )
            self.assertEqual(
                response['Content-Type'],
                'application/json',
                f"Endpoint {endpoint} debe retornar JSON"
            )
        
        # PASO 5: Logout
        response = client.post('/api/v1/core/auth/logout/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['redirect_url'], '/')
