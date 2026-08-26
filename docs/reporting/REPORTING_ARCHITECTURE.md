# Reporting Hub — Arquitectura

**Fecha:** 2026-08-26
**Estado:** REPORTING_HUB = COMPLETED_WITH_DEFERRED (ver §"Release Gate")

---

## 1. Principio central

**Reporting no es dueño de los datos.** Cada app tenant sigue siendo la SSoT de su propio dominio. `apps/services/reporting/` solo posee: el vocabulario de un reporte (contratos), el catalogo (registry), la ejecucion (query engine), el scope (adapter sobre el Scope Engine ya existente) y la exportacion. Ninguna consulta de negocio vive dentro de `apps/services/reporting/` — todas viven en `apps/tenant/<dominio>/reporting/provider.py`.

## 2. Flujo real implementado

```
Datos de la app (ej. Venta, MovimientoContable)
    v
ReportProvider del dominio (apps/tenant/<app>/reporting/provider.py)
    v  (declara ReportDataset: dimensiones, medidas, filtros)
ReportRegistry (apps/services/reporting/registry.py) -- catalogo global
    v
ReportRequest (validado contra el catalogo, apps/services/reporting/query_engine.py)
    v
Scope Engine (apps/services/reporting/scope.py -- envuelve OrganizationalScope)
    v
Provider.execute(request, scope) -- ORM real, dentro del dominio
    v
ReportResult
    +-- JSON (Response directo)
    +-- CSV (apps/services/reporting/exporters.py, stdlib csv)
    +-- XLSX (openpyxl, ya era dependencia del proyecto)
    +-- PDF (DIFERIDO -- sin libreria instalada)
```

## 3. Componentes construidos

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Contratos | `apps/services/reporting/contracts.py` | `ReportDataset`, `ReportField`, `ReportMeasure`, `ReportFilterSpec`, `ReportRequest`, `ReportResult`, `ReportProvider` (Protocol) |
| Registry | `apps/services/reporting/registry.py` | Catalogo global, mismo patron que `document_intake/dispatcher.py` |
| Scope Engine | `apps/services/reporting/scope.py` | Envoltorio sobre `OrganizationalScope` (NO RBAC nuevo) + `ScopeViolationError` |
| Query Engine | `apps/services/reporting/query_engine.py` | Orquesta registry -> validacion -> scope -> provider -> result |
| Exportadores | `apps/services/reporting/exporters.py` | JSON/CSV/XLSX desde `ReportResult`, sin re-consultar la BD |
| API | `apps/services/reporting/api/{viewsets,serializers,urls}.py` | `/api/v1/reporting/` |
| Provider Ventas | `apps/tenant/ventas/reporting/provider.py` | Dataset `ventas.resumen` (primer dataset real, FASE 14) |
| Provider Contabilidad | `apps/tenant/contabilidad/reporting/provider.py` | Dataset `contabilidad.balance_prueba` (adapter, FASE 19 -- NO absorbe el calculo) |

## 4. Como se auto-registra un dominio

Mismo patron que `apps/services/document_intake/` (mision Mail Hub):

```python
# apps/tenant/<dominio>/reporting/__init__.py
def register() -> None:
    from apps.services.reporting.registry import registry
    from apps.tenant.<dominio>.reporting.provider import <Dominio>ReportProvider
    registry.register(<Dominio>ReportProvider())

# apps/tenant/<dominio>/apps.py
class <Dominio>Config(AppConfig):
    def ready(self) -> None:
        from apps.tenant.<dominio>.reporting import register
        register()
```

No hay import circular: `apps/services/reporting/` nunca importa `apps.tenant.*` a nivel de modulo (solo lazy imports dentro de funciones, igual que `organizational_context.py`).

## 5. Seguridad real (FASE 5, 10, 11, 28 de la mision)

