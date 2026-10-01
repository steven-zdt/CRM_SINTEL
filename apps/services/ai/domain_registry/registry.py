"""
Domain Registry (Fase 1 del plan de evolucion,
documentacion/PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md §31).

Genera `DomainDefinition` por app **desde codigo real** -- nunca datos
duplicados a mano. Cada campo se deriva en tiempo de ejecucion:

  app_label         <- Model._meta.app_label (Django, SSoT real)
  tools             <- AIToolRegistry.list_tools(domain=key) (ya registradas)
  knowledge_sources <- INDEXABLE_SOURCES filtrado por app_label (RAG real)

No es un segundo inventario que alguien tiene que mantener sincronizado a
mano -- si un dominio nuevo registra una tool o un origen RAG, aparece
aqui automaticamente la siguiente vez que se construye el registro (no
hay cache persistente entre procesos).

Ver tambien docs/adk/ADK_DOMAIN_INVENTORY.md (la misma informacion en
formato documento, con el analisis de por que faltan tools en algunos
dominios) -- este modulo es la version PROGRAMATICA de esa tabla, para
que otros componentes (agentes ADK, endpoints de introspection) puedan
consumirla sin parsear markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainDefinition:
    key: str  # nombre de dominio tal como lo usan las tools (BaseTool.domain)
    app_label: str  # Model._meta.app_label real (Django)
    primary_model: str  # "app_label.ModelName", derivado del modelo real
    selectors_module: str  # ruta real de services/selectors.py de esa app
    business_service_module: str  # ruta real de services/business_service.py de esa app
    tools: tuple[str, ...] = field(default_factory=tuple)  # nombres reales, AIToolRegistry
    knowledge_sources: tuple[str, ...] = field(
        default_factory=tuple
    )  # source_type reales, INDEXABLE_SOURCES


# (key, app_import_path, ModelClassName) -- unica lista "a mano" de este
# modulo: decidir CUALES 12 apps son dominios de negocio no se puede
# derivar solo, es una decision (misma lista que docs/adk/ADK_DOMAIN_INVENTORY.md).
# Todo lo DEMAS (app_label, tools, knowledge_sources) se deriva del codigo real.
_DOMAIN_MODELS: tuple[tuple[str, str, str], ...] = (
    ("clientes", "apps.tenant.clientes.models", "Cliente"),
    ("proveedores", "apps.tenant.proveedores.models", "Proveedor"),
    ("facturas", "apps.tenant.facturas.models", "Factura"),
    ("ventas", "apps.tenant.ventas.models", "Venta"),
    ("compras", "apps.tenant.compras.models", "OrdenCompra"),
    ("cotizaciones", "apps.tenant.cotizaciones.models", "Cotizacion"),
    ("inventario", "apps.tenant.inventario.models", "Producto"),
    ("gastos", "apps.tenant.gastos.models", "DocumentoSoporte"),
    ("empleados", "apps.tenant.empleados.models", "Empleado"),
    ("proyectos", "apps.tenant.proyectos.models", "Proyecto"),
    ("bancos", "apps.tenant.bancos.models", "CuentaBancaria"),
    ("contabilidad", "apps.tenant.contabilidad.models", "AsientoContable"),
)

_registry_cache: dict[str, DomainDefinition] | None = None


def _build_registry() -> dict[str, DomainDefinition]:
    import importlib

    from apps.services.ai.tools import list_tools
    from apps.tenant.ai_knowledge.services.sources import INDEXABLE_SOURCES

    registry: dict[str, DomainDefinition] = {}
    for key, model_module_path, model_name in _DOMAIN_MODELS:
        model_module = importlib.import_module(model_module_path)
        model_cls = getattr(model_module, model_name)
        app_label = model_cls._meta.app_label

        app_root = model_module_path.rsplit(".models", 1)[0]  # "apps.tenant.clientes"
        tool_names = tuple(t.name for t in list_tools(domain=key))
        source_types = tuple(
            s.source_type for s in INDEXABLE_SOURCES if s.model_label.split(".")[0] == app_label
        )

        registry[key] = DomainDefinition(
            key=key,
            app_label=app_label,
            primary_model=f"{app_label}.{model_name}",
            selectors_module=f"{app_root}.services.selectors",
            business_service_module=f"{app_root}.services.business_service",
            tools=tool_names,
            knowledge_sources=source_types,
        )
    return registry


def list_domains() -> list[DomainDefinition]:
    """Construye (o reusa dentro del mismo proceso) el registro completo."""
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = _build_registry()
    return list(_registry_cache.values())


def get_domain(key: str) -> DomainDefinition | None:
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = _build_registry()
    return _registry_cache.get(key)


def _reset_cache_for_tests() -> None:
    """Solo para tests -- nunca se llama desde codigo de produccion."""
    global _registry_cache
    _registry_cache = None
