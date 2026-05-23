"""
Tests para app proyectos segun protocolo TESTING_AGENT.md v4.0
"""
import datetime
from decimal import Decimal

import pytest
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model

from apps.config.tests.base_tenant import TenantAPITestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import (
    AsignacionPersonal,
    ItemPedido,
    PedidoProyecto,
    Proyecto,
)
from apps.tenant.proyectos.api.viewsets import ProyectoViewSet
from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.proyectos.services.business_service import (
    calcular_costo_mano_obra,
    calcular_costo_materiales,
    calcular_indicadores_financieros,
)

User = get_user_model()


class TestFase1SmokeTests(TestCase):
    """FASE 1: Smoke Tests y Compilacion"""
    
    def test_modelo_herencia_sintel(self):
        """Verificar herencia de SintelTenantBaseModel"""
        assert issubclass(Proyecto, SintelTenantBaseModel)
        assert hasattr(Proyecto, 'empresa_id')


class TestFase2BackendArchitecture(TestCase):
    """FASE 2: Testing de Backend y Service Layer"""
    
    def test_service_layer_estructura(self):
        """Verificar estructura modular obligatoria"""
        import os
        services_path = 'apps/tenant/proyectos/services/'
        
        assert os.path.exists(f'{services_path}__init__.py')
        assert os.path.exists(f'{services_path}crud_service.py')
        assert os.path.exists(f'{services_path}business_service.py')
        assert os.path.exists(f'{services_path}selectors.py')

    def test_gateway_directo_endpoints(self):
        """Verificar endpoints directos sin facades"""
        from apps.tenant.proyectos.api.urls import urlpatterns
        
        # Verificar que existen endpoints directos
        assert len(urlpatterns) > 0
        # Verificar que hay al menos una URL registrada
        assert any(url for url in urlpatterns)


class TestFase3FrontendFSD(TestCase):
    """FASE 3: Testing de Frontend Feature-Sliced Design"""
    
    def test_templates_fsd(self):
        """Verificar templates en ubicacion correcta"""
        import os
        template_path = 'apps/tenant/proyectos/templates/tenant/proyectos/'
        
        assert os.path.exists(f'{template_path}list.html')
        assert os.path.exists(f'{template_path}offcanvas_form.html')

    def test_javascript_namespace(self):
        """Verificar namespace JavaScript"""
        import os
        js_path = 'apps/tenant/proyectos/static/proyectos/js/'
        
        # Verificar archivos modulares
        assert os.path.exists(f'{js_path}proyectos.api.js')


class TestFase4SeguridadZeroTrust(TestCase):
    """FASE 4: Testing de Seguridad Avanzada"""
    
    def test_proyecto_has_empresa_id(self):
        """Verificar que Proyecto tiene campo empresa_id (Zero-Trust)"""
        # Verificar que el modelo tiene el campo empresa
        assert hasattr(Proyecto, 'empresa')
        assert hasattr(Proyecto, 'empresa_id')
        
    def test_proyecto_tenant_isolation_field(self):
        """Verificar campo de aislamiento en Proyecto"""
        # Verificar que el modelo Proyecto tiene el campo empresa como FK
        from django.db import models
        empresa_field = Proyecto._meta.get_field('empresa')
        assert isinstance(empresa_field, models.ForeignKey)
        assert empresa_field.remote_field.model.__name__ == 'Empresa'


