# AUDIT BASELINE — 2026-09-12

Auditoría Fase 0 (read-only) de la misión "SINTEL ERP — Auditoría profunda + corrección de lógica + UI + API + integraciones", ejecutada mediante 8 agentes de investigación en paralelo (uno por dominio) sobre el estado real del código en `feat/onboarding-cookie`. Ningún archivo fue modificado durante esta fase. Cada hallazgo cita archivo:línea real; los agentes tuvieron instrucción explícita de no fabricar hallazgos y de reportar explícitamente qué ya funciona correctamente para no re-auditar código sólido en fases posteriores.

**Regla de esta fase (recordatorio):** no corregir todo al mismo tiempo. Este documento es el punto de partida para decidir, por fase, qué se corrige primero.

## Resumen ejecutivo

| Dominio | Hallazgos | CRÍTICO | ALTO | MEDIO | BAJO |
|---|---|---|---|---|---|
| Clientes + Cartera | 5 | 2 | 0 | 2 | 1 |
| Empleados / Nómina | 6 | 0 | 0 | 3 | 3 |
| Cotizaciones | 8 | 1 | 0 | 5 | 2 |
| Compras | 8 | 0 | 4 | 3 | 1 |
| Ventas | 3 | 1 | 1 | 1 | 0 |
| Proyectos | 3 | 1 | 0 | 1 | 1 |
| Bancos | 6 | 0 | 1 | 4 | 1 |
| Moneda + Frontend transversal | 12 | 0 | 2 | 7 | 3 |
| **TOTAL (auditoría inicial)** | **51** | **5** | **8** | **26** | **12** |

*+1 hallazgo nuevo (T-13, BAJO) encontrado en vivo durante la Fase 2 de remediación, no parte de la auditoría inicial de 8 agentes — ver sección "Fase 2" abajo. Total actualizado: 52.*

Los 5 CRÍTICO son, en orden de blast-radius:

1. **Cartera**: los filtros y KPIs de cartera activa/pagada consultan `Factura.estado_pago`, que `registrar_abono()` (el único flujo de pago autorizado) nunca actualiza — una factura pagada 100% vía abono manual nunca aparece en "Pagadas" ni sale de "Pendiente"/"Vencidas" en KPIs.
2. **Cartera**: el endpoint de creación de obligaciones (`registrar_cartera`, pensado para ETL) puede sobreescribir silenciosamente `valor_pagado` de una obligación ya existente si se reenvía el mismo `(cliente, numero_factura)` — sin locking, sin guardas, sin trazabilidad — desde el mismo formulario manual "Nueva Obligación" que usa un usuario.
3. **Cotizaciones**: el PDF recalcula IVA de forma independiente al dominio y usa `iva_porcentaje or 19` en vez de `or 0` — una cotización explícitamente exenta de IVA (0%) se factura al cliente en el PDF con 19% de IVA.
4. **Ventas**: "Ver" está roto al 100% en producción — `{% load humanize %}` nunca fue registrado en `INSTALLED_APPS`, causando un 500 silencioso (HTMX no hace swap en respuestas no-2xx) cada vez que se abre el detalle de una venta.
5. **Proyectos**: `avanzar-fase` no persiste `fase_actual` en BD — el commit que "optimizó" el guardado (`update_fields` limitado a 4 campos financieros) eliminó sin darse cuenta el único `save()` que persistía el cambio de fase. La respuesta HTTP parece correcta (serializa el objeto en memoria) pero la fila real en Postgres nunca cambia.

---

## Estado de remediación (actualizado 2026-09-12, en vivo durante la ejecución de fases)

Detalle completo de cada fix (causa raíz exacta, diff conceptual, test, resultado de pytest) en `docs/remediation/RELEASE_GATE_20260912.md` y en el `.agent/*.md` de cada app tocada.

### Fase 1 — los 5 CRÍTICO — ✅ COMPLETADA, verificada con test

| # | Hallazgo | Fix | Test nuevo | Resultado |
|---|---|---|---|---|
| C-1 | Cartera: filtros/KPIs leían `Factura.estado_pago` | `selectors.py`: anota y prefiere `cartera_estado` | `test_cartera_filtros_kpis_reflejan_abono_real.py` | PASS |
| C-2 | Cartera: creación manual podía sobreescribir abono (+ bug lateral: creación nueva vía API estaba rota, nunca pasaba `cliente_id`) | `viewsets.py`: 409 en duplicado + fix `cliente_id` | `test_cartera_no_sobrescribe_obligacion_existente.py` | PASS |
| Q-1 | Cotizaciones: PDF cobraba 19% IVA en cotización exenta | `pdf_export_service.py`: `or 0` en vez de `or 19` | `test_pdf_iva_cero.py` | PASS |
| V-1 | Ventas: "Ver" 500 por `humanize` no registrado | Template: `currency_cop`/`format_cop` en vez de `humanize` | `test_detalle_venta_offcanvas.py` | PASS |
| P-1 | Proyectos: `avanzar-fase` no persistía `fase_actual` | `viewsets.py`: `save_proyecto()` completo restaurado | `test_avanzar_fase_persistencia.py` | PASS |

Regresión de app completa corrida tras Fase 1: `apps/tenant/clientes/tests/` → **51 passed** (el único `1 error` es un artefacto de teardown de pytest-django en `test_cartera_concurrencia.py`, diagnosticado como preexistente y no relacionado — la aserción del test en sí pasa en aislamiento, ver `.agent/AUDITORIA_FLUJO_CLIENTES.md`).

### Fase 2 — 8 ALTO — ✅ COMPLETADA, verificada con test

| # | Hallazgo | Fix | Test | Resultado |
|---|---|---|---|---|
| CO-1 | Compras: plantillas invisibles (gap de UI) | Pantalla de gestión nueva + editar + activar/desactivar | `test_co1_plantillas_visibles.py` (nuevo) + suite compras | PASS (1/1 + 43/43) |
| CO-2 | Compras: botón "Marcar Recibida" muerto | Botón removido del detalle | Suite compras (cambio de template) | PASS (43/43) |
| CO-3 | Compras: `estado` bypaseaba la máquina de estados | `estado` read-only en el serializer | `test_co3_co4_estado_endpoint.py` (nuevo) + suite compras | PASS (2/2 + 43/43) |
| CO-4 | Compras: transiciones no actualizaban `updated_at` | `update_fields` incluye `updated_at` | `test_co3_co4_estado_endpoint.py` (nuevo) + suite compras | PASS (1/1 + 43/43) |
| V-2 | Ventas: "Editar" no-op silencioso | Orquestación completa + UI reutilizando offcanvas de Crear | `test_editar_venta.py` + `test_detalle_venta_offcanvas.py` | PASS (4/4) |
| B-1 | Bancos: `_resolver_empresa_id` frágil vs. path de creación | Fallback amplio + singleton | `test_b1_resolucion_empresa_id_fallback.py` (nuevo) + suite bancos | PASS (1/1 + 14/14) |
| T-4 | Cotizaciones: PDF sin separador de miles | `currency_cop`/`format_cop` en `formato_profesional.html` | Template parsea correctamente; sin test específico de formato | PASS_WITH_LIMITATIONS |
| T-5 | NaN en Estado de Resultados + riesgo en Compras | Guardas null/NaN en ambos `formatMoney` | JS puro, `node --check` (sintaxis) — sin suite de tests de frontend en este repo | PASS_WITH_LIMITATIONS |

