# Organizational Scope Framework — Fase 0: Governance Baseline

**Fecha:** 2026-08-08
**Estado de esta fase:** 🟢 COMPLETA
**Alcance:** solo lectura/auditoría — cero código de producción modificado en esta fase (el único
cambio de esta fase es documental: la corrección de la tabla de ADRs en §7 de
`arquitectura_general.md`, ver Hallazgo 1).

**Origen:** `documentacion/Nueva recomendación arquitectónica.md` — propone reencuadrar el
proyecto "Organizational Context Framework" (OCF, 14 fases, cerrado 2026-08-08) como
**"Organizational Scope Framework" (OSF)**: no un framework nuevo, sino la finalización y
estandarización del Contexto Organizacional Sede/Área ya iniciado por ADR-003, con foco en
propagar la lógica de *scoping* real (Selectors → Business Services → Bridges) a las 17 apps, no
solo el *resolver contract* que OCF ya construyó.

**Relación con OCF (crítico, no repetir trabajo):** OCF (Fases 0-13) construyó el **contrato de
resolución** (`OrganizationalContext`, `OrganizationalContextMixin`, `OrganizationalPermission`,
`context.filter(Model)`) y lo adoptó de forma aditiva en los 14 ViewSets de la Fase 9 — pero
**deliberadamente no migró ningún `get_queryset()`/selector/business service a usarlo para
filtrado real**, documentado explícitamente en cada una de las 14 apps de la Fase 9 como
"parcial por diseño". Esto es exactamente el gap que este nuevo documento identifica y que las
Fases F7 (Selectors) y F8 (Business Services) de este plan deben cerrar. OSF no reemplaza OCF —
continúa donde OCF se detuvo a propósito.

---

## Hallazgo 1 — INCONSISTENTE → 🟢 RESUELTO en esta fase

**Numeración ADR duplicada**, confirmada por inspección directa (no solo por el documento de
recomendación, que solo detectó la mitad del problema):

| Número | Tabla histórica §7 (sin archivo propio) | Archivo real `docs/ADR-NNN-*.md` (activo) |
|---|---|---|
| ADR-002 | "Desacoplamiento Contable Total" (2026-05-28) | "Registro Dual de Endpoints en Schemas Publico y Tenant" (2026-06-09) |
| ADR-003 | "TareaCorta.cliente FK PROTECT → SET_NULL" (2026-05-29) | "Contexto Organizacional (Empresa→Sede→Área)" (2026-08-07) |

Verificado por `grep` exhaustivo: **cero** referencias de código usan "ADR-002"/"ADR-003" con el
significado de la tabla histórica — todas (docenas, en `apps/tenant/api/`, `apps/tenant/compras/`,
`apps/tenant/core/services/organizational_*.py`, `CLAUDE.md`) usan el significado del archivo
real. Los dos elementos de la tabla histórica nunca tuvieron un archivo `docs/ADR-NNN-*.md`
propio — fueron etiquetados "ADR-00X" informalmente en la tabla, antes de que la convención de
archivo dedicado existiera.

**Resolución aplicada (ver `arquitectura_general.md` §7):** se conservan los 4 archivos
`docs/ADR-001..004-*.md` sin renombrar (son la convención activa, referenciada extensamente) y se
retira el prefijo "ADR-NNN" de las 2 decisiones históricas sin archivo propio — quedan
documentadas como "Decisiones técnicas históricas (pre-ADR)", sin número, sin colisión.

**No se tocó ningún archivo de código ni se renombró ningún `docs/ADR-*.md`.**

---

## Estado por componente

| Componente | Estado | Evidencia |
|---|---|---|
| `SintelTenantBaseModel` | 🟢 IMPLEMENTADO | Base obligatoria de todo modelo tenant, universal, sin excepciones nuevas |
| `SedeAwareModel` | 🟡 PARCIAL | Mixin real, funcional, pero **solo 1 de 7 modelos candidatos lo usa** — ver Hallazgo 2 |
| `TenantProfile.alcance` | 🟡 PARCIAL | Campo real (EMPRESA/SEDE/AREA), ortogonal a `rol` — pero solo **1 app** (`compras`) lo consume para filtrar datos de verdad |
| `sedes_asignadas` / `areas_asignadas` (M2M) | 🟢 IMPLEMENTADO | Reales, usados por `HasOrganizationalScope` y `resolve_sede_activa_id()` |
| `HasOrganizationalScope` | 🟡 PARCIAL | Clase real y correcta — pero usada en **un solo ViewSet** (`OrdenCompraViewSet.get_permissions()`), en ningún otro |
| `filter_by_context()` (`organizational_filters.py`) | 🟢 IMPLEMENTADO | Reusado tanto por ADR-003 como por `OrganizationalContext.filter(Model)` (OCF Fase 6) |
| Selector "sede activa" en header compartido | 🟢 IMPLEMENTADO | `apps/tenant/core/static/core/js/common/sede_selector.js` + `_header.html`, visible en todo el Workspace |
| `OrganizationalContextMixin` (OCF) | 🟢 IMPLEMENTADO (contrato) / 🔴 NO USADO (filtrado) | Adoptado en 14/14 apps (26+ ViewSets) — expone `get_organizational_context()` pero ningún `get_queryset()` lo usa para filtrar (ver Relación con OCF arriba) |
| Migración a Selectors scope-aware | 🔴 PENDIENTE | Solo `OrdenCompraServiceMixin.get_qs_list()` filtra por sede/alcance de verdad hoy |
| Migración a Business Services scope-aware | 🔴 PENDIENTE | Solo `OrdenCompraBusinessService.crear_orden_compra()` recibe `sede` explícito |
| Migración de Bridges | 🔴 NO INICIADA | Ningún Bridge (Cliente/Proveedor/Inventario/Cotizacion/Bancos) conoce sede/área hoy |
| Ventas → Facturas con contexto | 🔴 NO INICIADA | `crear_factura_desde_venta()` no transporta sede/área |
| Contabilidad con contexto organizacional | 🔴 NO INICIADA | El Pull Model actual solo propaga `empresa_id` |

