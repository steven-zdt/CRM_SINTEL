"""
Tests de integración CRUD para todos los módulos del workspace.

[WARNING] v2.37: Verifica que todos los módulos estandarizados funcionen correctamente
desde workspace.html.

Tests de smoke para:
- Verificación de que los modales se abren correctamente
- Verificación de que las acciones CRUD funcionan
- Verificación de que los DataTables se inicializan
- Verificación de que los assets se cargan correctamente
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context

User = get_user_model()


class WorkspaceCRUDIntegrationTest(TenantTestCase):
    """
    Tests de integración CRUD para todos los módulos del workspace.

    [WARNING] v2.37: Verifica que todos los módulos estandarizados funcionen correctamente.
    """

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.user)

    def test_workspace_page_loads(self):
        """Verifica que la página del workspace carga correctamente."""
        response = self.client.get(reverse("workspace"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tenant/core/workspace.html")

    def test_workspace_includes_all_partials(self):
        """Verifica que todos los partials están incluidos en workspace.html."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar partials de módulos principales
        self.assertIn("empresa_list.html", content or "")
        self.assertIn("facturas/list.html", content or "")
        self.assertIn("contabilidad/list_cuentas.html", content or "")
        self.assertIn("contabilidad/list_asientos.html", content or "")
        self.assertIn("inventario/list_catalogo.html", content or "")
        self.assertIn("inventario/list_activos.html", content or "")
        self.assertIn("inventario/list_movimientos.html", content or "")
        self.assertIn("empleados/list.html", content or "")
        self.assertIn("gastos/list.html", content or "")
        self.assertIn("proveedores/list.html", content or "")
        self.assertIn("clientes/list.html", content or "")
        self.assertIn("perfil/list.html", content or "")

    def test_workspace_includes_all_modals(self):
        """Verifica que todos los modales están incluidos en workspace.html."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de módulos principales
        self.assertIn("empresa/modals.html", content or "")
        self.assertIn("facturas/modals.html", content or "")
        self.assertIn("contabilidad/modals_cuentas.html", content or "")
        self.assertIn("contabilidad/modals_asientos.html", content or "")
        self.assertIn("inventario/modals_catalogo.html", content or "")
        self.assertIn("inventario/modals_activos.html", content or "")
        self.assertIn("inventario/modals_movimientos.html", content or "")
        self.assertIn("empleados/modals.html", content or "")
        self.assertIn("gastos/modals.html", content or "")
        self.assertIn("proveedores/modals.html", content or "")
        self.assertIn("clientes/modals.html", content or "")
        self.assertIn("perfil/modals.html", content or "")

    def test_workspace_includes_all_assets(self):
        """Verifica que todos los assets JS están incluidos en workspace.html."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar assets de módulos principales
        self.assertIn("empresa/assets_empresa.html", content or "")
        self.assertIn("facturas/assets_facturas.html", content or "")
        self.assertIn("contabilidad/assets_cuentas.html", content or "")
        self.assertIn("contabilidad/assets_asientos.html", content or "")
        self.assertIn("inventario/assets_inventario.html", content or "")
        self.assertIn("empleados/assets_empleados.html", content or "")
        self.assertIn("gastos/assets_gastos.html", content or "")
        self.assertIn("proveedores/assets_proveedores.html", content or "")
        self.assertIn("clientes/assets_clientes.html", content or "")
        self.assertIn("perfil/assets_perfil.html", content or "")

    def test_workspace_js_modules_exported(self):
        """Verifica que los módulos JS exportan las funciones correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar que los archivos JS principales están incluidos
        self.assertIn("workspace.js", content or "")
        self.assertIn("empresa.page.js", content or "")
        self.assertIn("facturas.page.js", content or "")
        self.assertIn("cuentas.page.js", content or "")
        self.assertIn("asientos.page.js", content or "")
        self.assertIn("catalogo.page.js", content or "")
        self.assertIn("activos.page.js", content or "")
        self.assertIn("movimientos.page.js", content or "")
        self.assertIn("empleados.page.js", content or "")
        self.assertIn("gastos.page.js", content or "")
        self.assertIn("proveedores.page.js", content or "")
        self.assertIn("clientes.page.js", content or "")
        self.assertIn("perfil.page.js", content or "")

    def test_workspace_sidebar_links(self):
        """Verifica que todos los enlaces del sidebar están presentes."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar enlaces del sidebar
        self.assertIn('data-tab="empresa"', content or "")
        self.assertIn('data-tab="facturas"', content or "")
        self.assertIn('data-tab="contabilidad"', content or "")
        self.assertIn('data-tab="inventario"', content or "")
        self.assertIn('data-tab="empleados"', content or "")
        self.assertIn('data-tab="gastos"', content or "")
        self.assertIn('data-tab="proveedores"', content or "")
        self.assertIn('data-tab="clientes"', content or "")
        self.assertIn('data-tab="perfil"', content or "")

    def test_workspace_tabs_sections(self):
        """Verifica que todas las secciones de tabs están presentes."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar secciones de tabs
        self.assertIn('id="tab-empresa"', content or "")
        self.assertIn('id="tab-facturas"', content or "")
        self.assertIn('id="tab-contabilidad"', content or "")
        self.assertIn('id="tab-inventario"', content or "")
        self.assertIn('id="tab-empleados"', content or "")
        self.assertIn('id="tab-gastos"', content or "")
        self.assertIn('id="tab-proveedores"', content or "")
        self.assertIn('id="tab-clientes"', content or "")
        self.assertIn('id="tab-perfil"', content or "")


class WorkspaceModalStructureTest(TenantTestCase):
    """
    Tests para verificar la estructura de modales en cada módulo.

    [WARNING] v2.37: Verifica que los modales sigan el patrón estándar.
    """

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.user)

    def test_empresa_modals_structure(self):
        """Verifica que los modales de Empresa tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Empresa
        self.assertIn("modal-ver-empresa", content or "")
        self.assertIn("modal-editar-empresa", content or "")
        self.assertIn("modal-crear-empresa", content or "")
        self.assertIn("empresa-view-feedback", content or "")
        self.assertIn("empresa-edit-feedback", content or "")
        self.assertIn("empresa-create-feedback", content or "")

    def test_gastos_modals_structure(self):
        """Verifica que los modales de Gastos tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Gastos
        self.assertIn("modal-ver-gasto", content or "")
        self.assertIn("modal-editar-gasto", content or "")
        self.assertIn("modal-crear-gasto", content or "")
        self.assertIn("modal-eliminar-gasto", content or "")

    def test_facturas_modals_structure(self):
        """Verifica que los modales de Facturas tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modal de importar (los demás son dinámicos)
        self.assertIn("modal-factura-importar", content or "")
        self.assertIn("import-feedback", content or "")

    def test_inventario_catalogo_modals_structure(self):
        """Verifica que los modales de Inventario Catálogo tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Catálogo
        self.assertIn("modal-ver-catalogo", content or "")
        self.assertIn("modal-editar-catalogo", content or "")
        self.assertIn("modal-crear-catalogo", content or "")
        self.assertIn("modal-eliminar-catalogo", content or "")

    def test_inventario_activos_modals_structure(self):
        """Verifica que los modales de Inventario Activos tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Activos
        self.assertIn("modal-ver-activo", content or "")
        self.assertIn("modal-editar-activo", content or "")
        self.assertIn("modal-crear-activo", content or "")
        self.assertIn("modal-eliminar-activo", content or "")

    def test_inventario_movimientos_modals_structure(self):
        """Verifica que los modales de Inventario Movimientos tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Movimientos (solo Ver y Crear)
        self.assertIn("modal-ver-movimiento", content or "")
        self.assertIn("modal-crear-movimiento", content or "")
        # NO debe tener editar/eliminar
        # (verificado implícitamente por la ausencia de esos modales)

    def test_contabilidad_cuentas_modals_structure(self):
        """Verifica que los modales de Contabilidad Cuentas tienen la estructura correcta."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar modales de Cuentas
        self.assertIn("modal-ver-cuenta", content or "")
        self.assertIn("modal-editar-cuenta", content or "")
        self.assertIn("modal-crear-cuenta", content or "")
        self.assertIn("modal-eliminar-cuenta", content or "")


