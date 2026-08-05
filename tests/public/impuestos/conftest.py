"""
Fixtures base para tests de impuestos.

Proporciona:
- Configuración de Django DB (migrate_schemas)
- Celery en modo eager (determinístico)
- Cliente OpenSearch fake (si no hay cluster)
- Fixtures de usuario y cliente API
"""

import json
import os

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Asegura migraciones en esquema public (django-tenants).

    En CI/Local: migrate_schemas --shared --fake-initial
    """
    with django_db_blocker.unblock():
        call_command("migrate_schemas", "--shared", "--fake-initial", verbosity=0)


@pytest.fixture(autouse=True)
def celery_eager():
    """
    Configura Celery en modo eager para pruebas deterministas.

    Las tareas se ejecutan síncronamente, sin necesidad de worker.
    """
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


@pytest.fixture
def api_client(db):
    """Cliente API de DRF."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Usuario administrador para tests."""
    user = User.objects.create_superuser(
        email="admin@test.local", username="admin", password="admin123"
    )
    return user


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Cliente API autenticado como admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# ----- Fake OpenSearch client (si no hay cluster) -----


class FakeOSClient:
    """
    Cliente OpenSearch fake para tests sin cluster real.

    Mantiene la misma interfaz mínima que opensearch-py:
    - client.search()
    - client.cluster.health()
    - client.indices.exists_alias(), get_alias(), create(), update_aliases()
    """

    def __init__(self):
        self._docs = []  # Almacén en memoria

    class indices:
        @staticmethod
        def exists_alias(name):
            return True

        @staticmethod
        def get_alias(name):
            return {"impuestos-docs-v1": {"aliases": {"impuestos-docs": {}}}}

        @staticmethod
        def create(index, body):
            return {"acknowledged": True}

        @staticmethod
        def update_aliases(body):
            return {"acknowledged": True}

        @staticmethod
        def exists(index):
            return False

    class cluster:
        @staticmethod
        def health():
            return {
                "status": "green",
                "number_of_nodes": 1,
                "active_primary_shards": 1,
                "active_shards": 1,
                "relocating_shards": 0,
                "initializing_shards": 0,
                "unassigned_shards": 0,
            }

    def search(self, index, body):
        """
        Busca documentos en el índice fake.

        Args:
            index: Nombre del índice (ignorado en fake)
            body: Query body con multi_match

        Returns:
            dict: Formato OpenSearch hits
        """
        q = body.get("query", {}).get("multi_match", {}).get("query", "")
        size = body.get("size", 10)
        offset = body.get("from", 0)

        # Búsqueda simple: filtrar por texto en título o contenido
        hits = []
        for d in self._docs:
            source = d.get("_source", {})
            texto = source.get("texto", "").lower()
            titulo = source.get("titulo", "").lower()
            query_lower = q.lower()

            if query_lower in texto or query_lower in titulo:
                hit = {
                    "_source": source,
                    "_id": d.get("_id", ""),
                }
                # Agregar highlight si se solicita
                if body.get("highlight") and query_lower in texto:
                    hit["highlight"] = {
                        "texto": [f"<em>{q}</em> encontrado en el texto"]
                    }
                hits.append(hit)

        # Paginación
        total = len(hits)
        hits_paginated = hits[offset : offset + size]

        return {
            "hits": {
                "total": {"value": total},
                "hits": hits_paginated,
            }
        }


@pytest.fixture
def patch_opensearch(monkeypatch):
    """
    Cambia el cliente real por el fake (si no hay OpenSearch).

    Usage:
        def test_search(patch_opensearch, api_client):
            # Agregar documentos al fake
            patch_opensearch._docs.append({"_source": {...}})
            # Test...
    """
    from apps.public.impuestos import search

    fake = FakeOSClient()

    def _fake_client():
        return fake

    monkeypatch.setattr(search.client, "get_search_client", _fake_client)

    return fake


@pytest.fixture
def user_admin(db):
    """Usuario administrador para tests E2E."""
    from django.contrib.auth import get_user_model

    U = get_user_model()
    return U.objects.create_superuser(email="admin@test.local", password="admin123")


@pytest.fixture
def csrf_client(db):
    """
    Cliente Django con CSRF habilitado (enforce_csrf=True).

    Provee (client, csrftoken) tras solicitar una página interna para setear cookie.

    Usage:
        def test_something(csrf_client, user_admin):
            client, csrftoken = csrf_client
            client.login(...)
            resp = client.post(url, data={...}, HTTP_X_CSRFTOKEN=csrftoken)
    """
    from django.test import Client

    c = Client(enforce_csrf=True)

    # Cualquier GET interno que invoque get_token genera la cookie csrftoken;
    # el admin es suficiente y siempre está en el proyecto.
    c.get("/admin/login/")
    csrftoken = c.cookies.get("csrftoken").value if "csrftoken" in c.cookies else ""

    return c, csrftoken


@pytest.fixture
def admin_client(db, admin_user):
    """
    Cliente Django autenticado como admin.

    Usage:
        def test_something(admin_client):
            r = admin_client.get("/console/impuestos/")
            assert r.status_code == 200
    """
    from django.test import Client

    client = Client()
    client.force_login(admin_user)
    return client
