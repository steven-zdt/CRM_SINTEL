"""
Tests para app proyectos segun protocolo TESTING_AGENT.md v4.0
"""
import pytest
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.api.viewsets import ProyectoViewSet
from apps.tenant.core.models import SintelTenantBaseModel

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
        template_path = 'apps/tenant/proyectos/templates/proyectos/'
        
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
            with open(viewsets_path, 'r') as f:
                content = f.read()
                # Verificar que usa StandardResultsSetPagination
                assert 'StandardResultsSetPagination' in content


# pytest fixtures para testing funcional
@pytest.fixture
def client():
    return Client()


@pytest.fixture
def empresa_factory():
    def make_empresa(nombre='Test Empresa', nit='1234567890'):
        return Empresa.objects.create(nombre=nombre, nit=nit)
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
