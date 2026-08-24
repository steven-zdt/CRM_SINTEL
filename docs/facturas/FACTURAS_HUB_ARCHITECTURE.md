# Facturas Hub — Arquitectura (FASE 36)

**Fecha:** 2026-08-24. **Estado:** `FACTURAS_HUB = COMPLETED_WITH_DEFERRED`
(ver checklist FASE 39 al final). Complementa `FACTURAS_HUB_BASELINE.md`
(FASE 0, auditoría) — documenta el estado final, no repite la evidencia
ya citada ahí.

---

## 1. Facturas = motor receptor, no dueño de todo

```
Ventas       = dueño de la operación comercial de venta
Compras      = dueño de la operación de compra
Inventario   = dueño del stock y Kardex
Clientes     = dueño del tercero cliente
Proveedores  = dueño del tercero proveedor
Bancos       = dueño de conciliaciones y pagos
Contabilidad = dueño de la contabilización
Facturas     = dueño del DOCUMENTO FISCAL — punto de entrada, no dueño
               de lo que ese documento dispara en otras apps
```

Matriz de propiedad de datos, ya construida con evidencia real en
`docs/comercial/COMERCIAL_02_MATRIZ_SSOT.md` (misión Ciclo Comercial,
misma sesión) — sigue vigente sin cambios: Inventario con puerta única
(`KardexService`), Bancos híbrido push+pull, Contabilidad Pull puro
confirmado por grep. No se duplica aquí; se referencia como la fuente
única.

**Dato → dueño (ejemplos del enunciado, confirmados):**

| Dato | Dueño | Evidencia |
|---|---|---|
| CUFE | `Factura.cufe` | `FACTURAS_HUB_BASELINE.md` §3 |
| Cliente fiscal | `Cliente` (`resolver_o_crear_desde_factura_venta`) | `FACTURAS_HUB_BASELINE.md` §6 |
| Proveedor fiscal | `Proveedor` (`resolver_o_crear_desde_factura_compra`) | `FACTURAS_HUB_BASELINE.md` §6 |
| Stock | `MovimientoInventario` | `COMERCIAL_02_MATRIZ_SSOT.md` §3 |
| Conciliación | `TransaccionBancaria` | `COMERCIAL_02_MATRIZ_SSOT.md` §4 |
| Asiento | `AsientoContable` | `COMERCIAL_02_MATRIZ_SSOT.md` §5 |

`Factura` **referencia** cliente/proveedor por UUID soft (`cliente_uuid`/
`proveedor_uuid`), nunca copia permanentemente su información salvo el
snapshot fiscal inmutable (`emisor_*`/`receptor_*`, requerido porque el
XML firmado es un documento histórico — el tercero puede cambiar de
razón social después, la factura no debe mentir sobre lo que decía el
XML original).

---

## 2. Flujo interno vs. externo — separados, sin forzar equivalencia

```
VENTA INTERNA:                        VENTA/COMPRA EXTERNA:
Venta SINTIA                          XML externo
   ↓                                     ↓
Factura (origen=INTERNO)              Facturas (guardar_desde_dto,
   ↓                                     origen=EXTERNO)
Bancos                                   ↓
   ↓                                  Cliente/Proveedor (auto-resuelto)
Contabilidad                             ↓
                                       opcional: Compra (acción explícita,
                                       ver §4) / Venta (no automática)
```

`origen` (FASE 7, nuevo campo `Factura.Origen`: `INTERNO`/`EXTERNO`) y
`source_system` (FASE 8, `Factura.SourceSystem`: `SINTEL`/`SIIGO`/
`OTRO_FACTURADOR`/`MANUAL`/`DESCONOCIDO`) son los **únicos** campos
nuevos de esta misión — ambos en `XML_IMMUTABLE_FIELDS` (no editables
manualmente), poblados en los dos únicos puntos de creación de `Factura`:

- `crear_factura_desde_venta()` → siempre `INTERNO`/`SINTEL` (push real
  desde Ventas, nunca pasa por `guardar_desde_dto()`).
- `guardar_desde_dto()` → siempre `EXTERNO`; `source_system` solo si el
  DTO lo declara explícitamente (`dto.get("source_system")`), default
  `DESCONOCIDO` — **nunca inferido del contenido del XML** (instrucción
  explícita de la misión: "no asumir que todo XML proviene de SIIGO").
  `source_system` es puramente informativo/trazabilidad, nunca una regla
  fiscal (no condiciona `_resolver_naturaleza()` ni ninguna validación).

Backfill real para datos existentes (migración `0037`, no especulativo):
toda `Factura` con una `Venta.factura_asociada` real apuntando a ella se
retro-marcó `INTERNO`/`SINTEL` — la señal es la relación ya existente en
la base, no una suposición.

---

## 3. Vinculación cliente/proveedor — automática, ya robusta

Contrario a lo que el enunciado de la misión anticipaba (estado
`CLIENTE_NO_VINCULADO`/`PROVEEDOR_NO_VINCULADO` con acciones manuales),
el código real **resuelve-o-crea automáticamente** en cada importación
exitosa — nunca deja un documento fiscal huérfano de tercero. Documentado
con evidencia completa en `FACTURAS_HUB_BASELINE.md` §6. No se introdujo
el estado manual: haría el sistema **menos** robusto (introduciría un
estado "a medias" donde hoy no existe ninguno), contradiciendo la regla
de la misión de no crear un segundo sistema equivalente.

---

## 4. Compra/Venta/Inventario — no automáticos desde una Factura externa

