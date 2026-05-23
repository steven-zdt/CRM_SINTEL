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
        self.assertJSONResponse(res_del_fail, status.HTTP_400_BAD_REQUEST)
        
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
