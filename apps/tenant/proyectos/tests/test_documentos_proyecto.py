"""
Ciclo de Vida Controlado v4.0 - Expediente documental (Fase 44/46/49 mision).

CRUD de DocumentoProyecto, DSV multi-tenant, reemplazo automatico de tipos
de "unico vigente", y validacion de archivo (extension, tamano, firma
binaria real).
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django_tenants.utils import schema_context
from rest_framework.exceptions import ValidationError

from apps.tenant.proyectos.models import Proyecto, DocumentoProyecto
from apps.tenant.proyectos.services.documentos_service import (
    DocumentosBusinessService, validar_archivo,
)
from apps.tenant.empresa.models import Empresa

def _pdf(nombre='orden.pdf'):
    return SimpleUploadedFile(nombre, b'%PDF-1.4\n%contenido de prueba', content_type='application/pdf')


def _crear_proyecto(empresa):
    return Proyecto.objects.create(nombre='Proyecto Documentos', empresa=empresa, fase_actual='INICIO')


@pytest.mark.django_db
class TestValidarArchivo:

    def test_pdf_valido_pasa(self):
        validar_archivo(_pdf())  # no debe lanzar

    def test_extension_no_permitida_es_rechazada(self):
        archivo = SimpleUploadedFile('malware.exe', b'MZ\x90\x00', content_type='application/octet-stream')
        with pytest.raises(ValidationError):
            validar_archivo(archivo)

    def test_archivo_excesivamente_grande_es_rechazado(self):
        from apps.tenant.proyectos.services.documentos_service import TAMANO_MAXIMO_BYTES
        contenido = b'%PDF-1.4\n' + b'0' * (TAMANO_MAXIMO_BYTES + 1)
        archivo = SimpleUploadedFile('grande.pdf', contenido, content_type='application/pdf')
        with pytest.raises(ValidationError):
            validar_archivo(archivo)

    def test_extension_falsa_con_contenido_distinto_es_rechazada(self):
        """
        Extension .pdf declarada pero contenido real es texto plano -- la
        firma binaria (magic bytes) debe detectar el fraude, no solo confiar
        en el nombre del archivo.
        """
        archivo = SimpleUploadedFile('falso.pdf', b'esto no es un PDF real', content_type='application/pdf')
        with pytest.raises(ValidationError):
            validar_archivo(archivo)

    def test_xlsx_valido_pasa(self):
        archivo = SimpleUploadedFile(
            'cronograma.xlsx', b'PK\x03\x04resto-del-zip',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        validar_archivo(archivo)  # no debe lanzar


@pytest.mark.django_db
class TestDocumentosCRUD:

    def test_crear_documento(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)

            documento = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='AUTORIZACION', archivo=_pdf('autorizacion.pdf'),
            )

            assert documento.pk is not None
            assert documento.activo is True
            assert documento.empresa_id == proyecto.empresa_id
            assert documento.fase == proyecto.fase_actual

    def test_tipo_documento_invalido_es_rechazado(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)

            with pytest.raises(ValidationError):
                DocumentosBusinessService.crear_documento(
                    proyecto, tipo_documento='TIPO_INVENTADO', archivo=_pdf(),
                )

    def test_reemplazo_automatico_desactiva_el_anterior(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)

            doc_v1 = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='COTIZACION_APROBADA', archivo=_pdf('cotizacion_v1.pdf'),
            )
            doc_v2 = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='COTIZACION_APROBADA', archivo=_pdf('cotizacion_v2.pdf'),
            )

            doc_v1.refresh_from_db()
            assert doc_v1.activo is False, 'El documento viejo debe desactivarse, no borrarse.'
            assert doc_v2.activo is True
            assert DocumentoProyecto.objects.filter(
                proyecto=proyecto, tipo_documento='COTIZACION_APROBADA'
            ).count() == 2, 'El archivo viejo se conserva (soft), nunca se borra fisicamente.'

    def test_documento_ejecucion_admite_multiples_activos(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)

            doc1 = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='DOCUMENTO_EJECUCION', archivo=_pdf('bitacora1.pdf'),
            )
            doc2 = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='DOCUMENTO_EJECUCION', archivo=_pdf('bitacora2.pdf'),
            )

            doc1.refresh_from_db()
            assert doc1.activo is True, 'DOCUMENTO_EJECUCION no es de unico vigente -- no se desactiva.'
            assert doc2.activo is True

    def test_desactivar_documento_no_borra_el_archivo(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)
            documento = DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='AUTORIZACION', archivo=_pdf(),
            )

            DocumentosBusinessService.desactivar_documento(documento)

            documento.refresh_from_db()
            assert documento.activo is False
            assert documento.archivo.name  # el FileField sigue apuntando al archivo real

    def test_listar_documentos_solo_activos_por_defecto(self, tenant1):
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto = _crear_proyecto(empresa)
            DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='COTIZACION_APROBADA', archivo=_pdf('v1.pdf'),
            )
            DocumentosBusinessService.crear_documento(
                proyecto, tipo_documento='COTIZACION_APROBADA', archivo=_pdf('v2.pdf'),
            )

            activos = DocumentosBusinessService.listar_documentos(proyecto)
            todos = DocumentosBusinessService.listar_documentos(proyecto, solo_activos=False)

            assert activos.count() == 1
            assert todos.count() == 2


@pytest.mark.django_db
class TestDocumentosDSVMultiTenant:

    def test_documento_de_otro_proyecto_no_es_alcanzable_por_uuid(self, tenant1):
        """
        obtener_documento() exige proyecto=X ademas del uuid -- un UUID valido
        de OTRO proyecto (aunque exista) nunca debe resolverse para un
        proyecto distinto.
        """
        with schema_context(tenant1.schema_name):
            empresa = Empresa.objects.first()
            proyecto_a = _crear_proyecto(empresa)
            proyecto_b = Proyecto.objects.create(
                nombre='Proyecto B', empresa=empresa, fase_actual='INICIO'
            )
            documento_de_a = DocumentosBusinessService.crear_documento(
                proyecto_a, tipo_documento='AUTORIZACION', archivo=_pdf(),
            )

            resultado = DocumentosBusinessService.obtener_documento(proyecto_b, documento_de_a.uuid)

            assert resultado is None

    def test_documento_cross_tenant_no_es_alcanzable(self, tenant1, tenant2):
        with schema_context(tenant1.schema_name):
            empresa1 = Empresa.objects.first()
            proyecto1 = _crear_proyecto(empresa1)
            documento1 = DocumentosBusinessService.crear_documento(
                proyecto1, tipo_documento='AUTORIZACION', archivo=_pdf(),
            )
            documento1_uuid = documento1.uuid

        with schema_context(tenant2.schema_name):
            empresa2 = Empresa.objects.first()
            proyecto2 = _crear_proyecto(empresa2)

            resultado = DocumentosBusinessService.obtener_documento(proyecto2, documento1_uuid)

            assert resultado is None, (
                'Un documento de otro tenant (schema distinto) jamas deberia ser '
                'visible; ademas cada schema es una BD logica separada en Postgres.'
            )
