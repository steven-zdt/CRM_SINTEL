# Organizational Scope Framework — Fase F6: Matriz de Alcance Organizacional

**Fecha:** 2026-08-08
**Estado de esta fase:** 🟢 COMPLETA
**Objetivo (del documento de recomendación, Fase 6):** decidir, app por app, **qué entidad
realmente necesita Sede y Área** — el propio documento advierte explícitamente:

> "No debemos poner sede y area indiscriminadamente en todos los modelos."

Esta matriz reemplaza la tabla de ejemplo del documento de recomendación (que marcaba 15 de 17
apps genéricamente como "⏳ Pendiente", sin distinguir cuáles tienen de verdad un campo `sede`/
`area` hoy, ni evaluar si el dominio lo justifica) por el estado **verificado empíricamente**
contra el código real — grep directo de `models.py` de cada app, no supuestos.

---

## 1. Matriz completa — 17 apps tenant

| App | `empresa_id` | Campo `sede` hoy | Campo `area` hoy | ¿`SedeAwareModel`? | Alcance funcional hoy (filtra listas/writes) | Veredicto F6 |
|---|---|---|---|---|---|---|
| **compras** | ✅ | ✅ obligatorio | ✅ opcional | ✅ Sí | ✅ **Funcional** (F5: `OrganizationalScope`, conjunto completo) | 🟢 **PILOTO COMPLETO** — referencia para el resto |
| **empresa** | ✅ | — (es la fuente) | — (es la fuente) | N/A | N/A (no consume, define `Sede`/`Area`) | ⚪ N/A — fuente de la jerarquía, no consumidor |
| **perfil** | ✅ | — (es la fuente de `alcance`/`sedes_asignadas`) | — (idem `areas_asignadas`) | N/A | N/A (define el `alcance`, no lo consume sobre sí mismo) | ⚪ N/A — fuente de identidad/alcance, no consumidor |
| **facturas** | ✅ | ⚠️ informativo (`DT-SEDE-01`, `Factura.sede`) | ❌ no existe | ❌ No | ❌ Ninguno (campo nunca leído para filtrar/autorizar) | 🟡 **CANDIDATO FUERTE** — campo ya existe, falta activarlo (F11) |
| **cotizaciones** | ✅ | ⚠️ informativo (`DT-SEDE-0X`, `Cotizacion.sede`) | ❌ no existe | ❌ No | ❌ Ninguno | 🟡 **CANDIDATO FUERTE** |
| **gastos** | ✅ | ⚠️ informativo (`DT-SEDE-0X`, `DocumentoSoporte.sede`) | ❌ no existe | ❌ No | ❌ Ninguno | 🟡 **CANDIDATO FUERTE** |
| **inventario** | ✅ | ⚠️ informativo (`DT-SEDE-0X`, `MovimientoInventario.sede`) | ❌ no existe | ❌ No | ❌ Ninguno | 🟡 **CANDIDATO FUERTE** (bodega/almacén por sede es el caso de uso más natural de todo el ERP) |
| **proyectos** | ✅ | ⚠️ informativo (`DT-SEDE-0X`, `Proyecto.sede`) | ❌ no existe | ❌ No | ❌ Ninguno | 🟡 **CANDIDATO FUERTE** |
| **empleados** | ✅ | ⚠️ existe, sin tag `DT-SEDE` (`Empleado.sede`, hallazgo de OCF Fase 0) | ⚠️ existe (`Empleado.area`) | ❌ No | ❌ Ninguno | 🟡 **CANDIDATO FUERTE** (oficina/sede de trabajo del colaborador — caso de uso obvio) |
| **ventas** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno | 🟢 **CANDIDATO PLAUSIBLE, sin campo aún** — segunda ola natural tras `compras` (ver F10, `Venta`→`Factura`); ya vincula `cliente`/`proyecto` |
| **bancos** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno | 🟢 **CANDIDATO PLAUSIBLE** — cuentas bancarias por sucursal es real en la práctica; `TransaccionBancaria` ya tiene un campo de texto libre `sucursal` (indicio no estructurado de esta misma necesidad) |
| **contabilidad** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno (Pull Model solo propaga `empresa_id`) | 🟠 **CANDIDATO PARCIAL** — plausible SOLO para `AsientoContable`/`MovimientoContable` (segmentación por centro de costo); el catálogo de cuentas y los períodos fiscales son de empresa completa por diseño contable, NO deben llevar sede/area |
| **proveedores** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno | 🟠 **CANDIDATO DÉBIL** — la relación con un proveedor es típicamente de toda la empresa, no de una sede; `CuentasPagar` podría heredar la sede de la compra de origen en vez de tener campo propio |
| **clientes** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno | 🔴 **NO RECOMENDADO** — un cliente no está atado a una sede del vendedor; agregar el campo violaría la advertencia explícita de esta fase |
| **dashboard** | ✅ | ❌ no existe | ❌ no existe | ❌ No | ❌ Ninguno (agregador de solo lectura) | 🔴 **NO RECOMENDADO tal como está diseñado** — `SnapshotMetricaDiaria` es una métrica agregada a nivel empresa; requeriría rediseñar el modelo de snapshot (una fila por sede) para que sede/area tuviera sentido, no es un simple "agregar campo" |
| **core** | ✅ (`SintelTenantBaseModel`) | Define el mixin `SedeAwareModel` | Define el mixin `SedeAwareModel` | N/A (es la fuente del mixin) | N/A | ⚪ N/A — infraestructura compartida, no app de dominio |
| **landing** | N/A | ❌ no existe | ❌ no existe | N/A | N/A | ⚪ N/A — sin modelos de dominio propios (solo forms/views/API de onboarding público) |

