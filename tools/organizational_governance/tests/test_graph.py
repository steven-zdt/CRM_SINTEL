from tools.organizational_governance.graph import Edge, Graph, Node
from tools.organizational_governance.schema import (
    NODE_APP,
    NODE_MODEL,
    REL_OWNS,
    SCOPE_EMPRESA,
    SCOPE_NONE,
    SCOPE_SEDE,
)


def test_add_node_merges_props_on_same_identity():
    graph = Graph()
    graph.add_node(Node(NODE_APP, "compras", {"a": 1}))
    graph.add_node(Node(NODE_APP, "compras", {"b": 2}))

    assert len(graph.nodes_by_label(NODE_APP)) == 1
    merged = graph.get_node(NODE_APP, "compras")
    assert merged.props == {"a": 1, "b": 2}


def test_add_edge_requires_both_nodes_registered():
    graph = Graph()
    graph.add_node(Node(NODE_APP, "compras", {}))
    try:
        graph.add_edge(Edge(REL_OWNS, (NODE_APP, "compras"), (NODE_MODEL, "compras.OrdenCompra")))
    except KeyError:
        pass
    else:
        raise AssertionError("se esperaba KeyError por nodo destino no registrado")


def test_models_without_empresa_query():
    graph = Graph()
    graph.add_node(Node(NODE_MODEL, "x.Legit", {"scope": SCOPE_EMPRESA}))
    graph.add_node(Node(NODE_MODEL, "x.Broken", {"scope": SCOPE_NONE}))
    graph.add_node(Node(NODE_MODEL, "x.WithSede", {"scope": SCOPE_SEDE}))

    assert graph.models_without_empresa() == ["x.Broken"]


def test_to_jsonable_roundtrip_is_deterministic():
    graph = Graph()
    graph.add_node(Node(NODE_APP, "b", {}))
    graph.add_node(Node(NODE_APP, "a", {}))
    data = graph.to_jsonable()
    ids = [n["id"] for n in data["nodes"]]
    assert ids == sorted(ids), "to_jsonable() debe ordenar nodos para output reproducible"
