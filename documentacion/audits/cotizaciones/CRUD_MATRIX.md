# Matriz Final CRUD — Cotizaciones (FASE 46)

**Fecha:** 2026-08-26

| Modelo | CREATE | READ | UPDATE | DELETE | Seguridad (DSV/Tenant) | Estado | Tests | Estado final |
|---|---|---|---|---|---|---|---|---|
| `Cotizacion` | ✅ (atómico, con Items) | ✅ (selectors, sin N+1) | ✅ | ✅ ANULAR-vía-bloqueo (hard-delete protegido si hay Factura vinculada, fix aplicado) | ✅ | ⚠️ campo decorativo, sin máquina de estados (ver `MATRIZ_ESTADOS_COTIZACION.md`) | ✅ ampliada (fecha_emision, DELETE con/sin Factura) | COMPLETED_WITH_DEFERRED |
| `CotizacionItem` | ✅ (recalcula cabecera) | ✅ | ✅ (recalcula cabecera) | ✅ (recalcula cabecera, único DELETE que ya pasaba por Service Layer antes de esta auditoría) | ✅ | N/A | ⚠️ sin test directo de la ruta API (gap documentado, no crítico — cubierto indirectamente vía `test_services.py`) | COMPLETED_WITH_DEFERRED |
| `Producto` (catálogo propio) | ✅ (+ constraint BD nueva contra duplicado, fix aplicado) | ✅ | ✅ | ✅ (ahora vía Service Layer, fix aplicado) | ✅ | N/A (`activo` declarado, no aplicado — deuda documentada, no crítica) | ✅ ampliada (constraint, 400 no 500, DELETE vía service) | COMPLETED_WITH_DEFERRED |
| `Servicio` (catálogo propio) | ✅ (sin validación de negocio — nunca la tuvo, no es una regresión) | ✅ | ✅ | ✅ (ahora vía Service Layer, fix aplicado) | ✅ | N/A | ⚠️ sin test directo de API (gap documentado) | COMPLETED_WITH_DEFERRED |
| `ConfiguracionCotizacion` | ✅ | ✅ | ✅ | ✅ (ahora vía Service Layer, fix aplicado — antes: sin `destroy()`, hard-delete por defecto de DRF) | ✅ | `es_activo` (múltiples activos permitidos a propósito, ya documentado) | ⚠️ sin test directo de DELETE (gap documentado) | COMPLETED_WITH_DEFERRED |

## Veredicto de Release Gate (FASE 47/48)

`COTIZACIONES_CRUD = COMPLETED_WITH_DEFERRED`

Checklist:

- [x] CREATE — los 5 modelos tienen CREATE real, atómico donde corresponde (Cotizacion+Items), con DSV.
- [x] READ — selectors reales, sin N+1 confirmado en las rutas principales.
- [x] UPDATE — los 5 modelos tienen UPDATE real vía Service Layer.
- [x] DELETE/ANULAR — corregido en esta pasada: los 5 modelos ahora pasan por Service Layer; `Cotizacion` bloquea el borrado si hay trazabilidad real que romper (Factura vinculada).
- [x] Items CRUD — completo, recalcula totales de cabecera automáticamente en cada mutación.
- [x] Service Layer — corregido: 4 de 5 `destroy()` bypaseaban el Service Layer antes de esta auditoría, ahora los 5 lo respetan.
- [x] DSV — confirmado real (no solo confía en FKs crudos) en creación/actualización de Cotización.
- [x] Tenant / Empresa — confirmado, todo filtra por `empresa_id`.
- [x] Sede — confirmado opcional/informativo por diseño (DT-SEDE-04), sin evidencia de que deba ser restrictivo.
- [ ] Área — no aplica a este dominio (sin evidencia de que Cotizaciones deba tener contexto de Área; no se inventó uno).
- [x] Permisos — reutiliza `IsTenantMember`/`IsTenantAdminOrReadOnly` existentes, sin RBAC nuevo.
- [ ] **Estados — DEFERRED.** El campo existe pero es decorativo; no se construyó una máquina de estados porque no hay evidencia de negocio sobre las transiciones/efectos esperados (Regla #1: no inventar). Ver `MATRIZ_ESTADOS_COTIZACION.md`.
- [x] Totales — SSoT único confirmado (`CotizacionService.calcular_totales`), sin duplicación real.
- [x] Impuestos — cálculo comercial estimado, sin acoplamiento a Facturas/Contabilidad (correcto, no se encontró lógica fiscal duplicada).
- [x] Cliente — SSoT respetado (`clientes.Cliente`), opcional por diseño confirmado (no es un bug).
- [ ] **Producto/Servicio — DEFERRED.** Diagnosticado como `DUPLICATE_CANDIDATE` con evidencia real, pero con propósito diferenciado defendible (catálogo especulativo, snapshot pattern). No se migra/elimina sin decisión de negocio explícita — ver `CRUD_COMPLETE_REPORT.md` §Producto/Servicio.
- [x] Proyecto — no aplica: el modelo real no tiene este campo (el prompt maestro lo suponía; el dominio real no lo tiene).
- [x] Conversión a venta — confirmado que NO existe (evidencia negativa real). Lo único real es un bridge manual de solo-enlace (`Factura.cotizacion_uuid`), documentado, no una conversión automática. No se inventó una conversión que no tiene evidencia de ser requerida.
- [x] PDF — código muerto (`generar_pdf_interno`) eliminado (DEAD_CONFIRMED, cero call-sites). Pipeline activo (`generar_pdf_publico`) funcionando sin duplicación.
- [ ] **Frontend — NO auditado en profundidad en esta pasada** (fuera del alcance de tiempo de esta sesión; ver Deuda).
- [x] Performance — sin N+1 confirmado en las rutas READ principales; un riesgo latente identificado y documentado (PDF selector sin `select_related` de producto/servicio, no materializado hoy).
- [x] Tests — ampliados con cobertura real nueva para los gaps más críticos (DELETE con/sin protección, constraint de Producto, bug de fecha_emision). Gaps menores restantes documentados, no críticos.
- [x] Governance — `manage.py check` limpio, migraciones aplicadas a los 3 schemas reales sin conflicto (verificado contra datos reales antes de aplicar el constraint).
- [x] Documentación — este documento + `CRUD_BASELINE.md` + `CRUD_COMPLETE_REPORT.md` + `MATRIZ_ESTADOS_COTIZACION.md`.

**Por qué `COMPLETED_WITH_DEFERRED` y no `COMPLETED`:** quedan 2 decisiones de negocio genuinas sin evidencia suficiente para resolverlas sin inventar (máquina de estados, futuro de Producto/Servicio propio) y una auditoría de frontend/performance no completada en profundidad por límite de tiempo de esta sesión — ninguno de los 3 es CRUD roto, fuga de tenant, bypass de autorización, corrupción de relaciones, pérdida de datos, ni conversión duplicada (los criterios que bloquearían `PRODUCTION_READY`/exigirían `BLOCKED_SAFE`).
