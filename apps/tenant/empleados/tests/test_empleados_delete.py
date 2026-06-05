import uuid
from decimal import Decimal
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empleados.models import Empleado, Contrato, Devengo

@override_settings(ALLOWED_HOSTS=['*'])
class TestEmpleadoDeleteRecreate(TenantAPITestCase):

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
            'estado': 'ACTIVO'
        }

    def test_delete_and_recreate_empleado(self):
        # 1. Create Employee
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_post, status.HTTP_201_CREATED)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"

        # 2. Try to Delete (should fail since state is ACTIVO)
        res_del_fail = self.tdelete(url_detail)
        self.assertJSONResponse(res_del_fail, status.HTTP_409_CONFLICT)
        
        # 3. Change state to RETIRADO
        res_patch = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01'})
        self.assertJSONResponse(res_patch, status.HTTP_200_OK)
        
        # 4. Delete successfully
        res_del_ok = self.tdelete(url_detail)
        self.assertJSONResponse(res_del_ok, status.HTTP_200_OK)
        self.assertEqual(Empleado.objects.count(), 0)

        # 5. Recreate Employee with the same details
        res_recreate = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_recreate, status.HTTP_201_CREATED)

    def test_delete_fails_with_active_contract(self):
        # 1. Create Employee and transition to RETIRADO (but we will add an active contract)
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_post, status.HTTP_201_CREATED)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"

        res_patch = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01'})
        self.assertJSONResponse(res_patch, status.HTTP_200_OK)

        # 2. Create an active contract in tenant schema
        from django_tenants.utils import schema_context
        from apps.tenant.empresa.models import Empresa
        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            empleado = Empleado.objects.get(uuid=emp_uuid)
            Contrato.objects.create(
                empresa=empresa,
                empleado=empleado,
                tipo='INDEF',
                fecha_inicio='2023-01-01',
                salario_mensual=Decimal('2000000.00'),
                estado='ACTIVO',
                activo=True
            )

        # 3. Attempt to delete -> must fail with 409 Conflict
        res_del = self.tdelete(url_detail)
        self.assertJSONResponse(res_del, status.HTTP_409_CONFLICT)
        self.assertIn('contrato activo', str(res_del.data['detail']).lower())

    def test_delete_fails_with_active_payroll(self):
        # 1. Create Employee and transition to RETIRADO
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_post, status.HTTP_201_CREATED)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"

        res_patch = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01'})
        self.assertJSONResponse(res_patch, status.HTTP_200_OK)

        # 2. Create inactive contract and an active non-annulled payroll (Devengo) in tenant schema
        from django_tenants.utils import schema_context
        from apps.tenant.empresa.models import Empresa
        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            empleado = Empleado.objects.get(uuid=emp_uuid)
            contract = Contrato.objects.create(
                empresa=empresa,
                empleado=empleado,
                tipo='INDEF',
                fecha_inicio='2023-01-01',
                salario_mensual=Decimal('2000000.00'),
                estado='INACTIVO',
                activo=False
            )
            Devengo.objects.create(
                empresa=empresa,
                empleado=empleado,
                contrato=contract,
                periodo_mes='2023-12',
                fecha_pago='2023-12-30',
                salario_base=Decimal('2000000.00'),
                salud_empleado=Decimal('80000.00'),
                pension_empleado=Decimal('80000.00'),
                neto_pagar=Decimal('1840000.00'),
                anulado=False
            )

        # 3. Attempt to delete -> must fail with 409 Conflict
        res_del = self.tdelete(url_detail)
        self.assertJSONResponse(res_del, status.HTTP_409_CONFLICT)
        self.assertIn('nominas activas', str(res_del.data['detail']).lower())

    def test_delete_succeeds_with_inactive_contract_and_annulled_payroll(self):
        # 1. Create Employee and transition to RETIRADO
        res_post = self.tpost(self.url_list, data=self.valid_payload)
        self.assertJSONResponse(res_post, status.HTTP_201_CREATED)
        emp_uuid = res_post.data['uuid']
        url_detail = f"{self.url_list}{emp_uuid}/"

        res_patch = self.tpatch(url_detail, data={'estado': 'RETIRADO', 'fecha_retiro': '2024-01-01'})
        self.assertJSONResponse(res_patch, status.HTTP_200_OK)

        # 2. Create inactive contract and an annulled payroll (Devengo) in tenant schema
        from django_tenants.utils import schema_context
        from apps.tenant.empresa.models import Empresa
        with schema_context(self.tenant.schema_name):
            empresa = Empresa.objects.first()
            empleado = Empleado.objects.get(uuid=emp_uuid)
            contract = Contrato.objects.create(
                empresa=empresa,
                empleado=empleado,
                tipo='INDEF',
                fecha_inicio='2023-01-01',
                salario_mensual=Decimal('2000000.00'),
                estado='INACTIVO',
                activo=False
            )
            Devengo.objects.create(
                empresa=empresa,
                empleado=empleado,
                contrato=contract,
                periodo_mes='2023-12',
                fecha_pago='2023-12-30',
                salario_base=Decimal('2000000.00'),
                salud_empleado=Decimal('80000.00'),
                pension_empleado=Decimal('80000.00'),
                neto_pagar=Decimal('1840000.00'),
                anulado=True
            )

        # 3. Attempt to delete -> must succeed with 200 OK because contract is INACTIVO and payroll is annulled (anulado=True)
        res_del = self.tdelete(url_detail)
        self.assertJSONResponse(res_del, status.HTTP_200_OK)
        self.assertEqual(Empleado.objects.count(), 0)
