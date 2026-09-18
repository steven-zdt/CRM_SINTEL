# [PORTAL] Auditoría y SSoT: Módulo Empleados

**Versión:** v4.13.0 (SINTEL v3.16.x)
**Estado:** ⚠️ PRODUCTION READY CON DEUDAS DOCUMENTADAS (ver §Deudas Técnicas — quedan 5 abiertas, ver abajo. DEUDA-31 es la más grande: workflow de aprobación/pago INDIVIDUAL por empleado dentro de un período, sección 20-38 del prompt "Periodos de Nómina" — deliberadamente diferido, no implementado en esta pasada). **Re-auditado 2026-09-12** (`docs/remediation/AUDIT_BASELINE_20260912.md`) sin CRÍTICOS nuevos — ver nota abajo.
**Ubicación:** `apps/tenant/empleados/`
**Última Auditoría:** 2026-09-11 (v4.13.0: Centro de Control de Período — aportes patronales EPS/AFP/ARL/parafiscales + costo total empresa en `resumen`; base v4.12.0 sin cambios salvo lo indicado. Ver también v4.12.1 debajo: integridad PERIODOS-NOMINA-01, ya en el working tree antes de esta pasada). Re-verificación 2026-09-12.
**Auditor:** Claude Sonnet 5 (Anthropic) — v4.9.0, v4.10.0, v4.11.0, v4.12.0, v4.12.1, v4.13.0. v4.8.1 y anteriores: Claude Haiku 4.5 (Anthropic)

---

## 2026-09-12 — Re-auditoría transversal (docs/remediation/AUDIT_BASELINE_20260912.md), sin fixes aplicados

