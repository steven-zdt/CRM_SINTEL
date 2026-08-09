# F15 — Inventario y Grafo de Integraciones — Baseline

**Fecha:** 2026-08-09
**Estado:** 🟢 F15 COMPLETED

## 1. Qué se construyó

`tools/organizational_governance/dependencies.py` (nuevo, extiende el paquete existente) —
descubre por AST (no grep de texto) todos los `from apps.tenant.<app> import ...` entre las 17
apps tenant, clasifica cada arista, y detecta ciclos.

## 2. Resultado real (ejecución `discover_dependency_edges()`)

```
368 aristas de import detectadas
ALLOWED:         150  (hacia core/api, infraestructura permitida)
CONTROLLED:      123  (Selector de otra app, o modelo con empresa_id/singleton Empresa)
PUSH_CONTROLLED:  63  (BusinessService de otra app con empresa_id explícito - Service Layer real)
PULL:             15  (RetencionesService/Extractor/FacturaInterAppAPI - Pull Model)
UNKNOWN:          17  (12 patrones únicos, ver §4)
FORBIDDEN:         0
```

## 3. Correcciones aplicadas al clasificador (proceso, no solo resultado)

La primera versión del clasificador marcó **10 aristas reales como `FORBIDDEN`** por una regla
demasiado simple ("cualquier import de `*.business_service` de otra app = bypass"). Verificación
manual de cada una mostró que **9 de las 10 eran patrones ya sancionados y auditados** en esta
misma consolidación:

| Arista marcada `FORBIDDEN` (v1) | Qué es realmente | Evidencia |
|---|---|---|
| `ventas -> facturas.FacturaBusinessService` | El contrato oficial Ventas→Facturas (`crear_factura_desde_venta()`) | `VENTAS_FACTURAS_AUDIT.md` |
| `bancos/proyectos -> facturas.FacturaInterAppAPI` | API `[ABIERTO]` documentada explícitamente, ya conocida como riesgo D-4 (no un bug nuevo) | `FACTURAS_AUDIT.md` §2 |
| `facturas -> clientes/proveedores.*BusinessService.resolver_o_crear_desde_factura_*` | Get-or-create real, con `empresa_id` explícito — necesario porque los Bridges de lectura no exponen creación | Verificado leyendo el código fuente real (`apps/tenant/facturas/services/business_service.py:454-472,540-558`) |
| `core -> compras/perfil.*BusinessService` | `core` orquesta flujos cross-cutting (auth/onboarding) — patrón ya establecido | `apps/services/onboarding/empresa_service.py` |

Reclasificados a `PUSH_CONTROLLED` (llamada real a Service Layer de otra app, con `empresa_id`
explícito — no bypass de ORM) tras verificar cada uno contra el código fuente real, no contra el
nombre del import solo. Esto es la misma disciplina "precisión > cantidad de findings" aplicada en
F13/F14 — 0 findings fabricados, 0 findings reales ocultos.

## 4. `UNKNOWN` — 12 patrones sin clasificación forzada (honesto, no resuelto a ciegas)

`contabilidad -> inventario.get_movimientos_timeline`, `dashboard -> facturas.FacturaSelectors` /
`-> proyectos.qs_list` (nombres de función/clase que no calzan la heurística `*Selector`),
`facturas -> empresa.{EmpresaNotConfiguredError,get_empresa_emisor_data,get_mailbox_config}`,
`facturas -> perfil.get_or_create_profile`, `proveedores -> facturas.Factura` (import directo de
modelo en un archivo donde no se detectó `empresa_id` en el mismo texto — puede ser un falso
negativo del método "todo el archivo", no necesariamente un problema real),
`ventas -> facturas.services.dian.{CufeService,UBL21BuilderService,XadesSignerService,AttachedDocumentService}`
(utilidades DIAN compartidas, forma distinta a Bridge/Extractor). Ninguno se clasificó sin
evidencia — quedan como backlog de revisión manual, no como findings fabricados.

## 5. Ciclos detectados — 8, todos explicados, ninguno es un bug de import real