- El frontend solo puede enviar `dataset_id`, `filters`, `group_by`, `measures`, `order_by`, `page`, `page_size` — validado por `ReportQueryRequestSerializer`. Ningun campo libre de modelo/tabla/SQL es aceptado (Regla Absoluta #4).
- `ReportQueryEngine._validate_request()` rechaza cualquier dimension/medida/filtro/orden no declarado explicitamente en el `ReportDataset` del catalogo — confirmado con 400 real en vivo para un filtro inventado.
- El Scope Engine calcula el alcance real del usuario (`OrganizationalScope.resolve(request)`, ya probado y en produccion desde el proyecto OSF) e interseca contra cualquier filtro `sede`/`area` solicitado. Un perfil alcance=SEDE pidiendo una sede fuera de su `sedes_asignadas` recibe **403**, confirmado con test real (`apps/tenant/ventas/tests/test_reporting_provider.py`).
- No se creo ningun RBAC nuevo (Regla Absoluta #6): todo el calculo de permisos delega en `apps.tenant.core.services.organizational_scope`.

## 6. Rendimiento (FASE 30, medido no asumido)

Ejecucion en vivo contra el tenant `home` (dataset real, sin indices adicionales): `contabilidad.balance_prueba` (6 cuentas) = 21.16ms; `ventas.resumen` (agregado agrupado) = 11.56ms. Ambos dentro de un request HTTP normal — **no hay evidencia hoy que justifique ejecucion asincrona ni materializacion** (Regla Absoluta #7/FASE 31): se mantiene LIVE QUERY unicamente.

## 7. Bug real encontrado y corregido durante la construccion

`DefaultRouter` de DRF usa por defecto el regex `[^/.]+` para `pk`, que **excluye el punto**. Los `dataset_id` de este proyecto usan notacion `app.dataset` (`ventas.resumen`, `contabilidad.balance_prueba`) — sin el fix, `GET /api/v1/reporting/<dataset_id>/` siempre devolvia 404. Confirmado en vivo antes y despues del fix. Corregido con `lookup_value_regex = r"[^/]+"` en `ReportingViewSet`.

## 8. Loop de expansion (FASE 40) — como agregar el siguiente dataset

1. Verificar si ya existe un `Selectors.get_summary()`/agregado reusable en la app (ver `docs/reporting/REPORTING_BASELINE.md` §4) — si existe, envolverlo; si no, escribir la agregacion ORM dentro del Provider (nunca en Reporting).
2. Crear `apps/tenant/<app>/reporting/{__init__.py,provider.py}` siguiendo exactamente el patron de `ventas/reporting/`.
3. Agregar `ready()` a `apps/tenant/<app>/apps.py`.
4. Confirmar `scope_fields` reales del modelo (no asumir `sede`/`area` si el modelo no los tiene — ver ejemplo `ventas.resumen`).
5. Verificar en vivo: `GET /api/v1/reporting/` debe listar el nuevo dataset sin reiniciar nada mas que el proceso Django.
6. Test dirigido: registro + una query real + (si el modelo tiene sede/area) un caso de scope.

**No se requiere volver a auditar arquitectura** para cada nuevo dataset — el contrato ya esta cerrado y probado.

### 8.1. Bug real encontrado al agregar `inventario.movimientos` — alias de medida vs. nombre de campo

Al construir el tercer dataset del loop de expansion (`inventario.movimientos`, sobre `MovimientoInventario`) se encontro un bug real, confirmado en vivo: una medida cuyo NOMBRE PUBLICO coincide con el nombre real de un campo del modelo (`cantidad`, tanto la medida como `MovimientoInventario.cantidad`) rompe cuando OTRA medida en el mismo `annotate()`/`aggregate()` referencia ese campo dentro de una expresion compuesta (`costo_total = Sum(F('cantidad') * F('costo_unitario'))`). Django resuelve el `F('cantidad')` contra el ALIAS ya agregado en la misma llamada (que es en si mismo un `Sum(...)`), no contra el campo crudo, y lanza `FieldError: '...' is an aggregate`.

**Fix aplicado (en `inventario/reporting/provider.py`, replicable para cualquier provider futuro con medidas compuestas):** los alias internos usados en `.annotate()`/`.aggregate()` se prefijan (`m__<medida>`) para que NUNCA coincidan con un nombre de campo real, remapeando al nombre publico de la medida solo al leer los resultados. `ventas.resumen`/`tax.iva`/`tax.retenciones` no lo necesitaron porque ninguna de sus medidas usa una expresion compuesta que referencie OTRO campo por nombre -- este patron se vuelve necesario en cuanto un Provider tiene una medida tipo "cantidad × precio". Documentado aqui para que el proximo dataset con una medida compuesta no repita el mismo diagnostico.

## 9. Deuda diferida (explicita, no oculta)

| Item | Por que se difiere |
|---|---|
| Datasets Inventario/Facturas/Gastos/Empleados (FASE 15-18) | Patron ya probado con 2 datasets reales (Ventas + Contabilidad); replicable mecanicamente via §8 sin mas diseño — se prioriza dejar el contrato solido sobre construir 6 datasets a medio probar |
| Exportacion PDF (FASE 21) | Sin libreria instalada (`reportlab`/`weasyprint`); agregar una dependencia nueva requiere decision explicita, no se asume |
| Ejecucion asincrona + `ReportExecution`/historial (FASE 22-23) | Sin evidencia de que una query en vivo sea insuficiente (ver §6) -- Regla Absoluta #7 prohibe construir esto sin evidencia concreta |
| UI transversal de Reportes (FASE 24-26) | Esta pasada es backend-only; ningun consumidor de UI existe todavia que lo requiera |
| Migracion de Dashboard a datasets (FASE 20) | Dashboard funciona hoy (cacheado, snapshot nocturno); migrar sus 8 widgets es un cambio de alto impacto que la propia mision pide hacer "progresivamente...solo despues de verificar consumidores reales" -- no en esta pasada |
| Columnas sensibles con visibilidad por rol (FASE 29) | Ningun dataset real construido hoy tiene una columna que lo amerite (costo/margen/salario) -- se deja el campo `description` en `ReportFilterSpec`/`ReportField` como punto de extension, sin inventar la politica sin un caso real |
| Contrato IA en lenguaje natural (FASE 32) | El contrato `ReportRequest` ya es 100% declarativo (sin SQL/campo libre) -- estructuralmente listo sin trabajo adicional; no se construye una capa NL sin necesidad concreta |

## 10. Release Gate (FASE 38)

- [x] Baseline (`REPORTING_BASELINE.md`)
- [x] Inventario (`REPORTING_INVENTORY.md`)
- [x] Matriz SSoT
- [x] `ReportDataset` (contrato)
- [x] `ReportProvider` (contrato + 2 implementaciones reales)
- [x] Registry
- [x] Scope Engine
- [x] Query Engine
- [x] `ReportResult`
- [ ] Ventas — dataset real construido y validado en vivo; solo un dataset (`resumen`), no el dominio completo
- [ ] Inventario — DIFERIDO
- [ ] Facturas — DIFERIDO
- [ ] Gastos — DIFERIDO
- [x] Contabilidad adapters — `balance_prueba` (validado en vivo, cifras identicas a CONT-19); `estado_resultados`/`libro_diario` diferidos (forma de salida distinta, requieren diseño propio)
- [ ] Dashboard integrado — DIFERIDO
- [x] Exportacion — JSON/CSV/XLSX reales, validados en vivo; PDF diferido
- [x] Seguridad — validado en vivo (400 catalogo, 403 scope)
- [x] Performance — medido, live query suficiente
- [x] Documentacion — este documento + BASELINE + INVENTORY + CATALOG
- [x] Governance — ver `docs/reporting/REPORTING_CATALOG.md` §Governance

## 11. Estado final

**REPORTING_HUB = COMPLETED_WITH_DEFERRED**

El nucleo transversal (contratos, registry, scope engine, query engine, exportadores, API) esta completo, probado en vivo con datos reales, y sigue el principio "Reporting no es dueño de los datos" de punta a punta. Dos datasets reales (`ventas.resumen`, `contabilidad.balance_prueba`) prueban el patron end-to-end. La expansion a los demas dominios es mecanica (§8) y queda como trabajo futuro explicitamente no urgente, no como deuda oculta.