---

## Hallazgo 2 — Matriz preliminar de `sede`/`área` a nivel de modelo

Confirmado con precisión exacta gracias a la regla de gobernanza EKG construida en OCF Fase 11
(`find_sede_or_area_field_without_sede_aware_model`, `tools/ekg/governance.py`) — no una
estimación, un resultado de grafo real:

| App | Modelo | Campo `sede`/`area` | ¿Hereda `SedeAwareModel`? |
|---|---|---|---|
| `compras` | `OrdenCompra` | `sede` (obligatorio) + `area` (opcional, heredado) | ✅ SÍ — único caso migrado |
| `facturas` | `Factura` | `sede` (DT-SEDE, informativo/reporting) | ❌ NO |
| `gastos` | `DocumentoSoporte` | `sede` (DT-SEDE) | ❌ NO |
| `inventario` | `MovimientoInventario` | `sede` (DT-SEDE) | ❌ NO |
| `cotizaciones` | `Cotizacion` | `sede` (DT-SEDE) | ❌ NO |
| `proyectos` | `Proyecto` | `sede` (DT-SEDE) | ❌ NO |
| `empleados` | `Empleado` | `sede`/`area` (sin tag DT-SEDE, encontrado en Fase 0 de OCF) | ❌ NO |
| Resto (Ventas, Clientes, Proveedores, Bancos, Contabilidad, Dashboard) | — | Ninguno | N/A |

**Confirma exactamente el riesgo que el documento de recomendación anticipa en su §3**: hay
hasta 7 formas potenciales de "sede" si no se estandariza — hoy son 6 apps con el campo crudo (sin
mixin) + 1 migrada. Es el checklist en vivo que la nueva regla de gobernanza (OCF Fase 11) ya
rastrea automáticamente vía `make ekg-summary` (`sede_or_area_field_without_sede_aware_model`).

---

## Hallazgo 3 — UX de "sede activa" en compras (verificado, no es un bug)

El offcanvas de creación/edición de `OrdenCompra` **no muestra un selector de Sede** — inicialmente
parecía un gap, pero se verificó que es diseño deliberado: la sede se resuelve server-side desde
`request.session['sede_activa_id']` (establecida por el selector del header compartido,
`_header.html` líneas 12-31, visible en todo el Workspace) vía
`SintelDSVMixin.get_sede_id()`/`_get_sede()`. Es el mismo patrón que un selector global de
"almacén activo" en un ERP tradicional — no un formulario por sede. **No requiere corrección**,
pero sí debería documentarse explícitamente como el patrón de UX esperado antes de replicarlo en
otras apps (Fase F5/F6 de este plan).

---

## Auditoría específica de apps nombradas por el documento de recomendación

- **`compras`**: el único piloto real y funcional (Model + Selector + BusinessService +
  CRUDService + Permission). Serializer/Template/HTMX/JS no exponen sede explícitamente (por
  diseño, ver Hallazgo 3) — **pendiente de auditoría exhaustiva formal** (Fase F5 de este plan).
- **`empresa`/`perfil`**: son la **fuente** de Sede/Área/TenantProfile.alcance, no consumidores.
  Adoptaron `OrganizationalContextMixin` (OCF Fase 9) de forma aditiva; no aplica migrar su propio
  `get_queryset()` a scope-aware porque no filtran datos organizacionales de terceros.
- **`facturas`**: tiene `sede` a nivel de modelo (DT-SEDE) pero **puramente informativo** — ni
  `FacturaSelectors`, ni `FacturaBusinessService`, ni `HasOrganizationalScope` lo usan para
  restringir acceso. Coincide exactamente con el diagnóstico del documento de recomendación
  (§Fase 11: "sede todavía es esencialmente informativa/reporting").

---

## Checklist de cierre — Fase 0

- [x] Validado `arquitectura_general.md`, `AGENTS.md`, `MEMORY.md`, ADRs existentes contra el
      código real (no asumido)
- [x] Validado `compras`, `empresa`, `perfil`, `facturas` específicamente
- [x] Inconsistencia documental (numeración ADR) identificada **y resuelta** antes de continuar
      (regla explícita del documento de recomendación: "no continuar hasta resolver
      inconsistencias documentales")
- [x] Matriz preliminar de `sede`/`area` por modelo, con evidencia exacta (grafo EKG, no estimada)
- [x] Relación con el proyecto OCF recién cerrado documentada explícitamente, para no duplicar
      trabajo
- [x] Documento `ORGANIZATIONAL_SCOPE_BASELINE.md` (este archivo) producido

**Estado: 🟢 FASE 0 COMPLETA.**
