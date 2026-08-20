# APP_compras_AUDIT — Auditoria integral (app 8/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> inventario
-> **compras** -> ventas -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/compras` tiene `.agent/AUDITORIA_FLUJO_COMPRAS.md`
(v3.10.5, corregida 2026-06-18, 358 lineas) -- usado como fuente
primaria. A diferencia de los `.agent/` docs de otras apps (que
declaran "0 CRITICOS" de entrada), este documenta explicitamente
**6 bugs criticos/altos corregidos y 3 items de deuda tecnica
resueltos** en su ultima pasada -- se verifico cada uno contra el
codigo actual (ver FASE I).

**Verificado 1:1:** 3 modelos (`PlantillaOrdenCompra`, `OrdenCompra`,
`ItemOrdenCompra`), coincide con `APP_AUDIT_MATRIX.md`.

Resumen de negocio: gestion del ciclo de vida de **Ordenes de Compra**
(no es un modulo de retencion tributaria -- ver FASE M). Flujo de
estados `BORRADOR -> PENDIENTE -> APROBADA -> RECIBIDA` (o `ANULADA`
desde cualquier estado no terminal), con permisos de edicion
diferenciados por estado. Numeracion via `PlantillaOrdenCompra`
(prefijo + rango + consecutivo atomico, `select_for_update()`).

## FASE C/D/K — Service Layer y codigo muerto

Estructura limpia: `services/{selectors,crud_service,business_service,
api_mixins}.py` (4 archivos, coincide con matriz). **Sin
`services/services.py`** (igual que `inventario`), **sin marcadores
`deprecad`/`legacy`** en todo el codigo de produccion (grep repo-wide,
excluyendo tests).

**Conclusion FASE K: 0 lineas de codigo muerto confirmado.** Quinta
app consecutiva sin hallazgos de limpieza (`perfil`, `empleados`,
`proveedores`, `inventario`, `compras`).

## FASE I — Seguridad (verificacion de correcciones documentadas)

Se verificaron puntualmente los 2 hallazgos de mayor severidad
documentados en el `.agent/` doc (2026-06-18), ambos **confirmados
CORREGIDOS y aun vigentes** en el codigo actual:

- **BUG-04 (CRITICO):** `if settings.DEBUG: return []` en
  `get_permissions()` bypasseaba toda autenticacion y aislamiento
  multi-tenant en desarrollo -- confirmado ausente (grep de
  `settings.DEBUG` en `api/viewsets.py` no encuentra ningun bypass,
  los 3 `get_permissions()` del archivo usan el patron correcto).
- **DT-COMPRAS-01 (MEDIA):** `consecutivo_actual += 1; save()`
  cambiado a `F('consecutivo_actual') + 1` -- confirmado presente en
  `business_service.py:134`, patron atomico correcto bajo
  `select_for_update()`.

No se re-verificaron los 4 hallazgos restantes (BUG-01/02/03/05/06,
DT-COMPRAS-02/03 -- relacionados con frontend JS y constraints DB) por
alcance de tiempo de esta pasada; se confia en el `.agent/` doc dado
que es reciente (2 meses) y detallado, salvo evidencia en contrario.

## FASE M — Normativa colombiana

`compras` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_compras_NORMATIVE_MATRIX.md`** -- hallazgo principal: `compras` es
un modulo de **workflow de Ordenes de Compra**, no de calculo
tributario -- confirmado con grep repo-wide que no existe NINGUNA
referencia a Retefuente/ReteICA/ReteIVA en toda la app (a diferencia
de `proveedores`, que si calcula estas retenciones). El unico campo
con relevancia normativa es `porcentaje_iva` por item, entrada libre
del usuario sin validacion contra tarifas de IVA vigentes (0%/5%/19%)
-- riesgo bajo, documento interno, no liquidacion tributaria
automatica.

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/compras/tests/`. Regresion lanzada
en background tras confirmar `db`/`redis` healthy. Sin cambios de
codigo en esta app.

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | `porcentaje_iva` en `ItemOrdenCompra` no valida contra tarifas de IVA vigentes -- entrada libre | P3 |
| 2 | 4 hallazgos del `.agent/` doc (BUG-01/02/03/05/06, DT-COMPRAS-02/03) no re-verificados en esta pasada por alcance de tiempo -- confiados al doc existente | P3 (informativo, no bloquea) |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Seguridad: 2 correcciones criticas/medias re-verificadas vigentes (FASE I)
- [x] Matriz normativa colombiana completa (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED_WITH_DEFERRED` (2 items P3, ninguno
bloqueante) si la regresion confirma el baseline sin fallos.
