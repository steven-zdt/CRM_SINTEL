# Cross-App Findings — SINTEL ERP

**Fecha:** 2026-08-26 | **Fases:** REL-03 (cardinalidades) + REL-06 (relaciones faltantes) + REL-07 (relaciones incorrectas)

Este es el documento accionable de la auditoría. Todo lo listado aquí tiene evidencia real (archivo:línea) citada en los 4 reportes de origen. Nada fue inventado; donde no había evidencia suficiente, el sub-agente correspondiente lo marcó explícitamente como "requiere revisión manual" y se preserva esa marca aquí.

---

## Resumen ejecutivo — 4 hallazgos CRITICAL

| # | Hallazgo | Ciclo | Impacto |
|---|---|---|---|
| 1 | `CuentasPagar` (nacida de Compras) no tiene ningún bridge a Bancos | Compra | Toda CxP generada desde una Orden de Compra aprobada (incluida la del bug reportado hoy) solo puede marcarse pagada manualmente — la conciliación bancaria nunca la toca |
| 2 | `DocumentoSoporte` (Gasto) no tiene ningún camino hacia Pago | Gasto | Un gasto puede crearse, generar retenciones y contabilizarse, pero el sistema no puede registrar ni consultar si fue pagado |
| 3 | El costo de venta (Inventario→Contabilidad) no llega al libro mayor por el pipeline automático real | Venta | `ExtractorInventario` existe y está probado, pero el Celery task que orquesta la integración completa no lo incluye — desbalance real entre ingreso y costo contabilizados |
| 4 | Bug funcional confirmado: `RetencionesService.listar_retenciones_por_documento` se llama sin `empresa_id` en el offcanvas de edición de Gasto | Gasto | `TypeError` silenciado por un `except Exception: pass` — el offcanvas nunca muestra los porcentajes de retención reales, sin log ni rastro visible |

Los 4 quedan detallados abajo con su clasificación completa.

---

## REL-06 — Relaciones faltantes (clasificadas)

### CRITICAL

- **`CuentasPagar` (Proveedores) sin bridge a `Bancos`.** `TransaccionBancaria` solo tiene `factura_uuid`/`proveedor_uuid`/`cliente_uuid` (`bancos/models.py:62-77`). `BancosCRUDService.conciliar_transaccion()` solo dispara recálculo de estado si `factura_uuid` está presente. Grep exhaustivo: cero referencias a `CuentasPagar` en toda la app `bancos`. — *Ciclo Compra*

- **`DocumentoSoporte` sin ningún camino hacia Pago.** Confirmado: `CuentasPagar` no tiene campo `documento_soporte_uuid`; `registrar_cuenta_pagar` nunca se invoca desde `gastos`; `TransaccionBancaria` no tiene `documento_soporte_uuid`; `DocumentoSoporte` no tiene campo local `pagado`/`estado_pago`/`fecha_pago`. — *Ciclo Gasto*

- **Inventario→Contabilidad no conectado al pipeline automático real.** `ExtractorInventario` registrado en `extractores/__init__.py` y probado (`test_f22_extractor_inventario_*.py`), pero `ContabilidadBusinessService.ejecutar_integracion_completa()` — el único método que invoca el Celery task periódico — no lo incluye en su lista (`contabilidad/services/business_service.py:1043-1051`). El docstring del propio Celery task promete "Sincroniza Facturas, Gastos e Inventario" (`contabilidad/tasks.py:20-21`). — *Ciclo Venta*

- **`PeriodoNomina` (PAGADO) sin bridge a Bancos.** `marcar_pagado()` es un registro manual — ya documentado como tal en 3 lugares del propio código (modelo, servicio, doc de arquitectura). No es un hallazgo oculto, pero se lista aquí para que quede en el mismo inventario que los otros 3 gaps de "→ Pago". — *Ciclo Nómina*

### IMPORTANT

