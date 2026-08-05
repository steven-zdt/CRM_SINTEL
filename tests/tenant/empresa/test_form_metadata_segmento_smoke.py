"""
Tests de smoke para form-metadata con segmentos_dian.

Verifica que GET /api/v1/empresa/form-metadata/ incluye segmentos_dian.
"""

import pytest
from rest_framework import status

from apps.tenant.api.tests.base import SintelTenantTestCase


@pytest.mark.django_db(transaction=True)
class FormMetadataSegmentoSmokeTest(SintelTenantTestCase):
    """
    Tests de smoke para form-metadata con segmentos_dian.
    """

    def setUp(self):
        super().setUp()
        self.form_metadata_url = "/api/v1/empresa/form-metadata/"

    def test_form_metadata_includes_segmentos_dian(self):
        """
        Verifica que GET /api/v1/empresa/form-metadata/ incluye segmentos_dian.
        """
        response = self.client.get(self.form_metadata_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Verificar que incluye segmentos_dian
        self.assertIn("segmentos_dian", data)
        segmentos_dian = data["segmentos_dian"]

        # Debe ser una lista
        self.assertIsInstance(segmentos_dian, list)
        self.assertGreater(len(segmentos_dian), 0)

        # Cada elemento debe tener 'value' y 'label'
        for segmento in segmentos_dian:
            self.assertIn("value", segmento)
            self.assertIn("label", segmento)
            self.assertIsInstance(segmento["value"], str)
            self.assertIsInstance(segmento["label"], str)

    def test_form_metadata_includes_tipo_contribuyente(self):
        """
        Verifica que form-metadata incluye tipo_contribuyente con clases y segmentos.
        """
        response = self.client.get(self.form_metadata_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Verificar estructura de tipo_contribuyente
        self.assertIn("tipo_contribuyente", data)
        tipo_contribuyente = data["tipo_contribuyente"]

        self.assertIn("clases", tipo_contribuyente)
        self.assertIn("segmentos", tipo_contribuyente)

        # Verificar clases
        clases = tipo_contribuyente["clases"]
        self.assertIsInstance(clases, list)
        self.assertGreater(len(clases), 0)

        # Verificar segmentos (por clase)
        segmentos = tipo_contribuyente["segmentos"]
        self.assertIn("PN", segmentos)
        self.assertIn("PJ", segmentos)
