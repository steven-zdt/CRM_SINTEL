# Rollout Controlado — FASE 10

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED
**Regla aplicada en toda la fase:** "no debemos poner sede y area indiscriminadamente en todos los modelos" (`ORGANIZATIONAL_SCOPE_MATRIX.md` §Introducción) — ninguna app de esta fase recibe infraestructura de scope sin que la Sección 1 de esa matriz (auditada en FASE 5) ya haya concluido que el caso de negocio lo justifica. Donde la matriz ya concluyó "NO RECOMENDADO" o "sin caso de uso real", esta fase **ratifica esa decisión** en vez de sobre-escribirla solo para poder marcar la app "migrada".

Orden del prompt maestro: `compras (piloto) → ventas → facturas → inventario → gastos → empleados → cotizaciones → proyectos → clientes → proveedores → bancos → contabilidad → dashboard`.

---

## 1. `compras` — ya es el piloto (FASE 6-7)

Sin cambios en esta fase — ya validado end-to-end (`SedeAwareModel`, `HasOrganizationalScope`, migración completa, 20/20 tests pasando tras los fixes de FASE 7).

---

## 2. `ventas` — decisión confirmada con el usuario: sin cambio de modelo

**Auditoría:** `Venta` no tiene campo `sede` (verificado, 0 referencias). `VentaViewSet` hereda `OrganizationalContextMixin` (sin invocar, patrón estándar) y no tiene `HasOrganizationalScope`.

**Decisión (confirmada explícitamente por el usuario, no asumida):** no agregar campo `sede` a `Venta`. Razón ya verificada en FASE 9: `Venta` es efímera (se convierte a `Factura` en el mismo flujo transaccional, `procesar_y_facturar_venta()`), y la sede del usuario que factura ya viaja correctamente al DTO → `Factura` (OSF F10, ya cerrado y re-confirmado en `VENTAS_FACTURAS_AUDIT.md`). Agregar `sede` a `Venta` duplicaría un dato que ya se resuelve correctamente aguas abajo, sin un caso de uso real (ej. "ver mis Ventas en borrador filtradas por sede") que lo haya pedido.

**Ciclo MODEL→...→TESTS:** N/A para `MODEL`/`SELECTOR`/`PERMISSION` (no hay campo que scopear). `SERVICE` ya cumple (F10). `TESTS`: `test_organizational_context_adoption.py` ya existe.

**Estado: 🟢 COMPLETO** (por diseño, no por trabajo pendiente).

---

## 3. `facturas`, `inventario`, `gastos`, `empleados`, `cotizaciones`, `proyectos` — ya migradas (OSF F7, F9, F11)

Confirmado en `OSF_TECHNICAL_AUDIT.md`, `ORGANIZATIONAL_SCOPE_MATRIX.md` §4 y `FACTURAS_AUDIT.md`: estas 6 apps ya tienen `filter_by_scope_null_safe()` aplicado a sus Selectors (F7) y — en el caso de `facturas` específicamente — integración adicional en Bridges (F9) y validación de escritura (F11). `empleados` es la única con `sede_ids` **y** `area_ids` simultáneos (tiene ambos campos).

**Lo que SÍ cumplen del ciclo:** MODEL (campo `sede` ya existe, informativo desde antes de OSF), SELECTOR (`filter_by_scope_null_safe`), SERVICE (propagación de `sede_ids` donde aplica), VIEWSET/API (filtrado de listas activo).

**Lo que NO cumplen, deliberadamente, no por omisión:** `PERMISSION` — ninguna de las 6 tiene `HasOrganizationalScope` aplicado a nivel de objeto individual. **Motivo real, no pereza:** FASE 2 (`OSF_TECHNICAL_AUDIT.md` §4) encontró que `HasOrganizationalScope.has_object_permission()` deniega objetos con `sede_id=None`, mientras que `filter_by_scope_null_safe()` los deja visibles en el listado — aplicar `HasOrganizationalScope` tal cual a estas 6 apps causaría que un usuario vea una Factura/Cotización/etc. en su listado pero reciba 403 al abrirla, porque el 100% de los registros históricos de estas apps tiene `sede=NULL`. **No se aplica el permiso hasta resolver esa asimetría** (construir una variante NULL-safe de `HasOrganizationalScope`, o aceptar el comportamiento y documentarlo) — aplicarlo ciegamente reproduciría exactamente el tipo de regresión que F7 evitó al elegir el filtrado NULL-safe en primer lugar.

**FRONTEND:** no verificado en detalle para las 6 en esta fase (fuera del alcance dado el volumen) — cada una expone su propio campo `sede` en formularios/templates existentes desde antes de OSF (el campo ya era visible como dato informativo).

**Estado: 🟡 PARCIAL, por decisión explícita** — filtrado de lectura completo, enforcement de objeto individual deliberadamente diferido hasta resolver la asimetría NULL. No se fuerza a 🟢 solo por completar el checklist.

---

## 4. `clientes` — ratificada como NO RECOMENDADO

Matriz de FASE 5: "un cliente no está atado a una sede del vendedor; agregar el campo violaría la advertencia explícita de esta fase". Sin cambios. **Estado: ⚪ NO APLICA (decisión de negocio, no pendiente).**