Detalle completo (root cause, diffs conceptuales, evidencia por fila) en `docs/remediation/RELEASE_GATE_20260912.md`. **Hallazgo lateral encontrado durante la verificación de V-2/CO-2** (no en la auditoría original): comentarios Django `{# ... #}` multilínea se renderizan como texto literal en vez de ser stripped (Django no soporta saltos de línea en la forma corta) — corregido en los 3 archivos tocados esta sesión, ver T-13 abajo. Mismo patrón confirmado como deuda preexistente (no tocada) en otros 3 archivos no relacionados a esta misión.

---

## Metodología

Cada agente auditó de forma read-only (Read/Grep/Glob/`git log`/`git show`/`git diff --stat`, sin editar ni ejecutar comandos mutantes) uno de estos 8 alcances, recorriendo MODELO → SERVICE → SELECTOR → SERIALIZER → VIEWSET → API CLIENT → JS → TEMPLATE → UI:

1. Clientes + Cartera (`apps/tenant/clientes/`)
2. Empleados / Períodos de Nómina (`apps/tenant/empleados/`)
3. Cotizaciones — botón Guardar + PDF (`apps/tenant/cotizaciones/`)
4. Compras — plantillas, edición, aprobar/anular (`apps/tenant/compras/`)
5. Ventas — CRUD + bug "Ver" (`apps/tenant/ventas/`)
6. Proyectos — sincronización de estado (`apps/tenant/proyectos/`)
7. Bancos — extractos, causación, CRUD (`apps/tenant/bancos/`)
8. Moneda COP transversal + infraestructura frontend compartida

Antes de reportar, cada agente verificó `git log`/`git show` de commits recientes relevantes al área (para no re-reportar como "nuevo" algo ya corregido) y contrastó contra la documentación `.agent/*.md` de cada app para distinguir deuda técnica ya conocida y aceptada de regresiones nuevas.

---

## 1. Clientes + Cartera

Arquitectura confirmada: `Cartera` (estado propio SIN_PAGO/PARCIAL/PAGADA, `models.py:119-227`) es un modelo separado de `Factura` (estado propio NO_PAGADA/PAGO_PARCIAL/PAGADA), unidos por `factura_uuid` sin FK (Bounded Context). El listado/KPIs de Cartera leen `Factura` vía Pull Model y sobreponen el estado real de `Cartera` cuando existe fila — pero solo en el *listado*, no en los *filtros* ni en los *KPIs*.

### C-1 — CRÍTICO — Filtros/KPIs de cartera leen `Factura.estado_pago`, no el estado real de `Cartera`
- **ARCHIVO:** `apps/tenant/clientes/services/selectors.py:343-345, 436-461`; `apps/tenant/clientes/services/business_service.py:300-327` (`registrar_abono`)
- **CAUSA:** `registrar_abono()` solo escribe `Cartera.valor_pagado/saldo/estado_pago`, nunca `Factura.estado_pago`. `qs_list_facturas_venta(estado_pago=...)` y `get_cartera_kpis_facturas_venta()` filtran/cuentan sobre `Factura.estado_pago`.
- **ACTUAL:** una factura pagada 100% solo vía abono manual (nunca conciliada por Bancos) nunca aparece bajo `?estado_pago=PAGADA`, sigue contando en `pendiente_count`/`vencidas_count`, y su monto nunca entra a `pagado_monto`.
- **ESPERADO:** filtros/KPIs deben reflejar el mismo estado (Cartera-override) que ya usa el listado visual.
- **SOLUCIÓN PROPUESTA:** reescribir `qs_list_facturas_venta`/`get_cartera_kpis_facturas_venta` para preferir el subquery/mapa de `Cartera` igual que ya hacen `sin_pago_count`/`parcial_count`, con fallback a `Factura.estado_pago` solo si no existe fila `Cartera`.
- **PRUEBA:** crear Factura con `estado_pago=NO_PAGADA` (default real, no forzado), registrar abono completo vía `registrar_abono()`, assert `GET /cartera/?estado_pago=PAGADA` la incluye y los KPIs reflejan el cambio.
- **NOTA:** el test existente (`test_cartera_pull_model_saldo_real.py:38-41`) enmascara este bug porque fuerza `Factura.estado_pago` a mano en vez de dejar que `registrar_abono()` sea la única fuente de cambio.

### C-2 — CRÍTICO — Segundo camino de escritura no controlado sobre `valor_pagado`
- **ARCHIVO:** `apps/tenant/clientes/services/business_service.py:258-298` (`registrar_cartera`); `apps/tenant/clientes/api/viewsets.py:859-888`; `offcanvas_crear_cartera.html:74-82`
- **CAUSA:** `registrar_cartera()` es un `get_or_create()` idempotente pensado para sync ETL, pero es la misma función que atiende `POST /api/v1/clientes/cartera/`, el endpoint que usa el formulario manual "Nueva Obligación" (con campo editable `valor_pagado`, escribible en el serializer). Si el `(cliente, numero_factura)` ya existe, la rama "not created" sobreescribe `valor_pagado` sin `select_for_update()`, sin guarda de "ya PAGADA", sin `CarteraNota`.
- **ACTUAL:** un usuario puede re-enviar "Nueva Obligación" con un `numero_factura` existente y un `valor_pagado` arbitrario, sobreescribiendo silenciosamente el abono ya registrado — bypaseando por completo `registrar_abono()`.
- **ESPERADO:** los pagos solo deben mutar vía `registrar_abono()`. Crear una obligación que ya existe debe rechazarse (409/400), no actualizarla.
- **SOLUCIÓN PROPUESTA:** separar el upsert ETL (uso interno/sistema) de `CarteraViewSet.create()` (uso manual, debe rechazar duplicados); marcar `valor_pagado` read-only en creación manual, o enrutar "Abono Inicial" a través de `registrar_abono()` después de crear la fila.
- **PRUEBA:** crear Cartera con abono parcial vía `registrar_abono()`, luego `POST /cartera/` con mismo cliente+numero_factura y `valor_pagado` distinto — debe rechazarse, hoy se sobreescribe.