**Verificación de la fuente:** los 6 campos "informativo (DT-SEDE)" y el de `empleados` son
exactamente los 6 hallazgos de la regla de gobernanza EKG
(`find_sede_or_area_field_without_sede_aware_model`, OCF Fase 11) más el propio hallazgo original
de Fase 0 de OCF para `empleados` — reutilizados aquí, no re-derivados. Los 8 campos "❌ no existe"
fueron verificados por un agente de exploración dedicado, leyendo directamente cada `models.py`
(cita archivo:línea disponible en el historial de esta fase).

---

## 2. Priorización recomendada para F13 (rollout al resto de apps)

**Tier 1 — Activar scoping en el campo que YA EXISTE (menor esfuerzo, mayor impacto):**
`facturas`, `cotizaciones`, `gastos`, `inventario`, `proyectos`, `empleados`. Estas 6 apps no
necesitan migración de esquema para empezar — el campo `sede` (y `area` en `empleados`) ya está
en la base de datos, solo falta: (a) migrar el modelo a heredar `SedeAwareModel` (o al menos
empezar a usar el campo para filtrar), (b) exigirlo en el Service Layer, (c) exponerlo en
Selector/Serializer/Template como hizo F5 con `compras`.

**Tier 2 — Requieren migración de esquema desde cero, pero el caso de negocio es real:**
`ventas` (prioridad alta — es el predecesor directo de `facturas` en el flujo
`crear_factura_desde_venta()`, F10), `bancos`, `contabilidad` (solo `AsientoContable`/
`MovimientoContable`, nunca el catálogo de cuentas ni los períodos), `proveedores` (prioridad
baja, caso débil).

**Tier 3 — No agregar sede/area (decisión explícita, no simplemente "pendiente"):** `clientes`,
`dashboard` (tal como está diseñado hoy), `core` y `landing` (no son apps de dominio). `empresa` y
`perfil` son la fuente de la jerarquía, no consumidores — no aplica evaluarlos con este mismo
criterio.

---

## 3. Por qué esta matriz difiere de la tabla del documento de recomendación

El documento original marcaba **15 de 17 apps** genéricamente como "⏳ Pendiente" en Sede y Área,
sin distinguir entre "el campo ya existe pero no se usa para nada" (6 apps) y "el campo no existe
y hay que decidir si tiene sentido crearlo" (el resto). Tratar ambos casos igual habría llevado a
F7/F8/F13 a repetir el mismo trabajo de descubrimiento que esta fase ya hizo una vez. Además, el
documento no distinguía candidatos plausibles de no-plausibles — literalmente advertía contra
"poner sede y area indiscriminadamente" pero su propia tabla de ejemplo marcaba todo como
"Pendiente" sin ese filtro. Esta matriz aplica ese filtro explícitamente.

---

## Checklist de cierre — Fase F6

- [x] Las 17 apps tenant auditadas (no solo las 15 de la tabla de ejemplo del documento —
      se incluyeron `core` y `landing`, ausentes de esa tabla)
- [x] Estado de `sede`/`area` verificado empíricamente (grep directo, no asumido)
- [x] Veredicto explícito de plausibilidad de negocio por app (no solo "pendiente" genérico)
- [x] Priorización para F13 basada en esfuerzo real (campo existente vs. campo por crear)
- [x] Documento `ORGANIZATIONAL_SCOPE_MATRIX.md` (este archivo) producido

**Estado: 🟢 FASE F6 COMPLETA.**

---

## 4. Estado tecnico real de adopcion — auditoria 2026-08-09 (FASE 5, plan de consolidacion)

