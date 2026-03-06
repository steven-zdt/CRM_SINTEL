"""
⚠️ FASE 6: Tests críticos de Aislamiento de Datos.

Confirman el principio fundamental del SaaS multitenant: cada tenant solo accede a sus propios datos.
"""
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from django.db import connection
from django.utils import timezone
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, NaturalezaFactura
from apps.public.tenants.models import Client
from decimal import Decimal


class DataIsolationCriticalTests(TenantTestCase):
    """
    Tests críticos de aislamiento de datos entre tenants.
    
    ⚠️ FASE 6: Validaciones mínimas pero críticas del aislamiento por esquema.
    """
    
    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """Configura tenant de prueba."""
        from apps.public.tenants.models import Client as TenantClient
        return TenantClient.objects.create(
            schema_name="test_tenant_a",
            nombre="Test Tenant A",
            is_active=True,
            on_trial=True
        )
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        # Crear datos en el tenant actual (Tenant A)
        self.empresa_a = Empresa.objects.create(
            razon_social="Empresa Tenant A",
            nit="900111111",
            dv="1"
        )
        self.factura_a = Factura.objects.create(
            numero="FAC-001-A",
            prefijo="FAC",
            consecutivo=1,
            fecha_emision=timezone.now(),
            emisor_nit="900111111",
            receptor_nit="900222222",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=Decimal("1000.00"),
            impuestos=Decimal("190.00"),
            total=Decimal("1190.00"),
            moneda="COP"
        )
    
    def test_tenant_a_no_ve_datos_tenant_b(self):
        """
        Test: Tenant A no puede leer datos del Tenant B.
        
        Criterios de aceptación:
        - Cada tenant solo accede a su propio esquema
        - No hay filtraciones de datos entre empresas
        """
        # Crear Tenant B con datos
        from apps.public.tenants.models import Client as TenantClient, Domain
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Crear Tenant B
        tenant_b = TenantClient.objects.create(
            schema_name="test_tenant_b",
            nombre="Test Tenant B",
            is_active=True,
            on_trial=True
        )
        Domain.objects.create(domain="tenant-b.localhost", tenant=tenant_b, is_primary=True)
        
        # Crear datos en Tenant B
        with schema_context("test_tenant_b"):
            empresa_b = Empresa.objects.create(
                razon_social="Empresa Tenant B",
                nit="900333333",
                dv="1"
            )
            factura_b = Factura.objects.create(
                numero="FAC-001-B",
                prefijo="FAC",
                consecutivo=1,
                fecha_emision=timezone.now(),
                emisor_nit="900333333",
                receptor_nit="900444444",
                naturaleza=NaturalezaFactura.VENTA,
                subtotal=Decimal("2000.00"),
                impuestos=Decimal("380.00"),
                total=Decimal("2380.00"),
                moneda="COP"
            )
        
        # Volver al esquema de Tenant A (automático con TenantTestCase)
        # Verificar que Tenant A solo ve sus propios datos
        empresas_a = Empresa.objects.all()
        facturas_a = Factura.objects.all()
        
        self.assertEqual(empresas_a.count(), 1)
        self.assertEqual(empresas_a.first().nit, "900111111")
        
        self.assertEqual(facturas_a.count(), 1)
        self.assertEqual(facturas_a.first().numero, "FAC-001-A")
        
        # Verificar que NO puede acceder a datos de Tenant B por ID
        # (esto debería fallar o retornar None)
        with schema_context("test_tenant_b"):
            factura_b_id = factura_b.id
        
        # Intentar acceder desde Tenant A (debe fallar o no encontrar)
        factura_b_from_a = Factura.objects.filter(id=factura_b_id).first()
        self.assertIsNone(factura_b_from_a, "Tenant A no debe poder acceder a facturas de Tenant B")
    
    def test_queries_ejecutan_esquema_correcto(self):
        """
        Test: Queries ejecutadas bajo el esquema correcto.
        
        Criterios de aceptación:
        - Las queries se ejecutan en el esquema del tenant actual
        - No hay mezcla de esquemas
        """
        # Verificar esquema actual
        self.assertEqual(connection.schema_name, "test_tenant_a")
        
        # Crear datos
        empresa = Empresa.objects.create(
            razon_social="Test Schema",
            nit="900555555",
            dv="1"
        )
        
        # Verificar que la query se ejecutó en el esquema correcto
        with schema_context("test_tenant_a"):
            count = Empresa.objects.count()
            self.assertGreaterEqual(count, 1)
            self.assertTrue(Empresa.objects.filter(nit="900555555").exists())
    
    def test_acceso_directo_por_id_imposible(self):
        """
        Test: Acceso directo por ID entre tenants es imposible.
        
        Criterios de aceptación:
        - Intentar acceder a un ID de otro tenant retorna None o 404
        - No hay fuga de información entre tenants
        """
        # Crear Tenant B con datos
        from apps.public.tenants.models import Client as TenantClient, Domain
        
        tenant_b = TenantClient.objects.create(
            schema_name="test_tenant_b_isolation",
            nombre="Test Tenant B Isolation",
            is_active=True,
            on_trial=True
        )
        Domain.objects.create(domain="tenant-b-isolation.localhost", tenant=tenant_b, is_primary=True)
        
        # Crear factura en Tenant B
        with schema_context("test_tenant_b_isolation"):
            factura_b = Factura.objects.create(
                numero="FAC-B-ISOLATION",
                prefijo="FAC",
                consecutivo=1,
                fecha_emision=timezone.now(),
                emisor_nit="900666666",
                receptor_nit="900777777",
                naturaleza=NaturalezaFactura.VENTA,
                subtotal=Decimal("3000.00"),
                impuestos=Decimal("570.00"),
                total=Decimal("3570.00"),
                moneda="COP"
            )
            factura_b_id = factura_b.id
        
        # Intentar acceder desde Tenant A (debe fallar)
        factura_from_a = Factura.objects.filter(id=factura_b_id).first()
        self.assertIsNone(
            factura_from_a,
            "Tenant A no debe poder acceder a facturas de Tenant B por ID"
        )
        
        # Verificar que Tenant A solo ve sus propias facturas
        facturas_a = Factura.objects.all()
        for factura in facturas_a:
            self.assertNotEqual(factura.id, factura_b_id)
            self.assertNotEqual(factura.numero, "FAC-B-ISOLATION")
    
    def test_empresa_aislamiento_por_tenant(self):
        """
        Test: Cada tenant tiene su propia Empresa (SSoT).
        
        Criterios de aceptación:
        - Cada tenant puede tener solo una Empresa
        - Las Empresas de diferentes tenants son independientes
        """
        # Verificar que Tenant A tiene su Empresa
        empresa_a = Empresa.objects.first()
        self.assertIsNotNone(empresa_a)
        self.assertEqual(empresa_a.nit, "900111111")
        
        # Crear Tenant B
        from apps.public.tenants.models import Client as TenantClient, Domain
        
        tenant_b = TenantClient.objects.create(
            schema_name="test_tenant_b_empresa",
            nombre="Test Tenant B Empresa",
            is_active=True,
            on_trial=True
        )
        Domain.objects.create(domain="tenant-b-empresa.localhost", tenant=tenant_b, is_primary=True)
        
        # Crear Empresa en Tenant B
        with schema_context("test_tenant_b_empresa"):
            empresa_b = Empresa.objects.create(
                razon_social="Empresa Tenant B",
                nit="900888888",
                dv="1"
            )
        
        # Verificar que Tenant A no ve la Empresa de Tenant B
        empresas_a = Empresa.objects.all()
        for empresa in empresas_a:
            self.assertNotEqual(empresa.nit, "900888888")
            self.assertNotEqual(empresa.razon_social, "Empresa Tenant B")
