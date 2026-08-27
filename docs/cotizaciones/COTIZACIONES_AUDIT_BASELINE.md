# Cotizaciones — Audit Baseline (FASE 0/1, misión de modernización integral)

**Fecha:** 2026-08-27
**Regla aplicada:** esta misión NO duplica auditoría ya hecha hoy mismo. Antes de escribir una sola línea nueva, se consolida lo que ya existe con evidencia real.

---

## 0. Lo que ya existe (NO se re-audita desde cero)

En la misma sesión, horas antes de esta misión, se completó una auditoría CRUD completa de Cotizaciones (commit `5ff3470`) con 4 documentos reales en `documentacion/audits/cotizaciones/`:

| Documento | Cubre (fases de esta misión) |
|---|---|
| `CRUD_BASELINE.md` | Inventario de los 5 modelos reales (Cotizacion, CotizacionItem, Producto, Servicio, ConfiguracionCotizacion), clasificación CORE/CHILD/CATALOG/SUPPORT, endpoints reales | FASE 0/1 |
| `CRUD_COMPLETE_REPORT.md` | CREATE/READ/UPDATE/DELETE fase por fase, con evidencia archivo:línea | FASE 3-14 |
| `MATRIZ_ESTADOS_COTIZACION.md` | Estados reales (`BORRADOR/ENVIADA/ACEPTADA/CANCELADA`), confirmado que NO existe ninguna transición con respaldo en código | FASE 15 |
| `CRUD_MATRIX.md` | Veredicto final por modelo, release gate de esa misión | — |

Hallazgos y fixes de esa auditoría (ya commiteados, no se repiten aquí):
- DELETE bypaseaba el Service Layer en 4 de 5 modelos → corregido, todos pasan por BusinessService.
- `Cotizacion.fecha_emision` tenía `auto_now_add=True` → corregido con `default=_hoy` (con una regresión real detectada y corregida en la misma pasada, documentada honestamente).
- `Producto.codigo` sin constraint de unicidad real (TOCTOU) → corregido con `UniqueConstraint` de BD.
- `generar_pdf_interno()` código muerto (template inexistente) → eliminado.
- Producto/Servicio propios: `DUPLICATE_CANDIDATE` frente a Inventario, con propósito diferenciado defendible → NO migrado/eliminado, documentado.
- Conversión Cotización→Venta: confirmado que NO existe (evidencia negativa real) → NO inventada, documentado como GAP.

**Todo esto se da por válido y vigente para esta misión.** Las fases 0-9 y 12-19 de esta misión de 57 fases están, en sustancia, ya cubiertas por lo anterior — se referencian, no se reescriben.

---

## 1. FASE 2 — Descubrimiento de fallo de creación (YA REPRODUCIDO Y RESUELTO, en vivo, horas antes de esta misión)

El usuario reportó en vivo, después del CRUD audit, que "no permite crear cotización". Se reprodujo el flujo completo end-to-end y se encontraron y corrigieron **2 causas raíz reales, independientes, en capas distintas**:

### Causa raíz 1 — `Content-Type` faltante (commit `3aff2b9`)
`getHeaders()` en `cotizaciones.api.js` (SSoT de headers) nunca incluía `Content-Type: application/json`. Los 3 flujos que hacen `fetch()` crudo con `body: JSON.stringify(...)` (crear/editar Cotización, Producto, Servicio) mandaban el body como `text/plain` — DRF respondía `415 Unsupported Media Type` antes de que la vista se ejecutara. Verificado en vivo: reproducido el 415 exacto, confirmado que con `Content-Type` explícito la petición llega a la vista, y `POST` end-to-end → `201` real.

### Causa raíz 2 — Tabulator no traduce la paginación de DRF (commit `21641cb`)
`configuracion_list.js`, `producto_list.js`, `servicio_list.js` instanciaban Tabulator directo (`new w.Tabulator(...)`) sin ningún adaptador de la respuesta paginada de DRF (`{count, next, previous, results}`) — Tabulator recibía un objeto donde esperaba un array: `"RowManager.js:251 Data Loading Error... Expecting: array. Received: object."` (error real reportado en vivo por el usuario, con el payload exacto capturado). La grilla principal de Cotizaciones nunca tuvo este problema porque ya usa `TabulatorFactory` (SSoT compartido). Fix: las 3 grillas ahora usan `TabulatorFactory.create()`.

**Pruebas de humo API reales ejecutadas en vivo tras ambos fixes** (contra tenant `home`, con JWT real): CREATE/READ list/READ detail/UPDATE/DELETE/verificar-eliminado para `Cotizacion` (con items, totales calculados: `1309.00` correcto) y `ConfiguracionCotizacion` (Plantilla/Config) — **10/10 operaciones OK**.

