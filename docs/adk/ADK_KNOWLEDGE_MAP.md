# ADK_KNOWLEDGE_MAP — Fase 2 (Mapa de Conocimiento)

**Fecha:** 2026-09-22
**Fuente:** `PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md` §60
**Depende de:** `docs/adk/ADK_DOMAIN_INVENTORY.md` (Fase 1)

STATUS FASE 2: **PASS** (documental — no crea índices nuevos, mapea los 3 existentes: RAG/pgvector, EKG, tools).

Para cada dominio: **RAG scope** (¿tiene documentos indexados hoy?), **EKG nodes** (¿tiene snapshot real?), **business rules** (dónde viven, no reproducidas aquí), **tools** (de la Fase 1), **permisos requeridos**, **riesgo**.

## Regla de fondo (§60 del plan): no crear índices redundantes

Los 3 índices ya existen y son independientes por diseño — ADK debe consultarlos como 3 tools distintas (`buscar_conocimiento` → RAG, `ai_project_map` → EKG, `consultar_*`/`buscar_*` → tools de dominio), nunca fusionarlos en uno nuevo:

| Índice | Qué contiene | Tool que lo expone |
|---|---|---|
| RAG / pgvector (`apps/tenant/ai_knowledge/`) | Texto libre indexado (`INDEXABLE_SOURCES`) — hoy solo `Cliente.observaciones` y `Producto.descripcion` | `buscar_conocimiento` |
| EKG (`tools/ekg/out/*.json`) | Estructura del código: modelos, servicios, endpoints, templates, reglas, docs, FKs — por app | `ai_project_map` |
| Tools de dominio (`apps/services/ai/tools/*_tools.py`) | Datos transaccionales reales (fuente de verdad, nunca vectorial) | `buscar_cliente`, `consultar_venta`, etc. |

## Mapa por dominio

| Dominio | RAG scope (indexado hoy) | EKG snapshot | Permisos requeridos | Riesgo (tools existentes) |
|---|---|---|---|---|
| clientes | **Sí** — `cliente_observaciones` | `tools/ekg/out/clientes.json` | `IsTenantMember` + `TenantProfile` válido (vía `AIContext`) | SAFE_READ |
| proveedores | No | `tools/ekg/out/proveedores.json` | ídem | SAFE_READ |
| facturas | No | `tools/ekg/out/facturas.json` | ídem | SAFE_READ |
| ventas | No | `tools/ekg/out/ventas.json` | ídem | SAFE_READ |
| compras | No | `tools/ekg/out/compras.json` | ídem | SAFE_READ |
| cotizaciones | No | `tools/ekg/out/cotizaciones.json` | ídem | SAFE_READ |
| inventario | **Sí** — `producto_descripcion` | `tools/ekg/out/inventario.json` | ídem | SAFE_READ |
| gastos | No | `tools/ekg/out/gastos.json` | ídem | SAFE_READ |
| empleados | No | `tools/ekg/out/empleados.json` | ídem | **SENSITIVE_READ** |
| proyectos | No | `tools/ekg/out/proyectos.json` | ídem | SAFE_READ |
| bancos | No | `tools/ekg/out/bancos.json` | ídem | **SENSITIVE_READ** |
| contabilidad | No | `tools/ekg/out/contabilidad.json` | ídem | **SENSITIVE_READ** (SUGGEST) |

**Lectura del mapa:** 10 de 12 dominios de negocio tienen EKG (estructura de código) pero NO tienen RAG (texto libre indexado) — para esos dominios, ADK debe apoyarse en `ai_project_map` + las tools transaccionales, sin poder recuperar contexto semántico de texto libre todavía. Esto no bloquea la Fase 4-9 del plan de ADK (que no dependen del RAG), pero sí limita la Fase 11 (Supervisión) si esa fase asume poder buscar semánticamente sobre "observaciones"/notas de otros dominios — no existen hoy.

## Reglas de negocio — dónde viven (no reproducidas aquí, por diseño)

El plan (§20, prompting "just-in-time") exige que los agentes NO carguen el modelo completo del ERP en el prompt — deben recuperar reglas bajo demanda. Las fuentes reales, ya existentes, que un especialista de ADK debe consultar en tiempo de ejecución (nunca copiar a un prompt estático que se desactualiza):

- **Reglas de campo/seguridad**: `docs/ai/AI_SECURITY_MODEL.md` (clasificación FORBIDDEN/MASKED/SENSITIVE por campo, ya usada por `INDEXABLE_SOURCES` y por el `ToolRisk` de cada tool).
- **Reglas estructurales por app**: snapshot EKG de esa app (`rules_for_app`/`docs_for_app` vía `ai_project_map`).
- **Reglas de validación real**: el propio `Serializer.is_valid()`/`business_service.py` de cada dominio — las tools `validar_*` ya las envuelven sin reimplementarlas (Fase 1).
- **Reglas contables (pull model)**: `docs/ADR-001-retention-pull-model.md` — relevante si algún especialista de Fase 9 toca Ventas/Compras/Gastos/Empleados, que nunca escriben asientos directamente.

## Permisos — un solo mecanismo, no 12

Los 12 dominios comparten el mismo requisito de acceso al AI Engine: `AIContext.build_context()` exige `request.user.tenant_profile` real (Fase 0). No hay permisos diferenciados por dominio a nivel de "quién puede usar la tool" más allá de lo que ya impone `IsTenantMember` en el endpoint HTTP — la diferenciación real ocurre a nivel de **flag por `ToolKind`** (`AI_READ_ENABLED`/`AI_VALIDATE_ENABLED`/etc.) y de **riesgo** (`ToolRisk`), no de un permiso nuevo por dominio. ADK debe reutilizar esto tal cual (§12 del plan), no inventar `clientes.create`/`ventas.read` como permisos Django nuevos.

## Conclusión de Fase 2

```
FASE 2 — MAPA DE CONOCIMIENTO = PASS
```

Sin índices nuevos creados. El hallazgo accionable real es la cobertura RAG limitada (2/12 dominios) — queda registrado, no resuelto en esta fase (resolverlo es trabajo de `apps/tenant/ai_knowledge/`, fuera del alcance de "integrar ADK como orquestador").