class TestPaginacionStandard(TestCase):
    """Testing de Paginacion Estandar"""
    
    def test_paginacion_formato(self):
        """Verificar formato de paginacion DRF"""
        import os
        viewsets_path = 'apps/tenant/proyectos/api/viewsets.py'
        
        if os.path.exists(viewsets_path):
            with open(viewsets_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Verificar que usa StandardResultsSetPagination
                assert 'StandardResultsSetPagination' in content


class TestIndicadoresFinancieros(TenantAPITestCase):
    """
    PASO 3 Roadmap M3 — Cobertura de pruebas P&L.
    Valida calcular_costo_mano_obra(), calcular_costo_materiales()
    y calcular_indicadores_financieros() con casos exactos.
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test P&L',
                nit='900999000',
            )
        else:
            self.empresa.razon_social = 'Empresa Test P&L'
            self.empresa.nit = '900999000'
            self.empresa.save()
            
        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto P&L Test',
            codigo='PRJ-2026-TEST',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('10000000.00'),
        )

    # ------------------------------------------------------------------
    # Caso 1 — costo_mano_obra (asignaciones activas)
    # ------------------------------------------------------------------
    def test_calcular_costo_mano_obra_suma_asignaciones_activas(self):
        AsignacionPersonal.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            nombre_colaborador='Tecnico Uno',
            rol='TECNICO',
            fecha_asignacion=datetime.date.today(),
            activo=True,
            horas_totales_registradas=Decimal('160.00'),
            costo_hora=Decimal('25000.00'),
            costo_total_asignacion=Decimal('4000000.00'),
        )
        AsignacionPersonal.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            nombre_colaborador='Ayudante Dos',
            rol='AYUDANTE',
            fecha_asignacion=datetime.date.today(),
            activo=True,
            horas_totales_registradas=Decimal('80.00'),
            costo_hora=Decimal('15000.00'),
            costo_total_asignacion=Decimal('1200000.00'),
        )
        # Asignacion inactiva — NO debe sumarse
        AsignacionPersonal.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            nombre_colaborador='Inactivo',
            rol='TECNICO',
            fecha_asignacion=datetime.date.today(),
            activo=False,
            costo_total_asignacion=Decimal('999999.00'),
        )

        resultado = calcular_costo_mano_obra(self.proyecto)

        self.assertEqual(resultado, Decimal('5200000.00'))

    # ------------------------------------------------------------------
    # Caso 2 — costo_materiales (items de pedidos APROBADO)
    # ------------------------------------------------------------------
    def test_calcular_costo_materiales_solo_pedidos_aprobados(self):
        pedido_aprobado = PedidoProyecto.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            tipo_recurso='MATERIALES',
            fuente_suministro='PROVEEDOR',
            estado='APROBADO',
        )
        ItemPedido.objects.create(
            pedido=pedido_aprobado,
            empresa=self.empresa,
            nombre_material='Cable UTP Cat6',
            cantidad=Decimal('10.00'),
            unidad_medida='MTR',
            precio_unitario=Decimal('5000.00'),
        )
        ItemPedido.objects.create(
            pedido=pedido_aprobado,
            empresa=self.empresa,
            nombre_material='Patch Panel 24p',
            cantidad=Decimal('2.00'),
            unidad_medida='UND',
            precio_unitario=Decimal('150000.00'),
        )
        # Pedido en BORRADOR — NO debe sumarse
        pedido_borrador = PedidoProyecto.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            tipo_recurso='EQUIPOS',
            fuente_suministro='PROVEEDOR',
            estado='BORRADOR',
        )
        ItemPedido.objects.create(
            pedido=pedido_borrador,
            empresa=self.empresa,
            nombre_material='Switch 24p',
            cantidad=Decimal('1.00'),
            unidad_medida='UND',
            precio_unitario=Decimal('2000000.00'),
        )

        resultado = calcular_costo_materiales(self.proyecto)

        # (10 * 5000) + (2 * 150000) = 50000 + 300000 = 350000
        self.assertEqual(resultado, Decimal('350000.00'))

    # ------------------------------------------------------------------
    # Caso 3 — P&L completo: utilidad, margen y persistencia
    # ------------------------------------------------------------------
    def test_calcular_indicadores_financieros_pl_completo(self):
        # Mano de obra: 3_000_000
        AsignacionPersonal.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            nombre_colaborador='Residente',
            rol='RESIDENTE',
            fecha_asignacion=datetime.date.today(),
            activo=True,
            costo_total_asignacion=Decimal('3000000.00'),
        )
        # Materiales: 2_000_000
        pedido = PedidoProyecto.objects.create(
            empresa=self.empresa,
            proyecto=self.proyecto,
            tipo_recurso='MATERIALES',
            fuente_suministro='ALMACEN',
            estado='APROBADO',
        )
        ItemPedido.objects.create(
            pedido=pedido,
            empresa=self.empresa,
            nombre_material='Materiales varios',
            cantidad=Decimal('1.00'),
            unidad_medida='GLB',
            precio_unitario=Decimal('2000000.00'),
        )

        resultado = calcular_indicadores_financieros(self.proyecto)

        # P&L esperado:
        # contrato         = 10_000_000
        # costo_total      = 3_000_000 + 2_000_000 = 5_000_000
        # utilidad         = 10_000_000 - 5_000_000 = 5_000_000
        # margen           = 5_000_000 / 10_000_000 * 100 = 50.00%
        self.assertEqual(resultado['costo_mano_obra_real'], Decimal('3000000.00'))
        self.assertEqual(resultado['costo_materiales_real'], Decimal('2000000.00'))
        self.assertEqual(resultado['costo_total'], Decimal('5000000.00'))
        self.assertEqual(resultado['utilidad_estimada'], Decimal('5000000.00'))
        self.assertEqual(resultado['margen_rentabilidad'], Decimal('50.00'))

        # Verificar persistencia en BD
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.costo_mano_obra_real, Decimal('3000000.00'))
        self.assertEqual(self.proyecto.costo_materiales_real, Decimal('2000000.00'))
        self.assertEqual(self.proyecto.utilidad_estimada, Decimal('5000000.00'))
        self.assertEqual(self.proyecto.margen_rentabilidad, Decimal('50.00'))

    def test_margen_cero_cuando_contrato_es_cero(self):
        self.proyecto.valor_contrato_proyectado = Decimal('0.00')
        self.proyecto.save(update_fields=['valor_contrato_proyectado'])

        resultado = calcular_indicadores_financieros(self.proyecto)

        self.assertEqual(resultado['margen_rentabilidad'], Decimal('0.00'))


class TestCierreProyectoBloqueo(TenantAPITestCase):
    """
    Fase 4 - Control de Edicion en fase de CIERRE.
    Verifica que no se puedan modificar datos criticos cuando el proyecto esta en CIERRE,
    y que se bloqueen asignaciones de personal y pedidos asociados.
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test Bloqueo',
                nit='900999001',
            )
        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre='Proyecto en Cierre',
            codigo='PRJ-CIERRE-01',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('5000000.00'),
            fase_actual='CIERRE',
        )

    def test_no_editar_proyecto_cerrado(self):
        """Verifica que cualquier intento de edicion (PATCH/PUT) a un proyecto cerrado retorne 400 Bad Request."""
        url = f'/api/v1/proyectos/{self.proyecto.uuid}/'
        payload = {
            'nombre': 'Proyecto Editado en Cierre',
            'valor_contrato_proyectado': '6000000.00'
        }
        # PATCH
        response = self.client.patch(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.json())
        
        # PUT
        response = self.client.put(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_permitir_carga_reportes_en_cierre(self):
        """Verifica que si se permite actualizar campos de cierre (actas, reportes, avance, estado)."""
        url = f'/api/v1/proyectos/{self.proyecto.uuid}/'
        payload = {
            'porcentaje_avance': 100,
            'estado_tarea': 'COMPLETADO'
        }
        response = self.client.patch(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.porcentaje_avance, 100)
        self.assertEqual(self.proyecto.estado_tarea, 'COMPLETADO')

    def test_bloqueo_asignacion_personal_en_cierre(self):
        """Verifica que no se puedan agregar asignaciones de personal cuando el proyecto esta en CIERRE."""
        from apps.tenant.proyectos.api.serializers import AsignacionPersonalSerializer
        serializer = AsignacionPersonalSerializer(data={
            'nombre_colaborador': 'Colaborador Test',
            'rol': 'TECNICO',
            'fecha_asignacion': '2026-05-19',
            'costo_hora': '20000.00',
            'horas_totales_registradas': '10.00',
            'activo': True
        }, context={'proyecto': self.proyecto})
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('No se pueden agregar o modificar asignaciones', str(serializer.errors['non_field_errors'][0]))

    def test_bloqueo_pedido_proyecto_en_cierre(self):
        """Verifica que no se puedan agregar pedidos cuando el proyecto esta en CIERRE."""
        from apps.tenant.proyectos.api.serializers import PedidoProyectoSerializer
        serializer = PedidoProyectoSerializer(data={
            'proyecto': self.proyecto.id,
            'tipo_recurso': 'MATERIALES',
            'fuente_suministro': 'PROVEEDOR',
            'proveedor_nombre': 'Proveedor Test',
            'estado': 'BORRADOR'
        }, context={'proyecto': self.proyecto})
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('No se pueden generar o modificar pedidos', str(serializer.errors['non_field_errors'][0]))


class TestServicioAsociado(TenantAPITestCase):
    """
    FASE 5 QA — Testing de Vinculación Servicio-Proyecto (v3.5.4)
    Valida:
    - Creación de proyecto con servicio_asociado (UUID-Safe)
    - DSV: Bloqueo de servicio de otro tenant
    - Actualización de proyecto con nuevo servicio
    - Rechazo de servicio inexistente
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                razon_social='Empresa Test Servicio',
                nit='900111222',
            )

    def test_asociar_servicio_proyecto_exitoso(self):
        """
        Crear proyecto con UUID de Servicio válido.
        Valida que el campo servicio_asociado se asigna correctamente.
        """
        try:
            from apps.tenant.inventario.models import Servicio
        except ImportError:
            self.skipTest('Inventario app no disponible')

        # Crear un servicio en la empresa
        servicio = Servicio.objects.create(
            empresa=self.empresa,
            nombre='Servicio Instalación',
            descripcion='Servicio de instalación técnica',
            tipo='SERVICIO',
            codigo='SRV-001',
        )

        # Crear proyecto CON servicio_asociado
        from apps.tenant.proyectos.services.business_service import orchestrate_create_proyecto

        proyecto = orchestrate_create_proyecto(
            empresa=self.empresa,
            data={
                'nombre': 'Proyecto con Servicio',
                'tipo_servicio': 'INSTALACION',
                'servicio_asociado': servicio,  # Pasar instancia de Servicio
            }
        )

        # Validar que el servicio se asoció correctamente
        self.assertIsNotNone(proyecto.servicio_asociado)
        self.assertEqual(proyecto.servicio_asociado.id, servicio.id)
        self.assertEqual(proyecto.servicio_asociado.empresa_id, self.empresa.id)

    def test_dsv_asociar_servicio_otro_tenant(self):
        """
        DSV: Intentar asociar un servicio de otra empresa debe fallar.
        Valida que la validación DSV en business_service bloquea IDOR.
        """
        try:
            from apps.tenant.inventario.models import Servicio
        except ImportError:
            self.skipTest('Inventario app no disponible')

        # Crear empresa 2 (otro tenant)
        empresa2 = Empresa.objects.create(
            razon_social='Otra Empresa',
            nit='900222333',
        )

        # Crear servicio EN OTRA EMPRESA
        servicio_otro = Servicio.objects.create(
            empresa=empresa2,
            nombre='Servicio Otra Empresa',
            descripcion='Servicio de otra empresa',
            tipo='SERVICIO',
            codigo='SRV-002',
        )

        # Intentar crear proyecto en empresa1 con servicio de empresa2 — DEBE FALLAR
        from apps.tenant.proyectos.services.business_service import orchestrate_create_proyecto
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            orchestrate_create_proyecto(
                empresa=self.empresa,
                data={
                    'nombre': 'Proyecto IDOR Attempt',
                    'tipo_servicio': 'INSTALACION',
                    'servicio_asociado': servicio_otro,  # Servicio de otra empresa
                }
            )

        # Validar que el error menciona empresa_id mismatch
        self.assertIn('no pertenece a la empresa', str(ctx.exception))

    def test_update_servicio_asociado_exitoso(self):
        """
        Actualizar proyecto existente con nuevo servicio_asociado.
        Valida que orchestrate_update_proyecto sincroniza el cambio.
        """
        try:
            from apps.tenant.inventario.models import Servicio
        except ImportError:
            self.skipTest('Inventario app no disponible')

        # Crear dos servicios
        servicio1 = Servicio.objects.create(
            empresa=self.empresa,
            nombre='Servicio A',
            tipo='SERVICIO',
            codigo='SRV-A',
        )
        servicio2 = Servicio.objects.create(
            empresa=self.empresa,
            nombre='Servicio B',
            tipo='SERVICIO',
            codigo='SRV-B',
        )

        # Crear proyecto con servicio1
        from apps.tenant.proyectos.services.business_service import (
            orchestrate_create_proyecto,
            orchestrate_update_proyecto,
        )

        proyecto = orchestrate_create_proyecto(
            empresa=self.empresa,
            data={
                'nombre': 'Proyecto Actualizable',
                'tipo_servicio': 'INSTALACION',
                'servicio_asociado': servicio1,
            }
        )

        self.assertEqual(proyecto.servicio_asociado.id, servicio1.id)

        # Actualizar a servicio2
        proyecto_actualizado = orchestrate_update_proyecto(
            proyecto=proyecto,
            data={
                'servicio_asociado': servicio2,
            }
        )

        # Validar cambio
        self.assertEqual(proyecto_actualizado.servicio_asociado.id, servicio2.id)

    def test_serializer_queryset_filtrado_por_empresa(self):
        """
        Validar que ProyectoDetailSerializer filtra servicios por empresa_id.
        El queryset del campo servicio_asociado debe incluir SOLO servicios
        de la empresa actual.
        """
        try:
            from apps.tenant.inventario.models import Servicio
        except ImportError:
            self.skipTest('Inventario app no disponible')

        from apps.tenant.proyectos.api.serializers import ProyectoDetailSerializer

        # Crear empresa2 y servicio en empresa2
        empresa2 = Empresa.objects.create(
            razon_social='Empresa B',
            nit='900333444',
        )
        servicio_empresa1 = Servicio.objects.create(
            empresa=self.empresa,
            nombre='Servicio Empresa1',
            tipo='SERVICIO',
            codigo='SRV-E1',
        )
        servicio_empresa2 = Servicio.objects.create(
            empresa=empresa2,
            nombre='Servicio Empresa2',
            tipo='SERVICIO',
            codigo='SRV-E2',
        )

        # Serializer con contexto de empresa1
        serializer = ProyectoDetailSerializer(
            context={'empresa_id': self.empresa.id}
        )

        # Validar que el queryset del campo servicio_asociado
        # incluye SOLO servicios de empresa1
        servicio_queryset = serializer.fields['servicio_asociado'].queryset
        servicio_ids = list(servicio_queryset.values_list('id', flat=True))

        self.assertIn(servicio_empresa1.id, servicio_ids)
        self.assertNotIn(servicio_empresa2.id, servicio_ids)


# pytest fixtures para testing funcional
@pytest.fixture
def client():
    return Client()


@pytest.fixture
def empresa_factory():
    def make_empresa(razon_social='Test Empresa', nit='1234567890'):
        return Empresa.objects.create(razon_social=razon_social, nit=nit)
    return make_empresa


@pytest.fixture
def proyecto_factory(empresa_factory):
    def make_proyecto(**kwargs):
        defaults = {
            'empresa': empresa_factory(),
            'codigo': 'PROJ-001',
            'nombre': 'Proyecto Test',
            'tipo_servicio': 'DESARROLLO'
        }
        defaults.update(kwargs)
        return Proyecto.objects.create(**defaults)
    return make_proyecto
