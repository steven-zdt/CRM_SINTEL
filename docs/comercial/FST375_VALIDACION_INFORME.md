# FST-375 — Informe de validación y ejecución

Ejecuta `apps/tenant/ventas/.agent/PROMPT_IA_EDITORA_FACTURAS_VENTAS_FST375.md`.
Ciclo real seguido: INSPECT → BASELINE → MAP → (decisión de alcance con el
usuario) → IMPLEMENT → TEST → DOCUMENT.

## 45.1 — Informe de auditoría

### Estado anterior

El propio INSPECT reveló que la mayor parte de la arquitectura que pide el
prompt **ya existía y estaba probada** desde dos misiones previas de este
mismo repo:

- `VENTAS-COMPRAS-FACTURAS-01` (2026-09-09) — bloqueó por completo la
  emisión fiscal desde Ventas (`EMISION_FISCAL_VENTA_AUTORIZADA = False`),
  estableció "Facturas = SSoT fiscal" / "Ventas = SSoT comercial".
- `FACTURAS-VENTAS-COMPRAS-01` — implementó `Venta.factura_asociada`
  (OneToOne), `VentaBusinessService.vincular_factura_existente()` con DSV
  real (naturaleza, empresa, idempotencia 409, 422, 404), el buscador
  `GET /api/v1/facturas/buscar-para-movimiento/`, la UI de "Buscar/Vincular
  Factura" en el detalle de Venta, y ya exponía en `VentaDetailSerializer`
  los campos de solo lectura `forma_pago`, `medio_pago_codigo`,
  `payment_due_date`, `fecha_pago`, `factura_cufe`, `factura_numero`,
  `factura_uuid`, `factura_estado`, `estado_pago` — todos sourced desde
  `factura_asociada`.

### Hallazgos

1. **Conflicto arquitectónico real (resuelto con el usuario antes de tocar
   código):** las secciones 24-31 del prompt piden rediseñar "Nueva
   Factura" como formulario manual editable (cliente, ítems, IVA, forma de
   pago). El formulario real (`offcanvas_crear_factura.html`) es
   exclusivamente un importador de XML UBL 2.1 (drag & drop) — no existe
   ningún camino de creación manual de una factura fiscal, por diseño
   deliberado ("Facturas = document store", la misma lógica que bloqueó la
   emisión fiscal desde Ventas). Decisión del usuario: **no construir el
   formulario manual**; en su lugar, enriquecer el DETALLE de solo lectura.
2. El detalle de Factura (`offcanvas_detalle_factura.html` +
   `FacturaDetailSerializer`) **no exponía** varios campos que el modelo
   `Factura` ya tenía poblados desde el XML: autorización DIAN completa
   (número/prefijo/rango/vigencia), `qr_code` (texto crudo), `fecha_
   vencimiento`, `forma_pago`, `medio_pago_codigo`. Gap real, sin conflicto
   arquitectónico — es una vista de solo lectura sobre datos ya persistidos.
3. No existía "valor en letras" en ningún punto del backend (ni utilidad,
   ni campo, ni dependencia `num2words` instalada).
4. No existía una herramienta de **reconciliación masiva** Facturas→Ventas
   (auditoría DRY RUN + creación/vínculo en lote). El único camino existente
   era manual, uno a uno, vía UI (`vincular_factura_existente`). El patrón
   de comandos `management/commands/backfill_*.py`/`audit_*.py` ya
   establecido en este repo se reutilizó como base.
5. Se detectó un caso real explotable con esta misma reconciliación: al
   correr el comando en modo DRY RUN sobre la base de datos real del
   entorno, se encontraron 30 Facturas naturaleza VENTA sin vínculo directo
   en 2 tenants reales (`home`, `admin`) — 5 ya vinculadas, 25 candidatas a
   creación de Venta nueva, 0 ambiguas, 0 errores. **No se ejecutó `--apply`
   sobre esos datos reales** — queda pendiente de que el usuario decida
   correrlo.

### Riesgos

- Crear Ventas en lote es una acción con efecto de datos real y no
  trivialmente reversible (no hay "deshacer masivo") — por eso el comando
  por defecto es DRY RUN (invierte la convención de los `backfill_*.py`
  existentes, que por defecto sí escriben).
- El campo `numero_factura` de `Venta` es un `CharField` libre (no único a
  nivel de BD) — el criterio de match "candidata única por número" puede
  fallar (marcar AMBIGUA) si el dato histórico tiene números duplicados por
  error de captura manual anterior a esta migración. Comportamiento
  intencional: ante ambigüedad, no vincular nunca automáticamente (regla
  explícita del encargo, sección 18).

### Correcciones aplicadas

Ver sección "Modified Files" abajo — todas aditivas, sin migraciones de
esquema (no se agregó ningún campo nuevo a `Factura`, ya existían todos).

---

## 45.2 — Matriz de mapeo Factura → Venta

