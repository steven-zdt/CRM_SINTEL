"""
Tests unitarios para materializar_factura_desde_result (Fase 2).

# WARNING: TENANT-AWARE: Usa TenantTestCase para garantizar aislamiento por esquema.

F26: corregido el contrato real de materializar_desde_result() --
`business_service.py`: `dto = result.get("dto"); if not dto: return
{"error": "invalid_result", ...}, 400`. Espera un dict "resultado de
pipeline" con el DTO anidado bajo la clave "dto" (mismo shape que produce
`importar_ubl(preview=True)`), no el DTO directo. Los tests originales
llamaban `materializar_factura_desde_result(DTO_VENTA)` pasando el DTO
suelto -- siempre retornaba 400 "invalid_result" antes de llegar a ninguna
logica real. Se envuelve cada DTO en `{"dto": ...}` para ejercitar el
contrato real.
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
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567",
        )
    
    def test_compra_vs_ssot(self):
        """Test: Materializa factura COMPRA cuando emisor != empresa (SSoT)."""
        out, code = materializar_factura_desde_result({"dto": DTO_COMPRA})
        
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
        out, code = materializar_factura_desde_result({"dto": DTO_VENTA})
        
        self.assertIn(code, (200, 201))
        self.assertIn("id", out)
        self.assertEqual(out["numero"], "FV-001")
        
        # Verificar que se creó la factura
        f = Factura.objects.get(numero="FV-001")
        self.assertEqual(f.naturaleza, Factura.Naturaleza.VENTA)
        self.assertEqual(f.emisor_nit, "901123299")
        self.assertEqual(f.receptor_nit, "900298074")
        # F26: la extraccion de prefijo/consecutivo desde "numero" ocurre en
        # el parser (_parsear_prefijo_consecutivo(), ubl_parser.py:548,
        # invocada durante el parseo real del XML), NO dentro de
        # guardar_desde_dto(), que solo lee dto.get("prefijo")/dto.get("consecutivo")
        # tal cual vienen en el DTO. Este test construye el DTO a mano sin
        # pasar por el parser, por lo que ambos quedan en su default
        # ("" / 0) -- comportamiento correcto para una llamada directa a
        # materializar_desde_result(), no un bug.
        self.assertEqual(f.prefijo, "")
        self.assertEqual(f.consecutivo, 0)
    
    def test_idempotencia_por_cufe(self):
        """Test: Idempotencia por CUFE (no duplica facturas)."""
        # Primera materialización
        out1, code1 = materializar_factura_desde_result({"dto": DTO_COMPRA})
        self.assertEqual(code1, 201)
        self.assertTrue(out1.get("created"))

        # Segunda materialización (mismo CUFE)
        out2, code2 = materializar_factura_desde_result({"dto": DTO_COMPRA})
        self.assertEqual(code2, 200)
        self.assertFalse(out2.get("created"))
        
        # Verificar que solo hay una factura
        self.assertEqual(Factura.objects.filter(numero="FE-10020298").count(), 1)
    
    def test_idempotencia_por_numero(self):
        """
        F26-006 (corregido). Antes: sin CUFE, `guardar_desde_dto()` guardaba
        `cufe=""` (no `None`) y saltaba por completo la rama de idempotencia
        (`if cufe: ...`), asi que la segunda materializacion con el mismo
        numero chocaba contra la unique constraint de BD
        (`facturas_factura_cufe_key`) con un `IntegrityError` sin manejar.
        Fix: (1) fallback de idempotencia por `numero`+`empresa` cuando no
        hay CUFE (mismo criterio "ya existe" que la rama por CUFE); (2)
        `cufe` se normaliza a `None` (no `""`) al persistir, para que
        documentos legitimamente distintos sin CUFE no choquen entre si.
        """
        dto_sin_cufe = {**DTO_COMPRA, "identificadores": {}}

        out1, code1 = materializar_factura_desde_result({"dto": dto_sin_cufe})
        self.assertEqual(code1, 201)
        self.assertTrue(out1.get("created"))

        out2, code2 = materializar_factura_desde_result({"dto": dto_sin_cufe})
        self.assertEqual(code2, 200)
        self.assertFalse(out2.get("created"))
        self.assertEqual(out2.get("numero"), "FE-10020298")

        # Solo una factura -- no duplico ni exploto.
        self.assertEqual(Factura.objects.filter(numero="FE-10020298").count(), 1)

        # La factura persistida tiene cufe=None (no ""), preservando la
        # semantica de unique=True + null=True para documentos distintos.
        f = Factura.objects.get(numero="FE-10020298")
        self.assertIsNone(f.cufe)

    def test_dos_facturas_distintas_sin_cufe_no_chocan(self):
        """
        F26-006: dos documentos DIFERENTES (numero distinto) sin CUFE deben
        poder coexistir -- no es un caso de idempotencia, es la razon real
        por la que `cufe` debe normalizarse a None y no "".
        """
        dto_a = {**DTO_COMPRA, "identificadores": {}, "numero": "FE-A"}
        dto_b = {**DTO_COMPRA, "identificadores": {}, "numero": "FE-B"}

        out_a, code_a = materializar_factura_desde_result({"dto": dto_a})
        out_b, code_b = materializar_factura_desde_result({"dto": dto_b})

        self.assertEqual(code_a, 201)
        self.assertEqual(code_b, 201)
        self.assertEqual(Factura.objects.filter(cufe__isnull=True).count(), 2)
    
    def test_sin_empresa_retorna_422(self):
        """Test: Retorna 422 si falta SSoT empresa."""
        # Eliminar empresa
        Empresa.objects.all().delete()

        out, code = materializar_factura_desde_result({"dto": DTO_COMPRA})
        
        self.assertEqual(code, 422)
        self.assertIn("error", out)
        self.assertEqual(out["error"], "empresa_no_configurada")
    
    def test_sin_anexos_en_dto_igual_crea_factura_anexos_vacio(self):
        """
        F26: TEST OBSOLETO actualizado con evidencia. El parametro
        `persist_anexos` que este test ejercitaba nunca existio en
        `guardar_desde_dto()`/`FacturaCRUDService.crear()` -- el contrato real
        actual es: `anexos_data` se construye siempre como
        `{"ubl_xml": xml_text or ...}` (un dict con 1 key, por lo tanto
        siempre truthy) y `FacturaCRUDService.crear()` crea `FacturaAnexos`
        cada vez que `anexos_data` es truthy (crud_service.py:55-62) -- no
        existe ninguna rama condicional que la omita. Un DTO sin
        `anexos.xml_raw` sigue creando `FacturaAnexos` con `ubl_xml` vacio,
        no la omite.
        """
        dto_sin_anexos = {**DTO_COMPRA, "anexos": {}}

        out, code = materializar_factura_desde_result({"dto": dto_sin_anexos})

        self.assertIn(code, (200, 201))
        f = Factura.objects.get(numero="FE-10020298")

        # Contrato real actual: FacturaAnexos SIEMPRE se crea.
        self.assertTrue(FacturaAnexos.objects.filter(factura=f).exists())
