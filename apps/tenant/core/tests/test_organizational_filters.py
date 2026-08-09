"""
Tests de apps/tenant/core/services/organizational_filters.py.

`filter_by_scope()` (F5) asume que `sede`/`area` son campos NOT NULL o que
un NULL simplemente no debe verse por nadie mas que EMPRESA (correcto para
compras.OrdenCompra, donde sede es obligatoria). `filter_by_scope_null_safe()`
(F7) es la variante para los 6 modelos donde sede/area es opcional Y el
100% de los datos reales existentes esta en NULL (verificado empiricamente
en Fase F7) - un NULL debe quedar visible para todos los alcances, no solo
EMPRESA, para no ocultar datos existentes al activar el filtrado.
"""
from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.core.services.organizational_filters import (
    filter_by_scope,
    filter_by_scope_null_safe,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class FilterByScopeTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F7", nit="900000555", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F7")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F7")

    def test_filter_by_scope_estricto_excluye_sede_no_asignada(self):
        """OrdenCompra.sede es NOT NULL - filter_by_scope() (F5) es correcto
        sin NULL-safety aqui."""
        proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Prov F7", numero_documento="F7-1", tipo_documento="NIT",
        )
        plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F7", prefijo="F7",
            rango_desde=1, rango_hasta=100, consecutivo_actual=1, vigente=True,
        )
        orden_a = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_a, proveedor=proveedor,
            plantilla=plantilla, fecha="2026-06-01", consecutivo=1,
        )
        OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_b, proveedor=proveedor,
            plantilla=plantilla, fecha="2026-06-01", consecutivo=2,
        )

        qs = filter_by_scope(
            OrdenCompra.objects.all(), self.empresa.id, sede_ids=frozenset({self.sede_a.id}),
        )

        self.assertEqual(set(qs.values_list("id", flat=True)), {orden_a.id})

    def _crear_factura(self, numero, sede=None):
        return Factura.objects.create(
            empresa=self.empresa,
            numero=numero,
            emisor_nit="900298074",
            emisor_razon_social="Proveedor Test F7",
            receptor_nit=self.empresa.nit,
            receptor_razon_social=self.empresa.razon_social,
            fecha_emision="2026-06-01T00:00:00Z",
            consecutivo=1,
            subtotal=100, impuestos=19, total=119,
            sede=sede,
        )

    def test_filter_by_scope_null_safe_deja_visible_lo_no_clasificado(self):
        """[OSF F7] Hallazgo real: el 100% de las Facturas reales tiene
        sede=NULL hoy. Un registro sin sede debe quedar visible para
        cualquier alcance - de lo contrario, activar el scoping ocultaria
        toda la data existente a un usuario con alcance SEDE."""
        factura_sin_sede = self._crear_factura("F7-SIN-SEDE")
        factura_sede_a = self._crear_factura("F7-SEDE-A", sede=self.sede_a)
        factura_sede_b = self._crear_factura("F7-SEDE-B", sede=self.sede_b)

        qs = filter_by_scope_null_safe(
            Factura.objects.all(), self.empresa.id, sede_ids=frozenset({self.sede_a.id}),
        )
        ids = set(qs.values_list("id", flat=True))

        self.assertIn(factura_sin_sede.id, ids)
        self.assertIn(factura_sede_a.id, ids)
        self.assertNotIn(factura_sede_b.id, ids)

    def test_filter_by_scope_null_safe_sin_restriccion_para_alcance_empresa(self):
        self._crear_factura("F7-A")
        self._crear_factura("F7-B", sede=self.sede_a)

        qs = filter_by_scope_null_safe(Factura.objects.all(), self.empresa.id, sede_ids=None)

        self.assertEqual(qs.count(), 2)
