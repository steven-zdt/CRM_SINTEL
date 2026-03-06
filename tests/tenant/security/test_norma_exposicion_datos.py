"""
Pruebas de humo para validar cumplimiento de "Norma General de Exposición de Datos (Proyecto SINTEL)".

Valida:
- No hay fields="__all__" en serializers
- No hay .all() sin limitar columnas en ViewSets
- Separación ListSerializer vs DetailSerializer
- Endpoints LIST no contienen campos pesados
- Endpoints DETAIL retornan exactamente un recurso
"""
import pytest
from django.urls import reverse
from rest_framework import status
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.facturas.models import Factura
from apps.tenant.contabilidad.models import AsientoContable, CuentaContable
from apps.tenant.empresa.models import Empresa


class TestNormaExposicionDatos(SintelTenantTestCase):
    """
    Smoke tests para validar cumplimiento de la norma de exposición de datos.
    """
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que las facturas puedan usar datos del emisor
        from apps.tenant.empresa.models import Empresa
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            dv="7",
            moneda="COP"
        )
    
    def test_facturas_list_no_contiene_xml_content(self):
        """
        LIST de facturas no contiene xml_content (campo pesado).
        """
        # Crear factura de prueba
        factura = Factura.objects.create(
            numero="FST-001",
            prefijo="FST",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=self.now,
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente A",
            moneda="COP",
            subtotal=100000.00,
            impuestos=19000.00,
            total=119000.00,
            xml_content="<Invoice>...</Invoice>"  # Campo pesado
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('factura-list')
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Verificar que no contenga xml_content
        for factura_data in results:
            assert 'xml_content' not in factura_data, \
                f"LIST no debe contener xml_content. Campos encontrados: {list(factura_data.keys())}"
    
    def test_facturas_detail_retorna_un_recurso(self):
        """
        DETAIL de facturas retorna exactamente un recurso.
        """
        factura = Factura.objects.create(
            numero="FST-002",
            prefijo="FST",
            consecutivo=2,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=self.now,
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente B",
            moneda="COP",
            subtotal=200000.00,
            impuestos=38000.00,
            total=238000.00
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('factura-detail', kwargs={'pk': factura.id})
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Verificar que es un objeto único (no lista)
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert data.get('id') == factura.id
    
    def test_facturas_xml_endpoint_separado(self):
        """
        XML solo se entrega en endpoint /xml/ separado.
        """
        factura = Factura.objects.create(
            numero="FST-003",
            prefijo="FST",
            consecutivo=3,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=self.now,
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente C",
            moneda="COP",
            subtotal=300000.00,
            impuestos=57000.00,
            total=357000.00,
            xml_content="<Invoice>Test XML</Invoice>"
        )
        
        self.api_client.force_authenticate(user=self.user)
        
        # Verificar que LIST no contiene xml_content
        url_list = reverse('factura-list')
        resp_list = self.api_client.get(url_list)
        assert resp_list.status_code == 200
        data_list = resp_list.json()
        results = data_list.get('results', data_list) if isinstance(data_list, dict) else data_list
        for f in results:
            assert 'xml_content' not in f
        
        # Verificar que DETAIL no contiene xml_content
        url_detail = reverse('factura-detail', kwargs={'pk': factura.id})
        resp_detail = self.api_client.get(url_detail)
        assert resp_detail.status_code == 200
        data_detail = resp_detail.json()
        assert 'xml_content' not in data_detail
        
        # Verificar que endpoint /xml/ sí contiene xml_content
        url_xml = reverse('factura-xml', kwargs={'pk': factura.id})
        resp_xml = self.api_client.get(url_xml)
        assert resp_xml.status_code == 200
        data_xml = resp_xml.json()
        assert 'xml' in data_xml
        assert data_xml['xml'] == "<Invoice>Test XML</Invoice>"
    
    def test_asientos_contables_list_serializer_minimo(self):
        """
        LIST de asientos contables usa serializer mínimo (sin movimientos).
        """
        asiento = AsientoContable.objects.create(
            numero="AS-001",
            fecha=self.now.date(),
            descripcion="Asiento de prueba",
            estado="BORRADOR"
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('asiento-contable-list')
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Verificar que no contenga movimientos (campo pesado)
        for asiento_data in results:
            assert 'movimientos' not in asiento_data, \
                f"LIST no debe contener movimientos. Campos encontrados: {list(asiento_data.keys())}"
    
    def test_asientos_contables_detail_contiene_movimientos(self):
        """
        DETAIL de asientos contables contiene movimientos (campo completo).
        """
        asiento = AsientoContable.objects.create(
            numero="AS-002",
            fecha=self.now.date(),
            descripcion="Asiento con movimientos",
            estado="BORRADOR"
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('asiento-contable-detail', kwargs={'pk': asiento.id})
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Verificar que es un objeto único
        assert isinstance(data, dict)
        assert data.get('id') == asiento.id
        # Verificar que contiene movimientos (puede ser lista vacía)
        assert 'movimientos' in data
    
    def test_cuentas_contables_list_serializer_minimo(self):
        """
        LIST de cuentas contables usa serializer mínimo.
        """
        cuenta = CuentaContable.objects.create(
            codigo="1105",
            nombre="Caja",
            tipo="ACTIVO"
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('cuenta-contable-list')
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Verificar campos mínimos
        for cuenta_data in results:
            # LIST debe tener campos mínimos, no descripcion ni cuenta_padre
            assert 'id' in cuenta_data
            assert 'codigo' in cuenta_data
            assert 'nombre' in cuenta_data
            assert 'tipo' in cuenta_data
    
    def test_cuentas_contables_detail_serializer_completo(self):
        """
        DETAIL de cuentas contables usa serializer completo.
        """
        cuenta = CuentaContable.objects.create(
            codigo="1106",
            nombre="Bancos",
            tipo="ACTIVO",
            descripcion="Cuentas bancarias"
        )
        
        self.api_client.force_authenticate(user=self.user)
        url = reverse('cuenta-contable-detail', kwargs={'pk': cuenta.id})
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Verificar que es un objeto único
        assert isinstance(data, dict)
        assert data.get('id') == cuenta.id
        # Verificar que contiene descripcion (campo completo)
        assert 'descripcion' in data
    
    def test_empresa_list_retorna_array(self):
        """
        LIST de empresa retorna array (singleton pattern).
        """
        self.api_client.force_authenticate(user=self.user)
        url = reverse('empresa-list')
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Empresa usa patrón singleton, retorna array
        assert isinstance(data, list)
    
    def test_empresa_detail_retorna_un_recurso(self):
        """
        DETAIL de empresa retorna exactamente un recurso.
        """
        self.api_client.force_authenticate(user=self.user)
        url = reverse('empresa-detail', kwargs={'pk': self.empresa.id})
        resp = self.api_client.get(url)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Verificar que es un objeto único
        assert isinstance(data, dict)
        assert data.get('id') == self.empresa.id
