# AI_CONTEXT_MODEL — Fases 8, 23, 43-44

## AI-01 = **VERIFIED** (2026-09-01, misión evolución READ_ONLY → contextual)

Cierre formal: `AIContext`/`build_context` ya cumplían la Fase 8 desde
la misión anterior; esta pasada agregó la prueba explícita que AI-01.3
exige literalmente ("usuario A / tenant A" vs. "usuario B / tenant B" →
contexto A ≠ contexto B):
`test_build_context_usuario_a_tenant_a_difiere_de_usuario_b_tenant_b`
(`apps/services/ai/tests/test_ai_context.py`) — construye 2 contextos
reales desde 2 perfiles/tenants distintos y confirma
`ctx_a != ctx_b`, `ctx_a.empresa_id != ctx_b.empresa_id`,
`ctx_a.schema_name != ctx_b.schema_name`. AI-01.1 (SSoT del contexto,
nunca del mensaje del usuario) y AI-01.2 (contexto mínimo, no "todo el
ERP") ya estaban cumplidos por diseño desde antes — ver el resto de
este documento.

## `AIContext` (implementado, `apps/services/ai/context/ai_context.py`)

```python
@dataclass(frozen=True)
class AIContext:
    user_id: int
    empresa_id: int
    schema_name: str
    rol: str
    alcance: str
    sede_ids: tuple[int, ...]
    area_ids: tuple[int, ...]
    screen_app: str | None
    screen_entity: str | None
    screen_entity_id: str | None
    screen_operation: str | None
```

**Inmutable** (frozen dataclass, probado en
`test_ai_context_es_inmutable`) -- ninguna tool puede ampliar su
propio contexto en tiempo de ejecución.

Construido **exclusivamente** desde `request.user.tenant_profile`
(mismo SSoT que `SintelDSVMixin.get_empresa_id()`), nunca desde el
payload de IA. `alcance=SEDE`/`AREA` puebla `sede_ids`/`area_ids`
desde las relaciones M2M reales del perfil (`sedes_asignadas`/
`areas_asignadas`) -- `buscar_cliente`/`buscar_producto` no usan
`sede_ids`/`area_ids` (esos modelos no tienen FK a Sede). **[2026-09-01]
`consultar_compra` sí los usa de verdad** (primera tool con alcance
organizacional real, `apps/services/ai/tools/compras_tools.py`) --
respeta exactamente la misma semántica que
`apps/tenant/core/services/organizational_filters.py::filter_by_scope`
ya usa en el resto del código: `sede_ids=None` → sin restricción
(alcance `EMPRESA`); `sede_ids=()` (tupla vacía, no `None`) →
restringir a nada (alcance `SEDE`/`AREA` sin ninguna sede asignada).
`AIContext.sede_ids` devuelve `()` para **ambos** casos (`EMPRESA` sin
restricción y `SEDE` sin asignaciones) — la tool traduce
explícitamente según `context.alcance` antes de pasarlo al selector
(`_scope_ids_or_none()`), nunca asume que "tupla vacía" siempre
significa "sin restricción". Probado con 2 usuarios reales (alcance
`EMPRESA` ve ambas sedes; alcance `SEDE` con una sola sede asignada
nunca ve la otra) en
`apps/services/ai/tests/test_ai03_mas_dominios_tool.py::ConsultarCompraToolTests`.

**[2026-09-01] `consultar_cotizacion`/`consultar_gasto`/`consultar_proyecto`
usan una variante distinta, NULL-safe** (`Cotizacion`/`DocumentoSoporte`/
`Proyecto` tienen `sede` opcional y el 100% de los registros reales
tiene `sede=NULL` hoy, OSF Fase F7 -- ver
`apps/tenant/core/services/organizational_filters.py::filter_by_scope_null_safe`
y la nota en cada selector). Estos 3 modelos no tienen campo `area`,
asi que no hay eje de area que traducir: la tool pasa
`context.sede_ids` (la tupla real, incluso vacia) para cualquier
alcance distinto de `EMPRESA` -- incluyendo alcance `AREA`, cuyo
`context.sede_ids` siempre es `()` (ver `build_context`), lo que hoy
es NULL-safe-permisivo (toda la data real es NULL) y se vuelve
correctamente restrictivo el dia que existan registros con sede real
asignada. Esto es intencionalmente mas simple que
`_scope_kwargs()` de `consultar_compra` porque aqui solo existe UN eje
(sede), no dos -- no hay riesgo de aplicar la misma regla a un
segundo eje que no corresponde.

## Fase 23 — Contexto de pantalla (implementado, opcional)

`build_context(request, screen={...})` acepta un dict con
exactamente 4 claves conocidas (`app`, `entity`, `entity_id`,
`operation`) -- cualquier otra clave enviada (ej. `password` por
error del caller) se ignora silenciosamente, nunca se copia a
`AIContext` (probado en
`test_build_context_incluye_contexto_de_pantalla_sin_secretos`). No
hay todavía ningún endpoint HTTP real que reciba este payload del
frontend -- el parámetro existe en `build_context()` listo para
cuando exista un endpoint de chat/asistente real.

## Fase 43-44 — Context retrieval / EKG retrieval (diseño, no implementado)

No hay hoy ningún flujo que necesite "recuperar solo el contexto
relevante" porque no hay generación de texto libre en el flujo real
todavía -- `buscar_cliente` devuelve datos estructurados directamente,
sin pasar por un LLM. Cuando exista un flujo de conversación real
(Fase 17+, Form Assistant), el diseño esperado es:

```
consulta "factura X" -> recuperar: factura + venta + cliente + impuestos + pagos
                          (relacionados por FK real, no "todos los clientes")
```

reutilizando selectors ya existentes de cada dominio (mismo patrón que
`ClienteSelector` en `buscar_cliente`), nunca un mecanismo de
embeddings/vector search nuevo sin necesidad demostrada.