- **Cotización→Venta sin automatización de código.** Ningún método convierte una `Cotizacion` (ACEPTADA) en `Venta`. El único puente es `Factura.cotizacion_uuid`, editable a mano, validado solo de existencia (no de coherencia de montos/cliente/ítems). — *Venta*

- **`Cartera` (CxC) no se alimenta automáticamente desde Facturas/Ventas.** `registrar_cartera()` existe y está documentado como "idempotent registration... from invoice synchronization", pero el único invocador real es el endpoint manual — cero llamadas desde `facturas/` o `ventas/`. — *Venta*

- **Dos catálogos de Producto/Servicio no unificados** (`cotizaciones.Producto/Servicio` vs. `inventario.Producto/Servicio`) — sin mapeo ni FK entre ambos; un ítem cotizado no se traza automáticamente a inventario. — *Venta*

- **`Factura.proveedor_uuid` nulo rompe la agregación por proveedor.** `ProveedorSelector.get_cuentas_pagar_resumen()` filtra por `proveedor_uuid`, mientras que `qs_list_facturas_compra()`/`qs_list_unificado()` no lo requieren — una Factura con `proveedor_uuid IS NULL` aparece en la grilla general pero desaparece del resumen consolidado por proveedor. Inconsistencia entre dos consumidores del mismo dato. — *Compra*

- **`OrdenCompraCRUDService.cambiar_estado()` no valida la transición de estado**, solo que el valor sea un choice válido. Nada impide `RECIBIDA`/`ANULADA` → `APROBADA` de nuevo (re-disparando la sincronización de CxP, protegido solo por `get_or_create`, no por una regla de máquina de estados). — *Compra*

- **`DocumentoSoporte.total_retefuente/reteica/reteiva` consultan `contabilidad.Retencion` directamente**, sin pasar por `RetencionesService` — a diferencia de `Factura`, que sí delega en el servicio (patrón `ARQ-C1` documentado). Inconsistencia arquitectónica dentro del mismo ciclo. — *Gasto/Compra*

- **Sin reversión automática de Contabilidad al anular un `DocumentoSoporte` ya contabilizado.** Riesgo de asiento contable "fantasma" que sigue afectando el libro mayor. — *Gasto*

- **Reglas contables faltantes para `categoria_contable=None`** quedan atrapadas como error genérico — el documento queda indefinidamente `PENDIENTE` sin alerta proactiva al usuario. — *Gasto*

- **Devengo sin máquina de estados propia de aprobación.** Un `Devengo` creado individualmente (fuera de `PeriodoNomina`, patrón legado aún soportado con `periodo=null`) nunca pasa por ningún flujo de aprobación — dos caminos de creación coexisten con distinto nivel de control. — *Nómina*

### OPTIONAL

- `Venta.proyecto` es de solo escritura — ningún código en `proyectos` lee `proyecto.ventas`; los indicadores financieros de Proyecto no incorporan ingresos reales de Venta. — *Venta*
- `MovimientoInventario.sede` opcional — afecta reportes por sede, no la integridad transaccional. — *Compra*
- `DocumentoSoporte.movimiento_inventario_uuid` sin propagación al asiento contable — posible duplicación evitada intencionalmente, sin documentación que lo confirme. — *Gasto*
- Gap teórico: `aprobar_periodo()`/`marcar_pagado()` no repiten la validación de "existen devengos activos" que sí hace `enviar_a_revision()` — secuencia poco probable, sin evidencia de que haya ocurrido. — *Nómina*

### DERIVED

- `AsientoContable`/`Retencion.documento_origen_*` — correctamente derivados/polimórficos con `UniqueConstraint` como defensa. Sin hallazgos.
- PILA/seguridad social — sin modelo ni integración, explícitamente fuera de alcance (decisión consciente, no accidental).

---

## REL-07 — Relaciones incorrectas o mal acopladas

