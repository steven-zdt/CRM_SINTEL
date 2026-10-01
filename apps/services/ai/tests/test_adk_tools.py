"""
Tests del agente ADK en proceso (Fase 4, apps/services/ai/adk/, ver
docs/adk/ADK_STATUS.md). ADK vive en el MISMO entorno/proceso que Django
(decision explicita del usuario, 2026-09-22) -- estas tools se llaman
como funciones Python normales, sin HTTP ni secreto compartido.

Verifica el camino completo SIN ningun LLM involucrado (no hay proveedor
conectado a ADK todavia): buscar_cliente() -> AIContext real re-derivado
de BD (nunca de un valor arbitrario) -> AIEngine.run_tool() -> tool real
(buscar_cliente del AIToolRegistry) -> Cliente real en BD.
"""

import asyncio

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


class _FakeToolContext:
    """Doble minimo de google.adk.tools.ToolContext -- las tools de este
    modulo solo leen `.state.get(...)`, nada mas del objeto real."""

    def __init__(self, state: dict):
        self.state = _FakeState(state)


class _FakeState:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.fixture
def adk_tenant(db):
    schema = "adk_tools_test"
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context("public"):
            tenant_obj = Client.objects.create(schema_name=schema, nombre="ADK Tools Test")
            Domain.objects.create(
                tenant=tenant_obj, domain=f"{schema}.sintel.net.co", is_primary=True
            )
    return tenant_obj


@pytest.fixture
def adk_user_y_cliente(adk_tenant):
    """
    Idempotente a proposito: los tests que llaman a `buscar_cliente()` real
    (via sync_to_async, hilo aparte) necesitan `django_db(transaction=True)`
    -- hallazgo real de esta sesion: con el `db` fixture normal (transaccion
    sin commit hasta el teardown), la conexion del hilo async NUNCA ve la
    fila recien creada aqui, y ademas queda bloqueada esperando el lock de
    esa transaccion abierta -- deadlock real, no solo "datos invisibles".
    Con transaction=True los datos SI se comitean, pero tambien persisten
    entre tests DENTRO de la misma corrida de pytest -- de ahi el
    get_or_create en vez de create().
    """
    with schema_context(adk_tenant.schema_name):
        empresa, _ = Empresa.objects.get_or_create(
            nit="900555666",
            defaults={"razon_social": "EMPRESA ADK TOOLS S.A.S.", "direccion": "Calle ADK Tools"},
        )
        user, created = User.objects.get_or_create(
            email="adk_tools_user@test.local",
            defaults={"username": "adk_tools_user@test.local", "password": "testpass123"},
        )
        if created:
            user.set_password("testpass123")
            user.save(update_fields=["password"])
        TenantProfile.objects.get_or_create(
            user=user, defaults={"empresa": empresa, "rol": "ADMIN"}
        )
        Cliente.objects.get_or_create(
            numero_documento="900222333",
            defaults={
                "empresa": empresa,
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "razon_social": "Cliente Via ADK Tools",
            },
        )
    return user


@pytest.mark.django_db
def test_root_agent_construye_con_sus_tools_sin_llm():
    """Prueba real (no solo declarativa): el Agent de ADK se construye con
    nuestras tools sin necesitar ningun LLM configurado."""
    from apps.services.ai.adk.agent import build_root_agent

    agent = build_root_agent()
    assert agent.name == "sintel_root"
    nombres = {getattr(t, "__name__", str(t)) for t in agent.tools}
    assert nombres == {"saludar", "buscar_cliente"}


@pytest.mark.django_db
def test_saludar_no_requiere_contexto_de_tenant():
    from apps.services.ai.adk.tools import saludar

    result = asyncio.run(saludar())
    assert result["ok"] is True


@pytest.mark.django_db(transaction=True)
@override_settings(**AI_FLAGS_ON)
def test_buscar_cliente_end_to_end_real(adk_tenant, adk_user_y_cliente):
    from apps.services.ai.adk.tools import buscar_cliente

    tool_context = _FakeToolContext(
        {
            "sintel_schema_name": adk_tenant.schema_name,
            "sintel_user_id": adk_user_y_cliente.id,
        }
    )
    result = asyncio.run(buscar_cliente("Via ADK Tools", tool_context))

    assert result["ok"] is True, result
    nombres = {c["razon_social"] for c in result["clientes"]}
    assert nombres == {"Cliente Via ADK Tools"}


@pytest.mark.django_db(transaction=True)
def test_buscar_cliente_sin_ai_enabled_es_permission_denied(adk_tenant, adk_user_y_cliente):
    """Sin AI_ENABLED, AIEngine.run_tool() bloquea -- la tool de ADK no lo salta."""
    from apps.services.ai.adk.tools import buscar_cliente

    tool_context = _FakeToolContext(
        {
            "sintel_schema_name": adk_tenant.schema_name,
            "sintel_user_id": adk_user_y_cliente.id,
        }
    )
    with override_settings(AI_ENABLED=False):
        result = asyncio.run(buscar_cliente("Via ADK Tools", tool_context))

    assert result["ok"] is False
    assert result["status"] == "PERMISSION_DENIED"


@pytest.mark.django_db
@override_settings(**AI_FLAGS_ON)
def test_buscar_cliente_sin_sesion_real_es_permission_denied():
    """Sesion ADK sin sintel_schema_name/sintel_user_id -- nunca se ejecuta la tool."""
    from apps.services.ai.adk.tools import buscar_cliente

    tool_context = _FakeToolContext({})
    result = asyncio.run(buscar_cliente("cualquier cosa", tool_context))

    assert result["ok"] is False
    assert result["status"] == "PERMISSION_DENIED"


@pytest.mark.django_db(transaction=True)
@override_settings(**AI_FLAGS_ON)
def test_buscar_cliente_usuario_sin_tenant_profile_es_permission_denied(adk_tenant):
    from apps.services.ai.adk.tools import buscar_cliente

    with schema_context(adk_tenant.schema_name):
        otro_user, _ = User.objects.get_or_create(
            email="sin_perfil_adk_tools@test.local",
            defaults={"username": "sin_perfil_adk_tools@test.local", "password": "testpass123"},
        )

    tool_context = _FakeToolContext(
        {
            "sintel_schema_name": adk_tenant.schema_name,
            "sintel_user_id": otro_user.id,
        }
    )
    result = asyncio.run(buscar_cliente("cualquier cosa", tool_context))

    assert result["ok"] is False
    assert result["status"] == "PERMISSION_DENIED"
