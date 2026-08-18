"""
Tests para Tareas Diarias (v3.5.3)

Cubre:
1. Validacion de fechas (dentro/fuera de rango)
2. DSV (Double Semantic Verification - multi-tenant isolation)
3. Bloqueo de operaciones en fase CIERRE
4. API endpoints (CRUD + cambiar-estado)
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from django_tenants.utils import schema_context

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import Proyecto, TareaDiariaProyecto
from apps.tenant.proyectos.services import (
    TareasDiariasBusinessService,
    TareasDiariasCRUDService
)
from rest_framework.exceptions import ValidationError


@pytest.mark.django_db
class TestTareasDiariasBusinessService:
    """Tests para la logica de negocio de tareas diarias."""

    @pytest.fixture(autouse=True)
    def setup(self, tenant1):
        """Setup: Crear empresa y proyecto base dentro del tenant."""
        with schema_context(tenant1.schema_name):
            self.empresa = Empresa.objects.first()

            hoy = date.today()
            self.proyecto = Proyecto.objects.create(
                empresa=self.empresa,
                nombre='Proyecto Test',
                tipo_servicio='PROYECTO_INTEGRAL',
                fase_actual='EJECUCION',
                valor_contrato_proyectado=Decimal('1000000.00'),
                fecha_inicio=hoy,
                fecha_fin_estimada=hoy + timedelta(days=30)
            )

    def test_crear_tarea_dentro_rango_fechas(self, tenant1):
        """[OK] Crear tarea con fecha valida (dentro de rango)."""
        with schema_context(tenant1.schema_name):
            fecha = self.proyecto.fecha_inicio + timedelta(days=5)
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=self.empresa,
                proyecto=self.proyecto,
                fecha=fecha,
                titulo='Tarea Test',
                descripcion='Descripcion test',
                prioridad='NORMAL'
            )

            assert tarea.id is not None
            assert tarea.estado == 'PENDIENTE'
            assert tarea.fecha == fecha
            assert tarea.titulo == 'Tarea Test'

    def test_crear_tarea_fecha_anterior_inicio(self, tenant1):
        """[ERROR] Crear tarea con fecha ANTES de fecha_inicio."""
        with schema_context(tenant1.schema_name):
            fecha_invalida = self.proyecto.fecha_inicio - timedelta(days=1)

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.crear_tarea(
                    empresa=self.empresa,
                    proyecto=self.proyecto,
                    fecha=fecha_invalida,
                    titulo='Tarea Invalida'
                )

    def test_crear_tarea_fecha_posterior_fin(self, tenant1):
        """[ERROR] Crear tarea con fecha DESPUeS de fecha_fin_estimada."""
        with schema_context(tenant1.schema_name):
            fecha_invalida = self.proyecto.fecha_fin_estimada + timedelta(days=1)

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.crear_tarea(
                    empresa=self.empresa,
                    proyecto=self.proyecto,
                    fecha=fecha_invalida,
                    titulo='Tarea Invalida'
                )

    def test_dsv_tarea_otro_empresa(self, tenant1):
        """[ERROR] DSV: Rechaza crear tarea con empresa distinta a la del proyecto.

        WARNING: Empresa es singleton por esquema (no se puede persistir una
        segunda empresa real en el mismo tenant) y comparar Empresa.id entre
        esquemas distintos no es confiable (secuencias de PK independientes
        por esquema, ej. ambos pueden tener id=1). _validar_empresa_dsv()
        compara solo proyecto.empresa_id != empresa.id ANTES de persistir
        nada, asi que una instancia de Empresa no guardada con un id distinto
        es suficiente para ejercitar el rechazo DSV de forma determinista.
        """
        with schema_context(tenant1.schema_name):
            empresa_otra = Empresa(id=self.empresa.id + 1)

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.crear_tarea(
                    empresa=empresa_otra,  # Empresa diferente (id distinto)
                    proyecto=self.proyecto,
                    fecha=self.proyecto.fecha_inicio,
                    titulo='Tarea DSV Falla'
                )

    def test_bloqueo_cierre_crear_tarea(self, tenant1):
        """[ERROR] Bloqueo: No permite crear tarea si proyecto esta en CIERRE."""
        with schema_context(tenant1.schema_name):
            self.proyecto.fase_actual = 'CIERRE'
            self.proyecto.save()

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.crear_tarea(
                    empresa=self.empresa,
                    proyecto=self.proyecto,
                    fecha=self.proyecto.fecha_inicio,
                    titulo='Tarea en CIERRE'
                )

    def test_bloqueo_cierre_cambiar_estado(self, tenant1):
        """[ERROR] Bloqueo: No permite cambiar estado si proyecto esta en CIERRE."""
        with schema_context(tenant1.schema_name):
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=self.empresa,
                proyecto=self.proyecto,
                fecha=self.proyecto.fecha_inicio,
                titulo='Tarea Normal'
            )

            self.proyecto.fase_actual = 'CIERRE'
            self.proyecto.save()

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.cambiar_estado_tarea(tarea, 'EN_PROCESO')

    def test_bloqueo_cierre_eliminar_tarea(self, tenant1):
        """[ERROR] Bloqueo: No permite eliminar tarea si proyecto esta en CIERRE."""
        with schema_context(tenant1.schema_name):
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=self.empresa,
                proyecto=self.proyecto,
                fecha=self.proyecto.fecha_inicio,
                titulo='Tarea a Eliminar'
            )

            self.proyecto.fase_actual = 'CIERRE'
            self.proyecto.save()

            with pytest.raises(ValidationError):
                TareasDiariasBusinessService.eliminar_tarea(tarea)

    def test_cambiar_estado_transicion_valida(self, tenant1):
        """[OK] Cambiar estado: PENDIENTE -> EN_PROCESO -> COMPLETADA."""
        with schema_context(tenant1.schema_name):
            tarea = TareasDiariasBusinessService.crear_tarea(
                empresa=self.empresa,
                proyecto=self.proyecto,
                fecha=self.proyecto.fecha_inicio,
                titulo='Tarea Estado'
            )

            assert tarea.estado == 'PENDIENTE'

            # Cambiar a EN_PROCESO
            tarea = TareasDiariasBusinessService.cambiar_estado_tarea(tarea, 'EN_PROCESO')
            assert tarea.estado == 'EN_PROCESO'

            # Cambiar a COMPLETADA
            tarea = TareasDiariasBusinessService.cambiar_estado_tarea(tarea, 'COMPLETADA')
            assert tarea.estado == 'COMPLETADA'

    def test_unique_constraint_tarea_fecha_titulo(self, tenant1):
        """[ERROR] Unique constraint: No permite dos tareas con mismo proyecto, fecha y titulo."""
        with schema_context(tenant1.schema_name):
            fecha = self.proyecto.fecha_inicio + timedelta(days=5)
            titulo = 'Tarea unica'

            # Crear primera tarea
            TareasDiariasBusinessService.crear_tarea(
                empresa=self.empresa,
                proyecto=self.proyecto,
                fecha=fecha,
                titulo=titulo
            )

            # Intentar crear segunda tarea identica
            from django.db import IntegrityError
            with pytest.raises(IntegrityError):
                TareasDiariasBusinessService.crear_tarea(
                    empresa=self.empresa,
                    proyecto=self.proyecto,
                    fecha=fecha,
                    titulo=titulo
                )


class TestTareaDiariaAPI(TenantAPITestCase):
    """Tests para endpoints REST de tareas diarias.

    TenantAPITestCase (django_tenants.TenantTestCase) fija el esquema del
    tenant para toda la duracion del test y provee self.client ya apuntando
    al dominio correcto -- mismo patron ya usado por TestCierreProyectoBloqueo/
    TestServicioAsociado en test_legacy_smoke_financials.py.
    """

    def setUp(self):
        """Setup: usar la Empresa singleton creada por TenantAPITestCase y crear el proyecto."""
        super().setUp()
        self.empresa = Empresa.objects.first()

        hoy = date.today()
        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto Test',
            tipo_servicio='PROYECTO_INTEGRAL',
            fase_actual='EJECUCION',
            valor_contrato_proyectado=Decimal('1000000.00'),
            fecha_inicio=hoy,
            fecha_fin_estimada=hoy + timedelta(days=30)
        )

    def test_api_get_tareas_por_proyecto_200(self):
        """[OK] GET /api/v1/proyectos/tareas-diarias/?proyecto_uuid=<uuid> retorna 200."""
        # Crear una tarea
        TareasDiariasBusinessService.crear_tarea(
            empresa=self.empresa,
            proyecto=self.proyecto,
            fecha=self.proyecto.fecha_inicio,
            titulo='Tarea API Test'
        )

        url = f'/api/v1/proyectos/tareas-diarias/?proyecto_uuid={self.proyecto.uuid}'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_api_post_crear_tarea_201(self):
        """[OK] POST /api/v1/proyectos/tareas-diarias/ con datos validos retorna 201."""
        # WARNING: TareaDiariaSerializer (contrato HTTP real) exige
        # fecha_inicio/fecha_fin -- 'fecha' es solo un alias que existe a
        # nivel de TareasDiariasBusinessService.crear_tarea() (Python), no
        # del serializer/endpoint HTTP.
        fecha = str(self.proyecto.fecha_inicio + timedelta(days=2))
        data = {
            'proyecto_uuid': str(self.proyecto.uuid),
            'fecha_inicio': fecha,
            'fecha_fin': fecha,
            'titulo': 'Tarea Creada por API',
            'prioridad': 'ALTA'
        }

        response = self.client.post('/api/v1/proyectos/tareas-diarias/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert TareaDiariaProyecto.objects.filter(titulo='Tarea Creada por API').exists()

    def test_api_post_crear_tarea_fecha_invalida_400(self):
        """[ERROR] POST con fecha fuera de rango retorna 400."""
        # WARNING: usaba 'fecha' (alias solo del service layer, no del
        # serializer HTTP) -- el 400 anterior era por campo requerido
        # ausente, no por la validacion de rango que este test dice probar.
        fecha_invalida = str(self.proyecto.fecha_fin_estimada + timedelta(days=10))
        data = {
            'proyecto_uuid': str(self.proyecto.uuid),
            'fecha_inicio': fecha_invalida,
            'fecha_fin': fecha_invalida,
            'titulo': 'Tarea Fecha Invalida'
        }

        response = self.client.post('/api/v1/proyectos/tareas-diarias/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_api_post_cambiar_estado_200(self):
        """[OK] POST /api/v1/proyectos/tareas-diarias/<id>/cambiar-estado/ retorna 200."""
        tarea = TareasDiariasBusinessService.crear_tarea(
            empresa=self.empresa,
            proyecto=self.proyecto,
            fecha=self.proyecto.fecha_inicio,
            titulo='Tarea Cambio Estado'
        )

        url = f'/api/v1/proyectos/tareas-diarias/{tarea.uuid}/cambiar-estado/'
        data = {'nuevo_estado': 'EN_PROCESO'}

        response = self.client.post(url, data, content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        tarea.refresh_from_db()
        assert tarea.estado == 'EN_PROCESO'

    def test_api_delete_tarea_204(self):
        """[OK] DELETE /api/v1/proyectos/tareas-diarias/<id>/ retorna 204."""
        tarea = TareasDiariasBusinessService.crear_tarea(
            empresa=self.empresa,
            proyecto=self.proyecto,
            fecha=self.proyecto.fecha_inicio,
            titulo='Tarea a Eliminar'
        )

        url = f'/api/v1/proyectos/tareas-diarias/{tarea.uuid}/'
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TareaDiariaProyecto.objects.filter(id=tarea.id).exists()