**Por que esta seccion existe y no un archivo paralelo:** FASE 0 del plan de consolidacion OCF/OSF
(`documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`) detecto que este archivo ya existia
(F6, 2026-08-08) y senalo el riesgo de crear un `ORGANIZATIONAL_SCOPE_MATRIX.md` paralelo en
FASE 5. La Seccion 1 de arriba sigue siendo correcta para su proposito original (¿que app
*deberia* tener sede/area?) pero quedo desactualizada en su columna "Alcance funcional hoy" —
fue escrita ANTES de que F7-F16 ejecutaran el rollout real. Esta seccion la reemplaza con el
estado tecnico verificado por codigo (grep exhaustivo, no supuesto) al cierre de F16, usando los
mismos componentes que pide FASE 5 del plan de consolidacion. **Regla aplicada:** ninguna app se
marca 🟢 COMPLETO solo por heredar `OrganizationalContextMixin` — se distingue "hereda" de
"invoca", ver `documentacion/OCF_TECHNICAL_AUDIT.md`.

**Leyenda:** 🟢 COMPLETO · 🟡 PARCIAL · 🔴 AUSENTE · ⚪ NO APLICA

### 4.1 Capa de Contexto/Alcance (Context/Scope)

| App | `OrganizationalContext` (invocado, no solo heredado) | `OrganizationalScope`/`filter_by_scope*` (uso real) | `HasOrganizationalScope` | `SedeAwareModel` |
|---|---|---|---|---|
| core | ⚪ (es la fuente) | ⚪ (es la fuente) | ⚪ (es la fuente) | ⚪ (es la fuente) |
| empresa | 🔴 hereda el Mixin, nunca lo invoca | ⚪ (es la fuente de `Sede`/`Area`) | ⚪ | ⚪ |
| perfil | 🔴 hereda el Mixin, nunca lo invoca | ⚪ (es la fuente de `alcance`) | ⚪ | ⚪ |
| facturas | 🔴 hereda, no invoca | 🟢 `filter_by_scope_null_safe` en selector + viewset (F7/F11) | 🔴 | 🔴 |
| contabilidad | 🔴 hereda, no invoca | 🔴 (Pull Model solo propaga `empresa_id`, ver Seccion 1) | 🔴 | 🔴 |
| gastos | 🔴 hereda, no invoca | 🟢 F7 | 🔴 | 🔴 |
| inventario | 🔴 hereda, no invoca | 🟢 F7 | 🔴 | 🔴 |
| empleados | 🔴 tiene `api/viewsets.py` con ViewSets reales (`EmpleadoViewSet`, etc.) pero **ninguno hereda** `OrganizationalContextMixin` — unica de las 14 apps con ViewSets DRF que no lo hereda en absoluto | 🟢 F7 (con `sede_ids` Y `area_ids`, unica de las 6) | 🔴 | 🔴 |
| cotizaciones | 🔴 hereda, no invoca | 🟢 F7 | 🔴 | 🔴 |
| clientes | 🔴 hereda, no invoca | 🔴 | 🔴 | 🔴 |
| proveedores | 🔴 hereda, no invoca | 🔴 | 🔴 | 🔴 |
| proyectos | 🔴 hereda, no invoca | 🟢 F7 | 🔴 | 🔴 |
| dashboard | 🔴 hereda, no invoca | 🔴 | 🔴 | 🔴 |
| bancos | 🔴 hereda, no invoca | 🔴 | 🔴 | 🔴 |
| compras (piloto) | 🔴 hereda, no invoca (usa `HasOrganizationalScope` en su lugar, patron ADR-003 previo a OCF) | 🟢 F5, estricto (`sede` NOT NULL) | 🟢 unico adoptante en todo el proyecto | 🟢 unico adoptante en todo el proyecto |
| ventas | 🔴 hereda el Mixin, no lo invoca; **pero SI usa `OrganizationalContext.resolve()` directo** (no via Mixin) para defaultear `sede_id` al crear una `Venta` (F10) — patron distinto a filtrado, ver Seccion 4.4 | 🔴 (no filtra listas por scope) | 🔴 | 🔴 |
| landing | ⚪ sin modelos de dominio | ⚪ | ⚪ | ⚪ |

**Hallazgo transversal:** `OrganizationalContextMixin` esta heredado en 14 ViewSets pero **invocado
activamente en 0** (confirmado en `OCF_TECHNICAL_AUDIT.md` §1) — la columna "invocado" de esta
tabla es 🔴 para las 14 apps que lo heredan, no 🟢, porque heredar sin invocar no produce ningun
efecto en runtime. `ventas` es la unica excepcion parcial: no usa el Mixin, pero llama
`OrganizationalContext.resolve()` directamente en su propio codigo.