**Conclusión FASE 2: RESUELTA.** El flujo de creación funciona de punta a punta hoy. Esta misión continúa desde aquí — no hace falta "descubrir" el fallo de nuevo, ya está reproducido, diagnosticado y corregido con evidencia.

---

## 2. Terreno genuinamente NUEVO para esta misión (lo que sí falta por auditar)

Lo que la auditoría CRUD de hoy **no** cubrió en profundidad, y que esta misión de 57 fases sí pide explícitamente:

| Área | Fases de esta misión | Estado antes de esta misión |
|---|---|---|
| Frontend baseline completo (todos los JS) | 27 | Parcial — solo se auditaron los 2 archivos con bugs reales |
| UX del formulario de creación / fricción | 28-33 | No auditado |
| Offcanvas (ciclo de vida, duplicación de listeners) | 34 | No auditado |
| Listado — filtros/búsqueda modernos | 35 | No auditado |
| Responsive / Accesibilidad | 37-38 | No auditado |
| Manejo de errores API → UX | 39 | Parcial (se vio en los 2 bugs, no sistemático) |
| Performance (N+1 backend, requests duplicados frontend) | 40 | Parcial (se vio un riesgo latente en PDF selector, no sistemático) |
| Código muerto/repetitivo frontend | 41-42 | Parcial (`item_editor.js` ya confirmado muerto) |
| Integridad cross-app completa (Cliente→Cotización→Producto→Venta→Factura) | 43 | Parcial (Venta/Factura ya cubierto en auditoría REL de hoy, `docs/integration/`) |
| Seguridad cross-tenant sistemática | 44 | Parcial (cubierto por tests OSF preexistentes, no repetido aquí) |
| Concurrencia (dos usuarios simultáneos) | 45 | No auditado |
| Tests: creación/edición/delete ampliados | 47-49 | Parcial (se agregaron tests de DELETE/constraint hoy) |
| Documentación final (END_TO_END, UI_GUIDE, RELEASE_GATE) | 53 | No creada |

**Esta es la lista de trabajo real de esta misión.** Las fases 3-26 se dan por auditadas (referencian los documentos de la sección 0), salvo que se encuentre evidencia nueva que las contradiga durante el trabajo de las fases de la sección 2 — en cuyo caso se documenta el drift explícitamente.

---

## 3. Decisión explícita sobre FASE 29 (formulario moderno, wizard de 7 pasos)

La misión pide diseñar un flujo visual de 7 pasos (Cliente → Configuración → Productos/Servicios → Precios → AIU/Impuestos → Fechas → Resumen). **Antes de construirlo, una advertencia con evidencia real:**

El formulario actual (un solo offcanvas con todos los campos, `editor_cotizacion.html` + `cotizacion_editor.js`) **ya funciona end-to-end** — confirmado hoy mismo con pruebas de humo reales (10/10 OK) tras los 2 fixes. No hay evidencia de que los usuarios reales tengan fricción con el formulario actual — el único problema reportado fue los 2 bugs técnicos ya corregidos, no "el formulario es confuso".

Rehacer el formulario en un wizard de 7 pasos es una reescritura de UI grande y de riesgo real (puede introducir regresiones en un flujo que hoy funciona), y la propia Regla Absoluta #4/#5 de esta misión advierte explícitamente contra inventar secuencias de negocio nuevas sin evidencia. **Decisión: no se reconstruye el formulario como wizard en esta pasada.** En su lugar, las fases 28-33 se ejecutan como una auditoría de fricción real (¿hay campos técnicos expuestos? ¿hay validación visual clara? ¿hay doble-submit posible?) y se corrigen los hallazgos concretos con evidencia, sin rediseñar la arquitectura del formulario. Si se encuentra evidencia real de que el formulario de un solo paso es inadecuado, se documenta como propuesta para decisión de producto, no se ejecuta unilateralmente.

---

## 4. Plan de ejecución de esta misión

1. Delegar a agentes en paralelo (background) la investigación de las áreas nuevas de la sección 2 que son puramente de diagnóstico (frontend baseline, performance, cross-app integrity, concurrencia) — mismo patrón que ya funcionó bien en las 2 misiones anteriores de hoy (REL-01 y CRUD Cotizaciones).
2. Aplicar fixes reales solo donde haya evidencia concreta de un defecto, siguiendo las Reglas Absolutas #1-4.
3. Ampliar tests donde se confirme cobertura faltante real.
4. Cerrar con la documentación final (FASE 53) y el release gate (FASE 55/56).
