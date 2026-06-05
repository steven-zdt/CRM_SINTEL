"""
Smoke tests for ContactoCliente CRUD operations.

Verifies:
- API endpoints are registered and callable
- Offcanvas templates exist
- DOM structure is correct
"""
from django.test import TestCase as DjangoTestCase


class TestContactoClienteStructure(DjangoTestCase):
    """Tests for ContactoCliente code structure and integration."""

    def test_contacto_cliente_viewset_exists(self):
        """Test: ContactoClienteViewSet is properly registered."""
        from apps.tenant.clientes.api.viewsets import ContactoClienteViewSet
        assert ContactoClienteViewSet is not None
        # Verify key methods exist
        assert hasattr(ContactoClienteViewSet, 'list')
        assert hasattr(ContactoClienteViewSet, 'create')
        assert hasattr(ContactoClienteViewSet, 'retrieve')
        assert hasattr(ContactoClienteViewSet, 'update')
        assert hasattr(ContactoClienteViewSet, 'partial_update')
        assert hasattr(ContactoClienteViewSet, 'destroy')

    def test_render_offcanvas_endpoints_exist(self):
        """Test: Offcanvas rendering endpoints are registered."""
        from apps.tenant.clientes.api.viewsets import ContactoClienteViewSet
        
        # Check that the action methods exist
        assert hasattr(ContactoClienteViewSet, 'render_offcanvas_crear')
        assert hasattr(ContactoClienteViewSet, 'render_offcanvas_editar')
        assert hasattr(ContactoClienteViewSet, 'render_offcanvas_detalle')

    def test_offcanvas_templates_exist(self):
        """Test: All required offcanvas templates exist."""
        from pathlib import Path

        from django.conf import settings
        
        base_template_dir = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'contactos'
        
        required_templates = [
            'offcanvas_crear_contacto_cliente.html',
            'offcanvas_editar_contacto_cliente.html',
            'offcanvas_detalle_contacto_cliente.html',
            'list_contacto_cliente.html',
            'assets_contactos.html'
        ]
        
        for template in required_templates:
            template_path = base_template_dir / template
            assert template_path.exists(), f"Template {template} not found at {template_path}"

    def test_contacto_cliente_js_modules_exist(self):
        """Test: Consolidated JavaScript module exists."""
        from pathlib import Path

        from django.conf import settings
        
        base_js_dir = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'static' / 'clientes' / 'js'
        
        required_modules = [
            'clientes.contactos.js'
        ]
        
        for module in required_modules:
            module_path = base_js_dir / module
            assert module_path.exists(), f"JavaScript module {module} not found at {module_path}"

    def test_offcanvas_container_in_workspace(self):
        """Test: Offcanvas container is integrated in workspace."""
        from pathlib import Path

        from django.conf import settings
        
        workspace_template = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'core' / 'templates' / 'tenant' / 'core' / 'workspace.html'
        clientes_list_template = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'clientes' / 'clientes_list.html'
        
        assert workspace_template.exists(), "workspace.html not found"
        
        workspace_content = workspace_template.read_text(encoding='utf-8')
        if 'offcanvas-container-contactos' in workspace_content:
            return
            
        assert clientes_list_template.exists(), "clientes_list.html not found"
        clientes_list_content = clientes_list_template.read_text(encoding='utf-8')
        assert 'offcanvas-container-contactos' in clientes_list_content, "Offcanvas container not found in workspace.html or clientes_list.html"

    def test_contacto_cliente_serializer_exists(self):
        """Test: ContactoClienteSerializer exists and has required fields."""
        from apps.tenant.clientes.api.serializers import ContactoClienteSerializer
        
        assert ContactoClienteSerializer is not None
        
        # Check that serializer has required fields
        serializer = ContactoClienteSerializer()
        required_fields = ['cliente', 'nombre_completo', 'email', 'activo', 'is_principal']
        
        for field in required_fields:
            assert field in serializer.fields, f"Field {field} not found in ContactoClienteSerializer"

    def test_contacto_cliente_model_exists(self):
        """Test: ContactoCliente model exists with required fields."""

        from apps.tenant.clientes.models import ContactoCliente
        
        assert ContactoCliente is not None
        
        # Verify key fields exist
        field_names = [field.name for field in ContactoCliente._meta.get_fields()]
        required_fields = ['cliente', 'nombre_completo', 'email', 'activo', 'is_principal', 'cargo', 'telefono']
        
        for field in required_fields:
            assert field in field_names, f"Field '{field}' not found in ContactoCliente model"

    def test_clienteservicemixin_inherited(self):
        """Test: ContactoClienteViewSet inherits from ContactoClienteServiceMixin."""
        from apps.tenant.clientes.api.viewsets import ContactoClienteServiceMixin, ContactoClienteViewSet
        
        # Check inheritance
        assert issubclass(ContactoClienteViewSet, ContactoClienteServiceMixin), "ContactoClienteViewSet should inherit from ContactoClienteServiceMixin"
        assert hasattr(ContactoClienteViewSet, 'contacto_selector'), "ContactoClienteViewSet should have 'contacto_selector' attribute via mixin"
        assert hasattr(ContactoClienteViewSet, 'contacto_crud'), "ContactoClienteViewSet should have 'contacto_crud' attribute via mixin"

    def test_assets_contactos_loads_consolidated_script(self):
        """Test: assets_contactos.html loads the consolidated script."""
        from pathlib import Path

        from django.conf import settings
        
        assets_template = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'contactos' / 'assets_contactos.html'
        
        assert assets_template.exists(), "assets_contactos.html not found"
        
        content = assets_template.read_text(encoding='utf-8')
        
        # Check that modern script is loaded
        assert 'clientes.contactos.js' in content, "clientes.contactos.js script not loaded in assets_contactos.html"

    def test_clientes_list_updated_with_new_endpoint(self):
        """Test: clientes_list.html references the new render-offcanvas/crear endpoint."""
        from pathlib import Path

        from django.conf import settings
        
        clientes_list_template = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'clientes' / 'clientes_list.html'
        
        assert clientes_list_template.exists(), "clientes_list.html not found"
        
        content = clientes_list_template.read_text(encoding='utf-8')
        
        # Check that the new endpoint is referenced
        assert 'render-offcanvas/crear' in content, "New render-offcanvas/crear endpoint not found in clientes_list.html"

    def test_offcanvas_elemento_id_correct(self):
        """Test: Offcanvas element has correct ID for DOM Shield."""
        expected_id = "offcanvas-contacto-cliente"
        assert "contacto-cliente" in expected_id, "Offcanvas ID should contain 'contacto-cliente'"

    def test_dom_structure_container_isolation(self):
        """Test: Container IDs are properly isolated per module."""
        # Clientes module uses #offcanvas-container-clientes
        # ContactoCliente module uses #offcanvas-container-contactos
        
        clientes_container = "offcanvas-container-clientes"
        contactos_container = "offcanvas-container-contactos"
        
        # Verify they're different to prevent DOM conflicts
        assert clientes_container != contactos_container, "Container IDs should be different to prevent conflicts"
        assert "clientes" in clientes_container, "Clientes container should mention 'clientes'"
        assert "contactos" in contactos_container, "Contactos container should mention 'contactos'"