### C-3 — MEDIO — "Todas" es el filtro por defecto (mezcla PAGADA con activa)
- **ARCHIVO:** `clientes_list.html:170-186`; `clientes.cartera.js:166-212,237-250`
- No hay vista "activa" por defecto (SIN_PAGO+PARCIAL) ni "histórico" dedicado — un único grid con filtro opcional. Es una decisión de producto pendiente de confirmar con el usuario, no un bug puro.

### C-4 — MEDIO — Divergencia Factura↔Cartera tras des-conciliación bancaria (deuda ya documentada, CLI-05)
- **ARCHIVO:** `apps/tenant/bancos/services/crud_service.py:190-224`; `apps/tenant/facturas/services/business_service.py:1441-1488`; `apps/tenant/clientes/services/business_service.py:351-427`
- Ya trackeado en `.agent/AUDITORIA_FLUJO_CLIENTES.md` (DEUDA-C03/CLI-05). Confirmado que sigue presente; no requiere nueva acción más allá de lo ya scoped, pero agrava C-1.

### C-5 — BAJO — Test-gap que enmascaró C-1
- Ver nota en C-1. Clasificación: DOCUMENTATION DRIFT / test-gap.

**Ya correcto (no re-auditar):** aritmética de `Cartera.save()` (SIN_PAGO/PARCIAL/PAGADA); aislamiento multi-tenant en selectors/viewsets/crud; DSV en `get_object()`; guardas de `registrar_abono()` (`select_for_update`, no-doble-pago, no-sobrepago) cuando se llega por el endpoint correcto; columnas del grid completas; `PATCH`/`DELETE` de Cartera correctamente restringidos; separación limpia de `registrar-abono`/`notas`/`kpis` (solo `list()` conflacía activa/histórico).

---

## 2. Empleados / Períodos de Nómina

El commit `e312dcbe` (2026-09-10, "NOMINA-01") ya corrigió correctamente: liquidación individual dentro de un período (con FK `periodo` en el serializer), endpoints `empleados-pendientes`/`empleados-liquidados`, retiro controlado, cierre con validación. Verificado end-to-end, no se re-flaguea.

### E-1 — MEDIO — Sin flujo de aprobación por empleado (Revisar/Aprobar/Devolver/Cancelar)
- **ARCHIVO:** `apps/tenant/empleados/api/viewsets.py:927-1176` (`DevengoViewSet`, solo tiene `anular`); `tables.py:411-428`
- `Devengo` no tiene más estado que el booleano `anulado`. Todo el workflow de aprobación vive solo a nivel de `PeriodoNomina` (todo el período), nunca por Devengo individual.
- **Ya documentado:** `.agent/AUDITORIA_FLUJO_EMPLEADOS.md` DEUDA-31 (2026-09-11) — mismo hallazgo, ya abierto.
- **SOLUCIÓN:** requiere una máquina de estados nueva sobre `Devengo` (migración + guardas + tests + UI) — no improvisar aquí, es su propia misión.

### E-2 — MEDIO — Sin selección múltiple para aprobación/pago masivo por empleado
- Mismo root cause que E-1 (mismo DEUDA-31). `aprobar`/`marcar_pagado` actúan siempre sobre el período completo.

### E-3 — GAP DE NEGOCIO — "Liquidar general" fuerza 30 días idénticos para todos (decisión ya documentada, no un bug nuevo)
- **ARCHIVO:** `apps/tenant/empleados/services/business_service.py:756-835`, hardcode línea 810
- `preliquidar_periodo()` no lee ningún dato por-empleado; da a Juan/Pedro/María 30 días a los tres. Para lograr 8/15/5 el operador debe usar "Liquidar individual" tres veces (ese camino sí preserva días independientes, verificado correcto).
- **Ya documentado como decisión consciente:** `.agent/AUDITORIA_FLUJO_EMPLEADOS.md` DEUDA-25-CERRADO ("base rápida corregible, nunca sustituto de la liquidación real").
- **RIESGO real:** ALTO si el operador usa "Preliquidar" creyendo que ya refleja días reales.

### E-4 — MEDIO — Sin confirmación en acciones críticas de período (Aprobar/Marcar pagado/Cerrar) — **hallazgo nuevo**
- **ARCHIVO:** `apps/tenant/empleados/static/empleados/js/features/periodo_detail.js:47-60`
- Solo `anular` tiene `confirm:`. `cerrar_periodo()` lleva a `CERRADO`, estado terminal sin transiciones de salida (`TRANSICIONES_VALIDAS['CERRADO'] = set()`) — un clic accidental es irreversible vía UI/API.
- **SOLUCIÓN:** agregar `confirm: '...'` a `aprobar`, `marcarPagado`, `cerrar` en `ACCIONES_POR_ESTADO`, mismo patrón que `anular` (~3 líneas).

### E-5 — BAJO — Código muerto en `PeriodoNominaCRUDService.actualizar_estado`
- **ARCHIVO:** `apps/tenant/empleados/services/crud_service.py:226-229` — `return contrato` inalcanzable tras `return periodo` (variable ni siquiera definida en ese scope). Eliminar línea 229.

### E-6 — BAJO — `min` del input de días no coincide con la regla real del backend
- **ARCHIVO:** `offcanvas_crear_devengo.html:114-115` (`min="0.1"`) vs `serializers.py:470-476`/`models.py:311` (mínimo real 0.5). Backend seguro (rechaza con 400), solo el hint del frontend es engañoso.

**Ya correcto (no re-auditar):** liquidación individual con FK período; anti-duplicidad (empleado, periodo) reforzada a **nivel BD** vía `UniqueConstraint` condicional (`models.py:400-404`, migración `0016`) + `select_for_update()`; caso Juan(8)/Pedro(15)/María(5) verificado — 3 Devengos independientes, imposible duplicar; aislamiento multi-tenant en todos los selectors; `cerrar_periodo()` bloqueando pendientes; retiro controlado de empleado; inmutabilidad de Devengo (update/partial_update → 405).

---

## 3. Cotizaciones

`COTIZACIONES-01` (commit `83416baf`) tocó máquina de estados y conversión a Venta — no tocó templates/JS/PDF, ortogonal a estos hallazgos.

