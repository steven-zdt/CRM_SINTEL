"""
Tests de UI/estructura del template workspace.html.

Verifica que:
- GET /workspace/ (autenticado en dominio tenant) devuelve 200
- La respuesta contiene el layout esperado y IDs/selectores críticos
- El JS embebido incluye helpers necesarios
"""

from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase


class TestWorkspaceUI(SintelTenantTestCase):
    """
    Tests para verificar la estructura y elementos del template workspace.html.
    """

    def test_workspace_returns_200_when_authenticated(self):
        """
        Verifica que GET /workspace/ retorna 200 cuando el usuario está autenticado.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "workspace", status_code=200)

    def test_workspace_contains_sidebar_structure(self):
        """
        Verifica que el template contiene la estructura del sidebar.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar elementos del sidebar
        self.assertContains(response, 'id="sidebar"', status_code=200)
        self.assertContains(response, 'id="nav"', status_code=200)

        # Verificar botones de navegación
        self.assertContains(response, 'data-view="perfil"', status_code=200)
        self.assertContains(response, 'data-view="empresa"', status_code=200)
        self.assertContains(response, 'data-view="facturas"', status_code=200)
        self.assertContains(response, 'data-view="contabilidad"', status_code=200)
        self.assertContains(response, 'data-view="mas"', status_code=200)

    def test_workspace_contains_view_sections(self):
        """
        Verifica que el template contiene todas las secciones de vista.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar secciones de vista
        self.assertContains(response, 'id="view-perfil"', status_code=200)
        self.assertContains(response, 'id="view-empresa"', status_code=200)
        self.assertContains(response, 'id="view-facturas"', status_code=200)
        self.assertContains(response, 'id="view-contabilidad"', status_code=200)
        self.assertContains(response, 'id="view-mas"', status_code=200)

    def test_workspace_contains_action_buttons(self):
        """
        Verifica que el template contiene los botones de acción críticos.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar botones de acción
        self.assertContains(response, 'id="btn-save-perfil"', status_code=200)
        self.assertContains(response, 'id="btn-save-empresa"', status_code=200)

    def test_workspace_contains_perfil_form_fields(self):
        """
        Verifica que el template contiene los campos del formulario de perfil.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar campos del formulario de perfil
        self.assertContains(response, 'id="pf_nombre"', status_code=200)
        self.assertContains(response, 'id="pf_email"', status_code=200)
        self.assertContains(response, 'id="pf_cargo"', status_code=200)
        self.assertContains(response, 'id="pf_departamento"', status_code=200)
        self.assertContains(response, 'id="pf_telefono"', status_code=200)
        self.assertContains(response, 'id="pf_config"', status_code=200)

    def test_workspace_contains_empresa_form_fields(self):
        """
        Verifica que el template contiene los campos del formulario de empresa.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar campos del formulario de empresa
        self.assertContains(response, 'id="em_razon_social"', status_code=200)
        self.assertContains(response, 'id="em_nit"', status_code=200)
        self.assertContains(response, 'id="em_dv"', status_code=200)
        self.assertContains(response, 'id="em_direccion"', status_code=200)
        self.assertContains(response, 'id="em_telefono"', status_code=200)
        self.assertContains(response, 'id="em_email_contacto"', status_code=200)

    def test_workspace_contains_js_http_helper(self):
        """
        Verifica que el template incluye el helper http() con credentials: "same-origin".
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el JS incluye el helper http
        self.assertContains(response, 'credentials: "same-origin"', status_code=200)
        self.assertContains(response, "async function http", status_code=200)

    def test_workspace_contains_401_redirect_logic(self):
        """
        Verifica que el template incluye la lógica de redirección a /login/ en caso de 401.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el JS maneja 401 y redirige a login
        self.assertContains(response, "res.status === 401", status_code=200)
        self.assertContains(response, "/login/", status_code=200)
        self.assertContains(response, "next=", status_code=200)

    def test_workspace_contains_status_elements(self):
        """
        Verifica que el template contiene elementos de estado para mostrar mensajes.
        """
        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar elementos de estado
        self.assertContains(response, 'id="status-perfil"', status_code=200)
        self.assertContains(response, 'id="status-empresa"', status_code=200)
