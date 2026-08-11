# F28 — Test Impact Analysis (validación)

## F28.23-24: reutilización, no construcción

Igual que en F27, se verificó primero si ya existía capacidad equivalente
(regla F28 REGLA 1: "NO crear otro sistema de Test Impact Analysis. Ya
existe `tools/ekg/impact.py`"). Confirmado: sigue existiendo, sigue
funcionando.

## Validación real en esta fase

```bash
python -m tools.ekg.build_graph --app facturas --schema tenant --dry-run --output tools/ekg/out/facturas.json
```
```
Extracted 368 nodos, 430 edges — identico a la regeneración de F27 (0
cambios de nodos/edges, esperado: F28 solo editó contenido de tests
existentes — assertions, fixtures, imports, base class — sin agregar,
eliminar ni renombrar ningún archivo ni símbolo de facturas).
```

```bash
PYTHONIOENCODING=utf-8 python -m tools.ekg.impact --offline --name FacturaBusinessService
```
```
tests_covering_impacted_set:
  apps/tenant/facturas/tests/test_devolucion_nota_credito.py
  apps/tenant/facturas/tests/test_nota_credito_pipeline.py
  apps/tenant/facturas/tests/test_organizational_context_adoption.py
  apps/tenant/facturas/tests/test_scope_ventas_facturas_f10.py
```
Idéntico al resultado de F27 — confirma estabilidad del grafo y de la
herramienta entre fases.

## Nota sobre el bug de encoding (F27, no corregido, sigue vigente)

El workaround `PYTHONIOENCODING=utf-8` (para el `UnicodeEncodeError` en
consola Windows al imprimir títulos de documento con emoji) sigue siendo
necesario. No se corrigió en F28 — cosmético, fuera del alcance de
estabilización de testing multi-tenant.

## Conclusión F28.23-25

`tools/ekg/impact.py` + `tools/ekg/build_graph.py` siguen siendo la
herramienta correcta y funcional para Test Impact Analysis. **0 herramientas
nuevas construidas.** El único mantenimiento real que requiere esta
capacidad es mantener los dumps de `tools/ekg/out/*.json` sincronizados
cuando cambian los tests de una app — recomendación repetida de F27,
reafirmada aquí: incorporar la regeneración del dump al checklist de cierre
de cada fase que toque una app específica.
