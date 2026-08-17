"""
Smoke tests de templates para la app impuestos.

Verifica que los endpoints API no renderizan templates HTML.
"""

from apps.config.tests.base_public import PublicAPITestCase


class ImpuestosTemplateTests(PublicAPITestCase):
    """Tests de templates para endpoints de impuestos."""

    def test_api_endpoints_no_render_templates(self):
        """Test: Los endpoints /api/public/v1/impuestos/ no renderizan templates."""
        endpoints = [
            "/api/public/v1/impuestos/tipos/",
            "/api/public/v1/impuestos/tarifas-iva/",
            "/api/public/v1/impuestos/conceptos-retencion/",
            "/api/public/v1/impuestos/codigos-tributarios/",
            "/api/public/v1/impuestos/actividades-economicas/",
        ]

        for endpoint in endpoints:
            response = self.json("get", endpoint)
            self.assertEqual(response["content-type"], "application/json")
            self.assertNotIn("text/html", response["content-type"])
