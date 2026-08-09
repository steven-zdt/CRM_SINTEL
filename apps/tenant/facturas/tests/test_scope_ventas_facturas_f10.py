"""
Fase F10 (proyecto OSF), "Ventas -> Facturas con contexto organizacional":
`crear_factura_desde_venta()` nunca propagaba ningun dato de sede - una
Factura generada automaticamente desde una Venta siempre quedaba con
`sede=None`, sin importar la sede activa de quien facturaba. `Venta` no
tiene campo `sede` propio (F6: candidato plausible sin campo aun), asi que
lo que se transporta es el contexto de QUIEN factura (OrganizationalContext,
sede ACTIVA - mismo criterio que compras usa para defaultear OrdenCompra.sede
en F5), no un campo de la Venta. Se transporta como dato plano dentro del
DTO ya existente (`dto["sede_id"]`, mismo patron que `cliente_uuid`/
`venta_uuid`) - nunca una FK directa Ventas->Facturas.
"""
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.services.business_service import FacturaBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class VentaFacturaScopeF10Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F10", nit="900000784", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F10")

    def test_crear_factura_desde_venta_propaga_sede_id_del_dto(self):
        dto = {"sede_id": self.sede_a.id}

        factura = FacturaBusinessService.crear_factura_desde_venta(self.empresa, dto)

        self.assertEqual(factura.sede_id, self.sede_a.id)

    def test_crear_factura_desde_venta_sin_sede_id_queda_en_none(self):
        """Comportamiento identico al de antes de esta fase para el caso
        sin contexto (ej. facturacion por lote/celery sin usuario activo)."""
        dto = {}

        factura = FacturaBusinessService.crear_factura_desde_venta(self.empresa, dto)

        self.assertIsNone(factura.sede_id)

    def test_crear_factura_desde_venta_ignora_sede_inexistente_anti_idor(self):
        """`Empresa` es singleton por esquema tenant (constraint `singleton_key`,
        apps/tenant/empresa/models.py:48): el aislamiento entre companias distintas
        se da por esquema Postgres separado, no por multiples filas `Empresa` en un
        mismo esquema, asi que no se puede modelar aqui una "sede de otra empresa"
        creando una segunda `Empresa`. Se ejercita en cambio el mismo camino
        defensivo (`Sede.objects.filter(id=..., empresa_id=empresa.id).first()`)
        con un sede_id que no corresponde a ninguna Sede del tenant."""
        sede_id_inexistente = self.sede_a.id + 999999
        dto = {"sede_id": sede_id_inexistente}

        factura = FacturaBusinessService.crear_factura_desde_venta(self.empresa, dto)

        self.assertIsNone(factura.sede_id)