| Dato | Factura (SSoT fiscal) | Venta (SSoT comercial) | Mecanismo |
|---|---|---|---|
| Vínculo | `venta_origen` (reverse OneToOne) | `factura_asociada` (FK) | Ya existía (VCF-005, deliberadamente FK directa, no soft-reference) |
| Cliente | `receptor_nit`/`receptor_razon_social`/`cliente_uuid` | `cliente` (FK real) | `ClienteBusinessService.resolver_o_crear_desde_factura_venta()` (ya existía) |
| Fechas | `fecha_emision` (DateTime), `fecha_vencimiento` (Date) | `fecha_emision`/`fecha_vencimiento` (Date) | Copiado 1 vez al crear (`crear_venta_desde_factura`, nuevo); no se re-sincroniza después |
| Ítems | `ItemFactura` (descripcion/cantidad/valor_unitario/porcentaje_iva) | `ItemVenta` | Copiado 1 vez al crear; `ItemVenta` es su propio registro comercial, no una referencia |
| Totales | `subtotal`/`impuestos`/`total` | `subtotal`/`impuestos`/`total_neto` | Copiado al crear; después, `Venta` mantiene los suyos (no se re-sincronizan automáticamente) |
| CUFE, forma_pago, medio_pago_codigo, payment_due_date, fecha_pago, estado_pago | Campos propios (SSoT) | `VentaDetailSerializer` los expone como `SerializerMethodField` de solo lectura leyendo `factura_asociada` en vivo | Ya existía (`FACTURAS-VENTAS-COMPRAS-01`) — nunca se copian a columnas de `Venta` |
| Autorización DIAN, QR | Campos propios (SSoT) | No expuesto en Venta (decisión: Ventas no debe ser un espejo fiscal completo, solo lo esencial para gestión de pago) | Sin cambios — visible solo en el detalle de Factura |
| Estado | `estado` (BORRADOR/ENVIADA/ACEPTADA/...) | `estado` pasa a `FACTURADA_DIAN` al vincularse | `VentaCRUDService.vincular_factura()` (ya existía) |

## 45.3 — Matriz FST 375 (dato visible → campo → origen → editable)

| Dato visible en FST 375 | Campo backend | Dónde se muestra | Origen | Editable desde UI |
|---|---|---|---|---|
| No. FST 375 | `Factura.numero`/`prefijo`/`consecutivo` | Detalle Factura, `Venta.numero_factura` | XML | No |
| Focus electronic security... / NIT 900.860.947-3 | `receptor_razon_social`/`receptor_nit` | Detalle Factura; `Venta.cliente` tras vincular | XML | No |
| Generación / Expedición 20/06/2026 10:18 | `Factura.fecha_emision` (un solo campo — el PDF muestra el mismo valor dos veces bajo dos etiquetas distintas, no son datos independientes) | Detalle Factura (`view_fecha_emision`) | XML | No |
| Vencimiento 20/07/2026 | `fecha_vencimiento` | Detalle Factura (nuevo: `view_fecha_vencimiento`) | XML | No |
| Ítem/Descripción/Cantidad/Vr.Unitario/Valor Impto./Vr.Total | `ItemFactura.*` | Detalle Factura (tabla de ítems, ya existía) | XML | No |
| Total Bruto / IVA 19% / Total a Pagar | `subtotal`/`impuestos`/`total` | Detalle Factura (ya existía) | XML | No |
| Valor en Letras | *(no persistido, calculado)* | `FacturaDetailSerializer.valor_en_letras` (nuevo) | Calculado en backend desde `total` (`core.services.numero_a_letras.monto_a_letras`) | No (no es un campo, es derivado) |
| Forma de pago: Crédito | `forma_pago` | Detalle Factura (nuevo: `view_forma_pago`); Venta (ya existía) | XML | No |
| Medio de pago: Otro - Crédito | `medio_pago_codigo` | Detalle Factura (nuevo: `view_medio_pago`); Venta (ya existía) | XML | No |
| Cuota No. 001 / vence 2026-07-20 / $5.139.915,83 | *(no modelado como cuotas — coincide 1:1 con `payment_due_date` + `total`, es un caso de pago único)* | — | — | — |
| Observaciones + OC | *(campo `observaciones` vive en `Venta`, no en `Factura` — es un dato comercial, no fiscal)* | Detalle Venta (ya existía) | Manual en Venta | Sí, en Venta |
| Número Autorización / prefijo / rango / vigencia | `autorizacion_numero`/`autorizacion_prefijo`/`autorizacion_rango_desde`/`_hasta`/`autorizacion_vigencia_inicio`/`_fin` | Detalle Factura (nuevo: bloque "Autorización DIAN") | XML | No |
| CUFE | `cufe` | Detalle Factura (ya existía); Venta (ya existía, `factura_cufe`) | XML | No |
| QR | `qr_code` (texto crudo)/`qr_url` | Detalle Factura (nuevo: `view_qr_code`) | XML | No — nunca se genera un QR ficticio |
| Régimen simple de tributación / Actividad económica / Tarifa 10x1000 | *(no existen como campos de `Factura` — son datos del emisor/tenant, no de la factura individual; fuera de alcance sin evidencia de dónde persistirlos)* | — | — | — |