Auditoría independiente ("Empleados / Períodos de Nómina") como parte de
la misión transversal de 7 apps. **Confirmó** (no re-inventó) DEUDA-31
(sin Revisar/Aprobar/Devolver/Cancelar por Devengo individual, sin
selección múltiple) y DEUDA-25-CERRADO ("Preliquidar" fuerza 30 días
iguales para todos, decisión consciente ya documentada) como deuda ya
conocida — no se re-abren como hallazgos nuevos. **1 hallazgo nuevo real,
no CRÍTICO** (E-4, MEDIO): las acciones críticas de período (Aprobar,
Marcar como pagado, Cerrar) no tienen diálogo de confirmación en
`periodo_detail.js` (`ACCIONES_POR_ESTADO`) — solo `anular` lo tiene, pese
a que `CERRADO` es un estado terminal sin transiciones de salida
(`TRANSICIONES_VALIDAS['CERRADO'] = set()`). También: código muerto en
`PeriodoNominaCRUDService.actualizar_estado` (`return contrato`
inalcanzable) y un `min="0.1"` en el HTML del formulario de devengo que no
coincide con el mínimo real del backend (0.5). **Esta fase (Fase 1, "solo
los 5 CRÍTICO") no tocó código de esta app** — ninguno de los hallazgos de
`empleados` fue CRÍTICO. Pendiente para una fase ALTO/MEDIO futura.

---

## v4.13.0 — Centro de Control de Período: Aportes Patronales + Costo Total Empresa (2026-09-11)

**Contexto:** continuación de la misión "PROMPT DE EJECUCIÓN — Auditoría,
Corrección de Lógica de Negocio y Perfeccionamiento de UI — Módulo Períodos
de Nómina". Esa misión pide (secciones 15-19) que "Períodos de Nómina"
evolucione a un centro de control del gasto, mostrando no solo el neto
pagado sino también aportes patronales (ARL/EPS/AFP/parafiscales) y el
costo total real para la empresa — nunca inventados en frontend, siempre
calculados en Backend.

**Encontrado:** `PeriodoNominaSelector.get_resumen()` (FASE 9, ya
existente) solo agregaba devengado/deducciones/neto del **empleado** — el
motor de nómina (`NominaCalculationService`) nunca calculaba nada a cargo
del **empleador**. Sin ese cálculo, la UI no tenía ningún dato real que
mostrar para "costo total empresa" (regla de la misión: "si el backend no
expone un concepto, no simularlo en frontend").

**Corregido:**
- `NominaCalculationService.calcular_aportes_patronales(ibc, tipo_contrato,
  nivel_riesgo_arl)` (nuevo, `business_service.py`) — EPS patronal (8.5%),
  pensión patronal (12%), ARL por clase de riesgo I-V (Decreto 1607/2002,
  valores mínimos de tabla), Caja de Compensación (4%), ICBF (3%), SENA
  (2%). Contratos `PRESTACION` retornan todo en cero (mismo criterio que
  las deducciones de empleado). Opera sobre el mismo `salario_base`
  (IBC) ya persistido en `Devengo` — nunca recalcula el devengo.
- `PeriodoNominaSelector.get_resumen()` ahora itera los `Devengo` no
  anulados del período (`select_related('empleado', 'contrato')`) y agrega
  `aportes_patronales` (desglose por concepto), `total_aportes_patronales`
  y `costo_total_empresa` (= `total_devengado` + `total_aportes_patronales`
  — nunca el neto, que ya tiene las deducciones del empleado restadas).
- `periodo_detail.js` — nueva sección "Resumen Financiero" en el offcanvas
  de detalle de período: devengado → deducciones empleado → neto, luego
  desglose de aportes patronales, luego costo total empresa. Jerarquía
  visual pedida por la misión (sección 38), todos los valores desde
  `GET .../resumen/`, ninguno calculado en JS.
- Tests nuevos: `tests/test_periodo_resumen_financiero.py` (4 casos: cálculo
  exacto de cada aporte para un empleado INDEF clase de riesgo I, ARL varía
  correctamente por clase de riesgo (I vs V), período sin devengos reporta
  ceros, contrato PRESTACION no genera aportes patronales pero sí cuenta el
  devengado).

**Supuestos documentados (no inventados — ver DEUDA-30):** ARL usa el valor
mínimo de tabla por clase (la tarifa real negociada puede variar dentro del
rango autorizado); NO se aplica la exoneración de ICBF/SENA de la Ley
1607/2012 art. 25 porque el régimen tributario de la empresa no es un dato
que el modelo `Empresa` capture hoy — se calcula el aporte completo como
cota superior conservadora, nunca subestimada.

**Deliberadamente NO implementado en esta pasada (ver DEUDA-31):** el
workflow de revisión/aprobación/devolución/cancelación **individual por
empleado** dentro de un período (secciones 20-38 del prompt), con
selección múltiple, aprobación masiva y autorización de pago
individual/masiva/de período completo. Hoy la aprobación sigue siendo
**a nivel de período completo** (`PeriodoNominaBusinessService.
TRANSICIONES_VALIDAS`, ya existente desde v4.9.0) — un `Devengo`
individual no tiene estado propio de revisión (`anulado` es la única
bandera). Implementarlo correctamente requiere una máquina de estados
nueva en `Devengo` (migración + guards + tests + UI con checkboxes) que
es, en tamaño y riesgo, una misión separada — no se improvisó a medias
para no dejar un estado inconsistente a mitad de camino.

---

## v4.12.1 — Integridad de Liquidación Individual: Duplicados, Solapamiento y Concurrencia (2026-09-11)

**Contexto:** mission "PERIODOS-NOMINA-01" (secciones 1-14 del prompt
"Periodos de Nómina") — ya estaba en el working tree al iniciar esta
sesión de auditoría; se documenta aquí porque el archivo nunca lo
registró como versión propia.

**Corregido:**
- **Unicidad a nivel de Base de Datos:** `models.py`, migración `0016` —
  `UniqueConstraint(fields=['empleado', 'periodo'], condition=Q(anulado=False),
  name='uniq_nomina_activo_per_empleado_periodo')`. Antes de esto, la única
  regla de "un empleado no puede tener dos nóminas válidas en el mismo
  período" vivía solo en `DevengoSerializer.validate()` (aplicación) — sin
  respaldo de base de datos.
- **Solapamiento de rango laborado:** `DevengoBusinessService.
  validar_no_solapamiento()` (nuevo) — rechaza una nómina cuyo
  `fecha_inicio`/`fecha_fin` se solape con otra nómina activa del mismo
  empleado; si no hay fechas (flujo legado), compara por `periodo_mes`.
- **Concurrencia:** `procesar_devengo()` ahora toma
  `Empleado.objects.select_for_update().get(pk=empleado.id)` antes de
  validar duplicado/solapamiento — serializa creaciones concurrentes del
  mismo empleado; el `UniqueConstraint` de BD sigue siendo la última línea
  de defensa si dos requests pasan la validación de lectura antes de que
  cualquiera persista.
- Tests: `test_liquidacion_individual_por_periodo.py` amplía cobertura
  (duplicado rechazado, período cerrado bloquea nueva liquidación).

---

## v4.12.0 — Vista de Detalle de Nómina + PDF + Rename "Colaboradores" (2026-09-11)

**Contexto:** segunda mitad de la sesión de auditoría de nómina iniciada el
2026-09-10 (ver v4.11.0 y v4.10.0 arriba), retomada y cerrada el 2026-09-11.

**Cambios:**
- **Vista de detalle de nómina dedicada, solo lectura** —
  `offcanvas_detalle_devengo.html` (nuevo): antes "Ver" en
  `DevengoDetailTable` reutilizaba el mismo template de crear/editar
  (`offcanvas_crear_devengo.html`) pasando `devengo` en el contexto — sin
  garantía de UX de solo-lectura, aunque el backend ya bloqueaba
  `update`/`partial_update` con 405 (ver DEUDA-28, ahora CERRADO). El nuevo
  template desglosa devengados/deducciones por concepto y agrega botón
  "Generar Desprendible PDF".
- **Desprendible de nómina en PDF** — `devengo_pdf.html` (nuevo), mismo
  patrón que `liquidacion_pdf.html` ya existente para
  `LiquidacionPrestacion`. Nueva acción `pdf` en `DevengoViewSet`
  (`GET /api/v1/empleados/devengos/<uuid>/pdf/`).
- **Fix real encontrado auditando con datos reales (servidor vivo, no solo
  lectura de código):** `DevengoViewSet.get_queryset()` retorna la
  INSTANCIA (no un QuerySet) para acciones que no son `list` — un primer
  intento de `render_offcanvas_detalle()` encadenaba
  `.select_related().get()` sobre eso y crasheaba con 500. Corregido usando
  `self.get_object()`, el patrón ya usado por el resto de acciones del
  mismo ViewSet.
- **Fix `info_empleado()`:** solo aceptaba UUID (500 si llegaba PK entero;
  `cargarInfoEmpleado()` en `devengo_editor.js` manda PK). Ahora acepta
  ambos, mismo criterio dual que `UUIDOrPKRelatedField` ya usa en otros
  endpoints vía serializer.
- **`DevengoDetailTable.render_acciones()`** (`tables.py`): botón Ver ahora
  abre el offcanvas de detalle dedicado + botón PDF (link directo
  `target=_blank`), además del botón Anular ya existente.
- **`nomina_list.js`:** nuevo handler `.btn-ver-nomina` →
  `abrirDetalleNomina()`, mismo patrón que
  `liquidacion_list.js::abrirDetalleLiquidacion()`.
- **Rename UI "Empleados" → "Colaboradores"** (solo texto visible: label
  del sidebar en `workspace.js`, header h1, subtítulo, stat label,
  sub-tab y panel master de Nóminas en `empleados_list.html`) — IDs y
  `data-module` internos NO se tocaron.
- **Reorden de pestañas** en `empleados_list.html`: Resoluciones DIAN,
  Empleados, Contratos, **Períodos de Nómina** (antes al final), Nóminas,
  Liquidaciones.
- **Fix de bug real de plantillas Django:** un comentario `{# ... #}`
  MULTILÍNEA se filtraba como texto literal en el HTML renderizado —
  Django `{# #}` solo es válido en una sola línea. Corregido en
  `empleados_list.html` y `offcanvas_crear_devengo.html`. Ver "Gotchas"
  abajo — aplica a todo el proyecto, no solo a este módulo.

**Tests:** 2 casos nuevos en `test_devengos_api_smoke.py`
(`test_info_empleado_acepta_pk_entero_y_uuid`, `test_devengo_detalle_y_pdf`).
7/7 tests del archivo verificados en verde (venv local,
`pytest apps/tenant/empleados/tests/test_devengos_api_smoke.py`, 2026-09-11).

---

## v4.11.0 — Corrección Arquitectónica: Liquidación Individual por Período (2026-09-10)

**Regla oficial de dominio establecida en esta pasada:** `PeriodoNomina` es
exclusivamente un contenedor administrativo (empresa, fechas, nombre,
frecuencia, estado) — **nunca determina los días laborados de un
empleado**. `Devengo` es la liquidación individual; cada empleado dentro
de un mismo período puede tener `dias_laborados` completamente distintos
(ej. Juan 8, Pedro 15, María 5, los tres en el mismo período).

**Brecha encontrada (evidencia de código, no de documentación):**
`DevengoSerializer` **no tenía campo `periodo`** — la única forma de
vincular un `Devengo` a un `PeriodoNomina` era `preliquidar_periodo()`
(batch), que genera una nómina BASE de 30 días idéntica para todos los
elegibles. Es decir, la liquidación individual (offcanvas "Liquidar",
usada desde siempre para nóminas fuera de un período) **no podía**
asociarse a ningún `PeriodoNomina` — por diseño incompleto, no por un bug
puntual.

**Corregido:**
- `DevengoSerializer.periodo` — nuevo campo (`UUIDOrPKRelatedField`,
  opcional). Valida: pertenece a la empresa (DSV), `periodo.estado` en
  `{ABIERTO, PRELIQUIDADO}` (no se puede liquidar en un período en
  revisión/aprobado/pagado/cerrado/anulado/bloqueado), y que el empleado
  no tenga ya un `Devengo` no-anulado en ese período (anti-duplicado
  específico, adicional al `UniqueConstraint` legado por
  `periodo_mes`+`fecha_pago`).
- `GET /periodos-nomina/{uuid}/empleados-pendientes/` — nuevo endpoint,
  única fuente de verdad backend-driven (reutiliza
  `EmpleadoSelector.get_empleados_pendientes_para_periodo()`, ya
  construido en la pasada anterior para el guard de `cerrar_periodo()`).
  Solo datos humanos (nombre, documento, cargo, tipo contrato, fecha
  ingreso) — nunca UUID como dato principal.
- `GET /periodos-nomina/{uuid}/empleados-liquidados/` — nuevo, vía
  `DevengoSelector.get_by_periodo()`.
- `PeriodoNominaSelector.get_resumen()` ahora incluye `pendientes` (conteo).
- **Frontend:** `offcanvas_crear_devengo.html` acepta contexto de período
  (`?periodo=<uuid>` en `render-offcanvas/crear/`) — campo oculto +
  panel informativo, sin tocar el flujo clásico (sin período) existente.
  `periodo_detail.js` gana tabs Pendientes/Liquidados con botón "Liquidar"
  por fila que preselecciona empleado+período; guarda vía el mismo
  `POST /devengos/` de siempre. Refresco selectivo tras guardar (fetch +
  re-render del offcanvas), nunca `location.reload()`.
- `preliquidar_periodo()` (batch, 30 días para todos) **se mantiene sin
  cambios** — sigue siendo una base rápida corregible, ahora con su
  docstring aclarando explícitamente que no es la vía recomendada para
  días individuales; la vía correcta es la liquidación individual descrita
  arriba. No se eliminó para no romper el flujo ya probado de la pasada
  anterior (`test_periodo_nomina_state_machine.py`).

**Tests:** nuevo `tests/test_liquidacion_individual_por_periodo.py` (4
casos: el escenario obligatorio Juan 8/Pedro 15/María 5 en el mismo
período, pendientes antes de liquidar, anti-duplicado, guard de período
cerrado). Un caso de DSV cross-empresa fue descartado explícitamente: no
se puede simular con una segunda fila `Empresa` en el mismo schema
(`Empresa` es singleton por schema, constraint `singleton_key`) — ese
aislamiento ya está cubierto por el patrón `tenant1`/`tenant2` existente.

**Histórico (FASE 23) reforzado:** `PeriodoNominaSelector.get_list()` ahora
anota `empleados_count`/`total_neto_periodo` (una sola query de agregación,
sin N+1) y `PeriodoNominaTable` (`tables.py`) las muestra — el listado de
períodos (ya existente, django-tables2, incluye todo estado incl.
`CERRADO`) ahora es un histórico real de un vistazo: `Período | Vigencia |
Fecha Pago | Empleados | Total Neto | Estado`, sin entrar a cada período.
Verificado en shell (no hay test automatizado dedicado a esta tabla —
ver Deudas Técnicas).

---

## v4.10.0 — Retiro de Empleado Controlado + Indemnización por Causal (auditoría integral nómina, 2026-09-10)

**Contexto:** auditoría integral del flujo de nómina (PROMPT MAESTRO) contrastó
esta documentación contra el código real. Encontró que el modelo `PeriodoNomina`
(v4.9.0) existía en código pero **no estaba documentado en este archivo**
(la tabla "6 modelos" de abajo nunca se actualizó), y 2 brechas críticas de
negocio no documentadas como deuda:

1. **Retirar un empleado era literalmente `PATCH estado=RETIRADO`** — sin
   catálogo de motivo, sin flujo de liquidación definitiva forzado. Corregido:
   `EmpleadoBusinessService.retirar_empleado()` es ahora el único punto de
   entrada (el PATCH genérico delega a él); exige `motivo_retiro` +
   `fecha_retiro`, cierra el contrato con `fecha_fin=fecha_retiro` (antes
   usaba incorrectamente la fecha de hoy), y genera automáticamente una
   `LiquidacionPrestacion` tipo `LIQUIDACION_DEFINITIVA` cuando hay contrato
   y nóminas previas.
2. **`indemnizacion` se recibía como número manual** del caller (frontend o
   Postman), nunca calculado. Corregido:
   `NominaCalculationService.calcular_indemnizacion_despido()` implementa
   CST art. 64 (Ley 789/2002 art. 28) — solo aplica con
   `motivo_retiro=SIN_JUSTA_CAUSA`; escala por tipo de contrato (INDEF:
   umbral 10 SMLMV + días/año; FIJO: salarios del tiempo restante pactado;
   OBRA: ídem con mínimo legal 15 días si hay `fecha_fin`; PRESTACION: no
   aplica). Siempre retorna `explicacion` + `base_legal`, nunca solo un
   número. Nuevo catálogo `MOTIVO_RETIRO_CHOICES` (`choices.py`) y campo
   `Empleado.motivo_retiro` (migración 0015).
3. **`LiquidacionPrestacionViewSet.create()` permitía generar una
   `LIQUIDACION_DEFINITIVA` para un empleado que seguía `ACTIVO`** (FASE 20:
   "no permitir liquidación definitiva sin fecha de retiro"). Corregido: ahora
   exige `empleado.estado=RETIRADO` y `fecha_retiro` seteada antes de aceptar
   ese tipo.

**Nuevo setting:** `SMLMV_VIGENTE` (`config/settings.py`, env var) — SMLMV
2025 por defecto, **debe actualizarse cada enero** (afecta el umbral legal de
10 SMLMV en la fórmula INDEF).

**Frontend actualizado:** `offcanvas_editar_empleado.html` ahora muestra
`fecha_retiro` + `motivo_retiro` (con explicación inline) cuando se
selecciona `estado=RETIRADO`; `empleado_editor.js` los incluye en el submit.

**Tests:** nuevo `tests/test_retiro_empleado.py` (8 casos: validaciones de
entrada, cálculo de indemnización por escenario, guard de liquidación
definitiva). `tests/test_empleados_delete.py` actualizado (los PATCH de
retiro ahora incluyen `motivo_retiro`).

**Deliberadamente NO corregido en esta pasada** (quedan como deuda abierta,
ver tabla de Deudas Técnicas): validación de "sin pendientes/errores" antes
de `cerrar_periodo()`/`enviar_a_revision()` en `PeriodoNomina`, y suite de
tests para la máquina de estados de `PeriodoNomina` (hoy: cero tests la
cubren en todo el repo).

---

## v4.9.0 — `PeriodoNomina` (mision nomina 2026-08-21)

Se agrega el 7mo modelo del app: `PeriodoNomina`, que agrupa los `Devengo`
de un mismo ciclo de pago y orquesta una máquina de estados de aprobación
en lote (`ABIERTO → PRELIQUIDADO → EN_REVISION → APROBADO → PAGADO →
CERRADO`, excepciones `ANULADO`/`BLOQUEADO`). **No reemplaza ni modifica
`Devengo`** — este sigue siendo la entidad de cálculo individual,
inmutable, con `update`/`partial_update` devolviendo `405` exactamente
igual que antes. `PeriodoNomina` solo añade una FK opcional
(`Devengo.periodo`, nullable) y orquesta llamadas al motor de cálculo ya
existente (`procesar_devengo()`), nunca calcula montos por sí mismo.

Nuevo endpoint base: `/api/v1/empleados/periodos-nomina/` (+ acciones
`preliquidar`, `enviar-revision`, `rechazar-revision`, `aprobar`,
`marcar-pagado`, `cerrar`, `anular`, `bloquear`, `desbloquear`, `resumen`).
Permisos por acción vía `HasTenantRole` (ya existente, sin permission
class nueva): `VISOR` solo consulta; `OPERADOR` + crear/preliquidar/
revisión; `ADMIN` + aprobar/pagar/cerrar/anular.

**Documentación completa, decisiones y supuestos:** ver
`docs/nomina/NOMINA_BASELINE.md` (auditoría previa) y
`docs/nomina/NOMINA_FLUJO_EMPRESARIAL.md` (diseño final + qué queda
deliberadamente fuera de alcance: DIAN XML real, PILA, integración
bancaria real, modelo `Novedad` separado, frontend).

---

## Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| [Este archivo](AUDITORIA_FLUJO_EMPLEADOS.md) | Portal SSoT + Resultados de Auditoría | ACTUALIZADO 2026-06-04 v4.8.0 |
| [Arquitectura y Microtareas](docs/empleados_microtasks_architecture.md) | Desglose atómico de responsabilidades | OK |
| [Mapas de Flujo](docs/empleados_flow_map.md) | Diagramas Mermaid del ciclo de vida laboral | OK |
| [Lógica de Negocio](docs/empleados_business_logic.md) | SSoT de cálculos y validaciones | DESACTUALIZADO — no incluye DSPNE ni prestaciones |
| [Plan Separación v3.8](docs/PLAN_SEPARACION_MODULOS_v3.8.md) | Plan FSD de CRUD independiente por módulo | IMPLEMENTADO |

---

## Changelog v4.7.0 → v4.8.1

| ID | Tipo | Descripción |
|---|---|---|
| **v4.8.1** | **Feature** | **Master-Detail Contexto Presdeterminado (4 Fases)**: Refactorización completa del flujo de registro de nóminas. FASE 1: `nomina_list.js` expone getter `getEmpleadoSeleccionado()`. FASE 2: `devengo_editor.open()` detecta empleado en Master y pasa UUID al backend. FASE 3: Offcanvas se abre precargado + campo selector bloqueado. FASE 4: Reset automático al cerrar. Nuevo endpoint GET `/info-empleado/?empleado=UUID`. Mejoras visuales: badges coloreados, panel info success-subtle, feedback mejorado. Sincronización automática de ambas tablas. |
| **v4.8.0** | **Fix** | **Master-Detail UI Nóminas**: `rowClick: fn` como propiedad de config Tabulator → ignorado silenciosamente en Tabulator 6. Fix: `masterTable.on('rowClick', _seleccionarEmpleado)` — ahora las nóminas del empleado seleccionado se muestran correctamente en el panel Detail |
| **v4.6.0** | Feature | FK `resolucion_dian` en `Empleado` (nullable, SET_NULL, mig 0012). Formulario crear/editar con dropdown de resoluciones activas. DSV en serializer. |
| **v4.6.0** | Feature | `procesar_devengo()` usa resolución asignada al empleado como prioridad 1; fallback a resolución activa de empresa |
| **v4.5.3** | Fix | `LiquidacionPrestacionViewSet.create()` — `perform_create()` reemplazado por `create()` completo que pre-calcula `dias_base_calculo`/`base_salarial`/`valor_total` antes de `is_valid()` |
| **v4.5.2** | Fix | Sync frontend-backend: IDs HTML corregidos, `numero_resolucion`, `UIManager`, `window.http`, `replaceData()`, URL `/simular/` |
| **v4.5.1** | Fix | `calcular_dias_360()`: d2=31→30 incondicional (estándar 30/360 europeo). `ResolucionDIAN.save()`: `consecutivo` inicializa desde `rango_desde`. |

---

## Responsabilidades Core (v4.8.0)

1. **Ciclo de Vida Laboral**: Gestión secuencial `Empleado → Contrato ACTIVO → Devengo` (anulable, no editable)
2. **Motor Nómina Colombia**: Salario proporcional + Auxilio + H.E./Recargos − Deducciones de ley (Salud 4% + Pensión 4% SOLO si `Contrato.tipo != PRESTACION`). Ley 2101/2021 (42h/sem = 200h/mes). Decreto 2663/1950 para factores H.E.
3. **DSPNE**: Validación `ResolucionDIAN` activa + `select_for_update()` + consecutivo + CUNE SHA-256 + `TransmisionNominaDIAN` atómica. Prioridad: resolución del empleado → fallback empresa.
4. **Asignación ResolucionDIAN por Empleado**: FK nullable en `Empleado` — el DSPNE usa la resolución preferida del empleado o la activa de la empresa.
5. **Motor Liquidación Prestaciones**: Prima, Cesantías, Intereses, Vacaciones según CST. Contratos PRESTACION retornan cero.
6. **Anti-duplicados por rango**: Bloqueo por solapamiento `fecha_inicio`/`fecha_fin` en `DevengoBusinessService.verificar_periodo()`
7. **Aislamiento Zero Trust**: `empresa_id` verificado en todas las capas (DSV — `SintelDSVMixin` + serializer `__init__` + Business)
8. **Integración Contable (Pull Model)**: `ExtractorNomina` en Contabilidad extrae `Devengo` — Empleados nunca importa Contabilidad
9. **Master-Detail UI — 5 módulos FSD independientes**: Empleados / Contratos / Nómina (Master-Detail v4.8.0) / Resoluciones DIAN / Liquidaciones

---

## Modelos (`models.py`) — 7 modelos, 15 migraciones

### `Empleado`
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `default=uuid4, unique=True, db_index=True, editable=False` |
| `empresa` | FK → `Empresa` | `PROTECT` |
| `tipo_documento` | CharField | Choices: CC, CE, PA, PPT |
| `numero_documento` | CharField | `db_index=True` |
| `primer_nombre` / `segundo_nombre` | CharField | |
| `primer_apellido` / `segundo_apellido` | CharField | |
| `email` | EmailField | |
| `telefono` | CharField | nullable |
| `eps` / `afp` / `arl` | CharField | choices de `choices.py` |
| `nivel_riesgo_arl` | CharField | Choices: I / II / III / IV / V, `default='I'` |
| `foto` | ImageField | `upload_to='empleados/fotos/'`, nullable (mig 0008) |
| `estado` | CharField | `ACTIVO / RETIRADO`, `default='ACTIVO'` |
| `fecha_ingreso` | DateField | |
| `fecha_retiro` | DateField | nullable |
| `motivo_retiro` | CharField | choices `MOTIVO_RETIRO_CHOICES` (mig 0015, v4.10.0) — requerido al retirar, ver `EmpleadoBusinessService.retirar_empleado()` |
| `sede` | FK → `Sede` | `SET_NULL`, nullable (mig 0009) |
| `area` | FK → `Area` | `SET_NULL`, nullable (mig 0009) |
| `resolucion_dian` | FK → `ResolucionDIAN` | `SET_NULL`, nullable (mig 0012) — resolución DIAN preferida para DSPNE |

**Constraint:** `UNIQUE(empresa, tipo_documento, numero_documento)` → `uniq_empleado_per_tenant`
**Índices BD:** `(empresa, estado)`, `(numero_documento)`
**@property:** `nombre_completo` = `primer_nombre + " " + primer_apellido`

---

### `Contrato`
**Herencia:** `SintelTenantBaseModel` ✅  
**Máquina de estados:** ACTIVO → INACTIVO (→ HISTORICO legacy). Solo 1 ACTIVO por empleado.

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | único, indexado |
| `empresa` | FK → `Empresa` | `PROTECT` |
| `empleado` | FK → `Empleado` | `CASCADE` |
| `tipo` | CharField | `FIJO / INDEF / OBRA / PRESTACION` |
| `fecha_inicio` | DateField | |
| `fecha_fin` | DateField | nullable |
| `salario_mensual` | DecimalField(12,2) | `MinValueValidator(0.01)` |
| `auxilio_transporte` | DecimalField(12,2) | `default=0` |
| `prestamos_empresa` | DecimalField(12,2) | `default=0` |
| `horas_semanales` | PositiveSmallIntegerField | choices: 36/40/42/44/48, `default=42` (Ley 2101/2021) |
| `cargo` | CharField(120) | |
| `archivo_pdf` | FileField | `upload_to='empleados/contratos/'`, nullable |
| `estado` | CharField | `ACTIVO / INACTIVO / HISTORICO`, `default='ACTIVO'` |
| `activo` | BooleanField | campo legacy sincronizado con `estado` en `clean()` |

**Constraint:** `UNIQUE(empleado) WHERE estado='ACTIVO'` → `uniq_contrato_activo_per_empleado`
**Índices BD:** `(empresa, estado)`, `(empleado, estado)`, `(empleado, activo)`
**clean():** garantiza que `estado` nunca sea NULL

---

### `Devengo` (Nómina — INMUTABLE tras creación)
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Grupo | Notas |
|-------|-------|-------|
| `uuid`, `empresa`, `empleado`, `contrato` | FKs | PROTECT / CASCADE |
| `periodo_mes` | CharField | formato `YYYY-MM` |
| `fecha_inicio`, `fecha_fin` | DateField | nullable — primer/último día del período |
| `fecha_pago` | DateField | |
| `dias_laborados` | DecimalField(5,2) | `default=30`, `MinValidator(0.5)`, rango 0.5–31 |
| `salario_base` | DecimalField(12,2) | calculado por `NominaCalculationService` |
| `auxilio_transporte` | DecimalField(12,2) | 0 si PRESTACION |
| `otros_devengos` | DecimalField(12,2) | `default=0` |
| `horas_extras_diurnas` | DecimalField(6,2) | Lun-Sab 6am–9pm (+25%) |
| `horas_extras_nocturnas` | DecimalField(6,2) | 9pm–6am (+75%) |
| `recargo_nocturno_horas` | DecimalField(6,2) | horas nocturnas ordinarias (+35%) |
| `recargo_festivo_horas` | DecimalField(6,2) | dominicales/festivos (+75%) |
| `valor_horas_extras` | DecimalField(12,2) | `editable=False` — calculado |
| `salud_empleado` | DecimalField(12,2) | 4% IBC — 0 si PRESTACION |
| `pension_empleado` | DecimalField(12,2) | 4% IBC — 0 si PRESTACION |
| `prestamos` | DecimalField(12,2) | `default=0` |
| `descuentos_operativos` | DecimalField(12,2) | `default=0` |
| `neto_pagar` | DecimalField(12,2) | `editable=False` — calculado |
| `observaciones` | TextField | nullable |
| `anulado` | BooleanField | `default=False` — flag de inmutabilidad |

**Constraint:** `UNIQUE(empleado, periodo_mes, fecha_pago) WHERE anulado=False`
**Índices BD:** `(empresa, fecha_pago)`, `(empleado, fecha_pago)`, `(empleado, anulado)`, `(contrato)`, `(periodo_mes)`

---

### `ResolucionDIAN`
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Notas |
|-------|-------|
| `uuid` | único, indexado |
| `numero_resolucion`, `prefijo` | datos de la resolución DIAN |
| `rango_desde`, `rango_hasta` | IntegerField — rango autorizado de consecutivos |
| `consecutivo` | IntegerField — inicializado a `rango_desde` en `save()` (DEUDA-05 fix) |
| `fecha_resolucion`, `fecha_inicio`, `fecha_fin` | DateField |
| `vigente` | BooleanField |

**Métodos:** `formar_consecutivo(numero)` → `"PREFIJO-N"`, `esta_dentro_de_fecha(fecha)` → bool

---

### `TransmisionNominaDIAN`
| Campo | Notas |
|-------|-------|
| `devengo` | OneToOneField (CASCADE) |
| `resolucion` | FK → `ResolucionDIAN` (PROTECT) |
| `numero_documento` | `"PREFIX-N"` generado |
| `cune` | SHA-256(numero_documento + uuid + fecha_pago) |
| `estado_dian` | PENDIENTE / ACEPTADO / RECHAZADO |
| `xml_enviado`, `xml_respuesta` | TextField nullable — Fase 2 pendiente |

---

### `LiquidacionPrestacion`
| Campo | Notas |
|-------|-------|
| `uuid` | único, indexado |
| `empleado` | FK → `Empleado` (PROTECT) |
| `contrato` | FK → `Contrato` (PROTECT) |
| `tipo_liquidacion` | `PRIMA_SERVICIOS / CESANTIAS / VACACIONES / LIQUIDACION_DEFINITIVA` |
| `fecha_corte` | DateField |
| `dias_base_calculo` | IntegerField — calculado por ViewSet antes de `is_valid()` |
| `base_salarial` | DecimalField — salario + auxilio_transporte |
| `valor_total` | DecimalField — resultado del cálculo |
| `estado` | `PROYECTADO / PAGADO` — `default='PROYECTADO'` |
| `desglose_conceptos` | JSONField nullable — desglose completo de cada concepto |
| `observaciones` | TextField nullable |

**Índices BD:** `(empresa, empleado)`

---

### `PeriodoNomina` (v4.9.0 — mig 0014)

Orquesta el ciclo de aprobación en lote de un mismo ciclo de pago. Ver
`docs/nomina/NOMINA_FLUJO_EMPRESARIAL.md` para el diseño completo.
**No calcula montos** — delega siempre a `procesar_devengo()`.

| Campo | Notas |
|-------|-------|
| `uuid` | único, indexado |
| `periodo_mes` | `YYYY-MM` |
| `fecha_inicio`, `fecha_fin`, `fecha_pago` | DateField |
| `estado` | `ABIERTO / PRELIQUIDADO / EN_REVISION / APROBADO / PAGADO / CERRADO / ANULADO / BLOQUEADO` |
| `creado_por`, `aprobado_por`, `pagado_por` | FK → `perfil.TenantProfile`, `SET_NULL` |
| `fecha_aprobacion`, `fecha_pago_real` | auditoría de transición |

**Constraint:** `UNIQUE(empresa, periodo_mes) WHERE estado != 'ANULADO'`
**Máquina de estados:** `PeriodoNominaBusinessService.TRANSICIONES_VALIDAS`
(única fuente de verdad, `services/business_service.py`).
**⚠️ Deuda abierta (v4.10.0):** ni `cerrar_periodo()` ni `enviar_a_revision()`
verifican ausencia de empleados pendientes/errores antes de transicionar —
ver §Deudas Técnicas DEUDA-22.

---

### Migraciones (15 aplicadas)

| # | Contenido |
|---|-----------|
| 0001 | Crea `Empleado`, `Contrato`, `Devengo` base |
| 0002 | Agrega campos `uuid` |
| 0003 | Agrega `cuenta_contable_uuid` (deprecado) |
| 0004 | Elimina `cuenta_contable_uuid` |
| 0005 | Agrega campos H.E./recargos a `Devengo` |
| 0006 | Agrega `fecha_inicio`, `fecha_fin` a `Devengo` |
| 0007 | Agrega `horas_semanales` a `Contrato` |
| 0008 | Agrega `foto` a `Empleado` |
| 0009 | Agrega `sede`, `area` FK a `Empleado` |
| 0010 | Elimina `cuenta_contable_uuid` de `Devengo` |
| 0011 | Crea `ResolucionDIAN`, `TransmisionNominaDIAN`, `LiquidacionPrestacion` |
| 0012 | Agrega `resolucion_dian` FK a `Empleado` |
| 0013 | Agrega `desglose_conceptos` (JSONField) a `LiquidacionPrestacion` |
| 0014 | Crea `PeriodoNomina`, agrega `Devengo.periodo` FK (v4.9.0) |
| 0015 | Agrega `Empleado.motivo_retiro` (v4.10.0) |

---

## Service Layer

### `selectors.py` — Constantes SSoT (Zero Waste)

```
EMPLEADO_LIST_FIELDS    = 17 campos: id, uuid, tipo_documento, numero_documento,
                           primer/segundo nombre/apellido, estado, fecha_ingreso,
                           empresa_id, foto, email, telefono, sede, area, resolucion_dian
EMPLEADO_DETAIL_FIELDS  = + eps, afp, arl, nivel_riesgo_arl, empresa, fecha_retiro
_EMPLEADO_DETAIL_TRAVERSALS = empresa__id, sede__id/uuid/nombre, area__id/uuid/nombre,
                              resolucion_dian__id/uuid/numero_resolucion/prefijo/vigente

CONTRATO_LIST_FIELDS    = id, uuid, empleado, tipo, fecha_inicio, fecha_fin,
                           salario_mensual, auxilio_transporte, cargo, estado, activo,
                           empresa_id, horas_semanales
CONTRATO_DETAIL_FIELDS  = + prestamos_empresa, archivo_pdf

DEVENGO_LIST_FIELDS     = id, uuid, empresa_id, empleado, contrato, periodo_mes,
                           fecha_inicio, fecha_fin, fecha_pago, dias_laborados,
                           salario_base, auxilio_transporte, otros_devengos,
                           horas_extras_*, recargo_*, valor_horas_extras,
                           salud_empleado, pension_empleado, prestamos,
                           descuentos_operativos, neto_pagar, anulado
DEVENGO_DETAIL_FIELDS   = + observaciones
```

#### EmpleadoSelector
| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, search)` | Tabulator list con anotaciones: `tiene_contrato_activo`, `tiene_nominas_registradas`, `contrato_activo_uuid`, `cargo` |
| `get_detail(empresa_id, empleado_uuid)` | Single empleado con related data |
| `get_by_id(empresa_id, empleado_id)` | PK lookup (solo payloads internos validados) |
| `get_empleados_activos(empresa_id)` | Solo ACTIVO |
| `get_empleados_sin_contrato(empresa_id)` | ACTIVO sin contrato activo |
| `get_disponibles_para_periodo(empresa_id, fecha_inicio, fecha_fin)` | Elegibilidad ANTES de preliquidar: contrato activo y sin nóminas solapadas por rango de fechas |
| `get_empleados_pendientes_para_periodo(periodo)` | (v4.10.0) SSoT de "pendientes" DESPUÉS de preliquidar: contrato activo sin `Devengo` (no anulado) vinculado a ESE `PeriodoNomina` específico. Usado por `PeriodoNominaSelector.get_resumen()` y por el guard de `cerrar_periodo()` (DEUDA-22) |

#### ContratoSelector
| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, search, empleado_id)` | `select_related('empleado')` |
| `get_detail(empresa_id, contrato_uuid)` | Single contrato |
| `get_activo_for_empleado(empresa_id, empleado_id)` | Contrato ACTIVO del empleado (max 1 por constraint) |

#### DevengoSelector
| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, search, empleado_id, periodo_mes)` | QuerySet filtrado |
| `get_detail(empresa_id, devengo_uuid)` | Single devengo |
| `get_historial(empleado_id, empresa_id, search)` | Historial del empleado |
| `exists_for_periodo(empresa_id, empleado_id, periodo_mes)` | Boolean check |
| `get_ultima_for_empleado(empresa_id, empleado_id)` | Último devengo activo |

#### NominaSummarySelector
| Método | Descripción |
|--------|-------------|
| `get_summary(empresa_id)` | Dict: total_empleados, empleados_activos, empleados_retirados, total_nomina_mes, empleados_pagados |

---

### `business_service.py` — Reglas de Negocio

#### EmpleadoBusinessService
| Método | Descripción |
|--------|-------------|
| `crear_empleado(data, empresa)` | Delega a CRUD |
| `actualizar_empleado(empleado, data)` | Si `estado→RETIRADO`: cancela contratos activos automáticamente |
| `eliminar_empleado_retirado(empleado, empresa_id)` | Solo `RETIRADO`. Retorna `{contratos_eliminados, devengos_eliminados, empleado_eliminado}` |
| `cancelar_contratos_activos(empleado)` | → int (contratos cancelados) |

#### ContratoBusinessService
| Método | Descripción |
|--------|-------------|
| `gestionar_contrato(empleado, data, contrato_existente)` | Garantiza único ACTIVO: desactiva anterior si existe, crea/actualiza nuevo |
| `preparar_datos_contrato(data)` | Normaliza fechas, montos a Decimal, `default estado='ACTIVO'` |

#### DevengoBusinessService
| Método | Descripción |
|--------|-------------|
| `validar_contrato_activo(empleado)` | Lanza ValidationError si no hay contrato ACTIVO |
| `validar_limite_dias_mes(empleado_id, periodo_mes, nuevos_dias, empresa_id, devengo_id_excluir)` | Dict `{total_dias, nuevos_dias, total_final, excede_limite}` |
| `validar_duplicado(empleado_id, periodo_mes, fecha_pago, empresa_id)` | Dict o None |
| **`procesar_devengo(empleado, contrato, data, empresa_id, instance)`** | @transaction.atomic. Orquestación completa: cálculo nómina → resolución DIAN (prioridad empleado → fallback empresa) → guards consecutivo → crear Devengo → numero_documento → CUNE → TransmisionNominaDIAN |
| `anular_devengo(devengo, empresa_id)` | Sets `anulado=True` |
| `eliminar_devengo(devengo, empresa_id)` | Hard delete, retorna ID |

**Flujo DSPNE en `procesar_devengo()` (v4.6.0):**
```
1. NominaCalculationService.calcular_liquidacion()
2. Resolución (2 niveles):
   a) empleado.resolucion_dian_id → filter(id=..., vigente=True, rango_fechas).select_for_update()
   b) Fallback: ResolucionDIAN.filter(empresa_id, vigente=True, rango_fechas).select_for_update()
