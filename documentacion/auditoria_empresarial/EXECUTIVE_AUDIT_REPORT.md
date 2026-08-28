# Informe Ejecutivo — Auditoría Empresarial Integral SINTEL ERP

**Fecha:** 2026-08-27. Rama `feat/onboarding-cookie`.

**Declaración obligatoria de alcance:** este informe NO certifica que SINTEL
cumple legalmente con la normativa colombiana, ni afirma que está
"certificado". Usa exclusivamente los estados `ALIGNED / PARTIALLY_ALIGNED /
GAP / BLOCKED / PROFESSIONAL_REVIEW_REQUIRED`. La verificación de
cumplimiento legal real requiere revisión por un profesional contable/
tributario colombiano con acceso a fuentes DIAN/Ministerio del Trabajo
vigentes — fuera del alcance de esta sesión.

---

## ¿Está SINTEL preparado para operar una MIPYME?

**PARTIALLY_ALIGNED.** El núcleo operativo (maestros, compras, inventario,
ventas, gastos, nómina interna, contabilidad por Pull Model) está
implementado con arquitectura sólida y consistente — verificado con
evidencia de código real en 17 apps, no solo por existencia de pantallas.
Los 2 gaps que impiden una respuesta `ALIGNED` sin reservas son: (1) ninguna
factura electrónica emitida tiene validez legal ante la DIAN hoy (sin
transmisión real), y (2) un hallazgo de integridad contable nuevo y crítico
(`Factura.destroy()` sin reversa) que puede corromper el historial contable/
de inventario si se ejerce.

## ¿Qué procesos están completos?

- **Compras → Recepción → Inventario**: completo y verificado end-to-end (confirmado con drift resuelto desde 2026-08-09).
- **Ventas → Inventario (Kardex)**: completo, incluyendo devoluciones vía Nota Crédito.
- **Traslados entre sedes**: completo, con máquina de estados e idempotencia real (F21).
- **Gastos → Retenciones → Contabilidad**: completo y correctamente centralizado (Pull Model puro, sin tarifas hardcodeadas).
- **Nómina interna (deducciones, prestaciones, recargos)**: completo, con cita normativa inline en la mayoría de las fórmulas.
- **Cierre de período contable (bloqueo de `AsientoContable` retroactivo)**: completo — pero sin extenderse a Facturas/Gastos (ver gaps).

## ¿Qué procesos tienen brechas?

- **Facturación electrónica DIAN** (transmisión real) — GAP crítico, EXTERNAL_DEPENDENCY.
- **Nómina electrónica DIAN (DSPNE)** — mismo patrón, menor alcance.
- **Eliminación de Factura** — sin reversa, GAP crítico de integridad.
- **Cierre de período vs. Facturas/Gastos** — el control documentado no está implementado.
- **Cotización → Venta** — discontinuidad de proceso, requiere decisión de negocio.
- **"¿Qué debo hacer hoy?"** — no existe una vista consolidada; el Dashboard cubre 7 de 9 dominios relevantes (faltan Compras y Bancos).

## ¿Qué datos faltan?

Ningún dato crítico faltante a nivel de maestros (Cliente/Proveedor tienen
identificación, régimen, configuración de retención). El hueco real es de
**catálogo normativo**, no de captura: no existe código de municipio DIAN
estandarizado para Cliente/Proveedor (solo texto libre `ciudad`), y no existe
ningún calendario tributario/de vencimientos en el sistema (correctamente no
hardcodeado, pero tampoco construido como catálogo configurable).

## ¿Qué relaciones faltan?

`Cotización → Venta` (ver arriba). `Factura` no tiene un campo persistido
hacia `Venta` pese a que el propio código sugiere que debería tenerlo — el
vínculo real es frágil (coincidencia de string, no FK/UUID). El Dashboard no
tiene extractor de Compras ni de Bancos, así que esas dos áreas no
participan del panorama consolidado de la empresa.

## ¿Qué integraciones fallan?

Ninguna integración cross-app confirmada como técnicamente rota — las 17
relaciones auditadas en `CROSS_APP_INTEGRATION_MATRIX.md` funcionan según lo
documentado (Pull Model consistente, sin `AsientoContable` creado fuera de
`contabilidad`). Los 2 fallos reales son externos al sistema (transmisión
DIAN), no fallos de integración interna.

## ¿Qué controles faltan?

De 5 flujos transaccionales auditados (Compras, Ventas, Gastos, Nómina,
Bancos), solo **Nómina** tiene segregación de rol real y forzada por
backend. Compras, Gastos y Bancos permiten que un mismo usuario ADMIN
ejecute el ciclo completo sin ningún punto de control — y Bancos ni siquiera
registra quién concilió una transacción. Esto es una decisión de producto
pendiente, no necesariamente un bug: depende de si el segmento MIPYME
objetivo de SINTEL requiere esa segregación o si el control social/manual es
aceptable a esa escala.

## ¿Qué procesos sobran?

Ninguno identificado — no se encontró funcionalidad completa y en uso que
deba eliminarse por redundancia de proceso (distinto de código muerto
puntual, que sí existe y está identificado — ver siguiente pregunta).

## ¿Qué funcionalidades están duplicadas?

- `Producto`/`Servicio` existen por separado en `cotizaciones` (texto libre de línea) e `inventario` (catálogo real) — confirmado que NO son la misma fuente de verdad ni están conectados, no es duplicación accidental sino diseño con propósitos distintos, documentado en la misión de Cotizaciones de esta sesión.
- "Valor de inventario" y "cartera pendiente de clientes" tienen cada una 2 implementaciones de fórmula divergentes en pantallas distintas (dashboard vs. vista propia; 2 selectores de `Cartera`) — riesgo real de mostrar cifras distintas para el mismo concepto de negocio.
- Código muerto confirmado (no duplicación activa, sino sobrante): `ProveedorBusinessService.obtener_configuracion_retenciones()`/`calcular_componentes_retencion()` (tarifas hardcodeadas nunca ejecutadas).

