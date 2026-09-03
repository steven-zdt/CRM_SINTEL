"""AI-VECTOR-06 (escenario 4): `ToolRisk` NO es enforcement automatico.

`ToolRisk.SENSITIVE_READ` es hoy SOLO metadata -- `AIEngine.run_tool()` no lo
lee para bloquear nada (verificado leyendo `engine/ai_engine.py`; documentado
en `docs/ai/AI_SECURITY_MODEL.md`). Un futuro `RetrievalTool` (AI-VECTOR-07)
que necesite proteccion sensible DEBE implementarla explicitamente dentro de
su `run()` -- no puede confiar en que `risk=SENSITIVE_READ` lo proteja.

Este test PINEA ese comportamiento: si alguien agrega enforcement de
`ToolRisk` al engine en el futuro, este test falla y obliga a actualizar
`AI_SECURITY_MODEL.md` (regla explicita de ese documento).
"""

import pytest
from django.test import override_settings

from apps.services.ai.context import AIContext
from apps.services.ai.engine import ai_engine as ai_engine_mod
from apps.services.ai.engine import run_tool
from apps.services.ai.tools.base import BaseTool, ToolKind, ToolResult, ToolRisk
from apps.services.ai.tools.registry import _REGISTRY, _reset_registry_for_tests, register_tool

_EXECUTED = {"flag": False}


class _SensitiveReadTool(BaseTool):
    name = "tool_sensible_de_prueba"
    description = "Tool marcada SENSITIVE_READ -- para probar que el riesgo NO bloquea solo."
    domain = "test_security"
    kind = ToolKind.READ
    risk = ToolRisk.SENSITIVE_READ

    def run(self, context, **kwargs):
        _EXECUTED["flag"] = True
        return ToolResult(status="OK", data={"ran": True})


class _FakeRequest:
    class _U:
        id = 1
        is_authenticated = True

    user = _U()
    tenant = None


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch):
    snapshot = dict(_REGISTRY)
    _EXECUTED["flag"] = False
    # Aislar build_context de la BD: el objeto de estudio es el enforcement de
    # ToolRisk, no la construccion de contexto (ya cubierta en test_ai_context).
    monkeypatch.setattr(
        ai_engine_mod,
        "build_context",
        lambda request, screen=None: AIContext(
            user_id=1, empresa_id=1, schema_name="t", rol="OPERADOR", alcance="EMPRESA"
        ),
    )
    yield
    _reset_registry_for_tests()
    _REGISTRY.update(snapshot)


@override_settings(AI_ENABLED=True, AI_READ_ENABLED=True)
def test_toolrisk_sensitive_read_no_bloquea_por_si_solo():
    register_tool(_SensitiveReadTool())
    result = run_tool("tool_sensible_de_prueba", _FakeRequest())
    # Se ejecuto: ToolRisk.SENSITIVE_READ por si solo NO impidio la ejecucion.
    assert result.status == "OK"
    assert _EXECUTED["flag"] is True


@override_settings(AI_ENABLED=True, AI_READ_ENABLED=False)
def test_lo_que_SI_bloquea_es_el_flag_de_kind():
    register_tool(_SensitiveReadTool())
    result = run_tool("tool_sensible_de_prueba", _FakeRequest())
    assert result.status == "PERMISSION_DENIED"
    assert _EXECUTED["flag"] is False


def test_engine_run_tool_no_referencia_toolrisk():
    """El codigo del engine no menciona ToolRisk (candado documental)."""
    import inspect

    src = inspect.getsource(ai_engine_mod)
    assert "ToolRisk" not in src, (
        "AIEngine parece haber ganado enforcement de ToolRisk -- actualiza "
        "docs/ai/AI_SECURITY_MODEL.md y este test."
    )
