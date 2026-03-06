"""
Tests unitarios para materializar_factura_desde_result (Fase 2).

⚠️ TENANT-AWARE: Usa TenantTestCase para garantizar aislamiento por esquema.
"""
from django_tenants.test.cases import TenantTestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos
from apps.tenant.facturas.services import materializar_factura_desde_result

# DTO de ejemplo (COMPRA: emisor != empresa)
DTO_COMPRA = {
    "tipo": "UBL_INVOICE",
    "emisor": {"nit": "900298074", "razon_social": "GVS COLOMBIA SAS"},
    "receptor": {"nit": "901123299", "razon_social": "SINTEL TECNOLOGY S A S"},
    "numero": "FE-10020298",  # Formato con prefijo para extraer consecutivo
    "fecha_emision": "2026-01-30T00:00:00-05:00",  # Formato datetime ISO
    "totales": {
        "subtotal": 10764.00,
        "impuestos": 2045.16,
        "total": 12809.16,
        "moneda": "COP"
    },
    "identificadores": {"uuid": "CUFE-ABC"},
    "anexos": {"xml_raw": "<Invoice>...</Invoice>"},
    "extras": {}
}

# DTO de ejemplo (VENTA: emisor == empresa)
DTO_VENTA = {
    "tipo": "UBL_INVOICE",
    "emisor": {"nit": "901123299", "razon_social": "SINTEL TECNOLOGY S A S"},
    "receptor": {"nit": "900298074", "razon_social": "GVS COLOMBIA SAS"},
    "numero": "FV-001",  # Formato con prefijo para extraer consecutivo
    "fecha_emision": "2026-01-30T00:00:00-05:00",  # Formato datetime ISO
    "totales": {
        "subtotal": 1000000.00,
        "impuestos": 190000.00,
        "total": 1190000.00,
        "moneda": "COP"
    },
    "identificadores": {"uuid": "CUFE-VENTA-001"},
    "anexos": {"xml_raw": "<Invoice>...</Invoice>"},
    "extras": {}
}


class MaterializarFromDTOTests(TenantTestCase):
    """Tests para materializar_factura_desde_result."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa SSoT para el tenant
        Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY S A S",
            nit="901123299"
        )
    
    def test_compra_vs_ssot(self):
        """Test: Materializa factura COMPRA cuando emisor != empresa (SSoT)."""
        out, code = materializar_factura_desde_result(DTO_COMPRA, persist_anexos=True)
        
        self.assertIn(code, (200, 201))
        self.assertIn("id", out)
        self.assertIn("numero", out)
        self.assertEqual(out["numero"], "FE-10020298")
        
        # Verificar que se creó la factura
        f = Factura.objects.get(numero="FE-10020298")
        self.assertEqual(f.naturaleza, Factura.Naturaleza.COMPRA)
        self.assertEqual(f.emisor_nit, "900298074")
        self.assertEqual(f.receptor_nit, "901123299")
        
        # Verificar que se guardaron anexos
        self.assertTrue(FacturaAnexos.objects.filter(factura=f).exists())
        anexos = FacturaAnexos.objects.get(factura=f)
        self.assertIsNotNone(anexos.ubl_xml)
    
    def test_venta_vs_ssot(self):
        """Test: Materializa factura VENTA cuando emisor == empresa (SSoT)."""
        out, code = materializar_factura_desde_result(DTO_VENTA, persist_anexos=True)
        
        self.assertIn(code, (200, 201))
        self.assertIn("id", out)
        self.assertEqual(out["numero"], "FV-001")
        
        # Verificar que se creó la factura
        f = Factura.objects.get(numero="FV-001")
        self.assertEqual(f.naturaleza, Factura.Naturaleza.VENTA)
        self.assertEqual(f.emisor_nit, "901123299")
        self.assertEqual(f.receptor_nit, "900298074")
        # Verificar que se extrajeron prefijo y consecutivo
        self.assertEqual(f.prefijo, "FV")
        self.assertEqual(f.consecutivo, 1)
    
    def test_idempotencia_por_cufe(self):
        """Test: Idempotencia por CUFE (no duplica facturas)."""
        # Primera materialización
        out1, code1 = materializar_factura_desde_result(DTO_COMPRA, persist_anexos=True)
        self.assertEqual(code1, 201)
        self.assertTrue(out1.get("created"))
        
        # Segunda materialización (mismo CUFE)
        out2, code2 = materializar_factura_desde_result(DTO_COMPRA, persist_anexos=True)
        self.assertEqual(code2, 200)
        self.assertFalse(out2.get("created"))
        
        # Verificar que solo hay una factura
        self.assertEqual(Factura.objects.filter(numero="FE-10020298").count(), 1)
    
    def test_idempotencia_por_numero(self):
        """Test: Idempotencia por número cuando no hay CUFE."""
        dto_sin_cufe = {**DTO_COMPRA, "identificadores": {}}
        
        # Primera materialización
        out1, code1 = materializar_factura_desde_result(dto_sin_cufe, persist_anexos=True)
        self.assertEqual(code1, 201)
        
        # Segunda materialización (mismo número)
        out2, code2 = materializar_factura_desde_result(dto_sin_cufe, persist_anexos=True)
        self.assertEqual(code2, 200)
        
        # Verificar que solo hay una factura
        self.assertEqual(Factura.objects.filter(numero="FE-10020298").count(), 1)
    
    def test_sin_empresa_retorna_422(self):
        """Test: Retorna 422 si falta SSoT empresa."""
        # Eliminar empresa
        Empresa.objects.all().delete()
        
        out, code = materializar_factura_desde_result(DTO_COMPRA, persist_anexos=True)
        
        self.assertEqual(code, 422)
        self.assertIn("error", out)
        self.assertEqual(out["error"], "empresa_no_configurada")
    
    def test_sin_anexos_no_guarda_factura_anexos(self):
        """Test: Si persist_anexos=False, no guarda FacturaAnexos."""
        dto_sin_anexos = {**DTO_COMPRA, "anexos": {}}
        
        out, code = materializar_factura_desde_result(dto_sin_anexos, persist_anexos=False)
        
        self.assertIn(code, (200, 201))
        f = Factura.objects.get(numero="FE-10020298")
        
        # Verificar que NO se creó FacturaAnexos
        self.assertFalse(FacturaAnexos.objects.filter(factura=f).exists())