### Q-1 — CRÍTICO — El PDF recalcula IVA de forma independiente y con bug (`or 19` en vez de `or 0`)
- **ARCHIVO:** `apps/tenant/cotizaciones/services/pdf_export_service.py:46-93`, línea 55 (`Decimal(str(cotizacion.iva_porcentaje or 19))`) vs SSoT `business_service.py:251` (`... or 0`)
- **ACTUAL:** una cotización explícitamente con IVA=0% (ej. exenta) se renderiza en el PDF con 19% de IVA — `0 or 19` evalúa `19` en Python. El total del PDF no coincide con `cotizacion.total_con_impuestos` mostrado en el resto de la UI.
- **SOLUCIÓN:** el PDF debe leer `cotizacion.total_con_impuestos` (ya calculado y persistido por el dominio) en vez de recalcular; o extraer un helper compartido `calcular_desglose()` usado por ambos, con el mismo `or 0` y la misma cuantización.
- **PRUEBA:** cotización con `iva_porcentaje=0` e ítems no-cero; assert `preparar_contexto()['iva_valor'] == 0` y `['total_neto'] == cotizacion.total_con_impuestos`. Sin cobertura hoy (`test_pdf_gating.py` no toca `iva_porcentaje`/`preparar_contexto`).

### Q-2 — MEDIO — Pipeline PDF duplicado sigue físicamente en disco pese a commit que dice haberlo eliminado
- **ARCHIVO:** `apps/tenant/cotizaciones/services/pdf/{__init__,generator,service}.py`
- Commit `76bf65cb` ("eliminar pipeline PDF duplicado y huerfano") los quitó de git tracking, pero `git status --porcelain` los muestra `??` (untracked) — siguen en el working tree. Confirmado inerte (cero importadores reales hoy), pero no borrado.
- **SOLUCIÓN:** eliminar físicamente el directorio, o confirmar y commitear la eliminación si nunca se hizo `git add`.

### Q-3 — MEDIO — Redondeo del PDF no coincide con el total persistido
- **ARCHIVO:** `pdf_export_service.py:67` (sin cuantizar) vs `business_service.py:253` (`_q()` con ROUND_HALF_UP). Además el subtotal se recalcula sumando en Python en vez de usar el mismo `Sum` agregado que `crud_service.get_items_subtotal`. Mismo fix que Q-1: una sola fuente de cálculo.

### Q-4 — MEDIO — Formato de moneda del PDF sin separador de miles
- **ARCHIVO:** `templates/tenant/cotizaciones/pdf/formato_profesional.html` (líneas 372-505) — usa `|floatformat:0` nativo de Django en vez del filtro ya existente `currency_cop` (`core/templatetags/currency_filters.py`), que sí usan los PDF de `empleados`. Resultado: `$15000000` en vez de `$ 15.000.000` en un documento comercial enviado a clientes. **Ver también hallazgo transversal T-4 (mismo bug, encontrado dos veces).**

### Q-5 — MEDIO-ALTO — Branding del PDF hardcodeado "SINTEL", no el logo/nombre del tenant
- **ARCHIVO:** `formato_profesional.html:310-313,511-513` — `Empresa.logo` existe (`apps/tenant/empresa/models.py:139-140`) y `empresa` ya llega al contexto del PDF, pero nunca se usa; el elemento de marca principal es el literal "SINTEL" (nombre del proveedor de la plataforma, no del tenant emisor).

### Q-6 — BAJO — Botón "Guardar Cotización" está en el header, no en el footer
- **ARCHIVO:** `editor_cotizacion.html` — botones Guardar/PDF en `offcanvas-header` sticky (líneas 8-37), sin footer, sin botón "Cancelar" (solo la X). **Verificado seguro de mover:** todo el JS (`cotizacion_editor.js`) se ata por `id`/delegación de eventos, no por posición DOM — mover el botón a un footer no rompe submit/validación/recalculo de ítems/cliente/estado.
- **NOTA:** la plantilla realmente en uso es `editor_cotizacion.html` (vía `ui_views.py`), no `offcanvas_crear_cotizacion.html`/`offcanvas_editar_cotizacion.html`, que están huérfanas desde 2026-08-27 (confirmado, no re-flaguear como bug nuevo).

### Q-7 — BAJO — No existe campo Observaciones/Condiciones en `Cotizacion`
- Gap de negocio preexistente, no regresión. Requiere modelo + migración + UI + PDF — fuera de alcance de un fix de template.

### Q-8 — BAJO — Doc `.agent` no marca las plantillas huérfanas como tales
- `AUDITORIA_FLUJO_COMPLETO.md:445-446` sigue listando `offcanvas_crear/editar_cotizacion.html` como activas.

**Ya correcto (no re-auditar):** SSoT del PDF es único *en la práctica* (solo `pdf_export_service.py` tiene importadores reales); gating PDF↔estado (mantiene BORRADOR si falla, pasa a ENVIADA solo si el PDF se genera bien); contenido del PDF completo salvo Q5/Q7; `empresa_id`/`.only()` correctos en `crud_service.py`; JS 100% id-based, seguro de reordenar.

---

## 4. Compras

### CO-1 — ALTO — Plantillas invisibles: gap de UI, no de API
- **ARCHIVO:** `apps/tenant/compras/api/viewsets.py:237` (`render_offcanvas_crear`, hardcodea `vigente_only=True`); no existe pantalla de listado de plantillas en ningún lugar (`compras_list.html:24-31` solo tiene "Nueva Plantilla"); `PlantillaOrdenCompraViewSet.list` y `API.plantillas.list` (`compras.api.js:40-44`) están correctamente implementados y `empresa_id`-scoped, pero **cero consumidores** en todo el repo.
- **ACTUAL:** cualquier plantilla con `vigente=False` es invisible en todas partes — no aparece en el dropdown ni hay otra pantalla para verla/reactivarla. Coincide exactamente con "BD tiene 3, UI muestra 0" si alguna está inactiva.
- **SOLUCIÓN:** construir pantalla de gestión de plantillas (grid + editar) consumiendo el endpoint ya funcional — no requiere cambio de backend.

### CO-2 — ALTO — "Marcar Recibida" es un botón muerto (regresión sin limpiar tras introducir Recepciones)
- **ARCHIVO:** `offcanvas_detalle_compras.html:280-283` vs `business_service.py:48-57` (`TRANSICIONES_VALIDAS['APROBADA'] = {'APROBADA','ANULADA'}`, comentario propio: "PARCIAL/RECIBIDA nunca se alcanzan por esta via manual")
- El único camino real a RECIBIDA es `RecepcionCompraBusinessService.confirmar_recepcion()`, y `RecepcionCompraViewSet` **no tiene ninguna UI** (docstring explícito: "no construir frontend nuevo en esta fase"). Órdenes aprobadas quedan sin salida en la UI — el botón siempre devuelve 400 `transicion_invalida`.
- **SOLUCIÓN:** quitar el botón muerto ya (fix rápido) y priorizar una UI mínima de Recepciones (fix medio) para que las órdenes aprobadas no queden atascadas.

