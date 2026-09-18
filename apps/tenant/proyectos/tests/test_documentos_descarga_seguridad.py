"""
Ciclo de Vida Controlado v4.0 - Descarga segura de documentos (Fase 7/49 mision).

El storage de DocumentoProyecto es privado (PRIVATE_MEDIA_ROOT, fuera de
MEDIA_ROOT/nginx publico) -- la UNICA forma soportada de leer el archivo es
el endpoint autenticado `.../documentos/{uuid}/descargar/`, que debe:
1. Servir el contenido real para el tenant/proyecto dueno.
2. Dar 404 (nunca el archivo) si el uuid pertenece a otro proyecto.
3. Dar 404 (nunca el archivo) si el uuid pertenece a otro tenant.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenant.proyectos.models import Proyecto
from apps.tenant.proyectos.services.documentos_service import DocumentosBusinessService
from apps.tenant.empresa.models import Empresa
from apps.public.accounts.models import User


def _pdf(nombre='autorizacion.pdf', contenido=b'%PDF-1.4\ncontenido real de prueba'):
    return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')


def _crear_usuario_admin(tenant, email):
    with schema_context('public'):
        user = User.objects.create_user(email=email, password='test123')
        from apps.public.tenants.models import TenantMembership
        TenantMembership.objects.update_or_create(
            client=tenant, user=user,
            defaults={'rol': 'ADMIN', 'is_active': True, 'is_primary_admin': True},
        )
    with schema_context(tenant.schema_name):
        from apps.tenant.perfil.models import TenantProfile
        empresa = Empresa.objects.first()
        TenantProfile.objects.create(user=user, empresa=empresa, rol='ADMIN')
    return user


@pytest.mark.django_db
class TestDescargaSegura:

    @pytest.fixture(autouse=True)
    def setup(self, tenant1, tenant2):
        self.tenant1 = tenant1
        self.tenant2 = tenant2
        self.user1 = _crear_usuario_admin(tenant1, 'descarga-doc-t1@test.com')
        self.user2 = _crear_usuario_admin(tenant2, 'descarga-doc-t2@test.com')

    def test_descarga_valida_devuelve_el_archivo_real(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Descarga', empresa=empresa, fase_actual='INICIO'
            )
            documento = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='AUTORIZACION',
                archivo=_pdf(contenido=b'%PDF-1.4\ncontenido-unico-12345'),
            )
            proyecto_uuid, documento_uuid = proyecto.uuid, documento.uuid

        client = APIClient()
        client.force_authenticate(user=self.user1)
        response = client.get(
            f'/api/v1/proyectos/{proyecto_uuid}/documentos/{documento_uuid}/descargar/',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )

        assert response.status_code == status.HTTP_200_OK
        contenido = b''.join(response.streaming_content) if response.streaming else response.content
        assert b'contenido-unico-12345' in contenido

    def test_documento_de_otro_proyecto_da_404(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto_a = Proyecto.objects.create(
                nombre='Proyecto A', empresa=empresa, fase_actual='INICIO'
            )
            proyecto_b = Proyecto.objects.create(
                nombre='Proyecto B', empresa=empresa, fase_actual='INICIO'
            )
            documento_de_a = DocumentosBusinessService.crear_documento(
                proyecto_a, tipo_documento='AUTORIZACION', archivo=_pdf(),
            )
            proyecto_b_uuid, documento_uuid = proyecto_b.uuid, documento_de_a.uuid

        client = APIClient()
        client.force_authenticate(user=self.user1)
        response = client.get(
            f'/api/v1/proyectos/{proyecto_b_uuid}/documentos/{documento_uuid}/descargar/',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_documento_cross_tenant_da_404(self, tenant1, tenant2):
        with schema_context(tenant1.schema_name):
            empresa1 = Empresa.objects.first()
            proyecto1 = Proyecto.objects.create(
                nombre='Proyecto Tenant1', empresa=empresa1, fase_actual='INICIO'
            )
            documento1 = DocumentosBusinessService.crear_documento(
                proyecto1, tipo_documento='AUTORIZACION', archivo=_pdf(),
            )
            documento1_uuid = documento1.uuid

        with schema_context(tenant2.schema_name):
            empresa2 = Empresa.objects.first()
            proyecto2 = Proyecto.objects.create(
                nombre='Proyecto Tenant2', empresa=empresa2, fase_actual='INICIO'
            )
            proyecto2_uuid = proyecto2.uuid

        client = APIClient()
        client.force_authenticate(user=self.user2)
        response = client.get(
            f'/api/v1/proyectos/{proyecto2_uuid}/documentos/{documento1_uuid}/descargar/',
            HTTP_HOST=f'{tenant2.schema_name}.sintel.net.co',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_subida_via_api_y_descarga_end_to_end(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto E2E', empresa=empresa, fase_actual='INICIO'
            )
            proyecto_uuid = proyecto.uuid

        client = APIClient()
        client.force_authenticate(user=self.user1)

        response_subida = client.post(
            f'/api/v1/proyectos/{proyecto_uuid}/documentos/',
            {'tipo_documento': 'AUTORIZACION', 'archivo': _pdf(contenido=b'%PDF-1.4\ne2e-content')},
            format='multipart',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )
        assert response_subida.status_code == status.HTTP_201_CREATED, response_subida.data
        documento_uuid = response_subida.data['uuid']

        response_lista = client.get(
            f'/api/v1/proyectos/{proyecto_uuid}/documentos/',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )
        assert response_lista.status_code == status.HTTP_200_OK
        assert len(response_lista.data) == 1
        assert 'archivo' not in response_lista.data[0], (
            'El listado no debe exponer la ruta fisica del archivo -- solo metadatos.'
        )

        response_descarga = client.get(
            f'/api/v1/proyectos/{proyecto_uuid}/documentos/{documento_uuid}/descargar/',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )
        assert response_descarga.status_code == status.HTTP_200_OK

    def test_subida_con_archivo_invalido_es_rechazada_400(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Rechazo', empresa=empresa, fase_actual='INICIO'
            )
            proyecto_uuid = proyecto.uuid

        client = APIClient()
        client.force_authenticate(user=self.user1)
        archivo_falso = SimpleUploadedFile('malware.exe', b'MZ\x90\x00', content_type='application/octet-stream')

        response = client.post(
            f'/api/v1/proyectos/{proyecto_uuid}/documentos/',
            {'tipo_documento': 'AUTORIZACION', 'archivo': archivo_falso},
            format='multipart',
            HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
