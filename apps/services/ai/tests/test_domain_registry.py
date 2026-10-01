"""
Test del Domain Registry (Fase 1 del plan de evolucion,
apps/services/ai/domain_registry/). Sin DB -- solo importa modelos reales
y cruza contra AIToolRegistry/INDEXABLE_SOURCES, ya poblados al importar.
"""

from apps.services.ai.domain_registry import get_domain, list_domains
from apps.services.ai.domain_registry.registry import _reset_cache_for_tests


def setup_function():
    _reset_cache_for_tests()


def test_list_domains_cubre_los_12_dominios_de_negocio():
    dominios = {d.key for d in list_domains()}
    assert dominios == {
        "clientes",
        "proveedores",
        "facturas",
        "ventas",
        "compras",
        "cotizaciones",
        "inventario",
        "gastos",
        "empleados",
        "proyectos",
        "bancos",
        "contabilidad",
    }


def test_app_label_se_deriva_del_modelo_real_no_se_adivina():
    """Hallazgo real conocido (AI_RELEASE_GATE.md AI-02): el app_label real
    diverge del nombre corto -- Cliente -> 'tenant_clientes', no 'clientes'."""
    clientes = get_domain("clientes")
    assert clientes.app_label == "tenant_clientes"
    assert clientes.primary_model == "tenant_clientes.Cliente"


def test_tools_vienen_del_ai_tool_registry_real():
    clientes = get_domain("clientes")
    assert "buscar_cliente" in clientes.tools
    assert "validar_cliente" in clientes.tools

    ventas = get_domain("ventas")
    assert ventas.tools == (
        "consultar_venta",
    )  # ventas no tiene validar_venta (decision ya documentada)


def test_knowledge_sources_solo_en_dominios_con_rag_real():
    """Solo clientes e inventario tienen RAG hoy (ver ADK_KNOWLEDGE_MAP.md)."""
    clientes = get_domain("clientes")
    assert "cliente_observaciones" in clientes.knowledge_sources

    inventario = get_domain("inventario")
    assert "producto_descripcion" in inventario.knowledge_sources

    proveedores = get_domain("proveedores")
    assert proveedores.knowledge_sources == ()


def test_selectors_y_business_service_apuntan_a_modulos_reales():
    import importlib

    for dominio in list_domains():
        importlib.import_module(dominio.selectors_module)
        importlib.import_module(dominio.business_service_module)


def test_get_domain_desconocido_devuelve_none():
    assert get_domain("dominio-que-no-existe") is None