Confirmado sin necesidad de cambios (ya era el comportamiento real,
verificado): `guardar_desde_dto()` **nunca** crea una `Compra`, `Venta`,
ni `MovimientoInventario` — solo persiste el documento fiscal y vincula
el tercero. La creación de una operación comercial a partir de una
factura externa (FASE 15/16 de la misión: "Registrar compra"/"Crear
operación comercial") sigue siendo, hoy, una **acción explícita separada**
que el usuario debe iniciar desde `Compras`/`Ventas` — no existe un botón
"Convertir en compra/venta" implementado, y esta fase **no lo construye**
tampoco: el enunciado pide diseñar el flujo IF y solo si existe evidencia
de necesidad real, y no se encontró un caso de uso pendiente o UI a medio
construir para eso — construirlo ahora sería especular sobre un flujo no
solicitado con datos concretos. Documentado como brecha consciente para
una fase de UI/producto futura, no un olvido.

---

## 5. Idempotencia — sin cambios, ya sólida

`FACTURAS_HUB_BASELINE.md` §3, sin repetir aquí. CUFE como ancla primaria,
fallback real por número (nunca una identidad inventada), pre-validación
rápida por regex antes del parsing completo.

---

## 6. Errores / batch / preview — sin cambios, ya cumple la misión

`FACTURAS_HUB_BASELINE.md` §11. Un archivo inválido no aborta el lote,
`preview=true` disponible en los 3 endpoints de upload.

---

## 7. Duplicación encontrada, no corregida en esta fase (riesgo bajo)

`services_mail_ingestion.py::preview_mail_ingestion()` reimplementa una
variante de la regla de naturaleza para su mensaje de preview
(`FACTURAS_HUB_BASELINE.md` §2). Es preview-only (nunca persiste) — se
documenta como deuda técnica real, no se toca en esta misión porque
requeriría auditar a fondo todo el subsistema de ingesta por correo
(fuera del alcance declarado: "no crear otro importador paralelo" implica
también no tocar el existente sin necesidad).

---

## 8. UX del Hub (FASE 25-27) — no implementada en esta fase

El enunciado pide una pantalla "centro de recepción documental"
(Importar/Ver venta/Ver compra/Pendientes de revisión). **No se construyó
UI en esta fase**: los datos que la UI necesitaría mostrar (`origen`,
`source_system`, filtros por ambos) ya quedan disponibles vía API
(§2, FASE 26 — agregados a `filterset_fields`), pero construir las
pantallas es trabajo de frontend no solicitado con la misma urgencia que
el resto de la misión (que es explícitamente sobre el motor, no sobre la
UI, según su propio título "MOTOR CENTRAL DE RECEPCIÓN"). Queda como
trabajo pendiente explícito, no oculto.

---

## 9. Estado separados — ya cumplía, confirmado

```
naturaleza  = VENTA | COMPRA           (Factura.naturaleza)
origen      = INTERNO | EXTERNO        (Factura.origen, NUEVO)
fiscal      = BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ERROR_TRANSMISION/ANULADA
                                        (Factura.estado, ver docs/fiscal/FISCAL_03_ESTADOS.md)
pago        = NO_PAGADA/PAGO_PARCIAL/PAGADA
                                        (Factura.estado_pago, Pull Model Bancos)
contable    = derivado, vía Extractor  (Contabilidad, Pull Model — Factura no lo persiste)
```

Cinco conceptos, cinco campos/mecanismos separados, ninguno mezclado —
confirma FASE 19 sin cambios necesarios más allá del campo `origen` ya
cubierto en §2.

---

## 10. Estado formal — FASE 39 (Release Gate)

```
[x] importación existente confirmada       -- FACTURAS_HUB_BASELINE.md §1
[x] XML parsing estable                    -- único punto: guardar_desde_dto()
[x] preview                                -- disponible en 3 endpoints
[x] VENTA automática                       -- _resolver_naturaleza(), confirmado
[x] COMPRA automática                      -- idem + Cascading Security
[x] CUFE idempotente                       -- confirmado, con fallback por numero
[x] cliente vinculado                      -- resolver_o_crear, MÁS robusto que lo pedido
[x] proveedor vinculado                    -- idem
[x] batch                                  -- _upload_ubl_batch(), ya robusto
[x] errores aislados                       -- 1 archivo invalido no aborta el lote
[x] tenant isolation                       -- IDOR fixes confirmados (v2.61.5)
[x] sede contextual                        -- MANUAL_EDITABLE_FIELDS, DSV+alcance (F11)
[x] origen documentado                     -- NUEVO: Factura.origen/source_system
[~] Venta integrada                        -- push interno funciona; "convertir externa
                                               en venta" NO implementado (§4, consciente)
[~] Compra integrada                       -- idem, "registrar compra" NO implementado
[ ] Inventario integrado (desde Factura)   -- fuera de alcance, correcto por diseño (§4)
[x] Bancos integrado                       -- Pull Model confirmado, ya auditado
[x] Contabilidad integrada                 -- Pull Model confirmado, ya auditado
[ ] UX diferenciada                        -- no construida en esta fase (§8)
[x] trazabilidad                           -- TransmisionFactura (ciclo fiscal) +
                                               logging estructurado ya existente
[x] sin duplicación de importadores        -- confirmado, un solo pipeline
[x] documentación actualizada              -- este documento + BASELINE
[x] governance PASS                        -- manage.py check + makemigrations --check
```

**`FACTURAS_HUB = COMPLETED_WITH_DEFERRED`** — el motor central
(recepción, normalización, clasificación, idempotencia, trazabilidad,
integración fiscal) está completo y verificado. Lo diferido (§4, §8) es
trabajo de UI/producto que requiere una decisión de negocio explícita
("¿debe existir un botón 'convertir en compra'?") que esta auditoría no
inventa sin evidencia — documentado con precisión de qué falta y por qué,
no como una casilla vacía sin explicación.