### CO-3 — ALTO — `estado` es escribible en el serializer genérico de edición, bypaseando la máquina de estados
- **ARCHIVO:** `apps/tenant/compras/api/serializers.py:218` (`OrdenCompraCreateUpdateSerializer`, sin `read_only_fields` para `estado`); `services/crud_service.py:174-241` (`actualizar_orden`, `setattr` ciego sin validar `TRANSICIONES_VALIDAS`)
- **ACTUAL:** `PATCH /api/v1/compras/{uuid}/` con `{"estado":"APROBADA"}` sobre una orden BORRADOR/PENDIENTE tiene éxito y **salta** `_sincronizar_cuenta_por_pagar()` (solo se invoca desde el endpoint de transición dedicado) — una orden puede llegar a APROBADA sin generar nunca su Cuenta por Pagar. La UI actual no dispara esto (nunca envía `estado` en el payload de edición), pero la superficie de API queda abierta.
- **SOLUCIÓN:** marcar `estado` read-only en `OrdenCompraCreateUpdateSerializer`, o validar `TRANSICIONES_VALIDAS` también en `actualizar_orden_compra` si `estado` viene en el payload.

### CO-4 — ALTO — Transiciones (Aprobar/Anular) no actualizan `updated_at`, sin registro de quién las ejecutó
- **ARCHIVO:** `services/crud_service.py:259` (`orden.save(update_fields=['estado'])`) — Django solo refresca `auto_now=True` si el campo está en `update_fields`, así que `updated_at` no avanza en una transición. Tampoco existe campo actor/`*_by` en `OrdenCompra`/`SintelTenantBaseModel`, ni historial (`django-simple-history` no está integrado en esta app).
- **RIESGO:** no cumple el requisito de auditoría "quién/cuándo" del encargo, especialmente grave en Aprobar (dispara efectos contables) y Anular.
- **SOLUCIÓN mínima:** `orden.save(update_fields=['estado','updated_at'])`. **Solución completa** (campo actor o log de transición) requiere autorización explícita del usuario por ser nuevo modelo, per regla del repo.

### CO-5 — MEDIO — Select de IVA limitado a 0/5/19% vs campo de modelo sin restricción
- **ARCHIVO:** `offcanvas_editar_compras.html:152-156` vs `models.py:313-319` (`porcentaje_iva` sin `choices`). Un ítem persistido con otro % (vía API directa) se edita mostrando "0%" y, si se toca cantidad/valor_unitario, el total se recalcula (y guarda) con la tasa incorrecta.

### CO-6 — MEDIO — Estado `PARCIAL` sin badge ni acciones en el detalle
- **ARCHIVO:** `tables.py:13-19`; `offcanvas_detalle_compras.html:56-66,269-287` — ninguna de las dos cadenas `{% if/elif %}` contempla `PARCIAL` (alcanzable desde `confirmar_recepcion()` parcial); el detalle no muestra badge ni ningún botón, ni siquiera Anular.

### CO-7 — BAJO — Sin acciones a nivel de fila en la tabla (solo en el detalle)
- Ver/Editar/Eliminar están en la tabla; Aprobar/Anular solo dentro de "Ver Detalle" — un nivel de navegación extra. Decisión de producto, no bug.

### CO-8 — BAJO — Evento `plantilla-created` sin listener (código muerto inofensivo)
- **ARCHIVO:** `compras_list.js:372` — hoy inofensivo porque el dropdown de plantillas se re-fetch al abrir "Nueva Orden", pero es código huérfano engañoso.

**Ya correcto (no re-auditar):** URLs API sin mismatch de basename; `empresa_id` correcto en todos los selectors; nombres de campo consistentes end-to-end (`valor_unitario`, `porcentaje_iva`, sin camelCase drift); `valor_iva`/`subtotal`/`total` correctamente read-only en el serializer de ítems; "Eliminar" solo permite hard-delete en BORRADOR; Aprobar/Anular **sí** pasan por el endpoint de transición validado cuando se llega desde el flujo normal (el bypass de CO-3 es un camino alterno, no el camino principal); DSV anti-IDOR consistente en `_obtener_entidad_por_id_o_uuid`.

---

## 5. Ventas

### V-1 — CRÍTICO — "Ver" rompe con 500 silencioso: `humanize` nunca registrado en `INSTALLED_APPS`
- **ARCHIVO:** `apps/tenant/ventas/templates/tenant/ventas/offcanvas_detalle_venta.html:2` (`{% load humanize %}`, usa `|intcomma` 5 veces) — `django.contrib.humanize` no está en `config/settings.py` `INSTALLED_APPS` (0 resultados en grep). Es la única plantilla de todo el repo que usa `humanize`.
- **CADENA:** clic en "Ver" → `venta_list.js` hace `htmx.ajax('GET', '/api/v1/ventas/render-offcanvas/detalle/...')` → el backend resuelve la Venta correctamente pero el render lanza `TemplateSyntaxError` → 500 → HTMX no hace swap en respuestas no-2xx → **no aparece ningún mensaje**, el usuario hace clic y no pasa nada.
- **VERIFICADO:** todo lo demás en la cadena (JS, endpoint, IDs, `mostrarOffcanvasSeguro()`, contenido del serializer de detalle) es correcto — el único eslabón roto es este.
- **SOLUCIÓN recomendada** (mínimo blast-radius, consistente con que ningún otro módulo usa humanize): quitar `{% load humanize %}` y `|intcomma`, reemplazar por el patrón de formateo ya usado en el resto del repo (`currency_cop` o formateo manual). Alternativa de mayor alcance: registrar `django.contrib.humanize` globalmente.
- **PRUEBA:** test de regresión `GET /api/v1/ventas/render-offcanvas/detalle/?uuid=<uuid>` debe devolver 200 (hoy 500). No existe hoy ningún test que ejercite esta acción.

### V-2 — ALTO — "Editar Venta" es un no-op silencioso (200 sin persistir nada)
- **ARCHIVO:** `apps/tenant/ventas/api/serializers.py:168` (`VentaDetailSerializer.Meta.read_only_fields = fields`) — todos los campos son read-only, así que `PATCH/PUT` responde 200 (nada que validar) sin cambiar nada en BD. `VentaCRUDService.actualizar_venta()` (`crud_service.py:79-121`) existe, con guarda de estado BORRADOR y soporte de reemplazo de ítems, pero **nadie lo invoca** — no hay acción de edición ni en el ViewSet ni en la UI.
- **SOLUCIÓN:** implementar el flujo de edición reutilizando `actualizar_venta()` (mismo patrón ya usado para `ResolucionFacturacion`), o si "Editar" está deliberadamente fuera de alcance, bloquear `update`/`partial_update` con 405 explícito en vez de un 200 engañoso.