3. Guard: no existe → ValidationError + logger.warning
4. Guard: consecutivo < rango_desde → ValidationError + logger.error
5. Guard: consecutivo > rango_hasta → ValidationError + logger.error
6. DevengoCRUDService.crear_devengo()
7. numero_documento = prefijo + "-" + consecutivo_actual
8. CUNE = SHA256(numero_documento + devengo.uuid + fecha_pago)
9. TransmisionNominaDIAN (estado='PENDIENTE')
10. resolucion.consecutivo += 1; save(update_fields=['consecutivo'])
```

#### NominaCalculationService
| Método | Descripción |
|--------|-------------|
| **`calcular_liquidacion(...)`** | Nómina mensual: salario proporcional (dias_laborados/30), auxilio, H.E. con factores Decreto 2663/1950, IBC, deducciones 4%+4% (0 si PRESTACION). `ROUND_HALF_UP`. Máx: 80h por tipo H.E., 200h total. |
| **`calcular_dias_360(fecha_inicio, fecha_fin)`** | Estándar 30/360 europeo: si día=31 → 30 (INCONDICIONAL). Retorna días inclusive. **Crítico: v4.5.1 fix — antes condicionaba `if d1 >= 30: d2=30`, ahora siempre `d2=30`.** |
| **`calcular_liquidacion_prestaciones(...)`** | Prima, Cesantías, Intereses (12%), Vacaciones (30/360). Acepta: `dias_salario_pendiente`, `indemnizacion`. Contratos PRESTACION → todo cero. |

---

### `crud_service.py` — Persistencia @atomic

| Servicio | Métodos |
|---|---|
| **EmpleadoCRUDService** | `crear_empleado(data, empresa)`, `actualizar_empleado(empleado, data)`, `eliminar_empleado(empleado)` → cascades + desvincula TareaCorta |
| **ContratoCRUDService** | `crear_contrato(empleado, data)`, `actualizar_contrato(contrato, data)`, `desactivar_contratos_previos(empleado, contrato_excluir)` → sincroniza `estado` ↔ `activo` legacy |
| **DevengoCRUDService** | `crear_devengo(empleado, data)`, `actualizar_devengo(devengo, data)`, `anular_devengo(devengo)`, `eliminar_devengo(devengo)`, `actualizar_prestamo_contrato(contrato, monto_diferencia)` |

---

## API Layer

### Serializers (`api/serializers.py`) — 7 serializadores + 3 mixins/helpers

| Serializer | Uso |
|---|---|
| `NormalizationMixin` | Capitaliza nombres, normaliza email, Decimal para dias_laborados, `_get_empresa_id()` |
| `NullableUUIDField` | UUIDField que convierte `""` → `None` (FormData/HTMX) |
| `UUIDOrPKRelatedField` | Acepta UUID (con guiones) O PK entero. Auto-filtra queryset por `empresa_id` (DSV). `to_internal_value()` detecta `'-'` → `queryset.get(uuid=...)` |
| `EmpleadoListSerializer` | GET list. Computed: `nombre_completo`, `tipo_doc_display`, `estado_display`, `sede_nombre`, `area_nombre`, `foto_url`, `tiene_contrato_activo`, `tiene_nominas_registradas`, `contrato_activo_uuid`, `cargo` |
| `EmpleadoDetailSerializer` | POST/PATCH. NormalizationMixin + DSV sede/area/resolucion_dian. Nuevos campos: `resolucion_dian` (UUIDOrPKRelatedField) + `resolucion_dian_info` (read-only snapshot). |
| `ContratoNestedSerializer` | CRUD contratos. `validate()`: único ACTIVO por empleado. `validate_empleado()`: DSV. `update()`: bloquea edición si no es ACTIVO a menos que sea cambio de estado. |
| `DevengoSerializer` | CRUD devengos. Computed read-only: `salario_base`, `auxilio_transporte`, `salud_empleado`, `pension_empleado`, `neto_pagar`, `valor_horas_extras`, `empleado_uuid/nombre/documento`, `contrato_tipo/display/cargo`. `validate()`: YYYY-MM format, 0.5-31 días, unicidad. Solo contratos ACTIVO en queryset. |
| `ResolucionDIANSerializer` | CRUD resoluciones. `validate()`: `rango_desde ≤ rango_hasta`, `fecha_inicio ≤ fecha_fin` |
| `LiquidacionPrestacionSerializer` | CRUD liquidaciones. `empleado_id`/`contrato_id` como `PrimaryKeyRelatedField`. Read-only: `tipo_display`, `estado_display`, `empleado_nombre`, `contrato_cargo`. `validate()`: DSV empleado + contrato. |

---

### ViewSets (`api/viewsets.py`) — 5 ViewSets

#### EmpleadoViewSet
```
Herencia : BaseTenantViewSet + SintelDSVMixin + EmpleadoServiceMixin
Lookup   : uuid
Permisos : IsTenantMember + IsTenantAdminOrReadOnly
Parsers  : MultiPartParser + FormParser + JSONParser (foto)
```

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/empleados/` | GET | list — Tabulator, con anotaciones |
| `/api/v1/empleados/` | POST | create — 201, `was_updated=False` |
| `/api/v1/empleados/{uuid}/` | GET | retrieve — DSV |
| `/api/v1/empleados/{uuid}/` | PATCH | partial_update — 200, `was_updated=True` |
| `/api/v1/empleados/{uuid}/` | DELETE | destroy — solo `RETIRADO` |
| `/api/v1/empleados/summary/` | GET | `{total_empleados, empleados_activos, empleados_retirados, total_nomina_mes, empleados_pagados}` |
| `/api/v1/empleados/{uuid}/historial-nominas/` | GET | HTML offcanvas o JSON `{format=json}` |
| `/api/v1/empleados/gestor-offcanvas/` | GET | HTML form loader: `?tipo=empleado|contrato|devengo&uuid=&mode=` |
| `/api/v1/empleados/contrato-disponible/` | GET | `{disponible, error, contrato, periodo_mes}` |

