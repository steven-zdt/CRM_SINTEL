# Ciclo Comercial — Auditoría Ventas ↔ Facturas (FASE COMERCIAL-01)

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código, por
instrucción explícita del plan). Ámbito: `Venta`/`ItemVenta`, `Factura`/
`ItemFactura`, `VentaBusinessService`, `FacturaBusinessService`,
`_construir_dto_factura()`, `crear_factura_desde_venta()`,
`procesar_y_facturar_venta()`, referencias UUID, estados, atomicidad,
idempotencia.

Complementa la documentación ya existente de F23 (`documentacion/
F23_SALE_INVENTORY_CONTRACT.md`, `F23_FINAL_REPORT.md`,
`F23_VENTAS_BASELINE.md`, `F23_FACTURAS_BASELINE.md`) — no la duplica.
Esta fase valida y consolida lo ya construido, y añade lo que esos
documentos no cubrían (el flujo `Venta → Factura` en sí, más allá de
`Venta → Inventario`).

---

## 1. Modelos

### `Venta` (`apps/tenant/ventas/models.py:127`)

- **Estados propios** (`Venta.Estado`): `BORRADOR` / `FACTURADA_DIAN` /
  `ANULADA`. Enum independiente de `Factura.Estado` — no fusionados
  (confirma el principio de COMERCIAL-05 ya respetado hoy).
- **`factura_asociada`** — `OneToOneField(facturas.Factura,
  on_delete=SET_NULL, null=True, related_name="venta_origen")`. **Es una
  FK real, no una referencia soft UUID.** Esto es una excepción
  deliberada y documentada (`[OSF Fase F10]`, docstrings de
  `_construir_dto_factura`/`procesar_y_facturar_venta`) al patrón de
  soft-reference que domina el resto del proyecto (`cliente_uuid`,
  `proveedor_uuid`, `cotizacion_uuid`, `item_inventario_uuid`) — se
  eligió FK real aquí porque `Venta` es la dueña de la relación 1:1 con
  "su" factura, no una referencia many-to-something. Confirmado
  unidireccional: `Factura` **no tiene** campo `venta_uuid` ni ningún
  otro puntero de vuelta hacia `Venta` — la única forma de ir
  Factura→Venta es el accessor reverso de Django
  (`factura.venta_origen`), no un campo propio de `Factura`.
- Constraints reales a nivel de BD: `subtotal >= 0`, `total_neto >= 0`
  (`CheckConstraint`).

### `ItemVenta` (`apps/tenant/ventas/models.py:233`)

FK a `Producto`/`Servicio` de `inventario` (ambos nullable — un item
puede no tener ninguno). `save()` calcula `subtotal` automáticamente y
auto-asigna `empresa_id` desde `venta_id` si falta — mismo patrón usado
en `ItemFactura`/`ItemNotaCredito` (`apps/tenant/facturas/models.py`).

### `Factura` (`apps/tenant/facturas/models.py:20`)

- **Estados propios** (`Factura.Estado`): `BORRADOR` / `ENVIADA` /
  `ACEPTADA` / `RECHAZADA` / `ANULADA`. Enum DIAN, no de negocio comercial
  — confirma de nuevo que no hay fusión con `Venta.Estado`.
- `naturaleza` (`VENTA`/`COMPRA`) resuelto por `_resolver_naturaleza()`
  (emisor_nit == empresa.nit → VENTA) — campo compartido con el flujo de
  importación XML, no exclusivo del flujo `Venta→Factura`.
- `cliente_uuid` — soft reference, se puebla desde `dto.get("cliente_uuid")`
  en `crear_factura_desde_venta()`.

### `ItemFactura`

Sin cambios respecto a lo ya documentado (`COMPLETO_FLUJO_FACTURAS.md`).
No participa directamente del flujo `Venta→Factura`: **las líneas de la
`Factura` creada por `crear_factura_desde_venta()` no se generan como
`ItemFactura`** — el DTO trae `lineas[]` para construir el XML UBL, pero
`crear_factura_desde_venta()` (ver §3) no crea `ItemFactura` a partir de
esas líneas. Confirmado leyendo el método completo: solo persiste la
`Factura` (cabecera). Esto es una asimetría real frente al pipeline de
importación XML (`guardar_desde_dto()`), que sí crea `ItemFactura` por
cada `InvoiceLine` parseada.

---

## 2. `VentaBusinessService._construir_dto_factura()`

(`apps/tenant/ventas/services/business_service.py:218`)

Construye el DTO canónico UBL 2.1 completo (emisor/receptor/líneas/
totales/impuestos discriminados/config DIAN software/resolución) que
alimenta tanto el cálculo de CUFE como el builder XML como la creación de
`Factura`. **Un solo punto de construcción** — no hay una segunda función
que arme un DTO equivalente en otro lugar del proyecto (grep confirmado:
solo este método construye un dict con las claves `emisor`/`receptor`/
`totales`/`lineas` en ese formato exacto). `sede_id` viaja como dato
plano del DTO, nunca como FK — coherente con el resto de soft-references.

