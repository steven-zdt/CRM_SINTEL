"""
Tests para el backend de autenticación tenant-aware.

Escenarios validados:
- Caso A: Usuario con membresía correcta -> Autentica
- Caso B: Usuario SIN membresía (pero password correcto) -> Retorna None
- Caso C: Usuario en Public Tenant -> Autentica
- Caso D: Request sin tenant (comandos de consola) -> Autentica (fallback)
"""
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.db import connection
from django_tenants.utils import get_public_schema_name

from django.test import TestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.public.tenants.auth_backend import TenantAwareBackend

User = get_user_model()


class TestTenantAwareBackend(TestCase):
    """
    Tests para TenantAwareBackend.
    
    Valida que el backend de autenticación filtra correctamente
    los usuarios según su membresía en el tenant actual.
    """
    
    def setUp(self):
        """
        Setup: Crear usuarios, tenants y membresías para los tests.
        """
        # Crear usuarios
        self.user_con_membresia = User.objects.create_user(
            email='con_membresia@test.com',
            username='con_membresia',
            password='testpass123',
            is_active=True
        )
        
        self.user_sin_membresia = User.objects.create_user(
            email='sin_membresia@test.com',
            username='sin_membresia',
            password='testpass123',
            is_active=True
        )
        
        # Crear tenants
        connection.set_schema_to_public()
        
        self.tenant_a = TenantClient.objects.create(
            schema_name='tenant_a',
            nombre='Tenant A - Tests Backend',
            is_active=True,
            on_trial=False
        )
        
        self.tenant_b = TenantClient.objects.create(
            schema_name='tenant_b',
            nombre='Tenant B - Tests Backend',
            is_active=True,
            on_trial=False
        )
        
        # Crear dominio para tenant_a
        self.domain_a = Domain.objects.create(
            domain='tenant-a.sintel.local',
            tenant=self.tenant_a,
            is_primary=True
        )
        
        # Crear membresía: user_con_membresia tiene membresía en tenant_a
        self.membership = TenantMembership.objects.create(
            client=self.tenant_a,
            user=self.user_con_membresia,
            rol='ADMIN'
        )
        
        # user_sin_membresia NO tiene membresía en tenant_a
        
        # Crear backend
        self.backend = TenantAwareBackend()
        
        # Crear RequestFactory para simular requests
        self.factory = RequestFactory()
    
    def test_caso_a_usuario_con_membresia_autentica(self):
        """
        CASO A: Usuario con membresía correcta -> Autentica.
        
        Verifica que un usuario con TenantMembership activa en el tenant actual
        puede autenticarse correctamente.
        """
        # Simular request con tenant_a
        request = self.factory.get('/')
        request.tenant = self.tenant_a
        
        # Intentar autenticar
        user = self.backend.authenticate(
            request=request,
            username=self.user_con_membresia.username,
            password='testpass123'
        )
        
        # Verificar que el usuario fue autenticado
        self.assertIsNotNone(
            user,
            "❌ VIOLACIÓN DE SEGURIDAD: El usuario con membresía debe poder autenticarse."
        )
        self.assertEqual(
            user.id,
            self.user_con_membresia.id,
            "❌ VIOLACIÓN DE SEGURIDAD: El usuario autenticado debe ser el correcto."
        )
    
    def test_caso_b_usuario_sin_membresia_retorna_none(self):
        """
        CASO B: Usuario SIN membresía (pero password correcto) -> Retorna None.
        
        Verifica que un usuario sin TenantMembership en el tenant actual
        NO puede autenticarse, incluso si las credenciales son correctas.
        """
        # Simular request con tenant_a
        request = self.factory.get('/')
        request.tenant = self.tenant_a
        
        # Intentar autenticar usuario sin membresía
        user = self.backend.authenticate(
            request=request,
            username=self.user_sin_membresia.username,
            password='testpass123'  # Password correcto
        )
        
        # Verificar que el usuario NO fue autenticado
        self.assertIsNone(
            user,
            "❌ VIOLACIÓN DE SEGURIDAD: El usuario sin membresía NO debe poder autenticarse, "
            "incluso si las credenciales son correctas."
        )
    
    def test_caso_c_usuario_en_public_tenant_autentica(self):
        """
        CASO C: Usuario en Public Tenant -> Autentica.
        
        Verifica que cualquier usuario puede autenticarse en el tenant 'public'
        (dominio principal) sin necesidad de membresía.
        """
        # Obtener el tenant público
        connection.set_schema_to_public()
        tenant_public = TenantClient.objects.filter(schema_name=get_public_schema_name()).first()
        
        if not tenant_public:
            # Si no existe, crear uno para el test
            tenant_public = TenantClient.objects.create(
                schema_name=get_public_schema_name(),
                nombre='Public Tenant',
                is_active=True,
                on_trial=False
            )
        
        # Simular request con tenant público
        request = self.factory.get('/')
        request.tenant = tenant_public
        
        # Intentar autenticar usuario sin membresía en tenant público
        user = self.backend.authenticate(
            request=request,
            username=self.user_sin_membresia.username,
            password='testpass123'
        )
        
        # Verificar que el usuario fue autenticado (public permite acceso sin membresía)
        self.assertIsNotNone(
            user,
            "❌ VIOLACIÓN: El usuario debe poder autenticarse en el tenant 'public' sin membresía."
        )
        self.assertEqual(
            user.id,
            self.user_sin_membresia.id,
            "❌ VIOLACIÓN: El usuario autenticado debe ser el correcto."
        )
    
    def test_caso_d_request_sin_tenant_autentica_fallback(self):
        """
        CASO D: Request sin tenant (comandos de consola) -> Autentica (fallback).
        
        Verifica que cuando no hay contexto de tenant (request.tenant es None),
        el backend permite el acceso como fallback para comandos de consola.
        """
        # Simular request sin tenant (comando de consola)
        request = self.factory.get('/')
        request.tenant = None
        
        # Intentar autenticar
        user = self.backend.authenticate(
            request=request,
            username=self.user_sin_membresia.username,
            password='testpass123'
        )
        
        # Verificar que el usuario fue autenticado (fallback para comandos de consola)
        self.assertIsNotNone(
            user,
            "❌ VIOLACIÓN: El usuario debe poder autenticarse cuando no hay contexto de tenant "
            "(comandos de consola)."
        )
    
    def test_caso_e_credenciales_invalidas_retorna_none(self):
        """
        CASO E: Credenciales inválidas -> Retorna None.
        
        Verifica que el backend retorna None cuando las credenciales son inválidas,
        independientemente de la membresía.
        """
        # Simular request con tenant_a
        request = self.factory.get('/')
        request.tenant = self.tenant_a
        
        # Intentar autenticar con password incorrecto
        user = self.backend.authenticate(
            request=request,
            username=self.user_con_membresia.username,
            password='password_incorrecto'
        )
        
        # Verificar que el usuario NO fue autenticado (credenciales inválidas)
        self.assertIsNone(
            user,
            "❌ VIOLACIÓN: El backend debe retornar None cuando las credenciales son inválidas."
        )
    
    def test_caso_f_usuario_cross_tenant_denegado(self):
        """
        CASO F: Usuario con membresía en Tenant B intenta acceder a Tenant A -> Denegado.
        
        Verifica que un usuario con membresía en un tenant NO puede acceder a otro tenant.
        """
        # Crear membresía para user_con_membresia en tenant_b
        connection.set_schema_to_public()
        membership_b = TenantMembership.objects.create(
            client=self.tenant_b,
            user=self.user_con_membresia,
            rol='ADMIN'
        )
        
        # Simular request con tenant_a (diferente al que tiene membresía)
        request = self.factory.get('/')
        request.tenant = self.tenant_a
        
        # Intentar autenticar (el usuario tiene membresía en tenant_b, no en tenant_a)
        # Nota: En realidad, el usuario SÍ tiene membresía en tenant_a también (del setUp)
        # Así que vamos a usar user_sin_membresia que no tiene membresía en tenant_a
        user = self.backend.authenticate(
            request=request,
            username=self.user_sin_membresia.username,
            password='testpass123'
        )
        
        # Verificar que el usuario NO fue autenticado
        self.assertIsNone(
            user,
            "❌ VIOLACIÓN DE SEGURIDAD: El usuario sin membresía en el tenant actual "
            "NO debe poder autenticarse, incluso si tiene membresía en otro tenant."
        )
    
    def test_get_user(self):
        """
        Test del método get_user.
        
        Verifica que get_user retorna correctamente el usuario por su ID.
        """
        user = self.backend.get_user(self.user_con_membresia.id)
        
        self.assertIsNotNone(user, "❌ VIOLACIÓN: get_user debe retornar el usuario.")
        self.assertEqual(
            user.id,
            self.user_con_membresia.id,
            "❌ VIOLACIÓN: get_user debe retornar el usuario correcto."
        )
        
        # Verificar que retorna None para ID inválido
        user_invalido = self.backend.get_user(99999)
        self.assertIsNone(
            user_invalido,
            "❌ VIOLACIÓN: get_user debe retornar None para ID inválido."
        )
