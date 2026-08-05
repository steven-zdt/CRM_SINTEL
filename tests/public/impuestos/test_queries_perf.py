"""
Tests de performance para verificar que no hay queries N+1.

Valida límites de queries con assertNumQueries y optimizaciones
con select_related/prefetch_related.
"""

import pytest
from django.db import connection, reset_queries
from django.test import TestCase
from django.urls import reverse

from apps.public.impuestos.models import DocumentoFuente, NormaTributaria, TipoImpuesto


@pytest.mark.django_db
class TestQueriesPerf(TestCase):
    """Tests para verificar límites de queries."""

    def setUp(self):
        """Preparar datos de prueba."""
        reset_queries()

    def test_listado_tipos_no_dispara_n1(self):
        """Verifica que listar tipos no dispara queries N+1."""
        # Crear datos de prueba
        TipoImpuesto.objects.bulk_create(
            [TipoImpuesto(codigo=f"T{i}", nombre=f"Tipo {i}") for i in range(10)]
        )

        reset_queries()

        # Verificar cota de queries al listar (endpoint API)
        with self.assertNumQueries(
            2
        ):  # SELECT count + SELECT data (ajustar según tu view)
            url = reverse("tipo-impuesto-crud-list")
            response = self.client.get(url)
            assert response.status_code == 200

    def test_listado_ingesta_no_dispara_n1(self, admin_client):
        """Verifica que listar ingesta no dispara queries N+1."""
        # Crear documentos de prueba
        DocumentoFuente.objects.bulk_create(
            [
                DocumentoFuente(fuente="DIAN", tipo="CSV", estado="PROCESADO")
                for _ in range(5)
            ]
        )

        reset_queries()

        # Verificar cota de queries al listar (vista consola)
        # Ajustar el número según tu vista real
        url = reverse("console:impuestos-ingesta-list")

        # Login si es necesario
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not hasattr(self, "admin_user"):
            self.admin_user = User.objects.create_superuser(
                email="admin@test.local", password="admin123"
            )
        self.client.force_login(self.admin_user)

        # Verificar queries (ajustar umbral según implementación)
        with self.assertNumQueries(3):  # SELECT count + SELECT data + user (ajustar)
            response = self.client.get(url)
            assert response.status_code == 200

    def test_detalle_ingesta_no_dispara_n1(self, admin_client):
        """Verifica que el detalle de ingesta no dispara queries N+1."""
        # Crear documento con logs
        doc = DocumentoFuente.objects.create(
            fuente="DIAN", tipo="CSV", estado="PROCESADO"
        )

        # Crear logs relacionados
        from apps.public.impuestos.models import IngestaLog

        IngestaLog.objects.bulk_create(
            [
                IngestaLog(
                    documento=doc, etapa="descarga", nivel="INFO", mensaje=f"Log {i}"
                )
                for i in range(10)
            ]
        )

        reset_queries()

        # Login
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if not hasattr(self, "admin_user"):
            self.admin_user = User.objects.create_superuser(
                email="admin@test.local", password="admin123"
            )
        self.client.force_login(self.admin_user)

        # Verificar queries (ajustar según implementación)
        url = reverse("console:impuestos-ingesta-detail", args=[doc.id])
        # Usar cota superior flexible
        queries_before = len(connection.queries)
        response = self.client.get(url)
        queries_after = len(connection.queries)
        num_queries = queries_after - queries_before

        assert response.status_code == 200
        # Verificar que no hay explosión N+1 (cota razonable)
        assert num_queries < 10, f"Demasiadas queries: {num_queries}"
