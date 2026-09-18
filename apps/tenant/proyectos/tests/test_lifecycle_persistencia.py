"""
Ciclo de Vida Controlado v4.0 - Persistencia real (Fase 47 de la mision).

Mismo criterio que el ya establecido en test_avanzar_fase_persistencia.py:
nunca confiar en el body 200 de la respuesta como evidencia de que algo
quedo en Postgres -- siempre releer con Proyecto.objects.get() despues.
Aqui se repite el patron para las 4 transiciones reales del ciclo de vida,
con los documentos requeridos ya cargados.
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework import status

from apps.tenant.proyectos.models import Proyecto, DocumentoProyecto, HistorialFaseProyecto
from apps.tenant.empresa.models import Empresa
from apps.public.accounts.models import User


def _doc(proyecto, tipo, fase):
    return DocumentoProyecto.objects.create(
        proyecto=proyecto, empresa_id=proyecto.empresa_id, fase=fase, tipo_documento=tipo, activo=True,
    )


@pytest.mark.django_db
class TestLifecyclePersistencia:

    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        self.tenant = tenant1
        with schema_context('public'):
            self.user = User.objects.create_user(email='lifecycle-persist@test.com', password='test123')
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.update_or_create(
                client=self.tenant, user=self.user,
                defaults={'rol': 'ADMIN', 'is_active': True, 'is_primary_admin': True},
            )
        with schema_context(self.tenant.schema_name):
            from apps.tenant.perfil.models import TenantProfile
            self.empresa = Empresa.objects.first()
            TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol='ADMIN')

    def _avanzar(self, client, proyecto_uuid, fase):
        return client.post(
            f'/api/v1/proyectos/{proyecto_uuid}/avanzar-fase/',
            {'fase': fase}, format='json',
            HTTP_HOST=f'{self.tenant.schema_name}.sintel.net.co',
        )

    def test_ciclo_completo_persiste_cada_transicion_en_bd(self, tenant1):
        with schema_context(tenant1.schema_name):
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Ciclo Completo', empresa=self.empresa, fase_actual='BORRADOR',
            )
            proyecto_uuid = proyecto.uuid

            client = APIClient()
            client.force_authenticate(user=self.user)

            # BORRADOR -> INICIO (sin gate documental)
            r1 = self._avanzar(client, proyecto_uuid, 'INICIO')
            assert r1.status_code == status.HTTP_200_OK, r1.data
            assert Proyecto.objects.get(pk=proyecto.pk).fase_actual == 'INICIO'

            # INICIO -> PLANEACION (requiere expediente de inicio)
            _doc(proyecto, 'ORDEN_COMPRA', 'INICIO')
            _doc(proyecto, 'AUTORIZACION', 'INICIO')
            _doc(proyecto, 'COTIZACION_APROBADA', 'INICIO')
            r2 = self._avanzar(client, proyecto_uuid, 'PLANEACION')
            assert r2.status_code == status.HTTP_200_OK, r2.data
            assert Proyecto.objects.get(pk=proyecto.pk).fase_actual == 'PLANEACION'

            # PLANEACION -> EJECUCION (requiere acta + cronograma)
            _doc(proyecto, 'ACTA_INICIO', 'PLANEACION')
            _doc(proyecto, 'CRONOGRAMA', 'PLANEACION')
            r3 = self._avanzar(client, proyecto_uuid, 'EJECUCION')
            assert r3.status_code == status.HTTP_200_OK, r3.data
            assert Proyecto.objects.get(pk=proyecto.pk).fase_actual == 'EJECUCION'

            # EJECUCION -> CIERRE (requiere acta de entrega + informe final)
            _doc(proyecto, 'ACTA_ENTREGA', 'EJECUCION')
            _doc(proyecto, 'INFORME_FINAL', 'EJECUCION')
            r4 = self._avanzar(client, proyecto_uuid, 'CIERRE')
            assert r4.status_code == status.HTTP_200_OK, r4.data
            assert Proyecto.objects.get(pk=proyecto.pk).fase_actual == 'CIERRE'

            # El historial debe reflejar las 4 transiciones reales, en orden,
            # cada una releida de BD (no del objeto en memoria de la vista).
            historial = list(
                HistorialFaseProyecto.objects.filter(proyecto=proyecto).order_by('created_at')
            )
            assert [h.fase_nueva for h in historial] == ['INICIO', 'PLANEACION', 'EJECUCION', 'CIERRE']
            assert [h.fase_anterior for h in historial] == ['BORRADOR', 'INICIO', 'PLANEACION', 'EJECUCION']

    def test_avanza_sin_documentos_y_persiste(self, tenant1):
        """
        2026-09-18: el checklist documental dejo de ser un gate bloqueante.
        Un proyecto sin ningun documento cargado DEBE poder avanzar de fase y
        persistir el cambio + su historial (antes devolvia 400
        "missing_documents" y dejaba el proyecto atascado).
        """
        with schema_context(tenant1.schema_name):
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Sin Documentos', empresa=self.empresa, fase_actual='INICIO',
            )
            proyecto_uuid = proyecto.uuid

            client = APIClient()
            client.force_authenticate(user=self.user)

            response = self._avanzar(client, proyecto_uuid, 'PLANEACION')

            assert response.status_code == status.HTTP_200_OK, response.data

            proyecto_en_bd = Proyecto.objects.get(pk=proyecto.pk)
            assert proyecto_en_bd.fase_actual == 'PLANEACION'
            assert HistorialFaseProyecto.objects.filter(proyecto=proyecto).count() == 1

    def test_transicion_no_adyacente_no_persiste_nada(self, tenant1):
        """
        La maquina de estados SI sigue siendo estricta: un salto de fase
        (INICIO -> CIERRE) se rechaza con 400 y no deja efectos parciales.
        Es la unica clase de bloqueo que queda tras volver opcionales los
        documentos.
        """
        with schema_context(tenant1.schema_name):
            proyecto = Proyecto.objects.create(
                nombre='Proyecto Salto Invalido', empresa=self.empresa, fase_actual='INICIO',
            )
            proyecto_uuid = proyecto.uuid

            client = APIClient()
            client.force_authenticate(user=self.user)

            response = self._avanzar(client, proyecto_uuid, 'CIERRE')

            assert response.status_code == status.HTTP_400_BAD_REQUEST

            proyecto_en_bd = Proyecto.objects.get(pk=proyecto.pk)
            assert proyecto_en_bd.fase_actual == 'INICIO'
            assert HistorialFaseProyecto.objects.filter(proyecto=proyecto).count() == 0
