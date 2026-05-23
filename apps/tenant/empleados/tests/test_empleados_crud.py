import uuid
from decimal import Decimal
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Empleado, Contrato, Devengo
from apps.tenant.empresa.models import Empresa


@override_settings(ALLOWED_HOSTS=['*'])
class TestEmpleadoAPI(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_list = '/api/v1/empleados/'
        self.valid_payload = {
            'tipo_documento': 'CC',
            'numero_documento': '1234567890',
            'primer_nombre': 'Juan',
            'primer_apellido': 'Perez',
            'email': 'juan.perez@example.com',
            'eps': 'EPS001',
            'afp': 'AFP001',
            'arl': 'ARL001',
            'nivel_riesgo_arl': 'I',
            'fecha_ingreso': '2023-01-01',
        }

    def test_crear_empleado_exito(self):
        response = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data['numero_documento'], '1234567890')
        self.assertTrue('uuid' in response.data)
        self.assertEqual(Empleado.objects.count(), 1)

    def test_crear_empleado_duplicado(self):
        self.tpost(self.url_list, data=self.valid_payload)
        response = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero_documento', str(response.data))

    def test_listar_empleados(self):
        self.tpost(self.url_list, data=self.valid_payload)
        response = self.tget(self.url_list)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)
        self.assertEqual(response.data['count'], 1)

    def test_detalle_empleado(self):
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"
        response = self.tget(url_detail)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['numero_documento'], '1234567890')

    def test_actualizar_empleado(self):
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"

        update_data = {'primer_nombre': 'Carlos'}
        response = self.tpatch(url_detail, data=update_data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['primer_nombre'], 'Carlos')
        # cuenta_contable_uuid movido a Devengo (Fase1 refactor)

    def test_uuid_read_only(self):
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"
        
        new_uuid = str(uuid.uuid4())
        update_data = {'uuid': new_uuid}
        response = self.tpatch(url_detail, data=update_data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        # El UUID no debe haber cambiado
        self.assertNotEqual(response.data['uuid'], new_uuid)

    def test_tenant_isolation(self):
        # Crear la entidad en el primer tenant
        self.tpost(self.url_list, data=self.valid_payload)
        
        # Testear con un segundo tenant para probar DSV cross-tenant isolation
        from django_tenants.utils import schema_context
        from apps.public.tenants.models import Client
        
        with schema_context('public'):
            tenant2 = Client.objects.create(
                schema_name='tenant2_test',
                nombre='Tenant 2',
                paid_until='2030-01-01',
                on_trial=False
            )
        
        with schema_context(tenant2.schema_name):
            empresa2 = Empresa.objects.create(
                razon_social='Empresa 2',
                nit='888888888',
                dv='8',
                direccion='Calle 2'
            )
            
        def create_empleado_isolated():
            empresa = Empresa.objects.first()
            print(f"DEBUG TENANT ISOLATION - Empresa actual: {empresa}")
            return Empleado.objects.create(
                empresa=empresa,
                tipo_documento='CC',
                numero_documento=str(uuid.uuid4().int)[:10],
                primer_nombre='A',
                primer_apellido='B',
                email='test@example.com',
                fecha_ingreso='2023-01-01',
                eps='EPS001',
                afp='AFP001',
                arl='ARL001',
                nivel_riesgo_arl='I'
            )
            
        self.assertTenantIsolation(
            self.tenant, 
            tenant2, 
            Empleado, 
            create_empleado_isolated
        )


@override_settings(ALLOWED_HOSTS=['*'])
class TestContratoAPI(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_empleados = '/api/v1/empleados/'
        self.url_contratos = '/api/v1/empleados/contratos/'
        
        empleado_payload = {
            'tipo_documento': 'CC',
            'numero_documento': '1234567890',
            'primer_nombre': 'Juan',
            'primer_apellido': 'Perez',
            'email': 'juan.perez@example.com',
            'fecha_ingreso': '2023-01-01',
            'eps': 'EPS001',
            'afp': 'AFP001',
            'arl': 'ARL001',
        }
        res_emp = self.tpost(self.url_empleados, data=empleado_payload)
        self.empleado_id = res_emp.data['id']
        self.empleado_uuid = res_emp.data['uuid']
        
        self.valid_payload = {
            'empleado': self.empleado_id,
            'tipo': 'INDEF',
            'salario_mensual': 2000000.00,
            'fecha_inicio': '2024-01-01',
            'cargo': 'Desarrollador',
            'estado': 'ACTIVO'
        }

    def test_crear_contrato_exito(self):
        response = self.tpost(self.url_contratos, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertEqual(Contrato.objects.count(), 1)
        self.assertTrue(response.data['activo'])

    def test_crear_multiples_contratos_activos_falla(self):
        self.tpost(self.url_contratos, data=self.valid_payload)
        response = self.tpost(self.url_contratos, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empleado', str(response.data))

    def test_actualizar_estado_contrato(self):
        res_post = self.tpost(self.url_contratos, data=self.valid_payload)
        contrato_uuid = res_post.data['uuid']
        url_detail = f"{self.url_contratos}{contrato_uuid}/"
        
        update_data = {'estado': 'INACTIVO', 'fecha_fin': '2024-12-31'}
        response = self.tpatch(url_detail, data=update_data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'INACTIVO')
        self.assertFalse(response.data['activo'])


@override_settings(ALLOWED_HOSTS=['*'])
class TestDevengoAPI(TenantAPITestCase):

    def setUp(self):
        super().setUp()
        self.url_empleados = '/api/v1/empleados/'
        self.url_contratos = '/api/v1/empleados/contratos/'
        self.url_devengos = '/api/v1/empleados/devengos/'
        
        empleado_payload = {
            'tipo_documento': 'CC',
            'numero_documento': '1234567890',
            'primer_nombre': 'Juan',
            'primer_apellido': 'Perez',
            'email': 'juan.perez@example.com',
            'fecha_ingreso': '2023-01-01',
            'eps': 'EPS001',
            'afp': 'AFP001',
            'arl': 'ARL001',
        }
        res_emp = self.tpost(self.url_empleados, data=empleado_payload)
        self.empleado_id = res_emp.data['id']
        
        contrato_payload = {
            'empleado': self.empleado_id,
            'tipo': 'INDEF',
            'salario_mensual': 2000000.00,
            'fecha_inicio': '2024-01-01',
            'cargo': 'Desarrollador',
            'estado': 'ACTIVO'
        }
        res_cont = self.tpost(self.url_contratos, data=contrato_payload)
        self.contrato_id = res_cont.data['id']
        
        self.valid_payload = {
            'empleado': self.empleado_id,
            'contrato': self.contrato_id,
            'periodo_mes': '2024-01',
            'fecha_pago': '2024-01-30',
            'dias_laborados': 30,
        }

    def test_crear_devengo_exito(self):
        response = self.tpost(self.url_devengos, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertEqual(Devengo.objects.count(), 1)
        
        # Validar cálculos read-only (Zero Trust)
        self.assertIn('salario_base', response.data)
        self.assertIn('salud_empleado', response.data)
        self.assertIn('pension_empleado', response.data)
        self.assertIn('neto_pagar', response.data)
        
        # Salario de 2,000,000 por 30 dias -> 2,000,000
        # Salud y pensión (4% c/u) -> 80,000 c/u
        # Neto: 2,000,000 - 160,000 = 1,840,000
        self.assertEqual(Decimal(response.data['salario_base']), Decimal('2000000.00'))
        self.assertEqual(Decimal(response.data['neto_pagar']), Decimal('1840000.00'))

    def test_crear_devengo_duplicado_falla(self):
        self.tpost(self.url_devengos, data=self.valid_payload)
        response = self.tpost(self.url_devengos, data=self.valid_payload)
        self.assertJSONResponse(response, status.HTTP_409_CONFLICT)
        self.assertIn('error', str(response.data).lower())

    def test_valores_calculados_no_modificables(self):
        # Intentar inyectar valores manipulados desde frontend
        payload = self.valid_payload.copy()
        payload['salario_base'] = '9999999.00'
        payload['neto_pagar'] = '9999999.00'
        
        response = self.tpost(self.url_devengos, data=payload)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        
        # El backend debe haber ignorado la inyección y calculado el valor correcto
        self.assertEqual(Decimal(response.data['salario_base']), Decimal('2000000.00'))
        self.assertEqual(Decimal(response.data['neto_pagar']), Decimal('1840000.00'))