### 4.2 Campos de datos (`empresa_id`/`sede`/`area`)

`empresa_id` es 🟢 universal en las 17 apps (regla Zero-Trust preexistente, AGENTS.md, no
especifica de OCF/OSF). `sede`/`area` — ver Seccion 1 de este documento para el detalle completo
por app (columnas "Campo `sede` hoy"/"Campo `area` hoy"), no se repite aqui.

### 4.3 Capa de Servicio/API (Selectors, BusinessService, ViewSet, Permissions)

Corresponde 1:1 con la columna `OrganizationalScope`/`filter_by_scope*` de la Seccion 4.1 — en
este proyecto, la adopcion de OSF ocurre exactamente en el par Selector+ViewSet/mixin de forma
atomica (verificado en F7/F11 de `ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`: cada app migrada tiene
"2 archivos de produccion modificados: selector + viewset/mixin"). No hay ningun caso de
"Selector migrado, ViewSet no" o viceversa. `BusinessService`/`CRUDService` como capas
independientes **no** consumen OCF/OSF directamente en ninguna app (ni siquiera `compras` — ver
`OCF_TECHNICAL_AUDIT.md` §7, el adaptador de Service Layer es codigo de demostracion sin
consumidor real); el filtrado ocurre en el Selector, antes de llegar al Business Service.
`Serializer` scope-aware (`sede_esta_en_alcance()`/`area_esta_en_alcance()` en `validate()`):
confirmado en `facturas`, `cotizaciones`, `gastos`, `proyectos`, `empleados` (las 5 apps con
campo `area`/`sede` editable por el usuario final, ver docstring de
`sede_esta_en_alcance` en `organizational_scope.py:134-147`) — `inventario` filtra listas (F7)
pero no fue confirmado en esta pasada si su Serializer tambien valida `sede_esta_en_alcance` en
escritura (verificar en una fase de implementacion si se necesita, no asumido aqui).

### 4.4 Frontend/HTMX

Unica pieza de frontend real de todo OCF/OSF: el selector de "Sede activa" en el header
compartido (`_header.html` + `sede_selector.js`, ver `OCF_TECHNICAL_AUDIT.md` §8) — es
transversal a las 17 apps (vive en el layout compartido, no por app) y esta 🟢 funcional. Ninguna
app tiene UI propia que exponga "filtrar por sede/area" en sus listados (los filtros de
`filter_by_scope*` son automaticos/silenciosos del lado servidor, no un control de UI que el
usuario vea u opere) — esto es coherente con el diseno (el usuario no "elige" su alcance, lo tiene
asignado), no un gap.

### 4.5 Tests

Ver tabla completa en `documentacion/OCF_OSF_BASELINE.md` §3 (conteo exacto de
`test_organizational_context_adoption.py` y `test_scope_*_fN.py` por app) — no se repite aqui.
Confirmado por ejecucion real (no solo lectura): las 9 suites de `apps/tenant/core/tests/` pasan
53/53 (ver `OCF_TECHNICAL_AUDIT.md` §11). Las suites por-app (`test_scope_selectors_f7.py`, etc.)
**no se ejecutaron en esta pasada** — quedan para FASE 7 (Tests de Aislamiento Organizacional) o
una verificacion dirigida si se necesita antes.

### 4.6 Resumen — ninguna app cumple el ciclo completo hoy

Cruzando las 4 subsecciones anteriores: **ninguna de las 17 apps tiene 🟢 en las 4 dimensiones
centrales simultaneamente** (`OrganizationalContext` invocado + `OrganizationalScope` en uso +
`HasOrganizationalScope` aplicado + `SedeAwareModel` adoptado). `compras` tiene 3 de 4 (todo
excepto `OrganizationalContext` invocado, que usa el patron ADR-003 anterior en su lugar); las 6
apps de F7 tienen 1 de 4 (`OrganizationalScope`/`filter_by_scope`, con filtrado NULL-safe, no
estricto); las 10 apps restantes (`empresa`, `perfil`, `contabilidad`, `clientes`, `proveedores`,
`dashboard`, `bancos`, `ventas`, `core`, `landing`) tienen 0 de 4 o son fuente/infraestructura sin
aplicar. Esto confirma, con una matriz completa en vez de hallazgos sueltos, la conclusion ya
adelantada en `OCF_TECHNICAL_AUDIT.md` §0: la mayoria de OCF/OSF esta construido y probado, pero
su adopcion real en produccion es mucho mas acotada que "17/17 fases completas" sugiere a primera
lectura.

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
