# VENTAS_COMPRAS_FACTURAS_FLOW — flujo real vs flujo objetivo

Mision VENTAS-COMPRAS-FACTURAS-01 (2026-09-09). Ver `VENTAS_COMPRAS_FACTURAS_DEPENDENCIES.md`
para la matriz completa de dependencias y `VENTAS_COMPRAS_FACTURAS_RELEASE_GATE.md`
para el veredicto y los tests.

## Regla de negocio objetivo (dictada por esta mision)

SINTEL todavia NO esta autorizada por la DIAN para crear/emitir/transmitir
Facturas electronicas. `facturas` es el receptor y dueño fiscal exclusivo
de documentos XML **generados externamente** (por un proveedor
tecnologico habilitado por la DIAN distinto de SINTEL) y cargados/
procesados dentro de SINTEL. `ventas` y `compras` CONSUMEN esa
informacion para sus propios procesos operativos -- nunca la crean.

## Flujo real encontrado (ANTES de esta mision)

```
                          ┌─────────────────────┐
                          │   VENTAS             │
                          │ procesar_y_facturar_  │
                          │ venta()               │
                          │  1. DTO DIAN completo │
                          │  2. CUFE real         │
                          │  3. XML UBL 2.1 real  │
                          │  4. Firma XAdES-EPES  │
                          └──────────┬────────────┘
                                     │ crea (PUSH)
                                     ▼
                          ┌─────────────────────┐
              XML externo │                     │
             ────────────►│      FACTURAS       │
           (guardar_desde_│  (dueño fiscal, OK)  │
              dto(), OK)  └─────────────────────┘

                          ┌─────────────────────┐
                          │      COMPRAS         │
                          │ (sin relacion alguna  │
                          │  con Facturas)        │
                          └─────────────────────┘
```

**Dos caminos de entrada a `Factura` coexistian:** (1) el correcto, XML
externo → `guardar_desde_dto()` (Fase 3 de la mision, ya funcionaba
bien); (2) el prohibido, `Ventas` generando su propio DTO/CUFE/XML/firma
y empujandolo a `Factura` como si fuera un documento externo mas. Ambos
escribian en el mismo modelo `Factura` sin que el modelo pudiera
distinguir cual vino de verdad de la DIAN.

`Compras` nunca tuvo ninguna relacion con `Facturas` (confirmado por
auditoria completa, `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md`,
sin ninguna mencion real de `Factura` en 405 lineas de documentacion
exhaustiva) -- ya cumplia la regla objetivo sin necesidad de cambios.

## Flujo objetivo (post-mision)

```
             ┌─────────────────────┐
 XML externo │                     │
────────────►│      FACTURAS       │
             │  fiscal source/SSOT │
             └──────────┬──────────┘
                        │
                  READ / CONSUME (DEFERRED -- Fase 9,
                  falta la decision de negocio exacta)
                 ┌──────┴──────┐
                 ▼             ▼
             VENTAS         COMPRAS
                 │             │
            (X bloqueado)  (ya cumplia)
                 ▼             ▼
             INVENTARIO     INVENTARIO
                 │             │
                 └──────┬──────┘
                        ▼
                  CONTABILIDAD
```

## Que se implemento en esta mision (evidencia real)

**Fase 8 -- barrera de emision fiscal: IMPLEMENTADO.**
`VentaBusinessService.procesar_y_facturar_venta()`
(`apps/tenant/ventas/services/business_service.py`) rechaza con `403` +
mensaje de dominio claro ANTES de cualquier escritura (DSV, consecutivo,
Venta, DTO, CUFE, XML, firma) cuando `EMISION_FISCAL_VENTA_AUTORIZADA`
(constante de codigo, no env var -- reactivarla exige un cambio de codigo
revisado, no un toggle de entorno) esta en `False` (su valor por
defecto). El codigo DIAN completo (`_construir_dto_factura`, CUFE,
`UBL21BuilderService`, `XadesSignerService`) **no se elimino** -- sigue
presente, simplemente inalcanzable. `CotizacionService.
facturar_venta_de_cotizacion()` hereda el bloqueo automaticamente porque
reutiliza el mismo metodo (`venta_existente=venta`), sin necesitar un
segundo guard.

La UNICA excepcion al bloqueo: una `Venta` que YA estaba `FACTURADA_DIAN`
(dato historico, o facturada en un entorno con el flag en `True`) sigue
pudiendo consultarse de forma idempotente -- es lectura pura, no crea
nada nuevo, y por eso no viola la regla.

## DEFERRED (Fase 9) -- que falta y por que no se inventa

**No se implemento un mecanismo automatico "Factura VENTA externa →
crea/actualiza Venta" ni "Factura COMPRA externa → crea/actualiza
Compra/Recepcion".** Motivo (mandato explicito de la mision, §15: "no
inventar una regla que diga que toda factura automaticamente crea
recepcion fisica"): no existe evidencia de la regla de negocio exacta
que el usuario quiere. Preguntas reales sin responder que bloquean
implementar esto sin inventar:

1. **Matching**: ¿como se asocia una `Factura` de VENTA externa recien
   cargada con una `Venta` existente en SINTEL (o se crea una `Venta`
   nueva a partir de ella)? ¿Por `numero`? ¿Manualmente desde la UI?
   ¿Automatico solo si el `cliente_uuid` coincide?
2. **Compras**: dado que `OrdenCompra`/`RecepcionCompra` hoy NO tienen
   ningun campo para vincular una Factura, ¿la asociacion es 1:1 con una
   `OrdenCompra` existente, o una Factura de COMPRA puede llegar sin
   Orden de Compra previa (compra menor, gasto directo)? El modulo
   `gastos` (`DocumentoSoporte`) ya cubre un flujo similar -- ¿debe
   Compras reusar ese patron en vez de inventar uno nuevo?
3. **Idempotencia del lado de consumo**: si la misma Factura se
   "consume" dos veces desde la UI, ¿que pasa? (Fase 10 de la mision
   pide esto probado, pero no hay implementacion de la que partir).

Documentar esto como DEFERRED (no como FAIL) es la accion correcta segun
el propio mandato de la mision: "Cuando falte una regla: DEFERRED y
documentar que decision se necesita" (§9 Compras) y "no corregir una
dependencia unicamente porque 'parece fea'" (§7). Implementar un
mecanismo de matching inventado arriesgaria construir la logica de
negocio equivocada dos veces.

## Hallazgo secundario (no bloqueante, documentado)

`Venta.factura_asociada` es un `OneToOneField` **directo** a
`facturas.Factura` (`apps/tenant/ventas/models.py:174-181`), a
diferencia del patron "Bounded Context §18" que el resto del sistema usa
consistentemente para referencias entre `facturas` y otras apps
(`cliente_uuid`, `proveedor_uuid`, `cotizacion_uuid` -- todos
`UUIDField` sin FK). Esto es una inconsistencia arquitectonica real,
pero **no se corrige en esta mision**: no hay evidencia de que cause un
problema real hoy (es `SET_NULL`, no genera acoplamiento circular de
imports ya que `ventas` sigue sin importar modelos de `facturas`
directamente en el codigo Python, solo en la migracion), y convertirlo a
soft-reference seria un cambio de esquema con riesgo de datos que el
mandato de la mision (§15, "nunca romper datos existentes") no justifica
sin evidencia de que sea necesario.
