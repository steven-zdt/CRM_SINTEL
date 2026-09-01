"""Tests puros de build_context -- con dobles de request/user/profile, sin DB real."""
import pytest

from apps.services.ai.context import PermissionDeniedError, build_context


class _FakeQS:
    def __init__(self, ids):
        self._ids = ids

    def values_list(self, *args, **kwargs):
        return self._ids


class _FakeProfile:
    def __init__(self, empresa_id=7, rol="OPERADOR", alcance="EMPRESA"):
        self.empresa_id = empresa_id
        self.rol = rol
        self.alcance = alcance
        self.sedes_asignadas = _FakeQS((1, 2))
        self.areas_asignadas = _FakeQS((3,))


class _FakeUser:
    def __init__(self, authenticated=True, profile=None, user_id=42):
        self.id = user_id
        self.is_authenticated = authenticated
        self.tenant_profile = profile


class _FakeTenant:
    def __init__(self, schema_name="acme"):
        self.schema_name = schema_name


class _FakeRequest:
    def __init__(self, user=None, tenant=None):
        self.user = user
        self.tenant = tenant


def test_build_context_usuario_no_autenticado_lanza_permission_denied():
    request = _FakeRequest(user=_FakeUser(authenticated=False))
    with pytest.raises(PermissionDeniedError):
        build_context(request)


def test_build_context_sin_tenant_profile_lanza_permission_denied():
    user = _FakeUser(profile=None)
    request = _FakeRequest(user=user)
    with pytest.raises(PermissionDeniedError):
        build_context(request)


def test_build_context_caso_real_empresa():
    profile = _FakeProfile(empresa_id=99, alcance="EMPRESA")
    user = _FakeUser(profile=profile)
    request = _FakeRequest(user=user, tenant=_FakeTenant("acme"))

    ctx = build_context(request)

    assert ctx.user_id == 42
    assert ctx.empresa_id == 99
    assert ctx.schema_name == "acme"
    assert ctx.alcance == "EMPRESA"
    # alcance EMPRESA -> no se restringe por sede/area especifica
    assert ctx.sede_ids == ()
    assert ctx.area_ids == ()


def test_build_context_alcance_sede_restringe():
    profile = _FakeProfile(alcance="SEDE")
    request = _FakeRequest(user=_FakeUser(profile=profile), tenant=_FakeTenant())

    ctx = build_context(request)

    assert ctx.sede_ids == (1, 2)
    assert ctx.area_ids == ()


def test_build_context_incluye_contexto_de_pantalla_sin_secretos():
    profile = _FakeProfile()
    request = _FakeRequest(user=_FakeUser(profile=profile), tenant=_FakeTenant())

    ctx = build_context(
        request,
        screen={
            "app": "ventas",
            "entity": "Venta",
            "entity_id": "uuid-123",
            "operation": "edit",
            "password": "nunca-deberia-copiarse",
        },
    )

    assert ctx.screen_app == "ventas"
    assert ctx.screen_entity == "Venta"
    assert ctx.screen_entity_id == "uuid-123"
    assert ctx.screen_operation == "edit"
    assert not hasattr(ctx, "password")


def test_build_context_usuario_a_tenant_a_difiere_de_usuario_b_tenant_b():
    """AI-01.3 (mision AI Engine, Fase AI-01): contexto A != contexto B, explicito."""
    profile_a = _FakeProfile(empresa_id=100, rol="ADMIN", alcance="EMPRESA")
    profile_b = _FakeProfile(empresa_id=200, rol="VISOR", alcance="EMPRESA")
    request_a = _FakeRequest(user=_FakeUser(profile=profile_a, user_id=1), tenant=_FakeTenant("tenant_a"))
    request_b = _FakeRequest(user=_FakeUser(profile=profile_b, user_id=2), tenant=_FakeTenant("tenant_b"))

    ctx_a = build_context(request_a)
    ctx_b = build_context(request_b)

    assert ctx_a != ctx_b
    assert ctx_a.empresa_id != ctx_b.empresa_id
    assert ctx_a.schema_name != ctx_b.schema_name
    assert ctx_a.user_id != ctx_b.user_id


def test_ai_context_es_inmutable():
    profile = _FakeProfile()
    request = _FakeRequest(user=_FakeUser(profile=profile), tenant=_FakeTenant())
    ctx = build_context(request)

    with pytest.raises(Exception):
        ctx.empresa_id = 1234  # frozen dataclass -- debe fallar