## ¿Qué riesgos contables existen?

1. **CRÍTICO**: `Factura.destroy()` puede dejar `MovimientoInventario`/`AsientoContable` huérfanos sin ningún bloqueo.
2. **CRÍTICO**: períodos contables cerrados no protegen a Facturas/Gastos del edit/anulación retroactiva, pese a que la documentación afirma que sí.
3. **ALTO**: `Retencion` puede duplicarse silenciosamente bajo un doble-submit o reprocesamiento — impacto directo en reportes de retenciones.
4. **ALTO**: numeración de comprobantes contables (`TipoComprobante`) sin bloqueo de concurrencia — riesgo de fallo bajo uso simultáneo real.

## ¿Qué riesgos fiscales existen?

1. Ninguna factura de venta tiene validez legal ante la DIAN (sin transmisión real) — el riesgo más alto de todo el sistema si hay tenants reales que dependen de facturación electrónica válida.
2. Mismo riesgo para nómina electrónica (DSPNE), de menor alcance.
3. IVA capturado como entrada libre sin validar contra tarifas vigentes (0%/5%/19%) en `ventas`/`compras`.
4. Ninguna tarifa de retención está hardcodeada (correcto), pero tampoco hay ninguna validación de que las tarifas que un tenant configure sean las vigentes — depende enteramente de quien administre `ConfiguracionRetenciones`.
5. Contenido de los seeds PUC/NIIF no verificado contra la versión normativa vigente — `PROFESSIONAL_REVIEW_REQUIRED`.

## ¿Qué bloqueadores dependen de terceros?

Exactamente 2, ambos de la misma naturaleza: transmisión real a la DIAN
(facturación electrónica de venta y nómina electrónica DSPNE) — requieren
credenciales, certificado digital y acceso al WSDL/ambiente DIAN de un
tenant real. Ninguna corrección de código dentro de este repositorio puede
cerrar estos 2 ítems por sí sola.

---

## Tabla ejecutiva final (FASE 72)

| Proceso | Estado | Riesgo | Brecha principal | Acción | Dependencia | Prioridad |
|---|---|---|---|---|---|---|
| Maestros (Cliente/Proveedor/Producto) | 🟢 GREEN | Bajo | Ninguna crítica | — | — | — |
| Cotizaciones | 🟡 AMBER | Bajo | No conecta con catálogo de Inventario; no dispara Venta automáticamente | Decisión de producto | — | P2 |
| Compras → Recepción | 🟢 GREEN | Medio | Sin segregación de rol; estado sin validar transiciones | Ver P1/P2 | — | P1 |
| Inventario / Kardex | 🟢 GREEN | Bajo | Ninguna crítica (auditado a fondo esta sesión) | — | — | — |
| Ventas → Facturación (DTO/CUFE/XML) | 🟢 GREEN | Bajo | Técnicamente correcto | — | — | — |
| **Transmisión DIAN (facturas/nómina)** | 🔴 RED | **Crítico** | Sin validez legal ante DIAN | Requiere decisión de negocio + credenciales | **EXTERNAL_DEPENDENCY** | P0 (bloqueado) |
| **Eliminación de Factura** | 🔴 RED | **Crítico** | Hard-delete sin reversa | Bloquear + reversa real | — | P0 |
| **Cierre de período vs. Facturas/Gastos** | 🔴 RED | **Crítico** | Control documentado, no implementado | Invocar validación existente | — | P0 |
| Gastos → Retenciones → Contabilidad | 🟢 GREEN | Bajo | Ninguna crítica | — | — | — |
| Nómina interna (cálculo) | 🟢 GREEN | Bajo | Formulas sin cita inline (documental) | Agregar comentarios de norma | — | P3 |
| Bancos / Tesorería | 🟡 AMBER | Medio | Sin segregación de rol ni trazabilidad de usuario; sin constraint de duplicados | Ver P1/P2 | — | P1/P2 |
| Contabilidad (asientos, Pull Model) | 🟡 AMBER | Medio | `Retencion` sin protección de duplicados; numeración sin lock | Ver P0 | — | P0 |
| Dashboard / "qué debo hacer hoy" | 🟡 AMBER | Bajo | Faltan Compras/Bancos; 1 widget mal etiquetado | Completar extractores | — | P3 |
| Reporting Hub | 🟡 AMBER | Bajo | 4/5 datasets sin UI; 2 fórmulas divergentes | Completar UI, unificar fórmulas | — | P3 |
| Controles internos (segregación de rol) | 🟡 AMBER | Medio-Alto | Solo Nómina tiene segregación real | Decisión de producto | — | P2 |
| Governance (check/migraciones/EKG) | 🟢 GREEN | Bajo | Hallazgos preexistentes repo-wide, no introducidos por esta auditoría | — | — | — |

---

## Cierre — Release Gate Empresarial

**ENTERPRISE_FLOW = COMPLETED_WITH_DEFERRED**, no `PRODUCTION_READY` — por
regla explícita de la misión (§75/§78), no se declara certificación ni
cumplimiento legal, y quedan 3 hallazgos P0 (2 de código, 1 bloqueado por
dependencia externa) sin cerrar. La auditoría en sí (mapeo, clasificación,
producción de las 10 matrices exigidas) está completa. La corrección de
código queda agendada en `REMEDIATION_MASTER_PLAN.md`, para ejecutarse en
misiones dedicadas subsecuentes, con el mismo rigor de test-verificación ya
demostrado 3 veces en esta sesión.
