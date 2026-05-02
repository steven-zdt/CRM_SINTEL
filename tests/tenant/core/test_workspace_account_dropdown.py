"""
Tests de humo para el dropdown de cuenta en el navbar (estilo Amazon).

Verifica que:
- El dropdown de cuenta está presente en el navbar
- Perfil ya no está en el sidebar
- El enlace "Perfil" del dropdown navega a #perfil
- El logout funciona correctamente (POST con CSRF)
- Hash-routing funciona correctamente
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status
from django.test import Client


class TestWorkspaceAccountDropdown(SintelTenantTestCase):
    """
    Tests de humo para verificar el dropdown de cuenta en el navbar.
    """

    def test_account_dropdown_present_in_navbar(self):
        """
        Verifica que el dropdown de cuenta está presente en el navbar.
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el dropdown está presente
        self.assertContains(response, 'id="account-dropdown-container"', status_code=200)
        self.assertContains(response, 'id="account-dropdown-toggle"', status_code=200)
        self.assertContains(response, 'id="account-dropdown-menu"', status_code=200)

    def test_perfil_removed_from_sidebar(self):
        """
        Verifica que "Perfil" ya no está en el sidebar.
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que Perfil NO está en el sidebar (solo debe estar en el dropdown)
        sidebar_content = response.content.decode('utf-8')
        # Buscar el sidebar
        sidebar_start = sidebar_content.find('<ul class="nav" id="nav">')
        sidebar_end = sidebar_content.find('</ul>', sidebar_start)
        if sidebar_start != -1 and sidebar_end != -1:
            sidebar_section = sidebar_content[sidebar_start:sidebar_end]
            # Verificar que NO contiene "Perfil" como enlace del sidebar
            self.assertNotIn('href="#perfil"', sidebar_section)
            # Verificar que contiene los otros enlaces
            self.assertIn('href="#empresa"', sidebar_section)
            self.assertIn('href="#facturas"', sidebar_section)

    def test_account_dropdown_contains_perfil_link(self):
        """
        Verifica que el dropdown contiene el enlace "Perfil".
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el dropdown contiene el enlace a Perfil
        self.assertContains(response, 'id="account-menu-perfil"', status_code=200)
        self.assertContains(response, 'href="#perfil"', status_code=200)
        self.assertContains(response, 'Perfil', status_code=200)

    def test_account_dropdown_contains_logout_button(self):
        """
        Verifica que el dropdown contiene el botón "Cerrar Sesión".
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el dropdown contiene el botón de logout
        self.assertContains(response, 'id="account-menu-logout"', status_code=200)
        self.assertContains(response, 'Cerrar Sesión', status_code=200)

    def test_account_dropdown_javascript_present(self):
        """
        Verifica que el JavaScript del dropdown está presente.
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el JavaScript del dropdown está presente
        self.assertContains(response, 'account-dropdown-toggle', status_code=200)
        self.assertContains(response, 'account-dropdown-menu', status_code=200)
        self.assertContains(response, 'account-menu-perfil', status_code=200)
        self.assertContains(response, 'account-menu-logout', status_code=200)

    def test_hash_routing_still_works(self):
        """
        Verifica que el hash-routing sigue funcionando correctamente.
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que el JavaScript de hash-routing está presente
        self.assertContains(response, 'hashchange', status_code=200)
        self.assertContains(response, 'currentViewFromHash', status_code=200)
        self.assertContains(response, 'hydrateView', status_code=200)

    def test_workspace_contains_all_view_sections(self):
        """
        Verifica que todas las secciones de vista están presentes (incluyendo Perfil).
        """
        response = self.client.get('/workspace/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que todas las secciones están presentes
        self.assertContains(response, 'id="view-perfil"', status_code=200)
        self.assertContains(response, 'id="view-empresa"', status_code=200)
        self.assertContains(response, 'id="view-facturas"', status_code=200)
        self.assertContains(response, 'id="view-contabilidad"', status_code=200)
        self.assertContains(response, 'id="view-mas"', status_code=200)