---

## 45.4 — Migración (resultado real de DRY RUN sobre datos de este entorno)

```
Modo: DRY RUN (solo reporte, nada se escribe)

[home]
  facturas_naturaleza_venta_total: 2
  facturas_naturaleza_compra: 5
  notas_credito: 0
  notas_debito: 0
  ya_vinculadas: 1
  vinculadas_a_venta_existente: 0
  ventas_creadas: 1
  ambiguas: 0
  omitidas_sin_items: 0
  errores: 0

[admin]
  facturas_naturaleza_venta_total: 28
  facturas_naturaleza_compra: 0
  ya_vinculadas: 4
  vinculadas_a_venta_existente: 0
  ventas_creadas: 24
  ambiguas: 0
  omitidas_sin_items: 0
  errores: 0

TOTAL: 30 facturas venta, 5 ya vinculadas, 25 candidatas a Venta nueva,
0 ambiguas, 0 errores.
```

**No se ejecutó `--apply`** sobre estos datos reales — es una decisión que
le corresponde al usuario (crea registros comerciales reales). Comando:
`python manage.py migrar_facturas_a_ventas [--schema=<tenant>] [--apply]`.

## 45.5 — Tests

Archivo nuevo: `apps/tenant/ventas/tests/test_fst375_migracion_y_autorrelleno.py`
(9 casos, valores reales de FST 375 como fixture de test, nunca como
literales en código de producción):

- Detalle de Factura expone `valor_en_letras` exacto, autorización DIAN
  solo-lectura, forma/medio de pago.
- DRY RUN no escribe nada.
- `--apply` crea la Venta, autorrellena cliente/fechas/ítems/totales, y dicho
  autorrelleno queda visible vía `VentaDetailSerializer` (solo lectura).
- Idempotencia: correr dos veces no duplica.
- No duplica si ya existe una Venta manual con el mismo `numero_factura`
  (la vincula en vez de crear una segunda).
- Ambigüedad: 2 Ventas candidatas → no vincula, cuenta como `ambigua`.
- `crear_venta_desde_factura` falla explícitamente si la Factura no tiene
  ítems.

Resultado: **ver evidencia de ejecución en el hilo de trabajo** (corrida
real dentro de Docker, `pytest apps/tenant/ventas/tests/test_fst375_migracion_y_autorrelleno.py`).

## 45.6 — Evidencia UI

No disponible en este entorno (sin navegador) — mismo límite documentado en
todas las misiones anteriores de esta sesión. Verificado en su lugar: HTML
del offcanvas + JS de wiring revisados línea por línea, sintaxis JS validada
con `node --check`, y el flujo de datos (API → `setElement()` → DOM) sigue
el mismo patrón ya usado por los campos preexistentes (`view_cufe`, etc.).

---

## Modified Files

Backend:
- `apps/tenant/core/services/numero_a_letras.py` — **nuevo**, conversor de
  monto a letras en español (sin dependencias nuevas).
- `apps/tenant/facturas/services/selectors.py` — `DETAIL_FIELDS` +9 campos
  (autorización DIAN, `qr_code`, teléfonos).
- `apps/tenant/facturas/api/serializers.py` — `FacturaDetailSerializer.
  valor_en_letras` (nuevo `SerializerMethodField`) + campos nuevos marcados
  `read_only`.
- `apps/tenant/ventas/services/business_service.py` —
  `VentaBusinessService.crear_venta_desde_factura()` (nuevo, compone
  servicios ya existentes, no duplica lógica).
- `apps/tenant/facturas/management/commands/migrar_facturas_a_ventas.py` —
  **nuevo**, reconciliación masiva DRY RUN por defecto.

Frontend:
- `apps/tenant/facturas/templates/tenant/facturas/offcanvas_detalle_factura.html`
  — bloques nuevos: fecha de vencimiento, forma/medio de pago, valor en
  letras, autorización DIAN, QR (todo solo lectura).
- `apps/tenant/facturas/static/facturas/js/features/ver_detalle_factura.js`
  — wiring de los bloques nuevos.

Tests:
- `apps/tenant/ventas/tests/test_fst375_migracion_y_autorrelleno.py` — nuevo.

## No tocado (deliberadamente)

- `offcanvas_crear_factura.html` (importador XML) — decisión explícita del
  usuario, ver hallazgo 1.
- `VentaDetailSerializer` — ya exponía todo lo necesario de `factura_asociada`,
  sin gap real.
- Modelo `Factura`/`Venta` — cero migraciones nuevas, todos los campos ya
  existían.
- Régimen tributario / actividad económica / tarifa ICA — sin campo real
  donde persistirlos a nivel de Factura individual; no se inventó uno.
