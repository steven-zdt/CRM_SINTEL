# Facturas Hub — Baseline (FASE 0)

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código).
Ámbito: `apps/tenant/facturas/` y sus integraciones reales con
`clientes`/`proveedores`/`compras`/`ventas`/`inventario`/`bancos`/
`contabilidad`/`core`. Metodología: lectura directa del código real —
"el código real prevalece", no se asumió que documentación previa
(`COMPLETO_FLUJO_FACTURAS.md`) fuera exacta sin re-verificar cada
afirmación contra las líneas reales.

**Conclusión adelantada:** la mayor parte de lo que esta misión pide ya
existe, funciona, y está mejor resuelto de lo que el enunciado de la
misión asumía en varios puntos (documentado explícitamente abajo, no
oculto). Solo se identificó **un gap real de modelo** (origen/sistema de
origen, FASE 7-8) y **una duplicación real de lógica** (naturaleza en
preview de ingesta por correo, FASE 32) — ninguno bloqueante.

---

## 1. `importar_documento()` — pipeline real confirmado

`FacturaBusinessService.importar_documento(file_bytes, filename, preview,
async_mode)` (`business_service.py:915`):

```
file_bytes
   ↓ (si FEATURE_DOCUMENT_PIPELINE) ingest_document() [pipeline universal]
   ↓ (si preview=True o falla) retorna DTO / error, NO persiste
   ↓ (si preview=False) FacturaBusinessService.guardar_desde_dto(dto, ...)
```

Fallback legacy (sin el feature flag): `ubl_parser.parse_ubl_to_dict()`
directo, mismo destino final (`guardar_desde_dto()`) — **un solo punto de
persistencia**, confirmado, sin importar qué rama de parsing se tome.

**Endpoints reales** (`api/mixins/factura_ubl_mixin.py`):
- `POST /api/v1/facturas/upload-ubl/` — **DEPRECATED** (marcado en su
  propio docstring), soporta single-file y batch (`files[]`).
- `POST /api/v1/facturas/importar-ubl/` — **DEPRECATED**, XML como texto.
- `POST /api/v1/facturas/upload-document/` — endpoint universal
  (`FEATURE_UPLOAD_DOCUMENT_ENDPOINT`), soporta XML/PDF/XLS/CSV/TXT.
- `POST /api/v1/facturas/create-from-dto/` — persiste un DTO ya parseado
  (usado también por `VentaBusinessService.procesar_y_facturar_venta()`,
  ver §9).
- `GET /api/v1/facturas/ingest/{task_id}/status/` — polling de tareas
  Celery para archivos async/batch grande.

Ninguno de los 3 endpoints de upload duplica el parser ni la
persistencia — todos convergen en `guardar_desde_dto()` (directo o vía
`ingest_document()`).

---

## 2. `_resolver_naturaleza()` — SSoT confirmada

```python
# business_service.py:243
if nit_dto and nit_tenant and nit_dto == nit_tenant:
    return Factura.Naturaleza.VENTA
return Factura.Naturaleza.COMPRA
```

Coincide exactamente con la regla que la misión describe. Además,
`guardar_desde_dto()` aplica una **segunda capa de seguridad** no
mencionada por la misión ("Cascading Security", línea 413-427): si el NIT
de la empresa no coincide NI con emisor NI con receptor, rechaza el
documento entero (`ValidationError`) antes de resolver naturaleza; y si
la naturaleza resuelta es `COMPRA`, exige además que el receptor sea
realmente el tenant (rechaza documentos de un tercero ajeno con
`document_not_for_tenant`). Esto ya cubre varios de los "casos" que
FASE 2 pedía analizar (emisor incorrecto, factura de un tercero ajeno).

**Duplicación real encontrada (FASE 32):** `services_mail_ingestion.py`
(`preview_mail_ingestion()`, línea ~763) reimplementa una versión
**distinta** de esta regla para mostrar un mensaje de validación temprano
en la vista previa de ingesta por correo — no llama a
`_resolver_naturaleza()`, tiene su propia comparación emisor/receptor
contra el NIT del tenant. Es **preview-only** (nunca persiste, solo
informa `belongs_to_tenant`/`validation_message` al usuario antes de
confirmar) — no puede producir una `Factura` con naturaleza incorrecta
por sí sola, pero si esta lógica diverge de `_resolver_naturaleza()` +
Cascading Security en el futuro, el mensaje de preview podría mentir
sobre el resultado real de la persistencia. Documentado, no corregido en
esta fase (bajo riesgo, fuera del flujo de persistencia real).

---

## 3. Idempotencia — CUFE como ancla primaria, con fallback real por número

`guardar_desde_dto()` (línea 472-567):
- **Con CUFE:** `Factura.objects.filter(cufe=cufe, empresa=...)` — si
  existe, retorna la factura existente (200, `created: False`) **y
  además intenta vincular cliente/proveedor si faltaba** (auto-reparación
  en cada reintento, no solo en la creación inicial).
