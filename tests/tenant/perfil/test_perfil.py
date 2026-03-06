"""
Tests para la app de Perfil Privado del Colaborador.

Escenarios validados:
- Test A: Crear un perfil vía Service Layer
- Test B: Consumir endpoint /me/ y verificar que devuelve los datos combinados (User global + Perfil local)
- Test C: Verificar que los datos del perfil en el Tenant A son diferentes a los del Tenant B para el mismo usuario (Aislamiento)
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.tenant.perfil.models import TenantProfile
from apps.services.perfil.perfil_service import obtener_o_crear_perfil, actualizar_configuracion_ui

User = get_user_model()


class TestPerfilService(SintelTenantTestCase):
    """
    Tests para el servicio de perfil (Service Layer).
    
    Valida que la lógica de negocio funciona correctamente:
    - obtener_o_crear_perfil crea perfiles cuando no existen
    - obtener_o_crear_perfil retorna perfiles existentes
    - actualizar_configuracion_ui actualiza la configuración de forma segura
    """
    
    def test_a_crear_perfil_via_service_layer(self):
        """
        TEST A: Crear un perfil vía Service Layer.
        
        Verifica que el servicio `obtener_o_crear_perfil` crea correctamente
        un perfil cuando no existe, usando valores por defecto.
        """
        # Verificar que el perfil no existe inicialmente
        perfil_existente = TenantProfile.objects.filter(user=self.user).first()
        self.assertIsNone(
            perfil_existente,
            "❌ VIOLACIÓN: El perfil no debería existir antes de llamar al servicio."
        )
        
        # Crear el perfil usando el servicio
        perfil = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Contador Senior',
                'departamento': 'Finanzas',
                'telefono_corporativo': '6012345678'
            }
        )
        
        # Verificar que el perfil fue creado
        self.assertIsNotNone(perfil, "❌ VIOLACIÓN: El servicio debe crear el perfil si no existe.")
        self.assertEqual(perfil.user, self.user, "❌ VIOLACIÓN: El perfil debe estar asociado al usuario correcto.")
        self.assertEqual(perfil.cargo, 'Contador Senior', "❌ VIOLACIÓN: El cargo debe ser el especificado.")
        self.assertEqual(perfil.departamento, 'Finanzas', "❌ VIOLACIÓN: El departamento debe ser el especificado.")
        self.assertEqual(perfil.telefono_corporativo, '6012345678', "❌ VIOLACIÓN: El teléfono debe ser el especificado.")
        
        # Verificar que el perfil tiene configuración por defecto (dict vacío)
        self.assertIsInstance(perfil.configuracion, dict, "❌ VIOLACIÓN: La configuración debe ser un diccionario.")
    
    def test_a_obtener_perfil_existente_via_service_layer(self):
        """
        TEST A (Extensión): Obtener perfil existente vía Service Layer.
        
        Verifica que el servicio `obtener_o_crear_perfil` retorna el perfil
        existente en lugar de crear uno nuevo.
        """
        # Crear un perfil manualmente
        perfil_original = TenantProfile.objects.create(
            user=self.user,
            cargo='Contador Senior',
            departamento='Finanzas'
        )
        
        # Obtener el perfil usando el servicio
        perfil = obtener_o_crear_perfil(self.user)
        
        # Verificar que es el mismo perfil (mismo ID)
        self.assertEqual(
            perfil.id,
            perfil_original.id,
            "❌ VIOLACIÓN: El servicio debe retornar el perfil existente, no crear uno nuevo."
        )
        self.assertEqual(perfil.cargo, 'Contador Senior', "❌ VIOLACIÓN: El cargo debe ser el del perfil existente.")
    
    def test_a_actualizar_configuracion_ui(self):
        """
        TEST A (Extensión): Actualizar configuración de UI.
        
        Verifica que el servicio `actualizar_configuracion_ui` actualiza
        la configuración de forma segura, preservando valores existentes.
        """
        # Crear un perfil con configuración inicial
        perfil = obtener_o_crear_perfil(self.user)
        perfil.configuracion = {'modo_oscuro': False, 'densidad_tablas': 'normal'}
        perfil.save()
        
        # Actualizar una clave específica (merge=True)
        perfil_actualizado = actualizar_configuracion_ui(
            self.user,
            'modo_oscuro',
            True,
            merge=True
        )
        
        # Verificar que la configuración fue actualizada correctamente
        self.assertEqual(
            perfil_actualizado.configuracion['modo_oscuro'],
            True,
            "❌ VIOLACIÓN: La configuración debe actualizar la clave especificada."
        )
        self.assertEqual(
            perfil_actualizado.configuracion['densidad_tablas'],
            'normal',
            "❌ VIOLACIÓN: La configuración debe preservar valores existentes cuando merge=True."
        )


class TestPerfilAPI(SintelTenantTestCase):
    """
    Tests para la API de perfil.
    
    Valida que los endpoints funcionan correctamente:
    - GET /api/v1/perfil/me/ retorna el perfil del usuario actual
    - PATCH /api/v1/perfil/me/ actualiza el perfil del usuario actual
    - Los datos incluyen información del User global (nested)
    """
    
    def test_b_consumir_endpoint_me_y_verificar_datos_combinados(self):
        """
        TEST B: Consumir endpoint /me/ y verificar que devuelve los datos combinados.
        
        Verifica que el endpoint GET /api/v1/perfil/me/ retorna:
        - Datos del perfil (cargo, departamento, etc.)
        - Datos del User global (email, username, first_name, last_name) como campos de solo lectura
        """
        # Crear un perfil para el usuario
        perfil = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Contador Senior',
                'departamento': 'Finanzas',
                'telefono_corporativo': '6012345678'
            }
        )
        
        # Hacer GET al endpoint /me/
        # DRF genera el nombre de URL como {basename}-{url_name} = 'perfil-me'
        url = '/api/v1/perfil/perfiles/me/'
        response = self.api_client.get(url)
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(
            response.status_code,
            200,
            f"❌ VIOLACIÓN: El endpoint debe retornar 200 OK. Status recibido: {response.status_code}"
        )
        
        # Verificar que los datos del perfil están presentes
        data = response.json()
        self.assertIn('id', data, "❌ VIOLACIÓN: La respuesta debe incluir el ID del perfil.")
        self.assertIn('cargo', data, "❌ VIOLACIÓN: La respuesta debe incluir el cargo.")
        self.assertEqual(data['cargo'], 'Contador Senior', "❌ VIOLACIÓN: El cargo debe ser el correcto.")
        self.assertEqual(data['departamento'], 'Finanzas', "❌ VIOLACIÓN: El departamento debe ser el correcto.")
        self.assertEqual(data['telefono_corporativo'], '6012345678', "❌ VIOLACIÓN: El teléfono debe ser el correcto.")
        
        # Verificar que los datos del User global están presentes (nested)
        self.assertIn('user_id', data, "❌ VIOLACIÓN: La respuesta debe incluir user_id.")
        self.assertIn('user_email', data, "❌ VIOLACIÓN: La respuesta debe incluir user_email.")
        self.assertIn('user_username', data, "❌ VIOLACIÓN: La respuesta debe incluir user_username.")
        self.assertEqual(data['user_email'], self.user.email, "❌ VIOLACIÓN: El email debe ser el del usuario actual.")
        self.assertEqual(data['user_username'], self.user.username, "❌ VIOLACIÓN: El username debe ser el del usuario actual.")
    
    def test_b_actualizar_perfil_via_endpoint_me(self):
        """
        TEST B (Extensión): Actualizar perfil vía endpoint /me/.
        
        Verifica que el endpoint PATCH /api/v1/perfil/me/ actualiza
        correctamente el perfil del usuario actual.
        """
        # Crear un perfil inicial
        perfil = obtener_o_crear_perfil(self.user, defaults={'cargo': 'Colaborador'})
        
        # Actualizar el perfil vía PATCH
        url = '/api/v1/perfil/perfiles/me/'
        response = self.api_client.patch(
            url,
            {
                'cargo': 'Contador Senior',
                'departamento': 'Finanzas',
                'telefono_corporativo': '6012345678'
            },
            format='json'
        )
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(
            response.status_code,
            200,
            f"❌ VIOLACIÓN: El endpoint debe retornar 200 OK. Status recibido: {response.status_code}"
        )
        
        # Verificar que los datos fueron actualizados
        data = response.json()
        self.assertEqual(data['cargo'], 'Contador Senior', "❌ VIOLACIÓN: El cargo debe ser actualizado.")
        self.assertEqual(data['departamento'], 'Finanzas', "❌ VIOLACIÓN: El departamento debe ser actualizado.")
        self.assertEqual(data['telefono_corporativo'], '6012345678', "❌ VIOLACIÓN: El teléfono debe ser actualizado.")
        
        # Verificar en la base de datos
        perfil.refresh_from_db()
        self.assertEqual(perfil.cargo, 'Contador Senior', "❌ VIOLACIÓN: El cargo debe estar actualizado en la BD.")
        self.assertEqual(perfil.departamento, 'Finanzas', "❌ VIOLACIÓN: El departamento debe estar actualizado en la BD.")


class TestPerfilAislamiento(SintelTenantTestCase):
    """
    Tests de aislamiento de perfiles entre tenants.
    
    Valida que los perfiles están correctamente aislados:
    - El mismo usuario puede tener diferentes perfiles en diferentes tenants
    - Los datos del perfil en Tenant A son diferentes a los del Tenant B
    """
    
    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """
        Crea un tenant específico para estos tests de aislamiento.
        """
        tenant = TenantClient.objects.create(
            schema_name='tenant_a_perfil',
            nombre='Tenant A - Tests de Aislamiento',
            is_active=True,
            on_trial=False
        )
        return tenant
    
    @classmethod
    def setup_domain(cls, domain):
        """
        Configura el dominio para Tenant A.
        """
        domain.domain = 'tenant-a-perfil.sintel.local'
        domain.is_primary = True
        domain.save()
        return domain
    
    def setUp(self):
        """
        Setup: Crear usuarios y membresías para los tests.
        """
        # Llamar al setUp del padre (crea tenant_a_perfil, domain, user, membership)
        super().setUp()
        
        # Crear un segundo tenant (Tenant B) para tests de aislamiento
        connection.set_schema_to_public()
        
        self.tenant_b = TenantClient.objects.create(
            schema_name='tenant_b_perfil',
            nombre='Tenant B - Tests de Aislamiento',
            is_active=True,
            on_trial=False
        )
        
        self.domain_b = Domain.objects.create(
            domain='tenant-b-perfil.sintel.local',
            tenant=self.tenant_b,
            is_primary=True
        )
        
        # Crear membresía del usuario en Tenant B
        self.membership_b = TenantMembership.objects.create(
            client=self.tenant_b,
            user=self.user,
            rol='ADMIN'
        )
        
        # Restaurar esquema del tenant_a_perfil
        connection.set_schema(self.tenant.schema_name)
        
        # Crear cliente API para Tenant B
        from rest_framework.test import APIClient
        self.api_client_b = APIClient(HTTP_HOST=self.domain_b.domain)
        self.api_client_b.force_authenticate(user=self.user)
    
    def test_c_verificar_aislamiento_entre_tenants(self):
        """
        TEST C: Verificar que los datos del perfil en el Tenant A son diferentes a los del Tenant B.
        
        Valida que:
        - El mismo usuario puede tener diferentes perfiles en diferentes tenants
        - Los datos del perfil en Tenant A son independientes de los del Tenant B
        """
        # Crear perfil en Tenant A
        connection.set_schema(self.tenant.schema_name)
        perfil_a = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Contador Senior',
                'departamento': 'Finanzas',
                'telefono_corporativo': '6012345678'
            }
        )
        
        # Crear perfil en Tenant B (con datos diferentes)
        connection.set_schema(self.tenant_b.schema_name)
        perfil_b = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Auxiliar Administrativo',
                'departamento': 'RRHH',
                'telefono_corporativo': '6098765432'
            }
        )
        
        # Verificar que son perfiles diferentes (diferentes IDs)
        self.assertNotEqual(
            perfil_a.id,
            perfil_b.id,
            "❌ VIOLACIÓN DE AISLAMIENTO: Los perfiles en diferentes tenants deben tener IDs diferentes."
        )
        
        # Verificar que los datos son diferentes
        self.assertNotEqual(
            perfil_a.cargo,
            perfil_b.cargo,
            "❌ VIOLACIÓN DE AISLAMIENTO: Los cargos deben ser diferentes en diferentes tenants."
        )
        self.assertNotEqual(
            perfil_a.departamento,
            perfil_b.departamento,
            "❌ VIOLACIÓN DE AISLAMIENTO: Los departamentos deben ser diferentes en diferentes tenants."
        )
        self.assertNotEqual(
            perfil_a.telefono_corporativo,
            perfil_b.telefono_corporativo,
            "❌ VIOLACIÓN DE AISLAMIENTO: Los teléfonos deben ser diferentes en diferentes tenants."
        )
        
        # Verificar que consultar desde Tenant A solo retorna el perfil de Tenant A
        connection.set_schema(self.tenant.schema_name)
        perfiles_en_a = TenantProfile.objects.filter(user=self.user)
        self.assertEqual(
            perfiles_en_a.count(),
            1,
            "❌ VIOLACIÓN DE AISLAMIENTO: En Tenant A solo debe existir un perfil para este usuario."
        )
        self.assertEqual(
            perfiles_en_a.first().cargo,
            'Contador Senior',
            "❌ VIOLACIÓN DE AISLAMIENTO: El perfil en Tenant A debe tener el cargo correcto."
        )
        
        # Verificar que consultar desde Tenant B solo retorna el perfil de Tenant B
        connection.set_schema(self.tenant_b.schema_name)
        perfiles_en_b = TenantProfile.objects.filter(user=self.user)
        self.assertEqual(
            perfiles_en_b.count(),
            1,
            "❌ VIOLACIÓN DE AISLAMIENTO: En Tenant B solo debe existir un perfil para este usuario."
        )
        self.assertEqual(
            perfiles_en_b.first().cargo,
            'Auxiliar Administrativo',
            "❌ VIOLACIÓN DE AISLAMIENTO: El perfil en Tenant B debe tener el cargo correcto."
        )
    
    def test_c_verificar_aislamiento_via_api(self):
        """
        TEST C (Extensión): Verificar aislamiento vía API.
        
        Valida que los endpoints de API retornan datos diferentes
        para el mismo usuario en diferentes tenants.
        """
        # Crear perfil en Tenant A
        connection.set_schema(self.tenant.schema_name)
        perfil_a = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Contador Senior',
                'departamento': 'Finanzas'
            }
        )
        
        # Crear perfil en Tenant B
        connection.set_schema(self.tenant_b.schema_name)
        perfil_b = obtener_o_crear_perfil(
            self.user,
            defaults={
                'cargo': 'Auxiliar Administrativo',
                'departamento': 'RRHH'
            }
        )
        
        # Consultar endpoint /me/ en Tenant A
        connection.set_schema(self.tenant.schema_name)
        url = '/api/v1/perfil/perfiles/me/'
        response_a = self.api_client.get(url)
        self.assertEqual(response_a.status_code, 200)
        data_a = response_a.json()
        
        # Consultar endpoint /me/ en Tenant B
        connection.set_schema(self.tenant_b.schema_name)
        url_b = '/api/v1/perfil/perfiles/me/'
        response_b = self.api_client_b.get(url_b)
        self.assertEqual(response_b.status_code, 200)
        data_b = response_b.json()
        
        # Verificar que los datos son diferentes
        self.assertNotEqual(
            data_a['cargo'],
            data_b['cargo'],
            "❌ VIOLACIÓN DE AISLAMIENTO: Los cargos deben ser diferentes en diferentes tenants (API)."
        )
        self.assertNotEqual(
            data_a['departamento'],
            data_b['departamento'],
            "❌ VIOLACIÓN DE AISLAMIENTO: Los departamentos deben ser diferentes en diferentes tenants (API)."
        )
        
        # Verificar que el user_email es el mismo (usuario global)
        self.assertEqual(
            data_a['user_email'],
            data_b['user_email'],
            "❌ VIOLACIÓN: El email del usuario global debe ser el mismo en ambos tenants."
        )
