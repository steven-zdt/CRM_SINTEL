"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`inspect_model`. Unit tests puros (sin DB) -- Model._meta es metadata
de clase, no requiere consulta a la base de datos.
"""

from apps.services.ai.context import AIContext
from apps.services.ai.tools.platform_audit_tools import InspectModelTool


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_model_name_vacio_es_validation_error():
    result = InspectModelTool().run(_fake_context(), model_name="")
    assert result.status == "VALIDATION_ERROR"


def test_modelo_inexistente_es_not_found():
    result = InspectModelTool().run(_fake_context(), model_name="ModeloQueNoExisteJamas")
    assert result.status == "NOT_FOUND"


def test_modelo_real_expone_fields_constraints_e_indexes():
    result = InspectModelTool().run(_fake_context(), model_name="Cliente")

    assert result.status == "OK"
    assert result.data["match_count"] == 1
    model = result.data["models"][0]
    assert model["model"] == "Cliente"
    assert model["app_label"] == "tenant_clientes"
    assert model["field_count"] > 0
    field_names = {f["name"] for f in model["fields"]}
    assert "empresa" in field_names
    # UniqueConstraint real de FASE 4 (anti-duplicidad de documento) --
    # confirma que se leyo Model._meta.constraints real, no una lista vacia.
    constraint_names = {c["name"] for c in model["constraints"]}
    assert "uniq_doc_cliente_empresa" in constraint_names
    assert len(model["indexes"]) > 0
    # Una relacion reversa real (Cliente <- Venta) debe describirse con su
    # "kind" y el modelo relacionado, no solo el nombre.
    ventas_field = next(f for f in model["fields"] if f["name"] == "ventas")
    assert ventas_field["relation"]["kind"] == "one_to_many"
    assert ventas_field["relation"]["related_model"] == "Venta"


def test_es_case_insensitive():
    result = InspectModelTool().run(_fake_context(), model_name="cliente")
    assert result.status == "OK"