- **Sin CUFE** (F26-006, ya documentado en sesión previa de esta misma
  auditoría): fallback a idempotencia por `numero` — evita el
  `IntegrityError` que produciría guardar `cufe=""` repetido contra la
  `unique constraint` (el campo es `null=True`, no `blank=""`).
- **Pre-validación rápida** (`upload_ubl`, `fast_get_cufe()`): extrae el
  CUFE por regex ANTES del parsing completo, para responder 200
  "duplicado" en milisegundos sin gastar CPU en re-parsear un XML ya
  conocido — optimización real, no solo un TODO.

Confirma exactamente lo que FASE 3 pedía: mismo XML/CUFE cargado 2 o 3
veces → un solo documento fiscal, sin duplicados. No se inventó una
identidad fiscal para documentos sin CUFE — se usa `numero` (dato real
del documento), consistente con la instrucción "no inventar".

---

## 4. Clasificación de documento

`doc_type` se lee de `dto.get("document_type"/"type"/"tipo")`. Detecta
`is_credit_note` (NC) y `debitnote` (ND) explícitamente; todo lo demás
cae a `Factura.TipoFactura.FE`. **No existe una categoría explícita
`OTRO`/`INVALIDO`** a nivel de `Factura.tipo` — pero la validación de
campos obligatorios (línea 405: `numero` + `emisor_nit` + `receptor_nit`,
salvo NC) actúa como el filtro real: un XML que no tenga esa forma
mínima nunca llega a persistirse, retorna `422 missing_required_fields`
en su lugar. Cumple la intención de FASE 4 (no guardar cualquier XML bien
formado como factura) sin necesitar un estado `INVALIDO` explícito — el
rechazo ocurre antes de crear la fila.

---

## 5. Inmutabilidad — confirmada, coincide exactamente con la misión

`models.py:984-1030`:
- `MANUAL_EDITABLE_FIELDS` (9 campos): `estado`, `estado_pago`,
  `categoria`, `fecha_vencimiento`, `payment_due_date`, `forma_pago`,
  `medio_pago_codigo`, `cotizacion_uuid`, `cotizacion_numero`, `sede`.
- `XML_IMMUTABLE_FIELDS` (18 campos, incluye **`naturaleza`**) — un
  usuario no puede convertir `COMPRA → VENTA` manualmente, confirmado a
  nivel de modelo (`actualizar_factura_limitado()` rechaza con 400
  explícito cualquier campo de esta lista, línea 1019-1025).

Cumple FASE 5 sin cambios necesarios.

---

## 6. Vinculación cliente/proveedor — MÁS automática de lo que la misión asumía

**Hallazgo importante para FASE 11/12:** la misión asume un flujo con
estado `CLIENTE_NO_VINCULADO`/`PROVEEDOR_NO_VINCULADO` y acciones
manuales ("Crear cliente", "Vincular existente", "Revisar"). **El código
real no tiene ese estado — resuelve o crea automáticamente en cada
importación:**

```python
# guardar_desde_dto(), naturaleza == VENTA
cliente, _ = ClienteBusinessService.resolver_o_crear_desde_factura_venta(...)
# busca por NIT (ClienteSelector.get_cliente_by_documento) -- si existe, lo usa
# si NO existe, lo CREA automaticamente (tipo_persona=JURIDICA, regimen=ORDINARIO)
# solo lanza ValidationError si falta NIT o razon_social en el XML
```

Mismo patrón para `ProveedorBusinessService.resolver_o_crear_desde_factura_compra()`.
**Consecuencia real:** una `Factura` importada exitosamente **siempre**
queda con `cliente_uuid`/`proveedor_uuid` poblado — nunca queda en un
limbo "sin vincular" salvo que el XML mismo no traiga NIT/razón social
(en cuyo caso la importación completa falla con 422, no queda a medias).
**No se introduce el estado `NO_VINCULADO`** en esta fase: hacerlo
sería duplicar un mecanismo que ya resuelve el problema de forma más
robusta (nunca deja huérfanos) — contradiría la instrucción de la misión
de "no crear otro sistema equivalente". Si el negocio real quiere una
revisión manual ANTES de auto-crear un tercero, es una decisión de
producto que debe pedirse explícitamente, no inferirse.

---

## 7. Origen del documento — **gap real confirmado**

Grep de `origen`/`source_system`/`origin` sobre `models.py`: **cero
resultados relevantes** (los únicos matches son `documento_origen_app`/
`documento_origen_modelo` del mecanismo de trazabilidad de
`Retencion`/`MovimientoInventario`, un concepto no relacionado). **No
existe ningún campo en `Factura` que distinga**:
- Si la factura se originó `INTERNO` (vía `crear_factura_desde_venta()`,
  push desde `ventas`) vs `EXTERNO`/`IMPORTADO` (vía XML/upload).
