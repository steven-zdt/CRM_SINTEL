"""
Smoke tests para filtros de API de facturas.

Valida que los filtros personalizados funcionen correctamente:
- naturaleza (VENTA|COMPRA)
- nit (busca en emisor_nit o receptor_nit)
- fecha_emision (rango de fechas)
"""
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.facturas.models import Factura


class TestFacturasFiltersAPI(SintelTenantTestCase):
    """
    Smoke tests para filtros de API de facturas.
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
        
        # Crear facturas de prueba
        self.factura_venta = Factura.objects.create(
            numero="FST-001",
            prefijo="FST",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=timezone.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente A",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
            cufe="abc123def456"
        )
        
        self.factura_compra = Factura.objects.create(
            numero="FST-002",
            prefijo="FST",
            consecutivo=2,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.COMPRA,
            categoria=Factura.Categoria.PRODUCTO,
            fecha_emision=timezone.now(),
            emisor_nit="900999888",
            emisor_razon_social="Proveedor B",
            receptor_nit="900123456",
            receptor_razon_social="Empresa Test",
            moneda="COP",
            subtotal=Decimal("50000.00"),
            impuestos=Decimal("9500.00"),
            total=Decimal("59500.00"),
            cufe="xyz789uvw012"
        )
    
    def test_filter_by_naturaleza_venta(self):
        """
        GET /api/v1/facturas/?naturaleza=VENTA → todas con VENTA.
        """
        self.api_client.force_authenticate(user=self.user)
        
        url = reverse('factura-list')
        resp = self.api_client.get(url, {'naturaleza': 'VENTA'})
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Todas deben ser VENTA
        for factura in results:
            assert factura.get('naturaleza') == 'VENTA', f"Expected VENTA, got {factura.get('naturaleza')}"
    
    def test_filter_by_naturaleza_compra(self):
        """
        GET /api/v1/facturas/?naturaleza=COMPRA → todas con COMPRA.
        """
        self.api_client.force_authenticate(user=self.user)
        
        url = reverse('factura-list')
        resp = self.api_client.get(url, {'naturaleza': 'COMPRA'})
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Todas deben ser COMPRA
        for factura in results:
            assert factura.get('naturaleza') == 'COMPRA', f"Expected COMPRA, got {factura.get('naturaleza')}"
    
    def test_filter_by_nit_emisor(self):
        """
        GET /api/v1/facturas/?nit=900123456 → resultados donde emisor_nit o receptor_nit contengan "900123456".
        """
        self.api_client.force_authenticate(user=self.user)
        
        url = reverse('factura-list')
        resp = self.api_client.get(url, {'nit': '900123456'})
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Todas deben tener 900123456 en emisor_nit o receptor_nit
        for factura in results:
            emisor = factura.get('emisor_nit', '')
            receptor = factura.get('receptor_nit', '')
            assert '900123456' in emisor or '900123456' in receptor, \
                f"Expected 900123456 in emisor_nit or receptor_nit, got emisor={emisor}, receptor={receptor}"
    
    def test_filter_by_nit_receptor(self):
        """
        GET /api/v1/facturas/?nit=900999888 → resultados donde emisor_nit o receptor_nit contengan "900999888".
        """
        self.api_client.force_authenticate(user=self.user)
        
        url = reverse('factura-list')
        resp = self.api_client.get(url, {'nit': '900999888'})
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Todas deben tener 900999888 en emisor_nit o receptor_nit
        for factura in results:
            emisor = factura.get('emisor_nit', '')
            receptor = factura.get('receptor_nit', '')
            assert '900999888' in emisor or '900999888' in receptor, \
                f"Expected 900999888 in emisor_nit or receptor_nit, got emisor={emisor}, receptor={receptor}"
    
    def test_filter_by_date_range(self):
        """
        GET /api/v1/facturas/?fecha_emision__date__gte=2024-01-01&fecha_emision__date__lte=2024-12-31 → rango correcto.
        """
        self.api_client.force_authenticate(user=self.user)
        
        # Crear factura con fecha específica
        fecha_especifica = timezone.make_aware(datetime(2024, 6, 15))
        factura_fecha = Factura.objects.create(
            numero="FST-003",
            prefijo="FST",
            consecutivo=3,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            categoria=Factura.Categoria.SERVICIO,
            fecha_emision=fecha_especifica,
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="900999888",
            receptor_razon_social="Cliente C",
            moneda="COP",
            subtotal=Decimal("200000.00"),
            impuestos=Decimal("38000.00"),
            total=Decimal("238000.00"),
            cufe="fecha123test456"
        )
        
        url = reverse('factura-list')
        resp = self.api_client.get(url, {
            'fecha_emision__date__gte': '2024-01-01',
            'fecha_emision__date__lte': '2024-12-31'
        })
        
        assert resp.status_code == 200
        data = resp.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        assert isinstance(results, list)
        
        # Verificar que todas las facturas estén en el rango
        for factura in results:
            fecha_str = factura.get('fecha_emision', '')
            if fecha_str:
                # La fecha viene en formato ISO, verificar que esté en 2024
                assert '2024' in fecha_str or fecha_str.startswith('2024'), \
                    f"Expected fecha in 2024, got {fecha_str}"
