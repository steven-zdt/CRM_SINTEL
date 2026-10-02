"""
MCP Gateway SINTEL (PLAN_MCP_OPERACIONAL_PRIVADO_SINTEL_ERP.md).

Capa propia que gobierna el endpoint MCP real (`django-rest-framework-mcp`,
montado en `/mcp/`) -- nunca el motor `AIToolRegistry`/`AIEngine`
(`apps/services/ai/`, dominio `platform`, ver `docs/mcp/ADR-MCP-001.md`).
Ver `docs/mcp/ADR-MCP-002.md` para la decision que reabre el protocolo MCP
real como via adicional, y `docs/mcp/MCP_TOOL_COVERAGE.md` para el estado
de cobertura.

`apps/tenant/*` nunca debe importar `djangorestframework_mcp` directamente
-- esta es la unica capa que conoce esa dependencia alpha (Seccion 1.4 del
plan: "debe quedar encapsulada detras de una capa propia de SINTEL").
"""
