# Business Dependency Graph — SINTEL ERP

**Fecha:** 2026-08-26
**Misión:** REL-01..REL-10 (auditoría del grafo de dependencias de negocio, complementaria al grafo técnico de imports)
**Metodología:** 4 sub-auditorías paralelas (una por ciclo de negocio), cada una leyendo `models.py`/`services/*.py` reales de las apps involucradas, citando evidencia archivo:línea. Cero relaciones inventadas — todo lo marcado como "sin evidencia" queda explícito como tal en `CROSS_APP_FINDINGS.md`.

---

## 1. Grafo técnico (línea base) vs. grafo de negocio

`tools/organizational_governance/dependencies.py` (AST-based, ve imports Python reales) corrido en vivo el 2026-08-26:

| Métrica | Valor medido |
|---|---|
| Aristas totales | 354 |
| Clasificación | ALLOWED 158, CONTROLLED 126, PUSH_CONTROLLED 40, PULL 15, UNKNOWN 15 |
| FORBIDDEN | 0 |
| Ciclos detectados | 8 |

Los 8 ciclos técnicos:

```
1. empresa <-> perfil
2. bancos -> clientes -> facturas -> bancos
3. clientes -> facturas -> clientes
4. clientes -> facturas -> contabilidad -> clientes
5. facturas -> contabilidad -> facturas
6. contabilidad -> gastos -> contabilidad
7. facturas -> contabilidad -> gastos -> proveedores -> facturas
8. clientes -> facturas -> cotizaciones -> clientes
```

**Principio central de esta auditoría:** el grafo técnico ve *que* A importa algo de B. No ve *por qué* (FK real vs. soft-reference vs. llamada de servicio Pull vs. Push), ni el *estado* del documento que activa la relación, ni si la relación es *obligatoria* u *opcional* para el negocio. Ese es el contenido que agregan las secciones siguientes y los otros 5 documentos.

Los 354 registros crudos quedan en `docs/integration/_raw_technical_edges.csv` (working file, no es un entregable final — referencia de auditoría).

---

## 2. Grafo de negocio — Ciclo de Venta

```
                    CLIENTE
                       |
                       v
                  COTIZACION (opcional, sin automatizacion real Cotizacion->Venta)
                       |
                       v
                     VENTA -------------------- PROYECTO (contexto, opcional,
                ┌──────┼──────┐                  de solo-escritura hoy: nadie
                v      v      v                  en Proyectos lee Venta.proyecto)
             FACTURA  STOCK  (proyecto)
                │      │
          ┌─────┼──────┘
          v     v
       BANCOS KARDEX
          │     │
          │     v
          │  CONTABILIDAD (via ExtractorInventario -- PERO el Celery task real
          │     ^            NO lo incluye hoy, ver CROSS_APP_FINDINGS CRITICAL-1)
          └─────┘
        (push condicional a Factura.estado_pago, solo si medio_pago != Efectivo)
```

**Owner por nodo:** Cliente=`clientes`, Cotización=`cotizaciones` (catálogo de producto/servicio PROPIO, no comparte tabla con `inventario`), Venta=`ventas`, Factura=`facturas`, Stock/Kardex=`inventario`, Bancos=`bancos`, Contabilidad=`contabilidad`, Proyecto=`proyectos`.

**Transacción atómica real:** `Venta → Factura → Salida de Inventario` ocurre en una SOLA transacción (`VentaBusinessService.procesar_y_facturar_venta()`, `apps/tenant/ventas/services/business_service.py:441-674`). Un fallo en cualquier paso (incluido stock insuficiente) revierte los tres efectos juntos.

---

## 3. Grafo de negocio — Ciclo de Compra

