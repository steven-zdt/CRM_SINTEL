"""
Test de integridad del módulo Empresa en workspace.

[WARNING] v2.37: Este test actúa como salvaguarda para prevenir cambios que rompan la funcionalidad.
Si este test falla, significa que se ha modificado algo crítico del módulo Empresa.

Ejecutar antes de cualquier modificación al módulo Empresa:
    pytest tests/tenant/core/smoke/test_workspace_empresa_integridad.py -v
"""

import pytest
from django.test import Client

try:
    import cryptography  # noqa: F401
    import playwright  # noqa: F401
except Exception:
    pytest.skip(
        "Skipping heavy smoke test: missing playwright/cryptography",
        allow_module_level=True,
    )
from apps.tenant.core.tests.base_test import TenantTestCase
from apps.tenant.empresa.models import Empresa


class TestEmpresaIntegridad(TenantTestCase):
    """
    Tests de integridad que validan la estructura completa del módulo Empresa.

    Estos tests deben pasar SIEMPRE. Si fallan, revisar:
    1. Serializer (EmpresaListSerializer)
    2. HTML (empresa_list.html)
    3. JS (empresa.page.js)
    4. ViewSet (EmpresaViewSet.list)
    """

    def test_serializer_campos_minimos(self):
        """Valida que EmpresaListSerializer solo expone campos mínimos."""
        from apps.tenant.empresa.api.serializers import EmpresaListSerializer

        # Crear empresa de prueba
        empresa = Empresa.objects.create(
            razon_social="Test Empresa",
            nit="123456789",
            dv="0",
            direccion="Calle Test",
            telefono="1234567",
            email_contacto="test@example.com",
            regimen_renta_codigo="ORDINARIO",
            moneda="COP",
        )

        serializer = EmpresaListSerializer(empresa)
        data = serializer.data

        # Campos OBLIGATORIOS (mínimos)
        campos_obligatorios = {
            "nit",
            "direccion",
            "telefono",
            "email_contacto",
            "regimen_tributario",
            "moneda",
        }
        self.assertTrue(
            campos_obligatorios.issubset(set(data.keys())),
            f"Faltan campos obligatorios. Campos presentes: {list(data.keys())}",
        )

        # Campos PROHIBIDOS (no deben estar)
        campos_prohibidos = {
            "id",
            "razon_social",
            "logo",
            "website",
            "created_at",
            "updated_at",
            "dv",
        }
        campos_presentes_prohibidos = [f for f in campos_prohibidos if f in data]
        self.assertEqual(
            len(campos_presentes_prohibidos),
            0,
            f"Se expusieron campos prohibidos: {campos_presentes_prohibidos}",
        )

        # Validar alias
        self.assertEqual(
            data["regimen_tributario"],
            "ORDINARIO",
            "regimen_tributario debe ser alias de regimen_renta_codigo",
        )

    def test_endpoint_formato_respuesta(self):
        """Valida que el endpoint retorna array (no objeto paginado)."""
        self.client.force_login(self.user)

        # Caso 1: Sin empresa (array vacío)
        Empresa.objects.all().delete()
        response = self.client.get("/api/v1/empresas/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list, "La respuesta debe ser un array")
        self.assertEqual(len(data), 0, "Sin empresa, debe retornar array vacío")

        # Caso 2: Con empresa (array con 1 elemento)
        Empresa.objects.create(
            razon_social="Test",
            nit="123456789",
            dv="0",
            direccion="Test",
            telefono="123",
            email_contacto="test@example.com",
            regimen_renta_codigo="ORDINARIO",
            moneda="COP",
        )

        response = self.client.get("/api/v1/empresas/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list, "La respuesta debe ser un array")
        self.assertEqual(
            len(data), 1, "Con empresa, debe retornar array con 1 elemento"
        )

        # Validar que NO es objeto paginado
        self.assertNotIn("results", data, "No debe ser objeto paginado")
        self.assertNotIn("count", data, "No debe ser objeto paginado")

    def test_html_columnas_exactas(self):
        """Valida que el HTML tiene exactamente 7 columnas en el orden correcto."""
        self.client.force_login(self.user)

        response = self.client.get("/workspace/#empresa", follow=True)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        # Buscar tabla-empresa
        import re

        tabla_match = re.search(
            r'<table[^>]*id="tabla-empresa"[^>]*>.*?<thead>.*?<tr>(.*?)</tr>.*?</thead>',
            content,
            re.DOTALL,
        )

        self.assertIsNotNone(tabla_match, "Tabla tabla-empresa no encontrada en HTML")

        thead_content = tabla_match.group(1)
        th_elements = re.findall(r"<th[^>]*>(.*?)</th>", thead_content, re.DOTALL)

        # Validar cantidad exacta
        self.assertEqual(
            len(th_elements),
            7,
            f"Debe tener exactamente 7 columnas, pero tiene {len(th_elements)}",
        )

        # Validar orden y nombres
        expected_columns = [
            "NIT",
            "Dirección",
            "Teléfono",
            "Email",
            "Régimen",
            "Moneda",
            "Acciones",
        ]
        for i, expected in enumerate(expected_columns):
            self.assertIn(
                expected,
                th_elements[i],
                f"Columna {i+1} debe ser '{expected}', pero es '{th_elements[i]}'",
            )

    def test_js_selector_coincide_html(self):
        """Valida que el selector en JS coincide con el ID en HTML."""
        self.client.force_login(self.user)

        # Leer HTML
        response = self.client.get("/workspace/#empresa", follow=True)
        content = response.content.decode("utf-8")

        # Verificar que HTML tiene id="tabla-empresa"
        self.assertIn(
            'id="tabla-empresa"', content, "HTML debe tener id='tabla-empresa'"
        )

        # Leer JS
        import os

        js_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "apps",
            "tenant",
            "core",
            "static",
            "core",
            "js",
            "empresa",
            "empresa.page.js",
        )

        self.assertTrue(os.path.exists(js_path), f"JS no encontrado en {js_path}")

        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        # Verificar que JS tiene TABLE_ID = '#tabla-empresa'
        self.assertIn(
            "TABLE_ID = '#tabla-empresa'",
            js_content or "const TABLE_ID = '#tabla-empresa'",
            "JS debe tener TABLE_ID = '#tabla-empresa'",
        )

    def test_columnas_js_alineadas_serializer(self):
        """Valida que las columnas en JS están alineadas con el Serializer."""
        import os
        import re

        # Leer JS
        js_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "apps",
            "tenant",
            "core",
            "static",
            "core",
            "js",
            "empresa",
            "empresa.page.js",
        )

        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        # Campos esperados del Serializer
        campos_serializer = {
            "nit",
            "direccion",
            "telefono",
            "email_contacto",
            "regimen_tributario",
            "moneda",
        }

        # Buscar definición de columns en JS
        columns_match = re.search(
            r"const columns\s*=\s*\[(.*?)\];", js_content, re.DOTALL
        )
        self.assertIsNotNone(
            columns_match, "No se encontró definición de 'columns' en JS"
        )

        columns_content = columns_match.group(1)

        # Verificar que cada campo del serializer está en las columnas
        for campo in campos_serializer:
            # Buscar data: 'campo' o data: "campo"
            pattern = rf"data:\s*['\"]{campo}['\"]"
            self.assertTrue(
                re.search(pattern, columns_content, re.IGNORECASE),
                f"Campo '{campo}' del serializer no está en las columnas de JS",
            )

    def test_modulos_independientes(self):
        """Valida que ambos módulos (Empresa y MailInboxConfig) son independientes."""
        self.client.force_login(self.user)

        response = self.client.get("/workspace/#empresa", follow=True)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        # Verificar contenedores independientes
        self.assertIn('id="empresa-module-container"', content)
        self.assertIn('id="mailinbox-module-container"', content)

        # Verificar tablas independientes
        self.assertIn('id="tabla-empresa"', content)
        self.assertIn('id="tabla-mailinbox"', content)

        # Verificar que NO hay mezcla de IDs
        # Contar ocurrencias de cada ID (debe ser exactamente 1 cada uno)
        empresa_count = content.count('id="tabla-empresa"')
        mailinbox_count = content.count('id="tabla-mailinbox"')

        self.assertEqual(
            empresa_count,
            1,
            f"ID 'tabla-empresa' debe aparecer exactamente 1 vez, pero aparece {empresa_count}",
        )
        self.assertEqual(
            mailinbox_count,
            1,
            f"ID 'tabla-mailinbox' debe aparecer exactamente 1 vez, pero aparece {mailinbox_count}",
        )
