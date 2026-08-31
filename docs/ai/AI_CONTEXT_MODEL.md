# AI_CONTEXT_MODEL — Fases 8, 23, 43-44

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
`areas_asignadas`) -- **las tools de esta pasada (`buscar_cliente`) no
usan todavía `sede_ids`/`area_ids`** para filtrar (Cliente no tiene
FK a Sede en el modelo actual) -- el campo existe en `AIContext` listo
para cuando una tool de un dominio con alcance por sede lo necesite
(ej. inventario, empleados).

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