### V-3 — MEDIO — Doc `.agent/ARQUITECTURA_VENTAS.md` desactualizado
- Describe un botón "Facturar DIAN" y Tabulator que ya no existen (removidos tras VENTAS-COMPRAS-FACTURAS-01 y Fase 5-BIS). Riesgo: alguien podría reactivar el botón de emisión fiscal confiando en el doc.

**Confirmación explícita del bloqueo fiscal (restricción del encargo):** verificado intacto y correcto. `EMISION_FISCAL_VENTA_AUTORIZADA = False` (constante de código); `procesar_y_facturar_venta()` rechaza con 403 antes de escribir nada; botones "Guardar y Facturar DIAN"/"Facturar DIAN" removidos de ambos templates con comentario explícito; `vincular_factura_existente()` solo asocia una Factura ya persistida, nunca emite una nueva; test dedicado `test_bloqueo_emision_fiscal.py` existente. **No se encontró ningún elemento de UI que reexponga la emisión fiscal — reportado como control positivo, no tocar.**

**Ya correcto (no re-auditar):** flujo Create completo (offcanvas → editor → API → ViewSet → business service con DSV); List (django-tables2/HTMX, Fase 5-BIS, `empresa_id` correcto); serializer de detalle sí incluye todos los campos pedidos (el problema es que el render nunca completa, no que falten datos); routing DRF sin colisión; `mostrarOffcanvasSeguro()` correcto; Anular correctamente cableado.

---

## 6. Proyectos

### P-1 — CRÍTICO — `avanzar-fase` no persiste `fase_actual` en BD (regresión de una "optimización")
- **ARCHIVO:** `apps/tenant/proyectos/services/business_service.py:313-323` (`cambiar_fase_proyecto`, muta solo en memoria) + `:79-103` (`calcular_indicadores_financieros`, único `.save()` posterior, con `update_fields=['costo_mano_obra_real','costo_materiales_real','utilidad_estimada','margen_rentabilidad']`)
- **CAUSA RAÍZ:** `Model.save(update_fields=[...])` genera un `UPDATE` que solo toca esas columnas — `fase_actual` (y los campos de responsable asignados por `asignar_snapshot_responsable()`, también en memoria) se pierden silenciosamente. La respuesta HTTP se ve correcta porque serializa el objeto Python ya mutado, no lo que quedó en BD.
- **EVIDENCIA DE LA REGRESIÓN:** el propio doc `.agent/AUDITORIA_FLUJO_COMPLETO.md:194-195` registra el commit causante: *"FIX-3: Doble save en avanzar_fase — Eliminado save_proyecto() redundante... -50% writes"*. Ese "redundante" era el único save que persistía la fase.
- **ACTUAL:** `POST .../avanzar-fase/` devuelve 200 con la fase nueva, pero `proyecto.refresh_from_db()` (o cualquier otra sesión, o el siguiente refresh HTMX de la grilla) muestra la fase vieja.
- **SOLUCIÓN:** incluir `'fase_actual'` y los campos de responsable en el `update_fields` de `calcular_indicadores_financieros()`, o (más simple y más a prueba de futuro) restaurar un `save_proyecto(proyecto)` completo inmediatamente después de `cambiar_fase_proyecto()`, antes de/junto con el recálculo financiero.
- **PRUEBA:** crear proyecto BORRADOR, `POST avanzar-fase` a INICIO, `refresh_from_db()` (no reusar el objeto de la request) → debe ser INICIO. Hoy no existe ningún test sobre `avanzar-fase`/`avanzar_fase`.

### P-2 — MEDIO — Doc drift que documenta el bug sin señalarlo
- `AUDITORIA_FLUJO_COMPLETO.md` describe con precisión el flujo roto sin marcarlo como problema — debe actualizarse junto con el fix para no volver a "optimizar" este guardado.

**Confirmado explícitamente lo que el encargo pedía verificar:**
- **Sin doble fuente de verdad en frontend:** `proyectos_editor.js:233-283` lee el estado nuevo desde la respuesta del backend (no optimista), sin variable JS independiente.
- **Sin `location.reload()`** en ningún flujo de proyectos (grep confirmado 0 resultados reales).
- **Mapeo de badges completo** (`_FASE_MAP`, `_ESTADO_MAP` cubren las 5 fases y todos los estados de tarea reales; fallback muestra el valor crudo, nunca cae a "Borrador" por defecto).
- **La ruta genérica `PATCH`/`PUT` sí persiste `fase_actual` correctamente** (usa `save_proyecto(proyecto)` sin `update_fields`) — solo la acción dedicada `avanzar-fase` está rota.
- Otras transiciones de estado del módulo (tareas diarias, tareas cortas) sí persisten correctamente — no es un patrón sistémico, es puntual a `avanzar-fase`.

---

## 7. Bancos

### B-1 — ALTO — Resolución de `empresa_id` en la vista de listado es más frágil que en el path de creación
- **ARCHIVO:** `apps/tenant/bancos/views.py:25-33` (`_resolver_empresa_id`, solo atrapa `DRFValidationError`) vs `apps/tenant/api/mixins.py:142-160` (`BaseServiceMixin._get_empresa()`, atrapa cualquier excepción + fallback a `Empresa.objects.only('id').first()`)
- **ACTUAL:** si la resolución de `empresa_id` falla por cualquier motivo distinto de `ValidationError` en el GET que repuebla el panel de extractos, la tabla server-rendered (la que realmente maneja la UI, Fase 5-BIS) cae silenciosamente a queryset vacío ("No hay extractos bancarios registrados") sin ningún error visible — aunque la fila exista en BD. El path de creación (API) sí tiene fallback y no falla en el mismo escenario.
- **NOTA:** la cadena de subida→persistencia→refresh HTMX→render fue trazada end-to-end y está correctamente cableada — este es el único punto de fragilidad real encontrado que podría producir el síntoma reportado ("subí el extracto y no aparece").
- **SOLUCIÓN:** que `_resolver_empresa_id()` en `views.py` use el mismo fallback amplio que `BaseServiceMixin`, o al menos muestre un estado de error explícito en vez de una tabla vacía silenciosa.

### B-2 — MEDIO — Botón "Importar y Procesar" no procesa
- **ARCHIVO:** `offcanvas_crear_extracto.html:92-95` — el label promete procesamiento inmediato, pero `extracto_editor.js:_guardar()` solo hace `POST` de creación; `procesar()` (que genera las `TransaccionBancaria`) requiere un clic separado y posterior. El extracto sí aparece en la lista (con badge "Pendiente"), pero un usuario que confíe en el label puede pensar que la subida falló al no ver transacciones de inmediato.
- **SOLUCIÓN:** renombrar el botón a "Importar", o encadenar automáticamente `procesar()` tras el create exitoso.