#### ContratoViewSet
```
Herencia : BaseTenantViewSet + SintelDSVMixin + ContratoServiceMixin
Parsers  : MultiPartParser + FormParser + JSONParser (PDF)
```

| Endpoint | Descripción |
|---|---|
| `/api/v1/empleados/contratos/` | CRUD list/create/retrieve/partial_update |
| `/api/v1/empleados/contratos/{uuid}/cancelar/` | POST → `estado=INACTIVO` |
| `/api/v1/empleados/contratos/{uuid}/simular-liquidacion/` | GET → `{dias_primas, ..., total_neto}` |
| `render-offcanvas/crear|editar|detalle` | GET → HTML |

#### DevengoViewSet
```
Herencia : BaseTenantViewSet + SintelDSVMixin + DevengoServiceMixin
Filterset: empleado, anulado
Ordering : -fecha_pago, -periodo_mes, id
```

**IMPORTANTE:** `update()` / `partial_update()` → **405 Method Not Allowed**. Solo crear nuevos devengos.

| Endpoint | Descripción |
|---|---|
| `/api/v1/empleados/devengos/` | GET list / POST create |
| `/api/v1/empleados/devengos/{uuid}/` | GET retrieve / DELETE destroy |
| `/api/v1/empleados/devengos/{uuid}/anular/` | POST → `anulado=True` |
| `/api/v1/empleados/devengos/preview-calculo/` | POST → HTMX partial con valores calculados |
| `/api/v1/empleados/devengos/empleados-disponibles/` | GET → Empleados con contrato activo y sin nómina solapada |
| `/api/v1/empleados/devengos/{uuid}/ultimo-periodo/` | GET → `{tiene_nominas, ultimo: {...}}` |
| `/api/v1/empleados/devengos/verificar-periodo/` | GET → `{puede_crear, conflictos[], dias_registrados, dias_disponibles}` |
| `/api/v1/empleados/devengos/empleados-con-nominas/` | GET → Master panel: `[{empleado_uuid, empleado_nombre, empleado_documento, cargo, total_nominas, ultimo_periodo, ultimo_neto}]` |
| `/api/v1/empleados/devengos/{uuid}/info-empleado/` | GET → `{empleado, contrato}` para pre-fill de form |
| `render-offcanvas/crear|editar|detalle` | GET → HTML |

