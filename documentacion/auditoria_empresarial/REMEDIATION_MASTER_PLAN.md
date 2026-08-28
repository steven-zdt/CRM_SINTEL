# Plan Maestro de Corrección — SINTEL ERP

**Fecha:** 2026-08-27. Ordenado por prioridad real (seguridad/pérdida de
datos → integridad contable → integridad fiscal → integridad transaccional
→ integraciones → datos → UX → performance → limpieza), no por severidad
etiquetada sola. Cada ítem cita su hallazgo completo en `BUSINESS_GAP_MATRIX.md`.

**Ninguno de estos ítems se corrigió en esta sesión** — esta auditoría se
detuvo deliberadamente en AUDITAR/MAPEAR/CLASIFICAR (regla explícita del
prompt maestro §88). Corregir 8+ apps con cambios de esta naturaleza en la
misma pasada que genera 10 documentos de auditoría integral arriesgaría
calidad y verificación real (tests) sobre cada fix — el patrón ya establecido
en esta sesión es: una misión dedicada por app/hallazgo, con su propio ciclo
de test-verificación (ver las 3 misiones de modernización previas de
cotizaciones/proveedores/inventario). Este plan es la agenda para esas
misiones futuras, no un резervorio de trabajo pendiente sin dueño.

---

## P0 — Seguridad de datos / pérdida de integridad (corregir primero, alto blast radius si no se corrige)

| # | Ítem | App | Esfuerzo estimado | Bloqueante de |
|---|---|---|---|---|
| 1 | `Factura.destroy()` hace hard-delete sin reversa, incluso de facturas DIAN aceptadas | `facturas` | Medio — requiere diseño de reversa (mismo patrón que `Venta`/`Gasto`/`Contabilizador.reversar_asiento`), migración si se agrega campo de estado, tests de reversa de Kardex/Asiento vinculados | Integridad contable de todo el sistema |
| 2 | `PeriodoContable` no bloquea edición/anulación de Facturas/Gastos en períodos cerrados, pese a documentarlo | `contabilidad`↔`facturas`/`gastos` | Bajo-Medio — invocar función ya existente (`verificar_periodo_cerrado`) desde 2 apps más, tests de regresión en ambas | Confiabilidad de reportes de períodos ya cerrados |
| 3 | `Retencion` sin protección de duplicados (ni constraint ni check de aplicación) | `contabilidad` | Bajo — agregar `UniqueConstraint`, requiere migración + verificar 3 tenants reales por duplicados existentes antes de aplicar (mismo protocolo ya usado en las misiones de esta sesión) | Exactitud de reportes de retenciones DIAN |
| 4 | `TipoComprobante.obtener_siguiente_numero()` sin `select_for_update()` | `contabilidad` | Bajo — un `select_for_update()` adicional, mismo patrón ya probado en 4 apps distintas | Estabilidad bajo concurrencia real |

## P1 — Integridad transaccional / contable (segunda ola)

| # | Ítem | App | Notas |
|---|---|---|---|
| 5 | `OrdenCompra.cambiar_estado()` sin validación de máquina de estados; anulación no reversa CxP | `compras` | Requiere definir `TRANSICIONES_VALIDAS` explícitas (mismo patrón que `Factura`) |
| 6 | `Gastos.destroy()` bypasea protección `anulado` cuando `DEBUG=True` | `gastos` | Corrección de 1-2 líneas, mismo hallazgo ya corregido en Inventario esta sesión (commit `399f1c8`) |
| 7 | `TransaccionBancaria`/`ExtractoBancario` sin `UniqueConstraint` real | `bancos` | Requiere definir el alcance exacto del constraint sin bloquear reimportación legítima (ya idempotente vía delete-then-reinsert) |
| 8 | Sin validación de fecha pago vs. fecha documento en conciliación bancaria | `bancos` | Agregar validación en `ConciliarSerializer` |
| 9 | `cerrar_periodo()` sin checklist previo (pendientes=0, descuadres=0) | `contabilidad` | Requiere definir qué cuenta como "pendiente" cross-app (documentos sin contabilizar en `gastos`/`facturas`/`inventario`/`empleados` dentro del rango del período) |

## P2 — Controles internos / decisión de producto (requiere alineación de negocio antes de codificar)

| # | Ítem | Decisión requerida |
|---|---|---|
| 10 | Sin segregación de rol en Compras/Gastos/Bancos | ¿El negocio objetivo (MIPYME) necesita esto, o el control social/manual es aceptable a esta escala? Si se decide que sí, replicar `PeriodoNominaViewSet._ROLES_POR_ACCION` |
| 11 | Cotización → Venta no es un trigger automático | ¿Es intencional (Cotización = documento comercial sin efecto transaccional) o falta un paso de conversión? |
| 12 | `regimen_tributario` de Cliente capturado sin uso downstream | ¿Debe activar lógica distinta (ej. aplicabilidad de ciertas retenciones), o es correctamente solo informativo hoy? |
| 13 | Retención practicada por el cliente (dirección inversa, CxC) no confirmada como existente | Verificación dirigida primero (no se confirmó con lectura de código en esta sesión si es un gap real o simplemente no aplica al modelo de negocio actual) |

## P3 — UX / datos / limpieza (menor riesgo, alto valor de pulido)

| # | Ítem | App |
|---|---|---|
| 14 | Dashboard sin extractor de Compras ni de Bancos | `dashboard` |
| 15 | Widget "Gastos → Vencidos" mal etiquetado (muestra anulados) | `dashboard` |
| 16 | "Valor de inventario" con 2 fórmulas divergentes (dashboard vs. vista propia) | `dashboard`/`inventario` |
| 17 | "Cartera pendiente" de clientes con 2 selectores divergentes | `clientes` |
| 18 | Reporting Hub: 4 de 5 datasets sin pantalla propia en frontend | `core` (reporting frontend) |
| 19 | UI no oculta visualmente controles no permitidos por rol (backend-only) | `contabilidad`/`bancos`/`empleados` (transversal) |
| 20 | `Factura.consecutivo=0` para todas las facturas EXTERNO — inutilizable como identificador | `facturas` |
| 21 | `OrdenCompra.ANULADA` inalcanzable (sin método de servicio) | `compras` |
| 22 | `Factura` sin campo `venta_uuid` persistido pese a comentario que lo sugiere | `facturas` |
| 23 | Código muerto confirmado: `ProveedorBusinessService.obtener_configuracion_retenciones()`/`calcular_componentes_retencion()` | `proveedores` |

## EXTERNAL_DEPENDENCY (no se pueden cerrar sin insumos de terceros)

| # | Ítem | Qué se necesita |
|---|---|---|
| 24 | Transmisión real DIAN de facturas de venta | Credenciales/certificado/WSDL de un tenant real en producción, decisión de negocio sobre si hay tenants que lo requieren hoy |
| 25 | Transmisión real DSPNE de nómina electrónica | Igual que arriba, aplicado a nómina |

## Regla de ejecución para cuando se acometa este plan

Para cada ítem P0-P2: seguir el mismo ciclo ya validado 3 veces en esta
sesión (misiones de cotizaciones/proveedores/inventario) — 1) leer el código
real del hallazgo, 2) corregir en la capa propietaria (nunca en el
consumidor), 3) escribir/ejecutar tests reales locales (venv, nunca vía
`docker compose exec`), 4) verificar migraciones contra los 3 tenants reales
antes de aplicar si el fix requiere una, 5) documentar honestamente lo que
se hizo y lo que quedó fuera. No agrupar ítems de apps distintas en un solo
commit — mismo criterio ya aplicado (`399f1c8`, `fe9555a` de esta sesión).