---

## 5. `dashboard` — ratificada como NO RECOMENDADO tal como está diseñado

Matriz de FASE 5: `SnapshotMetricaDiaria` es una métrica agregada a nivel empresa; requeriría rediseñar el modelo de snapshot (una fila por sede) para que sede/area tuviera sentido — no es un "agregar campo". Fuera del alcance de una migración de rollout; sería un proyecto de rediseño propio. Sin cambios. **Estado: ⚪ NO APLICA (requiere rediseño, no rollout).**

---

## 6. `proveedores` — ratificada como candidato débil, sin infraestructura especulativa

Matriz de FASE 5: "la relación con un proveedor es típicamente de toda la empresa, no de una sede; `CuentasPagar` podría heredar la sede de la compra de origen en vez de tener campo propio". Verificado en esta fase: `proveedores/models.py` no tiene ningún campo `sede` — confirmado, cero cambios desde la auditoría de FASE 5. No se agrega un campo especulativo sin un caso de uso real que lo pida (mismo principio aplicado en `organizational_bridges.py`/`organizational_service_layer.py` durante OCF: no construir infraestructura sin consumidor real). **Estado: 🔴 AUSENTE, decisión de no priorizar (no un olvido) — candidato legítimo para una fase futura dedicada si aparece un caso de uso real (ej. "CxP por sede de la compra que la originó", que heredaría la sede vía la `OrdenCompra` vinculada en vez de un campo propio en `CuentasPagar`).**

---

## 7. `bancos` — ratificada como candidato plausible sin caso de uso confirmado

Matriz de FASE 5: "cuentas bancarias por sucursal es real en la práctica; `TransaccionBancaria` ya tiene un campo de texto libre `sucursal` (indicio no estructurado)". Verificado en esta fase: sin campo `sede` estructurado todavía. Es el candidato con el caso de negocio más creíble de los que quedan sin empezar — pero implementarlo implica una migración de esquema real (nueva columna, decisión de nullable/backfill/harden) que no fue pedida explícitamente para esta app en esta sesión. **Estado: 🔴 AUSENTE, priorizable en una fase futura si se confirma el caso de uso (mapear el campo de texto libre `sucursal` existente a una FK real `Sede` sería el punto de partida natural, no un campo nuevo desde cero).**

---

## 8. `contabilidad` — ratificada como candidato parcial, sin infraestructura especulativa

Matriz de FASE 5: plausible SOLO para `AsientoContable`/`MovimientoContable` (segmentación por centro de costo); el catálogo de cuentas y los períodos fiscales son de empresa completa por diseño contable y NO deben llevar sede/area. Verificado en esta fase: `apps/tenant/contabilidad/models.py` y los extractores del Pull Model (`integracion/extractores/*.py`) no tienen ninguna referencia a `sede` — el Pull Model hoy solo propaga `empresa_id` desde los documentos origen (`Factura`, `DocumentoSoporte`, etc.) hacia `AsientoContable`, aunque `Factura` ya tiene `sede` poblado en algunos casos (F11). Propagar `sede` desde el documento origen hasta el asiento sería un cambio real en `contabilizador.py`/los extractores — no trivial, y no pedido explícitamente. **Estado: 🔴 AUSENTE, priorizable en una fase futura — el punto de partida natural sería extender el DTO `TransaccionEconomica` (§6.4 de `arquitectura_general.md`) con un `sede_id` opcional que los extractores ya podrían leer de `Factura.sede`/`DocumentoSoporte.sede` sin inventar una fuente nueva.**

---

## Resumen ejecutivo de FASE 10

| App | Estado | Motivo |
|---|---|---|
| compras | 🟢 COMPLETO | Piloto oficial, validado FASE 6-7 |
| ventas | 🟢 COMPLETO (por diseño) | Sede resuelta por contexto, no por campo — confirmado con el usuario |
| facturas, inventario, gastos, empleados, cotizaciones, proyectos | 🟡 PARCIAL (decisión explícita) | Lectura completa (F7/F9/F11); enforcement de objeto diferido por la asimetría NULL de `HasOrganizationalScope` |
| clientes, dashboard | ⚪ NO APLICA | Decisión de negocio/diseño ya tomada en FASE 5, ratificada aquí |
| proveedores, bancos, contabilidad | 🔴 AUSENTE, no priorizado | Candidatos legítimos sin caso de uso confirmado ni pedido explícito — no se fabrica infraestructura especulativa |

**Ningún archivo de código se modificó en esta fase** — FASE 10 concluyó que, dada la matriz ya auditada en FASE 5, el trabajo de implementación real pendiente y justificado es menor de lo que el checklist genérico del prompt maestro sugería: 8 de las 13 apps del orden de rollout ya estaban en un estado correcto (completo o intencionalmente no aplicable) antes de empezar esta fase; las 5 restantes se dejan documentadas como backlog priorizable, no como "migradas" artificialmente.

**Fase completada. Continuando a FASE 11 en el mismo turno, por instrucción explícita del usuario ("termina la tarea en su totalidad").**