- **`DocumentoSoporte.proveedor` con `on_delete=CASCADE`** — borrar un Proveedor borra en cascada todo su historial fiscal de `DocumentoSoporte`, incluidos los ya contabilizados (dejando `AsientoContable.documento_origen_id` huérfano). Contrasta con `OrdenCompra.proveedor` (`PROTECT`) — inconsistencia de criterio dentro del mismo ciclo de Compra/Gasto. Documentado en el propio `help_text` del campo, pero merece revisión de negocio: ¿deberían los documentos fiscales legales ser `PROTECT`?

- **Bug funcional confirmado — `gastos/api/viewsets.py:223-227` llama `RetencionesService.listar_retenciones_por_documento` sin el parámetro obligatorio `empresa_id`.** La firma real exige `empresa_id` sin default. Lanza `TypeError` en cada ejecución, silenciado por `except Exception: pass` sin logging. Efecto: `retenciones_fracciones` siempre queda `{}`, el offcanvas de edición de Gasto nunca muestra los porcentajes de retención reales. Defecto real y accionable, no hipótesis.

- **Acoplamiento directo ORM (no Service Layer) de Contabilidad hacia Gastos.** `ExtractorGastos` importa `gastos.models.DocumentoSoporte` a nivel de módulo y ejecuta queries ORM directas en vez de pasar por `gastos.services.selectors`. Consistente con el Pull Model documentado, pero viola la capa de Service Layer estricta (AGENTS.md §7 FSD) — riesgo si `DocumentoSoporte` cambia de esquema sin coordinar con Contabilidad.

- **`Proyecto` se autodescribe "Zero-Coupling" en su propio docstring** ("NO hay ForeignKeys a Clientes, Proveedores, Empleados o Inventario") pero el mismo archivo define 4 FKs reales cross-app (`factura_costo`, `servicio_asociado`, `TareaCorta.cliente`, `TareaCorta.empleado`). Documentación desactualizada frente al código real.