#### ResolucionDIANViewSet
| Endpoint | Descripción |
|---|---|
| `/api/v1/empleados/resoluciones-dian/` | CRUD list/create |
| `/api/v1/empleados/resoluciones-dian/{uuid}/` | retrieve/partial_update |
| `render-offcanvas/crear` | GET → HTML |

#### LiquidacionPrestacionViewSet

**IMPORTANTE:** `create()` calcula `dias_base_calculo`, `base_salarial`, `valor_total` ANTES de llamar `is_valid()` — los inyecta en el payload para pasar validación del serializer.

| Endpoint | Descripción |
|---|---|
| `/api/v1/empleados/liquidaciones-prestaciones/` | GET list / POST create |
| `/api/v1/empleados/liquidaciones-prestaciones/{uuid}/` | GET retrieve / DELETE destroy (solo si no hay pagos) |
| `/api/v1/empleados/liquidaciones-prestaciones/{uuid}/pdf/` | GET → TemplateHTML para impresión |
| `/api/v1/empleados/liquidaciones-prestaciones/empleados-con-liquidaciones/` | GET → Master panel |
| `/api/v1/empleados/liquidaciones-prestaciones/simular/` | GET → `{resultados, dias_base_calculo, base_salarial, valor_total, total_neto}` |
| `render-offcanvas/crear|detalle` | GET → HTML |