### B-3 — MEDIO — No existe ningún mecanismo de causación (gap de funcionalidad, no violación)
- **ARCHIVO:** confirmado por grep — cero referencias a `AsientoContable`/`MovimientoContable`/`causa` en todo `apps/tenant/bancos`. `bancos` tampoco está registrado en `APP_ORIGEN_PREFIJOS` (`apps/tenant/contabilidad/services/selectors.py:98-113`), a diferencia de `facturas`/`clientes`.
- **IMPORTANTE — verificación positiva de ADR-001:** `conciliar_transaccion()` solo vincula la transacción a Factura/Proveedor/Cliente existentes y dispara las APIs propias de `facturas`/`clientes` (Pull Model) — **nunca** instancia tablas contables directamente. **No hay violación CRÍTICA de ADR-001 en Bancos.**
- **GAP real:** un movimiento bancario sin documento asociado (comisiones, GMF/4x1000, intereses) no tiene ningún camino hacia el libro contable.
- **SOLUCIÓN:** decisión de producto — documentar explícitamente como fuera de alcance, o diseñar un extractor real registrado en Contabilidad (mismo patrón que `facturas`/`clientes`).

### B-4 — MEDIO — `CuentaBancaria` no tiene mecanismo de desactivación, solo hard-delete
- **ARCHIVO:** `models.py:13-29` (sin campo `activo`, a diferencia de `Proveedor.activo`/`Cliente.activo` en el mismo repo) — el único camino de "eliminar" es `DELETE` físico, bloqueado solo si tiene extractos asociados. No hay forma de ocultar una cuenta con historial sin borrarla.

### B-5 — MEDIO — Sin cobertura de test sobre la vista de listado real (django-tables2)
- Toda la cobertura existente golpea los endpoints DRF/servicios, no `ExtractoBancarioTableView`/`CuentaBancariaTableView` — el path que realmente renderiza la UI (y donde vive B-1) no tiene ningún test.

### B-6 — BAJO — Doc `.agent` describe Tabulator, el código ya migró a django-tables2+HTMX
- `AUDITORIA_FLUJO_COMPLETO.md` (fechado 2026-06-04) desactualizado desde Fase 5-BIS.

**Ya correcto (no re-auditar):** CRUD completo de `CuentaBancaria` (salvo desactivación, B-4); cadena subir→persistir→refrescar→listar extracto correctamente cableada en todos sus eslabones; ETL "Procesar" idempotente (`select_for_update`, delete+bulk_create); conciliación con validación de fecha pago-antes-que-documento; **ADR-001 respetado, sin violación crítica**; `empresa_id` correcto en todo selector/CRUD/render, incluso con doble-chequeo defensivo en algunos puntos; autocomplete de búsqueda correctamente scoped.

---

## 8. Moneda (COP) + Infraestructura frontend transversal

### T-1 — MEDIO — SSoT de formateo de moneda existe pero tiene cero consumidores
- **ARCHIVO:** `apps/tenant/core/static/core/js/lib/dom-utils.js:188-229` (`DOMUtils.formatCurrency`) — bien construido (guardas null/undefined/NaN, `Intl.NumberFormat('es-CO', {style:'currency', currency:'COP'})`), pero grep confirma 0 consumidores reales en todo el repo.

### T-2 — MEDIO — Al menos 15 reimplementaciones locales de formateo de moneda, con decimales inconsistentes
- Lista completa con archivo:línea en el reporte del agente (compras, contabilidad×4, cotizaciones, facturas×5, inventario, empleados, proveedores, proyectos, gastos). El locale/moneda es consistente (`es-CO`/COP en todas), pero los decimales varían entre 0 y 2 según el archivo — el mismo monto se ve distinto entre módulos.

### T-3 — BAJO — Backend también duplica su propio formateador
- `apps/tenant/facturas/api/serializers.py:193-197` (`get_total_formateado`) reimplementa a mano lo que ya hace `currency_cop` (`core/templatetags/currency_filters.py`) — coinciden por casualidad, no por reuso.

### T-4 — ALTO — PDF de cotizaciones sin separador de miles (duplicado de Q-4, mismo bug, mismo fix)
- Confirmado independientemente por ambos agentes. Ver Q-4. `empleados` ya usa el filtro correcto (`currency_cop`) en sus PDFs — el patrón de fix ya existe en el repo.

### T-5 — ALTO — Riesgo real de "NaN" visible en el Estado de Resultados (reporte financiero) y riesgo latente en compras
- **ARCHIVO:** `apps/tenant/contabilidad/static/contabilidad/js/reporte/reporte.ui.js:176-241` (`formatMoney`, sin guard) — si el backend omite una clave del JSON (no solo la manda en 0), `Intl.NumberFormat().format(undefined)` imprime literalmente `"NaN"` en las tarjetas de Ingresos/Costos/Utilidad de un reporte usado para decisiones de negocio.
- **ARCHIVO 2:** `apps/tenant/compras/static/compras/js/features/compras_editor.js:17-22` (`formatCurrency`, mismo patrón sin guard) — hoy no se manifiesta porque los únicos call-sites ya filtran con `parseFloat(...)||0`, pero es una trampa abierta para el próximo consumidor.

### T-6 — BAJO — Llamada a método inexistente `DOMUtils.fmtMoney` (cae a fallback silenciosamente, sin impacto funcional)
- `apps/tenant/contabilidad/static/contabilidad/js/asiento/features/asiento_cargar_desde_docs.js:23-34` — señal de que la consolidación de T-1 nunca se completó ni se comunicó.

### T-7 — BAJO — `window.confirm()` nativo bypaseando `UIManager.confirm`
- `apps/tenant/inventario/static/inventario/js/features/inventario_list.js:388`.

### T-8 — BAJO — `location.reload()` real (no en comentario) en el selector de sede
- `apps/tenant/core/static/core/js/common/sede_selector.js:33`. (Nota metodológica: `empleados/periodo_detail.js` y `devengo_editor.js` fueron descartados como falsos positivos tras verificar que sus matches de grep eran comentarios que prohíben la práctica, no llamadas reales.)

### T-9 — MEDIO — ~70 archivos con URLs de API hardcodeadas fuera del `*.api.js` de su app
- Peores ofensores: `inventario` (9 archivos), `contabilidad` (10), `empleados` (8, aunque con patrón defensivo parcial — intenta el SSoT primero, cae a literal si falta). Riesgo: cambiar un path de API requiere tocar N archivos en vez de 1.