- **Celery task docstring vs. implementación real** — `ejecutar_integracion_contable_task` promete sincronizar "Facturas, Gastos e Inventario" pero el método que invoca omite Inventario (ver CRITICAL #3).

- **`.agent/AUDITORIA_INTEGRACION_EMPLEADOS_CONTABILIDAD.md` describe una integración que ya no existe.** El campo `cuenta_contable_uuid` (en `Empleado` y `Devengo`) fue removido en las migraciones `0004`/`0010`, pero el documento (fechado 2026-05-13) lo sigue describiendo como "✅ CORRECTO" y activo. Documento obsoleto que puede confundir auditorías futuras — debería marcarse como histórico.

- **Gap de estado Venta→Factura→Contabilidad.** `crear_factura_desde_venta()` deja la Factura en `BORRADOR`, pero `ExtractorFacturas` solo toma `estado=ACEPTADA`. Como la transición `BORRADOR→ENVIADA→ACEPTADA` no está automatizada (sin adaptador de transporte DIAN real, solo mock) y el cambio de estado es 100% manual, toda venta facturada requiere una acción humana explícita antes de poder contabilizarse — no documentado como requisito operativo en ningún lugar visible.

- **`ItemVenta` sin `CheckConstraint` de producto/servicio**, a diferencia de `MovimientoInventario` que sí lo tiene — inconsistencia de rigor de validación entre dos modelos del mismo ciclo (`ventas/models.py:245-261` vs. `inventario/models.py:346-353`).

---

## REL-03 — Cardinalidades auditadas

| Pregunta | Hallazgo | Evidencia |
|---|---|---|
| ¿Recepción puede pertenecer a varias empresas? | No — `empresa` FK única, sin campos adicionales | `compras/models.py:361-433` |
| ¿Producto sin empresa? | No — FK obligatoria `PROTECT` | `inventario/models.py:135-140` |
| ¿Movimiento sin sede? | **Sí** — `null=True, blank=True, SET_NULL`, "aplica a toda la empresa" si no se asigna; efecto real: invisible en reportes filtrados por sede | `inventario/models.py:302-313` |
| ¿OrdenCompra sin sede? | No — endurecido `NOT NULL` desde migración 0007 | `compras/models.py:109-122` |
| ¿DocumentoSoporte sin proveedor? | No — FK obligatoria (`CASCADE`, ver REL-07) | `gastos/models.py:140-147` |
| ¿Factura COMPRA sin proveedor_uuid resuelto? | **Sí** — nullable, se resuelve en `guardar_desde_dto()` pero sin constraint de BD que lo obligue por otras vías | `facturas/models.py:188-193` |
| ¿ItemOrdenCompra recibido de más? | No — `CheckConstraint(cantidad_recibida__lte=cantidad)` | `compras/models.py:346-351` |
| ¿AsientoContable duplicado para mismo origen? | No — `UniqueConstraint` condicional | `contabilidad/models.py:406-412` |
| ¿Venta sin cliente? | No — FK `PROTECT`, sin `null` (más estricta que lo que el prompt maestro asumía) | `ventas/models.py:149-154` |
| ¿Cotización sin cliente? | **Sí** — `SET_NULL`, `null=True` (coherente: cotización preliminar puede no tener cliente aún) | `cotizaciones/models.py:58` |
| ¿ItemVenta sin producto NI servicio? | **Sí, válido en BD** — ambos `null=True, blank=True` sin `CheckConstraint` — permite ítems de texto libre (intencional, pero no documentado como regla explícita) | `ventas/models.py:245-261` |
| ¿Factura.save() puede dejar empresa_id NULL? | No — pero tiene un fallback silencioso a `Empresa.objects.first()` si no se setea explícitamente, en vez de fallar duro; riesgo latente si algún día hay >1 Empresa por schema | `facturas/models.py:360-366` |
| ¿Retenciones de Gasto verifican empresa_id en sus properties de lectura? | **Inconsistente** — `total_retefuente/reteica/reteiva` filtran solo por `documento_origen_id` (sin `empresa=`); `total_retenciones` sí filtra por empresa. Mitigado por aislamiento a nivel de schema (no es fuga cross-tenant real), pero es un patrón inconsistente dentro del mismo archivo | `gastos/models.py:267-441` |
| ¿RetencionesService verifica que documento_origen pertenezca a empresa_id? | No — confía en el llamador; sin evidencia de que se explote incorrectamente hoy | `contabilidad/services/retenciones_service.py:179-245` |
| ¿Contrato sin Empleado? | No — FK `CASCADE` obligatoria | `empleados/models.py:178` |
| ¿Más de 1 Contrato ACTIVO por empleado? | No — `UniqueConstraint` condicional a nivel de BD | `empleados/models.py:244-248` |
| ¿Más de 1 PeriodoNomina vivo por empresa+mes? | No — `UniqueConstraint` a nivel de BD | `empleados/models.py:641-645` |
| ¿Devengo sin PeriodoNomina? | **Sí, válido** — `null=True`, "nullable por compatibilidad histórica" (decisión de diseño documentada) | `empleados/models.py:358-365` |

---

## Documentación desactualizada detectada durante esta auditoría (higiene, no funcional)

| Documento | Problema |
|---|---|
| `proyectos/models.py` (docstring del módulo) | Se autodescribe "Zero-Coupling" pero define 4 FKs cross-app reales |
| `contabilidad/tasks.py` (docstring de `ejecutar_integracion_contable_task`) | Promete sincronizar Inventario; el método real no lo hace |
| `.agent/AUDITORIA_INTEGRACION_EMPLEADOS_CONTABILIDAD.md` | Describe una integración (`cuenta_contable_uuid`) removida hace 2 migraciones — debería marcarse histórico |

---

## Siguiente paso sugerido (no ejecutado en esta pasada — requiere priorización explícita)

Esta auditoría es de diagnóstico (REL-01 a REL-10), no de corrección. Los 4 hallazgos CRITICAL y el bug confirmado de `empresa_id` en Gastos son candidatos concretos y acotados para una siguiente sesión de corrección — pero dado el volumen de hallazgos (4 CRITICAL + 1 bug confirmado + 7 IMPORTANT), se recomienda priorizarlos explícitamente antes de tocar código, en vez de corregir todo de una vez.
