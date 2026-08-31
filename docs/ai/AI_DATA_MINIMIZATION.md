# AI_DATA_MINIMIZATION — Fases 10, 43-46

## Lo que aplica hoy (con la única tool real)

`BuscarClienteTool.run()` usa `ClienteSelector.get_cliente_list()`,
que ya aplica `.only(*LIST_FIELDS)` -- **no** `DETAIL_FIELDS` (que
incluye más campos fiscales/de retención). La tool en sí serializa un
subconjunto aún más pequeño: `id`, `uuid`, `razon_social`,
`numero_documento`, `tipo_persona`, `activo` -- ni siquiera todos los
`LIST_FIELDS` llegan al resultado. Nada de esto pasa por un
`AIProvider` (no hay llamada a Anthropic en este flujo) -- es
minimización aplicada al propio resultado estructurado devuelto al
caller, no a un prompt.

## No implementado: clasificación de sensibilidad antes de enviar a un proveedor externo

No hay hoy ningún flujo que envíe datos de negocio a Anthropic/OpenAI
más allá del Asistente Contable existente (fuera del alcance de esta
pasada, ver `AI_CURRENT_STATE.md`) -- por eso no hay todavía un
mecanismo genérico de "clasificar sensibilidad antes de construir el
prompt". Diseño para cuando exista:

```
# DISEÑO:
def minimize_for_provider(data: dict, purpose: str) -> dict:
    """
    Filtra data a solo los campos que 'purpose' necesita
    (no "todo el registro por si acaso"). Nunca incluye:
    - Datos personales mas alla de lo necesario para la tarea
    - Informacion bancaria completa (numeros de cuenta completos)
    - Nomina, informacion fiscal completa
    - Documentos completos (XML/PDF binario)
    """
```

## Fase 10 — no devolver el grafo completo del EKG al modelo

Regla de diseño ya anotada en `AI_ENGINE_ARCHITECTURE.md` para la
futura tool `ai.project_map` -- filtrar a lo relevante para la
pregunta concreta, nunca el grafo Neo4j completo. No implementado
(la tool en sí no existe todavía).