```
                   PROVEEDOR
                       |
                       v
                 ORDEN COMPRA --APROBADA--> CUENTAS POR PAGAR (proveedores)
                       |                         ^ (v3.18.0, hoy mismo)
                       v                         |
                   RECEPCION                 (sin bridge a BANCOS -- CRITICAL)
                       |
                 ┌─────┴─────┐
                 v           v
             INVENTARIO     GASTO (DocumentoSoporte)
                 │           │
                 │           ├──> RETENCIONES (contabilidad, push directo)
                 │           │
                 └─────┬─────┘
                       v
                 FACTURA COMPRA (via XML DIAN -- flujo INDEPENDIENTE de OrdenCompra,
                       │          nunca se cruzan: 0 Facturas COMPRA en tenant `home`
                 ┌─────┼─────┐    hoy tenian OrdenCompra real)
                 v     v     v
              IMPUESTO BANCOS CONTAB.
           (Retenciones) (push a      (pull, ExtractorFacturas/
                          estado_pago) ExtractorGastos/ExtractorInventario)
```

**Owner por nodo:** Proveedor=`proveedores`, OrdenCompra/Recepción=`compras`, Inventario=`inventario`, Gasto=`gastos`, FacturaCompra=`facturas`, CuentasPagar=`proveedores`, Bancos=`bancos`, Contabilidad=`contabilidad`.

**Hallazgo estructural clave (ver `CROSS_APP_FINDINGS.md` para detalle):** este ciclo tiene **tres cadenas paralelas y parcialmente desconectadas** para "cómo se origina una obligación de pago a un proveedor":
1. `OrdenCompra --APROBADA--> CuentasPagar(orden_compra_uuid)` — nueva (hoy), nunca pasa por Factura.
2. `Factura(naturaleza=COMPRA) --estado_pago-->` leída directo por `CuentasPagarSelector`, sin crear necesariamente una fila `CuentasPagar`.
3. `DocumentoSoporte (Gasto)` — nunca crea `CuentasPagar` en absoluto; termina en Contabilidad, no en Pago (ver ciclo de Gasto).
Bancos concilia **solo** contra `Factura.factura_uuid` — ninguna de las 3 cadenas basadas en `CuentasPagar`/`DocumentoSoporte` tiene bridge automático a conciliación bancaria.

---

## 4. Grafo de negocio — Ciclo de Gasto

```
              PROVEEDOR
                  |
                  v
          DOCUMENTO SOPORTE  (modelo real -- "Gasto" como tabla separada
                  |            ya NO existe, absorbido en migracion 0010)
        ┌─────────┼─────────┐
        v         v         v
  RETENCIONES  CONTABILIDAD  (movimiento_inventario_uuid,
  (push directo (pull batch,   soft-ref, opcional, sin uso
   sincrono al   ExtractorGastos)  real en el asiento contable)
   crear)            |
        └──────┬─────┘
               v
         AsientoContable
               |
               X  <-- EL CICLO SE CORTA AQUI. No existe DocumentoSoporte -> CuentasPagar
                       ni DocumentoSoporte -> TransaccionBancaria. "...-> Pago" del
                       enunciado de la mision NO esta implementado (CRITICAL).
```

**Owner por nodo:** Proveedor=`proveedores`, DocumentoSoporte=`gastos`, Retenciones/Contabilidad=`contabilidad`.

---

## 5. Grafo de negocio — Ciclo de Nómina

```
   EMPLEADO --> CONTRATO --> DEVENGO <-- PERIODO NOMINA
                                |         (ABIERTO -> PRELIQUIDADO -> EN_REVISION
                                |          -> APROBADO -> PAGADO -> CERRADO)
                                v
                          CONTABILIDAD (pull real, ExtractorNomina -- SI funciona,
                                |        import ORM directo, unidireccional, no circular)
                                v
                              BANCOS
                                X  <-- NO EXISTE. marcar_pagado() es registro manual,
                                        documentado como tal en 3 lugares del propio codigo.
```

**Owner por nodo:** Empleado/Contrato/Devengo/PeriodoNomina=`empleados`, Contabilidad=`contabilidad`.

**Nota:** ninguno de los 8 ciclos técnicos detectados involucra `empleados` — confirmado que la integración real con Contabilidad existe (no es hipótesis), simplemente no es circular.

---

## 6. REL-09 — Auditoría de dependencias circulares de NEGOCIO (no solo imports)

Se investigaron los 2 ciclos técnicos que caen dentro de los 4 ciclos de negocio auditados:

### 6.1 `contabilidad -> gastos -> contabilidad`

