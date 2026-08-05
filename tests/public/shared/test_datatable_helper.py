"""
Tests de dependencias del helper DataTables reutilizable.

Valida que el helper se puede importar y usar correctamente.
"""

import pytest
from django.db.models import Q, QuerySet
from rest_framework.response import Response

from apps.shared.datatable import DataTableServer, DataTableSpec


def test_datatable_helper_importable():
    """Verifica que el helper se puede importar correctamente."""
    assert DataTableSpec is not None
    assert DataTableServer is not None


def test_datatable_spec_creation():
    """Verifica que DataTableSpec se puede crear con parámetros mínimos."""

    # Mock de QuerySet y Serializer
    class MockQuerySet:
        pass

    class MockSerializer:
        pass

    spec = DataTableSpec(
        fields_map={0: "id", 1: "name"},
        search_fields=["name"],
        base_qs=MockQuerySet(),
        serializer=MockSerializer,
    )

    assert spec.fields_map == {0: "id", 1: "name"}
    assert spec.search_fields == ["name"]
    assert spec.serializer == MockSerializer


def test_datatable_server_creation():
    """Verifica que DataTableServer se puede crear con una spec."""

    # Mock de QuerySet y Serializer
    class MockQuerySet:
        pass

    class MockSerializer:
        pass

    spec = DataTableSpec(
        fields_map={0: "id"},
        search_fields=[],
        base_qs=MockQuerySet(),
        serializer=MockSerializer,
    )

    server = DataTableServer(spec)
    assert server.spec == spec


def test_datatable_helper_methods_exist():
    """Verifica que DataTableServer tiene los métodos esperados."""

    class MockQuerySet:
        pass

    class MockSerializer:
        pass

    spec = DataTableSpec(
        fields_map={0: "id"},
        search_fields=[],
        base_qs=MockQuerySet(),
        serializer=MockSerializer,
    )

    server = DataTableServer(spec)

    # Verificar que tiene los métodos necesarios
    assert hasattr(server, "_apply_search")
    assert hasattr(server, "_apply_order")
    assert hasattr(server, "_parse_request")
    assert hasattr(server, "handle")

    # Verificar que son métodos (callable)
    assert callable(server._apply_search)
    assert callable(server._apply_order)
    assert callable(server._parse_request)
    assert callable(server.handle)