### URLs (`api/urls.py`) — Orden crítico

```python
router.register(r'contratos',                ContratoViewSet,             basename='contrato')
router.register(r'devengos',                 DevengoViewSet,              basename='devengo')
router.register(r'resoluciones-dian',        ResolucionDIANViewSet,       basename='resolucion-dian')
router.register(r'liquidaciones-prestaciones', LiquidacionPrestacionViewSet, basename='liquidacion-prestacion')
router.register(r'',                         EmpleadoViewSet,             basename='empleado')  # último
```

---

## Frontend

### JavaScript (`static/empleados/js/`) — 13 módulos

| Archivo | Namespace / Responsabilidad |
|---|---|
| `empleados.api.js` | `window.Sintel.Empleados.API` — SSoT de todos los endpoints |
| `empleados.module.js` | `...Module` — Orquestador principal. Sub-tabs: empleados/contratos/nominas/resoluciones/liquidaciones. `shown.bs.tab` listener. `tab-activated` listener. |
| `features/empleado_list.js` | `...EmpleadoList` — Tabulator grid empleados |
| `features/empleado_editor.js` | `...EmpleadoEditor` — Offcanvas crear/editar |
| `features/contrato_list.js` | `...ContratoList` — Tabulator grid contratos |
| `features/contrato_editor.js` | `...ContratoEditor` — Offcanvas contratos |
| `features/nomina_list.js` | `...NominaList` — **Master-Detail v4.8.0**: panel izquierdo = empleados con nóminas; panel derecho = historial del empleado seleccionado. `masterTable.on('rowClick', _seleccionarEmpleado)` (Tabulator 6 API — Fix v4.8.0) |
| `features/nomina_historial.js` | `...NominaHistorial` — Panel historial nóminas |
| `features/devengo_editor.js` | `...DevengoEditor` — Offcanvas crear devengo con preview cálculo. v4.8.1: Detecta empleado preseleccionado en Master → precarga automática de info vía `/info-empleado/` → bloquea selector general → dispara preview automático. Funciones nuevas: `_cargarInfoEmpleadoPreseleccionado()`, banderas `_precargarEmpleado` y `_empleadoPreseleccionado` con limpieza en `hide.bs.offcanvas`. |
| `features/resolucion_list.js` | `...ResolucionList` — Tabulator grid resoluciones DIAN |
| `features/resolucion_editor.js` | `...ResolucionEditor` — Offcanvas resoluciones |
| `features/liquidacion_list.js` | `...LiquidacionList` — **Master-Detail**: empleados con liquidaciones + historial. Botones Ver/PDF/Eliminar. |
| `features/liquidacion_editor.js` | `...LiquidacionEditor` — Offcanvas crear liquidación + panel simulación |

