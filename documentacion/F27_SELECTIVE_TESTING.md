# F27 — Testing Selectivo / Test Impact Analysis

## F27.17-20: no se crea un selector nuevo — ya existe uno real

Antes de considerar construir una herramienta de "que tests correr si cambio
X", se buscó capacidad equivalente ya existente en el repo (regla explícita
F27.18: "NO CREAR TEST SELECTOR SI YA EXISTE").

**Encontrado: `tools/ekg/impact.py`**, ya construido (Fase 12, EKG/Knowledge
Graph organizacional), responde exactamente las preguntas que F27.19 pide:

```bash
PYTHONIOENCODING=utf-8 python -m tools.ekg.impact --offline --name <Modelo|Service|ViewSet> [--label <Label>]
```

Camina el grafo de dependencias real (imports/herencia/uso/llamadas) desde
el símbolo indicado y responde:

- Qué módulos/servicios/ViewSets dependen de él (reverse walk).
- Qué Endpoints expone (forward walk).
- **Qué tests ya cubren el nodo o cualquier nodo impactado** (`TESTED_BY`,
  campo `tests_covering_impacted_set`).
- Qué apps se tocan y qué reglas (AGENTS.md/skills)/documentos (ADRs)
  revisar.

Ejemplo real corrido en esta fase:

```
$ python -m tools.ekg.impact --offline --name NotaCredito
== Impact of changing Model:NotaCredito (max 4 hops) ==
-- hop 1 -- [Serializer] NotaCreditoDetailSerializer, NotaCreditoListSerializer
-- hop 2 -- [ViewSet] NotaCreditoViewSet
-- hop 3 -- [Endpoint] notas-credito, [ViewSet] NotaCreditoCoreViewSet
-- Tests covering target or any impacted node --
  apps/tenant/facturas/tests/test_devolucion_nota_credito.py
  apps/tenant/facturas/tests/test_nota_credito_pipeline.py
```

Esto es exactamente la "suite mínima recomendada" que F27.17 pide para un
cambio dado — **reutilizada tal cual, no se construyó nada nuevo.**

## Hallazgos reales durante la verificación (F27.18: "si está incompleto, depurar/extender")

1. **El dump del grafo estaba desactualizado.** Antes de regenerarlo, la
   consulta de arriba solo devolvía `test_nota_credito_pipeline.py` —
   faltaba `test_devolucion_nota_credito.py` (agregado en la sesión de
   Devoluciones, DOC-M14, posterior al último `build_graph.py` real para
   `facturas`). Regenerado con:
   ```bash
   python -m tools.ekg.build_graph --app facturas --schema tenant --dry-run --output tools/ekg/out/facturas.json
   ```
   (368 nodos, 430 aristas). Tras la regeneración, la consulta ya incluye
   ambos archivos — confirmado. **Implicación real:** el impact engine es
   confiable solo si su dump está sincronizado con el código actual; no
   corre extracción "en vivo". Si se usa esta herramienta como parte de un
   gate de CI/PR en el futuro, el dump debe regenerarse en ese mismo paso,
   no asumirse fresco.
2. **Bug de encoding en consola Windows (no corregido, cosmético).**
   `impact.py::_print_report()` imprime títulos de documentos que a veces
   contienen emoji (ej. 📦) — en una consola Windows con codepage cp1252
   (el default de este entorno vía Git Bash/PowerShell), eso lanza
   `UnicodeEncodeError` y trunca la salida antes de imprimir la sección de
   docs. Workaround usado en esta fase: `PYTHONIOENCODING=utf-8` como
   variable de entorno antes del comando. No se modifica `impact.py` en
   este pase (cosmético, con workaround conocido, fuera del alcance
   quirúrgico de F27 sobre testing).

## Conclusión

F27.17-20 se resuelve por **reutilización real**, no por construcción. El
motor existente (`tools/ekg/impact.py` + `tools/ekg/build_graph.py`) ya
responde "¿qué tests cubren este símbolo?" con datos reales del grafo,
siempre que el dump del app afectado esté regenerado. Recomendación para
fases futuras: regenerar el dump de la app tocada como parte del checklist
de cierre (mismo lugar donde ya se corre `governance --report`), no
dejarlo a discreción de quien recuerde hacerlo.