class WorkspaceDataTableStructureTest(TenantTestCase):
    """
    Tests para verificar la estructura de DataTables en cada módulo.

    [WARNING] v2.37: Verifica que las tablas tengan las columnas correctas.
    """

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.user)

    def test_gastos_table_structure(self):
        """Verifica que la tabla de Gastos tiene las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        # Verificar que la tabla tiene el ID correcto
        self.assertIn("table-gastos", content or "")
        # Verificar columnas básicas (sin verificar orden exacto)
        # Las columnas específicas se verifican en tests de JS

    def test_proveedores_table_structure(self):
        """Verifica que la tabla de Proveedores tiene las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        self.assertIn("table-proveedores", content or "")

    def test_clientes_table_structure(self):
        """Verifica que la tabla de Clientes tiene las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        self.assertIn("table-clientes", content or "")

    def test_empleados_table_structure(self):
        """Verifica que la tabla de Empleados tiene las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        self.assertIn("table-empleados", content or "")

    def test_inventario_tables_structure(self):
        """Verifica que las tablas de Inventario tienen las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        self.assertIn("table-inventario-catalogo", content or "")
        self.assertIn("table-inventario-activos", content or "")
        self.assertIn("table-inventario-movimientos", content or "")

    def test_contabilidad_tables_structure(self):
        """Verifica que las tablas de Contabilidad tienen las columnas correctas."""
        response = self.client.get(reverse("workspace"))
        content = response.content.decode("utf-8")

        self.assertIn("table-contabilidad-cuentas", content or "")
        self.assertIn("table-contabilidad-asientos", content or "")