**Fix crítico v4.8.0 — `nomina_list.js`:**
```javascript
// ANTES (roto): rowClick como propiedad de config — ignorado silenciosamente en Tabulator 6
masterTable = new Tabulator(el, { rowClick: _seleccionarEmpleado, ... });

// DESPUÉS (correcto): API de eventos de Tabulator 6
masterTable = new Tabulator(el, { ... });
masterTable.on('rowClick', _seleccionarEmpleado);
```

### Templates (`templates/tenant/empleados/`) — 17 archivos

| Archivo | Descripción |
|---|---|
| `empleados_list.html` | Página principal — 5 sub-tabs: Empleados / Contratos / Nóminas (Master-Detail) / Resoluciones / Liquidaciones (Master-Detail) |
| `list.html` | Stub de entrada |
| `offcanvas_crear_empleado.html` | Form crear — incluye §6 "Nómina Electrónica DIAN" con dropdown de resoluciones activas |
| `offcanvas_editar_empleado.html` | Form editar — mismo §6 con valor pre-seleccionado; resolución inactiva como `disabled` con ⚠ |
| `offcanvas_detalle_empleado.html` | Read-only detail |
| `offcanvas_crear_contrato.html` | Form crear contrato |
| `offcanvas_editar_contrato.html` | Form editar contrato |
| `offcanvas_detalle_contrato.html` | Read-only detail contrato |
| `offcanvas_crear_devengo.html` | Form crear devengo (HTMX preview cálculo) |
| `offcanvas_crear_resolucion.html` | Form crear ResolucionDIAN |
| `offcanvas_crear_liquidacion.html` | Form crear liquidación + panel simulación |
| `offcanvas_detalle_liquidacion.html` | Detail liquidación — KPI strip + tabla conceptos + botones PDF / Marcar Pagado |
| `liquidacion_pdf.html` | Documento A4 standalone (Bootstrap CDN). `@media print` con `print-color-adjust: exact`. Firmas + footer legal normativa CST. |
| `devengo_calculo_partial.html` | HTMX partial — preview del cálculo en tiempo real |
| `offcanvas_historial_nominas.html` | Panel historial nóminas del empleado |
| `assets_empleados.html` | Carga assets JS en orden correcto |

---

## Conformidad AGENTS.md

| Regla | Sección | Estado |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | §14 | ✅ |
| `empresa_id` en todas las queries ORM | §4 | ✅ |
| `.only()` en todos los selectores | §4.5 | ✅ |
| `select_related()` donde hay FK traversals | §4.5 | ✅ |
| `uuid` como lookup_field (no PK entero en URLs) | §14, §25 | ✅ |
| `BaseTenantViewSet` en herencia ViewSets | §15 | ✅ |
| `IsTenantMember + IsTenantAdminOrReadOnly` | §15 | ✅ |
| `SintelDSVMixin` + `get_empresa()` en ViewSets | §13 | ✅ |
| `@transaction.atomic` en CRUD | §5 | ✅ |
| `select_for_update()` en asignación consecutivo DIAN | §5 | ✅ |
| Service Layer separado (CRUD + Business + Selectors) | §5 | ✅ |
| Pull Model Contabilidad — nunca import desde empleados | ADR-001 | ✅ |
| FK `resolucion_dian` en `Empleado` con DSV serializer | v4.6.0 | ✅ |
| `calcular_dias_360()`: d2=31→30 siempre | v4.5.1 fix | ✅ |
| `ResolucionDIAN.consecutivo` inicializa desde `rango_desde` | v4.5.1 fix | ✅ |
| `nomina_list.js`: `table.on('rowClick')` API Tabulator 6 | v4.8.0 fix | ✅ |
| `devengo_editor.js`: Master-Detail contexto + precarga empleado | v4.8.1 feature | ✅ |
| `nomina_list.js`: getter `getEmpleadoSeleccionado()` expuesto | v4.8.1 feature | ✅ |
| `empleados_list.html`: botón "Nueva Nómina" con listener `onclick` | v4.8.1 feature | ✅ |
| `offcanvas_crear_devengo.html`: mejorado panel-info + contenedor preselección | v4.8.1 feature | ✅ |
| `window.Sintel.Empleados.*` namespace FSD | §23 | ✅ |
| `window.http()` para mutaciones JS | §31 | ✅ |
| SSoT endpoints en `empleados.api.js` | §31 | ✅ |

**23/23 ✅ COMPLIANCE**

---

## Deudas Técnicas

| ID | Archivo | Prioridad | Descripción | Estado |
|---|---|---|---|---|
| DEUDA-11 | `TransmisionNominaDIAN` | MEDIA | XML UBL 2.1 no implementado. Infraestructura lista. `estado_dian='PENDIENTE'` indefinidamente. Fase 2 pendiente. | **AVANZADO (2026-09-18)** -- ver detalle abajo |
| DEUDA-06-CERRADO | `api/viewsets.py` | ~~ALTA~~ | `_RESOLUCION_LIST_FIELDS` y `_LIQUIDACION_LIST_FIELDS` agregados. Ambos `get_queryset()` usan `.only()`. | CERRADO |
| DEUDA-07-CERRADO | `business_service.py` | ~~CRÍTICA~~ | `calcular_dias_360()` corregido. Verified: año=360d, 2do sem=180d, Q1=90d. Impacto financiero ~$6.000 COP/empleado/período. | CERRADO |
| DEUDA-21-CERRADO | `api/viewsets.py` | ~~CRÍTICA~~ | `perform_create()` → `create()` completo pre-calcula campos antes de `is_valid()`. | CERRADO |
| DEUDA-22-CERRADO | `business_service.py` (`PeriodoNominaBusinessService`) | ~~ALTA~~ | `cerrar_periodo()` no validaba ausencia de empleados pendientes antes de transicionar (FASE 15: "no permitir CERRAR si hay empleados pendientes"). Corregido: guard vía `EmpleadoSelector.get_empleados_pendientes_para_periodo()`, probado en `test_cerrar_bloqueado_si_hay_empleados_pendientes`. `enviar_a_revision()` NO se tocó (avanzar con preliquidación parcial es una decisión de diseño ya documentada en `NOMINA_FLUJO_EMPRESARIAL.md` §3, no un bug). | CERRADO |
| DEUDA-23-CERRADO | `tests/` | ~~ALTA~~ | Cero tests automatizados cubrían la máquina de estados de `PeriodoNomina`. Corregido: `tests/test_periodo_nomina_state_machine.py` (8 casos: flujo completo, transiciones inválidas, duplicados, cierre con pendientes, anulación en cascada, bloqueo/desbloqueo, permisos por rol). | CERRADO |
| DEUDA-24-CERRADO | `models.py`, `business_service.py`, `api/viewsets.py` | ~~CRÍTICA~~ | Retiro de empleado era un PATCH directo sin motivo ni liquidación forzada; indemnización era un número manual; se podía crear LIQUIDACION_DEFINITIVA sin retiro. Corregido v4.10.0: `retirar_empleado()` + `calcular_indemnizacion_despido()` (CST art. 64) + guard en `LiquidacionPrestacionViewSet.create()`. | CERRADO |
| DEUDA-25-CERRADO | `api/serializers.py`, `api/viewsets.py`, frontend | ~~CRÍTICA~~ | `DevengoSerializer` no tenía campo `periodo` — imposible liquidar individualmente a un empleado dentro de un `PeriodoNomina` (la única vía, `preliquidar_periodo()`, fuerza 30 días para todos). Corregido v4.11.0: campo `periodo` + endpoints `empleados-pendientes`/`empleados-liquidados` + UI de tabs Pendientes/Liquidados. Ver sección v4.11.0 arriba. | CERRADO |
| DEUDA-26 | `business_service.py` (`preliquidar_periodo`) | BAJA (documentada, no oculta) | El batch `preliquidar_periodo()` sigue generando una base de 30 días idéntica para todos los elegibles — sigue siendo válido como atajo rápido, pero ya no es la única vía (ver DEUDA-25-CERRADO); su docstring ahora aclara explícitamente que la liquidación individual es la vía recomendada para días reales por empleado. No se eliminó ni se modificó su comportamiento para no romper `test_periodo_nomina_state_machine.py`. | **ABIERTO (por diseño, bajo impacto)** |
| DEUDA-27 | `tables.py` (`PeriodoNominaTable`) | BAJA | Columnas nuevas `empleados_count`/`total_neto_periodo` (FASE 23, histórico) verificadas manualmente en shell (queryset anotado + valores correctos) pero sin test automatizado dedicado a la tabla/vista HTML. | **ABIERTO** |
| DEUDA-28-CERRADO | `api/viewsets.py` (`DevengoViewSet.render_offcanvas_detalle`), `offcanvas_detalle_devengo.html` | ~~MEDIA~~ | FASE 19 pedía una vista de "revisión individual" de solo lectura para cada Devengo; `render_offcanvas_detalle` reutilizaba el MISMO template que crear. Corregido v4.12.0: template de detalle dedicado (`offcanvas_detalle_devengo.html`) + botón PDF, `render_offcanvas_detalle()` reescrito con `self.get_object()` (fix del bug de `get_queryset()` devolviendo instancia). | CERRADO |
| DEUDA-29 | Frontend (`static/empleados/js/`) | BAJA (arquitectura, no funcional) | FASE 30 de la misión pide un objeto `NominaStore` explícito como única fuente de verdad en el cliente. No se implementó: el patrón actual ya evita la causa raíz que ese Store buscaría prevenir (Tabulator/HTML nunca calculan pendientes ni montos — todo viene de `fetch` a los endpoints backend en cada apertura/refresco), pero el estado vive disperso en variables de módulo (`_periodoActualUuid`, `_periodoContexto`, etc.) en vez de un objeto centralizado. Refactor de arquitectura pura, alto esfuerzo/riesgo de regresión, sin beneficio funcional adicional sobre lo ya corregido — no se hizo en esta pasada. | **ABIERTO (arquitectura, bajo impacto funcional)** |
| DEUDA-30 | `business_service.py` (`calcular_aportes_patronales`) | MEDIA (supuesto legal documentado) | ARL usa el valor MÍNIMO de tabla por clase de riesgo (Decreto 1607/2002) — la tarifa real negociada con la ARL puede ser distinta dentro del rango autorizado por clase; y NO se aplica la exoneración de ICBF/SENA (Ley 1607/2012 art. 25) porque el régimen tributario de la empresa no es un dato que el modelo `Empresa` capture hoy. El aporte patronal calculado es una cota superior conservadora (nunca subestimada), no un valor certificado contra la parametrización fiscal real de cada tenant. | **ABIERTO (supuesto documentado, no oculto)** |
| DEUDA-31 | `business_service.py`, `api/viewsets.py`, frontend `periodo_detail.js` | ALTA (funcionalidad pedida, no implementada) | El prompt "Periodos de Nómina" secciones 20-38 pide revisión/aprobación/devolución/cancelación **individual por empleado** dentro de un período, con selección múltiple, aprobación masiva y autorización de pago individual/masiva/de período completo (con confirmación mostrando impacto económico). Hoy la aprobación sigue siendo SOLO a nivel de período completo (`PeriodoNominaBusinessService.TRANSICIONES_VALIDAS`) — `Devengo` no tiene estado de revisión propio (solo `anulado`). Requiere una máquina de estados nueva en `Devengo` (migración + guards + tests + UI con checkboxes) — misión separada por tamaño/riesgo, no improvisada a medias. | **ABIERTO (diferido explícitamente — ver v4.13.0)** |

