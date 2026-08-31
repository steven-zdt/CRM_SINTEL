"""
AI Tool Registry (Fase 12). Registro central y explicito de que
herramientas existen -- nunca introspeccion automatica de ViewSets ni
generacion dinamica de tools desde el ORM (eso violaria Regla
Absoluta 1/4: cada tool se declara a mano, semantica, con metadata de
riesgo explicita).
"""
from __future__ import annotations

from .base import BaseTool

_REGISTRY: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> BaseTool:
    """Registra una instancia de tool. Falla ruidosamente ante nombres duplicados."""
    if tool.name in _REGISTRY:
        raise ValueError(f"Tool duplicada: '{tool.name}' ya esta registrada.")
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> BaseTool | None:
    return _REGISTRY.get(name)


def list_tools(*, domain: str | None = None, kind=None) -> list[BaseTool]:
    tools = list(_REGISTRY.values())
    if domain is not None:
        tools = [t for t in tools if t.domain == domain]
    if kind is not None:
        tools = [t for t in tools if t.kind == kind]
    return tools


def tool_metadata() -> list[dict]:
    """Metadata serializable -- lo que un AIEngine/proveedor puede ver, nunca el objeto tool en si."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "domain": t.domain,
            "kind": t.kind.value,
            "risk": t.risk.value,
            "confirmation_required": t.confirmation_required,
            "idempotent": t.idempotent,
        }
        for t in _REGISTRY.values()
    ]


def _reset_registry_for_tests() -> None:
    """Solo para tests -- nunca se llama desde codigo de produccion."""
    _REGISTRY.clear()
