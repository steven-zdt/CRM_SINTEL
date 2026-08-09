# Matriz de Obligatoriedad Organizacional (F16.8)

**Fecha:** 2026-08-09
**Fuente:** reconstruida a partir del análisis real de negocio ya hecho en FASE 5 de la
consolidación OCF/OSF (`documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md` §1) — verificado contra
código real (grep de campos `sede`/`area` en cada `models.py`), no inventada de nuevo.

| Entidad | Empresa | Sede | Área | Estado real (código) |
|---|---|---|---|---|
| `OrdenCompra` (compras) | Obligatoria | **Obligatoria** (NOT NULL, `SedeAwareModel`) | Opcional | 🟢 Implementado — único caso con `sede` endurecida |
| `Factura` | Obligatoria | Según operación (campo existe, nullable, filtrado null-safe) | No (sin campo) | 🟡 Parcial — lectura scope-aware, sin endurecer |
| `Cotizacion` | Obligatoria | Según operación (campo existe, nullable) | No | 🟡 Parcial |
| `DocumentoSoporte` (gastos) | Obligatoria | Según origen (campo existe, nullable) | No | 🟡 Parcial |
| `MovimientoInventario` | Obligatoria | Según proceso (campo existe, nullable) | No | 🟡 Parcial |
| `Proyecto` | Obligatoria | Según ejecución (campo existe, nullable) | No | 🟡 Parcial |
| `Empleado` | Obligatoria | Según asignación (campo existe, nullable) | Según asignación (**único** con campo `area` propio, además de `sede`) | 🟡 Parcial |
| `Venta` | Obligatoria | No necesariamente — sin campo propio, resuelto por contexto del usuario al facturar | N/A | 🟢 Completo por diseño (ADR-005, decisión confirmada con el usuario) |
| `Producto`/`Servicio` (inventario) | Obligatoria | No necesariamente | No | 🔴 Sin campo — no priorizado (candidato plausible sin caso de uso confirmado, `ORGANIZATIONAL_SCOPE_MATRIX.md`) |
| `Cliente` | Obligatoria | **No** | No | ⚪ Explícitamente NO recomendado — "un cliente no está atado a una sede del vendedor" |
| `Proveedor` | Obligatoria | No (campo no existe) | No | 🔴 Candidato débil — podría heredar sede de la `OrdenCompra` de origen en vez de campo propio, no implementado |
| `CuentaBancaria`/`TransaccionBancaria` | Obligatoria | No (campo no existe; `TransaccionBancaria.sucursal` es texto libre, no FK) | No | 🔴 Candidato plausible, no implementado |
| `AsientoContable`/`MovimientoContable` | Obligatoria | No (campo no existe) | No | 🔴 Candidato parcial — solo estos 2 modelos, nunca el catálogo de cuentas ni períodos fiscales (por diseño contable) |
| `CuentaContable`/`PeriodoContable` | Obligatoria | **Explícitamente NO** (de empresa completa por diseño contable) | No | ⚪ NO aplica — decisión de dominio, no pendiente |
| `SnapshotMetricaDiaria` (dashboard) | Obligatoria | No (agregado de solo lectura) | No | ⚪ NO aplica tal como está diseñado — requeriría rediseño del modelo de snapshot |

## Regla de lectura de esta tabla

🟢 = implementado y suficiente para el caso de uso conocido. 🟡 = campo existe, filtrado de lectura
activo (`filter_by_scope_null_safe`), sin endurecer a `NOT NULL`/`SedeAwareModel` — decisión
deliberada (ADR-005), no una tarea pendiente urgente. 🔴 = sin campo, candidato documentado pero
sin caso de uso de negocio confirmado — no se agrega especulativamente (principio sostenido en
toda la consolidación OCF/OSF: "no infraestructura especulativa"). ⚪ = decisión explícita de que
el campo NO corresponde a este dominio.

**Ninguna fila de esta tabla es una migración pendiente implícita.** Antes de mover cualquier fila
de 🔴 a 🟢/🟡 se requiere una necesidad de negocio real y verificada — exactamente el principio del
§5 del prompt maestro de esta fase ("el objetivo NO es poner sede_id en todas las tablas").