- El sistema de origen real (`SIIGO`, otro facturador, manual, SINTEL).

**Confirmado gap real, no un malentendido de la misión** — FASE 7/8 se
implementan en la fase de código de esta misión (no en FASE 0, que es
auditoría pura), con campos nuevos aditivos.

---

## 8. `FacturaInterAppAPI` — contrato de lectura abierto, confirmado

`business_service.py:1160`. Métodos: `list_all()`, `get_by_id()`,
`summary_all()`, `get_by_cufe()`, `get_by_numero()`, `resolve_cotizacion()`,
`recalcular_estado_pago_automatico()` — todos **sin filtro `empresa_id`**
(aislamiento real via schema Postgres, no filtro de fila) y **solo
lectura**, salvo `recalcular_estado_pago_automatico()`, la única
excepción de escritura, disparada exclusivamente desde `Bancos` al
conciliar (confirma FASE 17, Pull Model de Bancos, ya auditado en
`COMERCIAL_02_MATRIZ_SSOT.md` §4 — sin cambios desde entonces).
Documentado en el propio docstring: **"no exponible como API HTTP"** —
uso exclusivo servicio-a-servicio.

---

## 9. Compatibilidad con Ventas — confirmada, sin duplicación

`crear_factura_desde_venta()` (auditado en profundidad en
`COMERCIAL_01_AUDITORIA.md`/`COMERCIAL_03_CONTRATO_DTO.md`, sin cambios
desde entonces) y `create-from-dto` (endpoint HTTP, usado por el pipeline
de importación XML) **comparten el mismo destino final**
(`guardar_desde_dto()`/persistencia de `Factura`), pero por dos caminos
de entrada distintos — `VentaFacturaDTO` (interno) vs DTO del pipeline
universal (externo). No hay una segunda función de persistencia, ambos
convergen. Cumple FASE 30 sin cambios.

---

## 10. Notas Crédito — confirmado, sin cambios necesarios

`NotaCredito`/`ItemNotaCredito` y su flujo completo
(`CreditNoteLine` → `ItemNotaCredito` → `ENTRADA_DEVOLUCION` real vía
`KardexService`) ya fue auditado y verificado exhaustivamente en una
fase anterior de esta misma sesión (commits `b141d91`/`4a88bcf`/`2c63b0f`/
`7ec22c4`, más el fix de `8c33cb8`). Cumple FASE 31 sin trabajo adicional.

---

## 11. Batch / Preview / Error management — confirmado, ya robusto

`_upload_ubl_batch()` (`factura_ubl_mixin.py:257`): procesa cada archivo
independientemente, **un archivo inválido no aborta el lote** — cada
resultado individual queda en `resultados[]` con `status: created |
duplicate | error`, más contadores agregados (`creados`/`duplicados`/
`errores`). Lotes >10 archivos se delegan a Celery
(`batch_upload_facturas_task`) para no bloquear la request. Cumple
FASE 20/22 exactamente como se pedía, sin cambios necesarios.

`preview=true` está soportado en los 3 endpoints de upload (no en batch,
explícitamente rechazado con mensaje claro:
`preview_batch_not_supported`) — retorna el DTO sin persistir. Cumple
FASE 21.

---

## 12. Seguridad tenant — confirmada

Múltiples comentarios `IDOR fix` explícitos en el código
(`upload_ubl`/`_upload_ubl_batch`, v2.61.5): `empresa_id` se resuelve
SIEMPRE desde `request.user.tenant_profile`, nunca se acepta del
frontend. Aislamiento real entre tenants es por schema Postgres
(`django-tenants`), no por filtro de fila — mismo patrón ya confirmado en
todas las auditorías previas de esta sesión. Cumple FASE 23.

---

## 13. Bancos / Contabilidad — confirmado, sin cambios (ya auditado)

Pull Model de ambos ya verificado con evidencia en
`COMERCIAL_02_MATRIZ_SSOT.md` §4-5 en esta misma sesión — sin cambios de
código desde entonces. `recalcular_estado_pago_automatico()` (§8 arriba)
sigue siendo la única escritura cruzada, disparada por Bancos, nunca al
revés. Cumple FASE 17/18 sin trabajo adicional.

---

## 14. Estado formal de FASE 0

**`FACTURAS_HUB FASE 0 = COMPLETA`.** Auditoría exhaustiva contra código
real, sin cambios de código en esta fase. Confirma que la mayoría de la
infraestructura que la misión pide **ya existe y funciona
correctamente** — el trabajo real restante de esta misión es acotado:
agregar `origen`/`sistema de origen` (FASE 7-8, gap real), documentar
formalmente el modelo de propiedad (FASE 36, ya construido en
`COMERCIAL_02_MATRIZ_SSOT.md`, se extiende aquí), y ejecutar la
verificación puntual/governance (FASE 37-39) — no reconstruir nada que
ya funcione.
