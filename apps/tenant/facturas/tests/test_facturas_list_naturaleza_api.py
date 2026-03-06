"""
Tests de humo para validar que la API de listado de facturas incluye naturaleza.
"""
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase
from apps.tenant.facturas.models import Factura, NaturalezaFactura
from apps.tenant.empresa.models import Empresa


class FacturasListNaturalezaAPITests(TenantTestCase):
    """Tests para validar que el listado de facturas incluye naturaleza correctamente."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY SAS",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
        
        # Crear factura de COMPRA (emisor diferente a empresa)
        Factura.objects.create(
            numero="BOG1299136",
            emisor_nit="860030723",
            emisor_razon_social="Proveedor Test",
            receptor_nit="901123299",
            receptor_razon_social="SINTEL TECNOLOGY SAS",
            naturaleza=NaturalezaFactura.COMPRA,
            subtotal=1076400,
            impuestos=204516,
            total=1280916,
            moneda="COP"
        )
        
        # Crear factura de VENTA (emisor igual a empresa)
        Factura.objects.create(
            numero="FST355",
            emisor_nit="901123299",
            emisor_razon_social="SINTEL TECNOLOGY SAS",
            receptor_nit="901761387",
            receptor_razon_social="Cliente Test",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=190974.2,
            impuestos=3664794.9,
            total=3855769.1,
            moneda="COP"
        )
    
    def test_list_incluye_naturaleza_correcta(self):
        """Valida que el listado incluye naturaleza y los valores son correctos."""
        url = reverse("factura-list")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Obtener resultados (puede ser paginado o lista directa)
        results = data.get("results", data) if isinstance(data, dict) else data
        
        # Crear índice por número de factura
        idx = {r["numero"]: r["naturaleza"] for r in results}
        
        # Validar que las naturalezas son correctas
        self.assertEqual(idx.get("BOG1299136"), NaturalezaFactura.COMPRA)
        self.assertEqual(idx.get("FST355"), NaturalezaFactura.VENTA)
        
        # Validar que todos los registros tienen naturaleza
        for r in results:
            self.assertIn("naturaleza", r)
            self.assertIn(r["naturaleza"], [NaturalezaFactura.VENTA, NaturalezaFactura.COMPRA])
