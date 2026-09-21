"""
Auditoria global de tablas/filtros (2026-09-18): `ProyectoTable.render_documentos()`
accede a `record.factura_costo.cotizacion_numero` cuando `factura_costo_id`
esta presente. `selectors.qs_list()` ya tenia `select_related('factura_costo')`
pero no nombraba ningun campo suyo en `.only()` -- verificado empiricamente
(revirtiendo el fix y re-corriendo este mismo test) que esto NO causaba N+1:
Django no aplica deferred loading a un modelo select_related si `.only()` no
lo menciona en absoluto, así que cargaba TODAS las columnas de Factura via el
JOIN. Se agrego `factura_costo__cotizacion_numero` a
`_FACTURA_COSTO_LIST_TRAVERSALS` solo por el criterio "Zero Waste" (evitar
sobre-seleccionar columnas de Factura que nadie usa aqui), no por un bug de
N+1 real. Este test protege la invariante real (0 queries extra al renderizar
"documentos"), que ya se cumplia antes y se sigue cumpliendo despues.
"""
from decimal import Decimal

from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.proyectos.services import selectors
from apps.tenant.proyectos.tables import ProyectoTable
from tests.tenant.base_test import SintelTenantTestCase


class QsListFacturaCostoN1Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa N1 Test", nit="900000980", direccion="Calle N1",
        )
        factura = Factura.objects.create(
            empresa=self.empresa, numero="N1-FE-1", consecutivo=1,
            fecha_emision="2026-06-01",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="900123456", receptor_razon_social="Cliente N1",
            naturaleza=Factura.Naturaleza.VENTA, estado=Factura.Estado.ACEPTADA,
            cotizacion_numero="COT-N1-001",
        )
        for i in range(3):
            Proyecto.objects.create(
                empresa=self.empresa, nombre=f"Proyecto N1 {i}",
                factura_costo=factura, factura_costo_numero=factura.numero,
                fase_actual="EJECUCION", estado_tarea="EN_PROCESO",
            )

    def test_render_documentos_no_dispara_query_extra_por_fila(self):
        qs = selectors.qs_list(empresa_id=self.empresa.id)
        table = ProyectoTable(list(qs))

        with CaptureQueriesContext(connection) as ctx:
            htmls = [table.rows[i].get_cell("documentos") for i in range(len(table.rows))]

        for html in htmls:
            self.assertIn("COT-N1-001", str(html))

        # 3 filas, cero queries adicionales -- el N+1 real disparaba 1 query
        # POR FILA (una por cada factura_costo.cotizacion_numero deferred).
        self.assertEqual(
            len(ctx.captured_queries), 0,
            f"Se esperaban 0 queries al renderizar 'documentos' (todo ya cargado via "
            f"select_related+only), se ejecutaron {len(ctx.captured_queries)}: "
            f"{[q['sql'][:120] for q in ctx.captured_queries]}",
        )