### T-10 — Informativo — El ERP es COP-only en la práctica; `moneda` es un artefacto de cumplimiento DIAN, no multi-currency real
- Verificado a fondo: cero ocurrencias de `tasa_cambio`/`exchange_rate`/`TRM` en ningún modelo; todos los tests instancian `moneda="COP"` explícito; el campo existe porque el estándar UBL 2.1 de la DIAN exige `DocumentCurrencyCode` en el XML. **Documentar para que fases de corrección no asuman que "solo falta cablear" un multi-currency que no existe, ni quiten el campo (es requerido por DIAN).**

### T-11 — Informativo — `config/settings.py` no define `USE_THOUSAND_SEPARATOR`
- Podría ser una solución sistémica alternativa a Q-4/T-4 (afectaría TODOS los usos de `floatformat`/`intcomma` del árbol, no solo cotizaciones) — requiere su propia auditoría de alcance antes de activarse, no decidir en esta fase.

### T-13 — BAJO — Comentarios Django `{# ... #}` multilínea se renderizan como texto literal (encontrado durante Fase 2, no en la auditoría original)
- **CAUSA:** Django's `{# comentario #}` (forma corta) **no admite saltos de línea entre `{#` y `#}`** — a diferencia de `{% comment %}...{% endcomment %}`. Si un comentario corto se escribe en varias líneas, Django no lo reconoce como tag de comentario y lo renderiza como texto plano, sin ningún error ni warning.
- **ARCHIVOS con el patrón (confirmado, pre-existentes, NO tocados en esta misión):** `apps/tenant/clientes/templates/tenant/clientes/offcanvas_abono_cartera.html:73`, `apps/tenant/cotizaciones/templates/tenant/cotizaciones/offcanvas_crear_servicio.html`, `apps/tenant/cotizaciones/templates/tenant/cotizaciones/offcanvas_crear_producto.html` — cada uno filtra un comentario de desarrollador como texto visible en el HTML renderizado (no es un bug de datos/negocio, pero sí ensucia el DOM real que ve el usuario/inspecciona el navegador).
- **ENCONTRADO EN VIVO:** al implementar V-2/CO-2 en Fase 2, se introdujo el mismo patrón en `offcanvas_crear_venta.html`, `offcanvas_detalle_venta.html` y `offcanvas_detalle_compras.html` — detectado porque el test de regresión de V-2 (`test_render_offcanvas_editar_precarga_datos`) hace `assertNotIn(b"{#", resp.content)`. **Corregido en el mismo fix** (reemplazado por `{% comment %}...{% endcomment %}` en los 3 archivos tocados por esta sesión).
- **SOLUCIÓN para los 3 pre-existentes:** mismo reemplazo (`{% comment %}...{% endcomment %}`), fuera de alcance de esta fase — no se tocó código no relacionado a los 8 ALTO priorizados.
- **PRUEBA:** cualquier test que haga `assertNotIn(b"{#", response.content)` sobre esas 3 vistas lo detectaría hoy.
- **CLASIFICACIÓN:** BUG (pre-existente, nuevo hallazgo) / no re-flaguear los 3 archivos ya corregidos de Ventas/Compras.

### T-12 — Informativo — Estado real de Tabulator vs django-tables2 por app (para no migrar/re-migrar por error)
| App | Patrón actual |
|---|---|
| compras, ventas, bancos, empleados | django-tables2 + HTMX (ya migradas) |
| clientes, cotizaciones, proyectos | Tabulator (pendiente, deliberado) |

**Inventario de infraestructura ya existente para reutilizar (no crear nueva):**
- `window.Sintel.Core.Http` — cliente HTTP único (`core-http.js:175-191`), contrato `{ok, status, data}`, `.upload()` obligatorio para FormData.
- `UIManager` — `.handleError()`, `.confirm()` (SweetAlert2), `.handleOffcanvas()`, `.resetForm()` (`ui-manager.js:487-501`).
- `SintelFeedback` — toasts (`.success/.error/.warning/.info`).
- `mostrarOffcanvasSeguro()` — SSoT de apertura/cierre de offcanvas, consolidó 16+ reimplementaciones previas.
- `DOMUtils.formatCurrency` — candidato natural a SSoT de moneda frontend (T-1).
- `currency_cop`/`format_cop` — filtros Django backend, usados hoy en PDFs de empleados/offcanvas de cotizaciones/bancos, no en el PDF de cotizaciones (Q-4/T-4) ni en el serializer de facturas (T-3).
- `routes.js` — descubrimiento de rutas backend, único literal de API legítimo del árbol `core/`.

---

## Hallazgos ya documentados como deuda conocida (no re-abrir como "nuevos" en fases futuras)

- E-1, E-2 (empleados): DEUDA-31, `.agent/AUDITORIA_FLUJO_EMPLEADOS.md`, abierto desde 2026-09-11.
- E-3 (empleados, "Preliquidar" 30 días): DEUDA-25-CERRADO, decisión consciente documentada.
- C-4 (clientes/bancos, divergencia post-desconciliación): CLI-05/DEUDA-C03.
- Q-2 (cotizaciones, PDF duplicado): reabre parcialmente un item que el commit `76bf65cb` creyó cerrado — archivos siguen en disco.

## Falsos positivos descartados durante la auditoría (no re-investigar)

- `save_proyecto()` como función aislada (proyectos) — el bug está en el caller, no en el wrapper.
- `location.reload()` en `empleados/periodo_detail.js` y `devengo_editor.js` — son comentarios que prohíben la práctica, no código real.
- Campo `moneda` como indicio de multi-currency real (T-10) — descartado tras verificación exhaustiva.
- Bloqueo de emisión fiscal en Ventas — verificado intacto, reportado como control positivo.
- Bancos/ADR-001 — verificado sin violación crítica (conciliación nunca escribe tablas contables directamente).

---

## Próximo paso

Este documento cierra la Fase 0. Por regla del encargo ("no corregir todo al mismo tiempo"), toca decidir con el usuario el orden de las fases de corrección (Fase 1 en adelante) antes de tocar código — priorización sugerida por blast-radius:

1. Los 5 CRÍTICO (C-1, C-2, Q-1, V-1, P-1) — todos son correcciones acotadas (1-2 archivos cada uno), de alto impacto, bajo riesgo de romper otras cosas.
2. Los 8 ALTO, agrupados por app para minimizar recorridas de regresión.
3. MEDIO/BAJO, agrupados por fase temática (moneda, infraestructura frontend) según lo define el propio encargo en sus Fases 3-8.

Cada fase debe seguir el loop obligatorio del encargo (INSPECT → REPRODUCE → ROOT CAUSE → PATCH → UNIT TEST → INTEGRATION TEST → UI TEST → RE-READ → RETEST) y cerrar con entradas en `docs/remediation/RELEASE_GATE_20260912.md`.