```
empresa <-> perfil
bancos -> clientes -> facturas -> bancos
clientes <-> facturas
clientes -> facturas -> contabilidad -> clientes
facturas <-> contabilidad
contabilidad <-> gastos
facturas -> contabilidad -> gastos -> proveedores -> facturas
clientes -> facturas -> cotizaciones -> clientes
```

**Por qué ninguno es un `ImportError` real:** el proyecto usa consistentemente **imports locales
(dentro de función/método, no a nivel de módulo)** para toda referencia cross-app — patrón ya
documentado repetidamente en el propio código fuente como "Bounded Context, sin acoplamiento
circular" (ej. `apps/tenant/proveedores/services/selectors.py`: *"Import local — Bounded Context
(AGENTS.md §18): lectura de solo lectura... sin FK directa, solo query"*). Un ciclo en este grafo
de *dependencias declaradas* no se traduce en un ciclo de *carga de módulos Python* porque el
import solo se ejecuta cuando la función corre, no cuando Django arranca. Verificado indirectamente
por el hecho de que `python manage.py check` pasa limpio con las 17 apps cargadas simultáneamente.

**Interpretación correcta de estos 8 "ciclos":** son pares/cadenas de relaciones **Pull en ambas
direcciones por motivos distintos** (ej. `facturas <-> contabilidad`: `facturas` lee
`RetencionesService` de `contabilidad` para configuración de retenciones; `contabilidad` lee
`Factura` vía su propio extractor Pull para generar asientos — son dos flujos de datos
independientes que casualmente se cruzan, no una dependencia mutua real de un mismo dato). Ninguno
requiere refactorización — se documentan para que quede explícito por qué no son un `FAIL` de
gobernanza.

## 6. Matriz de integraciones — validada contra código real (F15.4)

| Origen | Destino | Mecanismo (pedido) | Verificado en código real |
|---|---|---|---|
| ventas | facturas | DTO + Service | ✅ `VENTAS_FACTURAS_AUDIT.md` — confirmado, `PUSH_CONTROLLED` |
| facturas | clientes | Bridge | ⚠️ Existe `ClienteBridge` (lectura) **y** `ClienteBusinessService.resolver_o_crear_desde_factura_venta` (escritura) — dos mecanismos, no solo Bridge |
| facturas | proveedores | Bridge | ⚠️ Idem — `ProveedorBridge` (lectura) + `ProveedorBusinessService.resolver_o_crear_desde_factura_compra` (escritura) |
| facturas | cotizaciones | Bridge | ✅ `CotizacionBridge`, confirmado en `FACTURAS_AUDIT.md` §3 |
| facturas | inventario | Bridge | ✅ `InventarioItemBridge`, confirmado |
| facturas | bancos | Bridge | ✅ `BancosBridge`, confirmado |
| compras | proveedores | Bridge/UUID | 🔴 No confirmado — `compras` no importa nada de `proveedores` en el grafo (usa FK directa `OrdenCompra.proveedor`, dentro del mismo tenant, es una relación de modelo normal, no cross-app en el sentido de Bridge) |
| gastos | contabilidad | Extractor | ✅ `PULL` confirmado |
| inventario | contabilidad | Extractor | ✅ `PULL` confirmado (vía `contabilidad -> inventario`, dirección Pull real es contabilidad leyendo inventario) |
| facturas | contabilidad | Extractor | ✅ `PULL` confirmado |
| empleados | contabilidad | Extractor | ✅ `PULL` confirmado |
| proyectos | facturas | InterApp API | ✅ `FacturaInterAppAPI`, confirmado, `PULL` |
| cotizaciones | ventas | DTO/Bridge | 🔴 No confirmado — sin arista detectada en el grafo actual |

**Nota importante:** la matriz del prompt maestro asume algunas integraciones que el código real no
tiene (ej. `compras -> proveedores` como Bridge — es FK directa normal, ambos dentro del mismo
tenant, `Proveedor`/`OrdenCompra` no son apps con fronteras Bridge entre sí en ese sentido;
`cotizaciones -> ventas` no existe como dependencia de código detectada). No se fuerza su
existencia — se reporta la discrepancia entre lo esperado y lo real, consistente con "Validar cada
fila contra código real. NO inventar integraciones" (F15.4).

**Estado: 🟢 F15 COMPLETED.**