**Veredicto: artefacto del grafo de imports, NO circularidad de negocio real.** Son dos flujos unidireccionales distintos con objetos de datos distintos:
- `contabilidad -> gastos` (Pull, solo lectura): `ExtractorGastos` lee `DocumentoSoporte` para construir asientos.
- `gastos -> contabilidad` (Push de servicio + Pull de lectura): `GastoBusinessService.procesar_gasto()` invoca `RetencionesService.crear_retencion()` (Contabilidad escribe su propia tabla `Retencion`, Gastos solo dispara la llamada); y `DocumentoSoporte` lee `Retencion` vía import perezoso (`apps.get_model`, comentario explícito en `gastos/models.py:268`: *"para evitar importacion circular"* — el equipo ya era consciente y lo mitigó).

No hay una cadena de llamadas que vuelva sobre sí misma en tiempo de ejecución. Exactamente el patrón de ADR-001 (Pull Model), correctamente aplicado. **No requiere rediseño de contrato.**

### 6.2 `facturas -> contabilidad -> gastos -> proveedores -> facturas`

**Veredicto: artefacto del grafo de imports, NO circularidad de negocio real.** Las 4 aristas verificadas:
1. `facturas -> contabilidad`: `Factura.total_retencion_fuente` (property) hace Pull read-only vía `RetencionesService`, degrada a `Decimal('0.00')` en `except`.
2. `contabilidad -> gastos`: `ExtractorGastos` Pull read-only.
3. `gastos -> proveedores`: `DocumentoSoporte.proveedor` es FK real **obligatoria** — relación estructural, no depende de que el resto del ciclo exista.
4. `proveedores -> facturas`: `CuentasPagarSelector` Pull read-only para listados/agregación.

Ninguna arista requiere que el ciclo completo se resuelva para funcionar; 3 de 4 son Pull con degradación segura. **Hallazgo adicional (no en la lista original de 8):** existe también `gastos -> contabilidad` de tipo Push (mismo mecanismo que 6.1), formando un sub-ciclo de 2 nodos `contabilidad <-> gastos` más ajustado — tampoco es circularidad problemática, mismo razonamiento que 6.1.

### 6.3 Conclusión REL-09

**Ninguno de los 8 ciclos técnicos detectados representa una dependencia circular de negocio real (A necesita que B necesita que C necesite que A se resuelva primero).** Todos son artefactos de que el analizador AST clasifica por *dirección de import*, no por *dirección de dato*. No se requiere ningún rediseño de contrato ni eliminación de import dinámico — los imports perezosos ya presentes (`apps.get_model`, imports dentro de método) son la mitigación correcta y ya están aplicados donde hacía falta.

---

## 7. Ciclos de negocio NO cubiertos por los 4 sub-agentes (fuera de alcance de esta pasada)

- `empresa <-> perfil`: ciclo de infraestructura (identidad/tenant), no un proceso de negocio transaccional — no se auditó en esta pasada por ser cross-cutting, no específico de un ciclo contable.
- Cotizaciones→Ventas y Bancos↔Clientes↔Facturas quedaron cubiertos parcialmente dentro del ciclo de Venta (ver `CROSS_APP_FINDINGS.md` §Venta).

---

## 8. Índice de documentos de esta auditoría

| Documento | Contenido |
|---|---|
| `BUSINESS_DEPENDENCY_GRAPH.md` (este) | Grafo consolidado + REL-09 |
| `CROSS_APP_RELATION_MATRIX.md` | REL-02: matriz completa Origen/Destino/Relación/Obligación/Dirección/SSoT |
| `BUSINESS_PROCESS_LIFECYCLE.md` | REL-04/REL-05: estados de activación + mapas de procesos derivados/dependientes/posteriores |
| `ACCOUNTING_LIFECYCLE.md` | REL-10: validación del ciclo contable completo por proceso (Venta/Compra/Gasto/Nómina) |
| `CROSS_APP_CONTRACTS.md` | REL-08: contratos Consumer/Provider/Input/Output/Trigger/State/Idempotency/Rollback/Error/SSoT |
| `CROSS_APP_FINDINGS.md` | REL-03/REL-06/REL-07: cardinalidades, relaciones faltantes e incorrectas, clasificadas |
