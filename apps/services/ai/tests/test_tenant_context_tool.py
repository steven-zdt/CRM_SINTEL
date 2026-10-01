"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`tenant_context`. Unit test puro (sin DB) -- solo refleja un AIContext
ya construido, no consulta nada.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import TenantContextTool


def test_refleja_exactamente_el_context_recibido():
    context = AIContext(
        user_id=42,
        empresa_id=7,
        schema_name="acme",
        rol="OPERADOR",
        alcance="SEDE",
        sede_ids=(1, 2),
        area_ids=(),
    )

    result = TenantContextTool().run(context)

    assert result.status == "OK"
    assert result.data["user_id"] == 42
    assert result.data["empresa_id"] == 7
    assert result.data["schema_name"] == "acme"
    assert result.data["rol"] == "OPERADOR"
    assert result.data["alcance"] == "SEDE"
    assert result.data["sede_ids"] == [1, 2]
    assert result.data["area_ids"] == []


def test_run_no_acepta_ningun_parametro_que_permita_cambiar_el_contexto():
    """Regla Absoluta: nunca aceptar tenant_id/schema_name/empresa_id del
    agente como forma de cambiar el contexto de seguridad -- la tool no
    declara NINGUN parametro ademas de `context`."""
    import inspect

    sig = inspect.signature(TenantContextTool.run)
    assert list(sig.parameters) == ["self", "context"]
