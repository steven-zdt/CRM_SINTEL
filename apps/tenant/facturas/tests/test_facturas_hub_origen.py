"""
Facturas Hub FASE 7-8: Factura.origen / Factura.source_system.

Cubre: guardar_desde_dto() (importacion XML, unico punto de persistencia
externa) siempre marca EXTERNO; crear_factura_desde_venta() (unico otro
punto de creacion) siempre marca INTERNO/SINTEL; el campo es inmutable
via el endpoint de edicion limitada (XML_IMMUTABLE_FIELDS).
"""
from decimal import Decimal

from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.business_service import FacturaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class FacturaOrigenTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Hub Origen", nit="900000905", direccion="Calle Hub",
        )

    def test_guardar_desde_dto_marca_externo(self):
        dto = {
            "numero": "FE-HUB-EXT-1",
            "emisor": {"nit": "800111222", "razon_social": "Proveedor XYZ"},
            "receptor": {"nit": self.empresa.nit, "razon_social": self.empresa.razon_social},
            "totales": {"subtotal": "100", "impuestos": "19", "total": "119"},
            "fecha_emision": "2026-06-01",
        }

        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, empresa_id=self.empresa.id)

        self.assertEqual(code, 201, resultado)
        factura = Factura.objects.get(numero="FE-HUB-EXT-1")
        self.assertEqual(factura.origen, Factura.Origen.EXTERNO)
        self.assertEqual(factura.source_system, Factura.SourceSystem.DESCONOCIDO)

    def test_guardar_desde_dto_respeta_source_system_declarado_en_el_dto(self):
        dto = {
            "numero": "FE-HUB-EXT-2",
            "emisor": {"nit": "800111223", "razon_social": "Proveedor ABC"},
            "receptor": {"nit": self.empresa.nit, "razon_social": self.empresa.razon_social},
            "totales": {"subtotal": "100", "impuestos": "19", "total": "119"},
            "fecha_emision": "2026-06-01",
            "source_system": Factura.SourceSystem.SIIGO,
        }

        resultado, code = FacturaBusinessService.guardar_desde_dto(dto, empresa_id=self.empresa.id)

        self.assertEqual(code, 201, resultado)
        factura = Factura.objects.get(numero="FE-HUB-EXT-2")
        self.assertEqual(factura.source_system, Factura.SourceSystem.SIIGO)

    def test_crear_factura_desde_venta_marca_interno(self):
        dto = {
            "num_fac": "FE-HUB-INT-1",
            "emisor": {"nit": self.empresa.nit, "razon_social": self.empresa.razon_social},
            "receptor": {"nit": "800000000", "razon_social": "Cliente ABC"},
            "totales": {"subtotal": "100", "impuestos": "19", "total": "119"},
            "cliente_uuid": None,
        }

        factura = FacturaBusinessService.crear_factura_desde_venta(self.empresa, dto)

        self.assertEqual(factura.origen, Factura.Origen.INTERNO)
        self.assertEqual(factura.source_system, Factura.SourceSystem.SINTEL)

    def test_origen_es_inmutable_via_edicion_limitada(self):
        factura = Factura.objects.create(
            empresa=self.empresa, numero="FE-HUB-IMMUT-1", prefijo="FE", consecutivo=1, tipo="FE",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.BORRADOR, fecha_emision="2026-06-01",
            emisor_nit=self.empresa.nit, emisor_razon_social="X", receptor_nit="800000000", receptor_razon_social="Y",
            subtotal=Decimal("1"), impuestos=Decimal("0"), total=Decimal("1"),
        )
        self.assertEqual(factura.origen, Factura.Origen.EXTERNO)  # default del campo

        with self.assertRaises(DRFValidationError):
            FacturaBusinessService.actualizar_factura_limitado(
                factura, {"origen": Factura.Origen.INTERNO}, empresa_id=self.empresa.id,
            )
