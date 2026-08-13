"""
F31.6 -- Migracion de grillas de Inventario (Tabulator -> django-tables2 + HTMX).

Verifica las 4 vistas server-rendered ya wireadas en urls.py (categoria-tabla,
producto-tabla, servicio-tabla, activo-tabla) que reemplazan la
inicializacion de Tabulator en categorias_list.js/productos_list.js/
servicios_list.js/activos_list.js. "movimientos" (Kardex) queda fuera de
alcance -- ver docstring de apps/tenant/inventario/tables.py.

No existia cobertura previa para estas vistas (el backend -- tables.py/
views.py -- se habia comiteado sin tests en un pase anterior, commit
60d8a33). FALTA COBERTURA CRITICA -> CREAR (regla de F31: reutilizar >
corregir > consolidar > crear).
"""
from django.urls import reverse

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import ActivoFijo, CategoriaItem, Producto, Servicio
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class InventarioTablasHtmxTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F31 Inventario", nit="900000996", direccion="Calle 1",
        )
        TenantProfile.objects.get_or_create(
            user=self.user, defaults={"empresa": self.empresa, "rol": "ADMIN", "alcance": "EMPRESA"},
        )

    def test_categoria_tabla_renderiza_categoria_existente(self):
        CategoriaItem.objects.create(empresa=self.empresa, nombre="Categoria F31 Test")

        response = self.client.get(reverse("inventario:categoria-tabla"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Categoria F31 Test")
        self.assertContains(response, "btn-edit-categoria")
        self.assertContains(response, "btn-delete-categoria")

    def test_categoria_tabla_boton_acciones_usa_uuid_no_id(self):
        """
        Regresion: el JS legacy (pre-migracion) enviaba data-id=<int PK> a
        endpoints que exigen uuid (get_object()/service_categoria_get_offcanvas_context
        usan CategoriaItemSelector.get_detail(categoria_uuid=...)) -- un bug
        WRONG_LOOKUP real, nunca antes visible porque el boton nunca se habia
        probado. La tabla server-rendered ya usa data-uuid (tables.py); este
        test fija el contrato para que no regrese a data-id.
        """
        cat = CategoriaItem.objects.create(empresa=self.empresa, nombre="Categoria UUID Test")

        response = self.client.get(reverse("inventario:categoria-tabla"))

        self.assertContains(response, f'data-uuid="{cat.uuid}"')

    def test_producto_tabla_renderiza_producto_y_kpis(self):
        Producto.objects.create(
            empresa=self.empresa, codigo="SKU-F31", nombre="Producto F31 Test",
            stock_actual=10, stock_minimo=2, precio_venta=1000, costo_promedio=500,
        )

        response = self.client.get(reverse("inventario:producto-tabla"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Producto F31 Test")
        self.assertContains(response, "SKUs")
        self.assertContains(response, "btn-ver-kardex")

    def test_servicio_tabla_renderiza_servicio_existente(self):
        Servicio.objects.create(empresa=self.empresa, codigo="SRV-F31", nombre="Servicio F31 Test")

        response = self.client.get(reverse("inventario:servicio-tabla"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Servicio F31 Test")

    def test_activo_tabla_renderiza_activo_y_kpis(self):
        ActivoFijo.objects.create(
            empresa=self.empresa, codigo="ACT-F31", nombre="Activo F31 Test", estado="ACTIVO",
        )

        response = self.client.get(reverse("inventario:activo-tabla"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activo F31 Test")
        self.assertContains(response, "En Uso")

    def test_categoria_tabla_filtra_por_busqueda(self):
        CategoriaItem.objects.create(empresa=self.empresa, nombre="Electrodomesticos")
        CategoriaItem.objects.create(empresa=self.empresa, nombre="Ferreteria")

        response = self.client.get(reverse("inventario:categoria-tabla"), {"q": "Electro"})

        self.assertContains(response, "Electrodomesticos")
        self.assertNotContains(response, "Ferreteria")