**Cálculo de impuestos:** se calcula aquí, línea por línea
(`sub_linea * pct_iva/100`), agregado por tasa en `impuestos_por_tasa`.
Es el **único** lugar del flujo `Venta→Factura` donde se calculan
impuestos — `Factura.impuestos` se puebla directamente desde
`totales.impuestos` de este DTO (§3), sin un segundo cálculo
independiente en `FacturaBusinessService`. Confirma la pregunta de
COMERCIAL-03 ("¿impuestos calculados de manera diferente?"): **no**, un
solo cálculo, una sola fuente.

---

## 3. `FacturaBusinessService.crear_factura_desde_venta()`

(`apps/tenant/facturas/services/business_service.py:61`)

- Genera un **número provisional** `BORR-VTA-{uuid8}` (deliberado,
  documentado en el docstring: "hasta que la DIAN asigne el número
  definitivo"). Coincide con el hallazgo ya documentado de FASE
  NÓMINA-02/`arquitectura_general.md` DOC-M40 (P1): **el número nunca se
  vuelve "definitivo" en la práctica porque no existe transmisión real a
  la DIAN en ningún punto del sistema** — toda `Factura` de este flujo
  queda con numeración provisional indefinidamente hasta que se
  implemente el transporte (ya identificado como bloqueador de
  infraestructura en NÓMINA-03).
- **Consecutivo:** `select_for_update()` sobre la fila `Empresa`
  (singleton por tenant) + `Max(consecutivo)` sobre
  `Factura.objects.filter(naturaleza=VENTA)` — serializa la asignación
  entre transacciones concurrentes sin bloquear toda la tabla `Factura`.
  Mismo patrón que `ResolucionDIAN` en `gastos`. Verificado como
  correcto: el lock es sobre la entidad contenedora (`Empresa`), no sobre
  filas de `Factura` que crecen sin límite.
- **DSV real en `sede`:** un `sede_id` del DTO que no pertenece a la
  empresa se degrada silenciosamente a `sede=None` en vez de fallar la
  creación de la Factura — decisión documentada explícitamente en el
  propio código como "dato de contexto secundario", no un campo crítico.
- **No crea `ItemFactura`** (ver §1) — solo la cabecera.
- **Sin idempotencia propia** — ver §6.

---

## 4. `VentaBusinessService.procesar_y_facturar_venta()`

(`apps/tenant/ventas/services/business_service.py:491`)

Orquestador completo: DSV → asignar consecutivo de venta → crear `Venta`
(BORRADOR) → `_construir_dto_factura()` → CUFE/XML/firma/AttachedDocument
→ `FacturaBusinessService.crear_factura_desde_venta()` → vincular Factura
+ estado `FACTURADA_DIAN` → `_generar_salida_inventario()` (F23). Todo
bajo un único `@transaction.atomic`.

**Atomicidad: correcta y verificada.** Los 3 bloques `except`
(`ValueError`, `DjangoValidationError`, `Exception`) llaman
`transaction.set_rollback(True)` antes de retornar `(False, ...)` — el
fix real documentado en `F23_FINAL_REPORT.md` §3 sigue intacto, no
regresionado. Confirmado leyendo el método completo, líneas 629-639.

---

## 5. Hallazgo nuevo: gemelo no auditado del bug de atomicidad de F23

`F23_FINAL_REPORT.md` §15 dejó como riesgo conocido, explícitamente no
auditado: *"si existen otros métodos `@transaction.atomic` con el mismo
patrón try/except-sin-reraise en otras apps, siguen teniendo el mismo
riesgo latente"*. Esta auditoría lo encontró **en el mismo archivo**:

**`VentaBusinessService.crear_venta_borrador()`**
(`apps/tenant/ventas/services/business_service.py:441`) — `@transaction.atomic`,
pero sus bloques `except ValueError`/`except Exception` **no llaman
`transaction.set_rollback(True)`** (a diferencia de su método hermano ya
corregido).

**¿Es explotable?** Sí, de forma acotada. `VentaCRUDService.crear_venta()`
(`apps/tenant/ventas/services/crud_service.py:21`) hace **dos escrituras
separadas**: `venta.save()` (línea 41) y luego
`ItemVenta.objects.bulk_create(items_a_crear)` (línea 67). Si el
`bulk_create` falla (constraint de BD, dato inconsistente que pasó DSV),
la excepción llega a `crear_venta_borrador()`, se captura, se retorna
`(False, {...}, 500)` — **pero el `venta.save()` ya ejecutado queda
comprometido a nivel de savepoint interno, y como el bloque exterior
nunca marca rollback, Django confirma (commit) esa escritura junto con el
resto de la transacción exterior cuando esta termine sin excepción sin
capturar.** Resultado: una `Venta` `BORRADOR` huérfana, sin items,
persistida en la base, mientras la API reporta error al cliente.

**Contraste con `anular_venta()`:** mismo patrón de wrapper
(`business_service.py:686`, sin `set_rollback`), pero **no es
explotable** — `VentaCRUDService.anular_venta()` hace una sola escritura
(`venta.save(update_fields=["estado"])`), sin ventana entre dos writes;
o se ejecuta completa o no se ejecuta nada antes de la excepción. Se
documenta la distinción para no sobre-reportar: mismo patrón de código,
riesgo real solo donde hay múltiples escrituras secuenciales sin límite
de transacción propio.

**No corregido en esta fase** (auditoría, "no modificar todavía") — queda
como hallazgo para la fase de implementación que el usuario decida.

---

## 6. Idempotencia — gap real, no un mecanismo existente sin usar

**No existe ninguna protección contra doble-envío** en
`procesar_y_facturar_venta()` ni en `crear_factura_desde_venta()`:

- `crear_factura_desde_venta()` **siempre** crea una `Factura` nueva y
  **siempre** avanza el consecutivo (§3) — no hay `get_or_create()` por
  ninguna clave natural (a diferencia de `guardar_desde_dto()`, que sí es
  idempotente por CUFE cuando importa XML).
- `VentaViewSet`/`api_mixins.py::service_procesar_y_facturar_venta()`
  (`apps/tenant/ventas/services/api_mixins.py:43`) pasa el payload
  directo al business service sin ninguna capa de deduplicación HTTP
  (sin `Idempotency-Key`, sin ventana de tiempo, sin hash de payload).
- El único patrón de idempotencia real que existe hoy en el proyecto
  (`clientes`/`proveedores`, `test_idempotence_v2614.py`) es
  `update_or_create()` sobre una clave de negocio natural (NIT) — **no
  aplica directamente a `Venta`**, que no tiene un campo natural
  equivalente para deduplicar por sí sola.

**Consecuencia concreta:** un doble-click en "Procesar y Facturar", o un
reintento de red tras un timeout del lado del cliente (aunque el servidor
sí haya completado la operación), crea **dos `Venta` + dos `Factura`
completas e independientes**, cada una con su propio consecutivo DIAN
real consumido — no un registro duplicado inofensivo, sino dos documentos
fiscales distintos por una sola intención de negocio. Este es exactamente
el problema que FASE COMERCIAL-04 debe resolver; se documenta aquí como
diagnóstico verificado con evidencia de código, no como suposición.

---

## 7. Referencias UUID — resumen

| Relación | Mecanismo | Nota |
|---|---|---|
| `Venta.cliente` | FK real (`clientes.Cliente`) | Dentro del mismo bounded context comercial, no cruza a `facturas` |
| `Venta → Factura` | **FK real** (`factura_asociada`, OneToOne) | Única excepción documentada al patrón soft-UUID del resto del proyecto |
| `Factura ← Venta` (reverso) | Accessor Django (`venta_origen`) | Sin campo propio `venta_uuid` en `Factura` |
| DTO `cliente_uuid`/`venta_uuid`/`sede_id` | Dato plano en dict | Nunca persistidos como FK — `cliente_uuid` sí se guarda en `Factura.cliente_uuid` (soft), `venta_uuid` no se guarda en ningún lado de `Factura` |
| `ItemVenta.producto`/`.servicio` | FK real (`inventario`) | Igual patrón que `ItemFactura`/`ItemNotaCredito` |

---

## 8. Conclusión de esta fase

Ningún cambio de código en esta pasada, por instrucción explícita. Cuatro
hallazgos reales, verificados con evidencia de código, listos para las
fases siguientes del plan:

1. **DTO/cálculo de impuestos:** un solo punto de construcción y cálculo,
   sin duplicación — COMERCIAL-03 puede formalizar el contrato ya
   existente, no reconstruirlo.
2. **Estados:** ya separados correctamente (`Venta.Estado` ≠
   `Factura.Estado`) — COMERCIAL-05 es una tarea de documentar la matriz
   de transiciones cruzadas ya implícita en el código, no de re-diseñar
   nada.
3. **Atomicidad:** el fix de F23 en `procesar_y_facturar_venta()` sigue
   vigente; se encontró un gemelo real no corregido en
   `crear_venta_borrador()` (§5) — candidato concreto para
   COMERCIAL-01→implementación o una fase dedicada, pendiente de decisión
   del usuario sobre cuándo corregirlo.
4. **Idempotencia:** gap real confirmado, no un mecanismo ya construido
   sin adoptar — es trabajo genuino de diseño para COMERCIAL-04, no una
   simple migración a un patrón existente.

Y una asimetría arquitectónica documentada (no un bug): `Venta` sostiene
una FK real hacia `Factura` (única excepción al patrón soft-UUID del
proyecto), y `crear_factura_desde_venta()` no genera `ItemFactura` —
relevante para COMERCIAL-02 (matriz SSoT) al definir qué app es dueña de
qué dato exactamente.