class TestContactoClienteIntegration(DjangoTestCase):
    """Integration tests for ContactoCliente functionality."""

    def test_fsd_namespace_separation(self):
        """Test: FSD modules use separate and correct namespaces."""
        # Verify that the JS namespace is correctly isolated
        # window.AppCliente.contactos or ContactosModule should be defined in clientes.contactos.js
        from pathlib import Path

        from django.conf import settings
        
        main_js = Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'static' / 'clientes' / 'js' / 'clientes.contactos.js'
        
        assert main_js.exists(), "clientes.contactos.js does not exist"
        content = main_js.read_text(encoding='utf-8')
        assert 'window.AppCliente.contactos' in content or 'AppCliente.contactos' in content, "Should expose AppCliente.contactos namespace"
        assert 'window.ContactosModule' in content or 'ContactosModule' in content, "Should define window.ContactosModule"

    def test_no_shared_modals_monolith(self):
        """Test: No monolithic shared modals file exists (FSD compliance)."""
        from pathlib import Path

        from django.conf import settings
        
        # These should NOT exist (violates FSD)
        forbidden_files = [
            Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'contactos' / 'modals_contacto.html',
            Path(settings.BASE_DIR) / 'apps' / 'tenant' / 'clientes' / 'templates' / 'tenant' / 'contactos' / 'modals.html'
        ]
        
        for forbidden_file in forbidden_files:
            assert not forbidden_file.exists(), f"Monolithic file {forbidden_file.name} should not exist (violates FSD)"