---

### DEUDA-11 (2026-09-18) — XML NominaIndividual + CUNE real al procesar un Devengo

**Que se hizo:** `apps/tenant/empleados/services/dian/` (nuevo paquete):
`CuneService.calcular()` (formula CUNE propia, ya no el placeholder
`SHA256(numero_documento+devengo.uuid+fecha_pago)` que existia antes) y
`NominaXMLBuilderService.build()` (XML `NominaIndividual` completo:
control DIAN, Empleador, Trabajador, Pago, Devengados, Deducciones,
Resumen). `DevengoBusinessService._generar_xml_nomina_dian()` (nuevo,
`business_service.py`) construye el DTO desde `Devengo`/`Empleado`/
`Contrato`/`Empresa`/`ResolucionDIAN`, calcula el CUNE, genera el XML y lo
firma con `apps.tenant.core.dian.XadesSignerService.sign()` (mismo
servicio ya compartido con Factura Electronica desde NOMINA-03, ver
`docs/nomina/NOMINA_DIAN_AUDIT.md`) -- `TransmisionNominaDIAN.xml_enviado`
ahora queda poblado con el XML real (firmado si hay certificado DIAN
configurado, sin firmar en modo borrador si no -- mismo comportamiento que
Factura Electronica).

**Bug real encontrado (y corregido en el codigo nuevo) durante esta
pasada:** el patron `ET.Element(tag, attrib={"xmlns": NS[...]})` +
`root.set("xmlns:prefix", ...)` manual, ya usado en
`UBL21BuilderService._build_invoice()` (facturas), produce XML con
atributos `xmlns:*` DUPLICADOS (`ElementTree.tostring()` los vuelve a
emitir automaticamente via `register_namespace()`) -- confirmado
reproduciendolo contra el propio `UBL21BuilderService`:
`ET.fromstring()` sobre su salida lanza `ParseError: duplicate attribute`.
Es decir, **el XML de Factura Electronica que ya esta en produccion segun
`COMPLETO_FLUJO_FACTURAS.md` no es XML valido/parseable tal como se
genera hoy** -- hallazgo nuevo, no corregido en `facturas` en esta pasada
(fuera de alcance de DEUDA-11, requiere decision explicita antes de
tocar el pipeline de Factura Electronica). `NominaXMLBuilderService`
evita el bug (no declara `xmlns:*` a mano, deja que
`register_namespace()` los genere solos).

**Verificado (corrida limpia, sin contaminacion de otras corridas):**
`pytest apps/tenant/empleados/tests/test_dian_nomina_electronica.py
apps/tenant/empleados/tests/test_crud_smoke_v38.py` -> **28 passed**,
incluye `test_transmision_nomina_dian_queda_con_xml_firmado` (crea un
Devengo real via API, confirma `TransmisionNominaDIAN.xml_enviado` no
vacio, XML parseable, CUNE de 96 hex chars presente en el XML y
coincidente con `TransmisionNominaDIAN.cune`). No se pudo re-verificar
`test_periodo_nomina_state_machine.py` en esta pasada por inestabilidad
de infraestructura de la sesion (la base `test_sintel` se caia a mitad de
creacion repetidamente, sin ningun traceback dentro del codigo tocado --
0 excepciones de negocio, solo `OperationalError`/`SystemExit` de
Postgres) -- pendiente de una corrida limpia en un entorno estable antes
de dar por cerrado el regression gate completo de `empleados`.

**NO VERIFICADO (bloqueador real, documentado, no oculto -- mismo
criterio que `apps/tenant/core/dian/adapters.py`):** la formula exacta
del CUNE (orden/nombres de campo) y la estructura exacta del XML
`NominaIndividual` (namespaces, tags) estan reconstruidas de
conocimiento publico general del Anexo Tecnico DSPNE v1.0, **no
confirmadas contra el PDF oficial ni contra el ambiente de habilitacion
DIAN**. Transmision SOAP real sigue sin existir (mismo bloqueador que
Factura Electronica -- `DIANAdapter` no verificado, sin WSDL/certificado
configurado en ningun entorno). No usar para transmitir a produccion sin
antes: (1) confirmar CUNE/XML contra el Anexo Tecnico vigente, (2)
validar contra un caso de prueba DIAN real, (3) resolver el bloqueador de
transporte SOAP (compartido con facturas).

---

## Validaciones (manage.py check)

```
Sistema: 0 errores
python manage.py check: 0 errores (verificado 2026-09-10)
py_compile: OK (archivos tocados en v4.10.0)
node --check: disponible en el HOST (v26.7.0, corrige nota anterior) aunque no en el contenedor `web` -- usado en v4.13.0 para validar los 17 .js modificados/nuevos de la sesion (incluye `periodo_detail.js`), 0 errores de sintaxis.
Migraciones: 0015 aplicada en public + los 3 tenants (2026-09-10)
```

---

**Última Actualización:** 2026-09-11 (v4.13.0)
**Auditor:** Claude Sonnet 5 (Anthropic)
**Status:** ⚠️ PRODUCTION READY CON DEUDAS DOCUMENTADAS — ver §Deudas Técnicas (DEUDA-11, DEUDA-26, DEUDA-27, DEUDA-29, DEUDA-30, DEUDA-31 abiertas) — 23/23 AGENTS.md COMPLIANCE
**Cambios v4.13.0:** Centro de control de período — aportes patronales EPS/AFP/ARL/parafiscales + costo total empresa en `GET periodos-nomina/{uuid}/resumen/`, sección "Resumen Financiero" en `periodo_detail.js`. Ver sección v4.13.0 arriba. **Pendiente explícitamente diferido:** workflow de aprobación/pago individual por empleado dentro de un período (DEUDA-31).
**Cambios v4.12.1 (ya en el working tree al iniciar esta auditoría):** integridad de liquidación individual — `UniqueConstraint` de BD (migración 0016), `validar_no_solapamiento()`, `select_for_update()` en `procesar_devengo()`. Ver sección v4.12.1 arriba.
**Migraciones:** 0001–0016 (16 total, todas aplicadas)
**Tests:** `tests/test_periodo_resumen_financiero.py` (nuevo, 4 casos, v4.13.0) + `tests/test_liquidacion_individual_por_periodo.py` (5 casos, v4.12.1) + `tests/test_periodo_nomina_state_machine.py` (8 casos, v4.9.0) — ejecutados via `pytest apps/tenant/empleados/tests` en Docker, 2026-09-11 (ver resultado real antes de asumir vigente, no se copia aquí un conteo que no se haya verificado en esta misma pasada).
