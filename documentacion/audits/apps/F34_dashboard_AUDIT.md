# F34_dashboard_AUDIT — Auditoria integral de negocio/arquitectura (app 16/16, ULTIMA)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_dashboard_AUDIT.md` (0 codigo muerto -- `services.py`/`services/`
investigado y confirmado NO dead, resuelto deliberadamente con
`importlib.util.spec_from_file_location()`).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`dashboard` agrega metricas de 8 apps de dominio via extractores Pull
Model. Sin cambios de codigo en esta pasada. Se investigo el patron
de manejo de errores de los extractores (nuevo angulo, no cubierto
antes) y se confirmo `select_related`/`prefetch_related` ausente en
los 8 extractores -- **verificado que es correcto por diseño**, no un
N+1 sin detectar.

## FASE 6 — ORM/BD: verificacion N+1 (con hallazgo aclarado)

Los 8 extractores (`facturas_ext.py`, etc.) usan exclusivamente
`.count()`/`.aggregate()` sobre querysets filtrados -- **nunca
iteran filas individuales con acceso a campos relacionados**. Por
eso `select_related`/`prefetch_related` estan ausentes en los 8
archivos (0 ocurrencias) -- **correcto por diseño**, no un N+1 sin
detectar: una agregacion SQL (`COUNT`/`SUM`) no necesita optimizacion
de traversal de FK porque nunca materializa objetos Python por fila.

## FASE 9/20 — Manejo de errores (hallazgo nuevo, informativo)

**7 de los 8 extractores** (`clientes_ext`, `empleados_ext`,
`facturas_ext`, `gastos_ext`, `inventario_ext`, `proveedores_ext`,
`proyectos_ext`) comparten el mismo patron: `try/except Exception:
return <DTO con todo en cero>` -- **sin logging de la excepcion**.
Es un patron de resiliencia DELIBERADO y consistente (si UNA app
falla, el dashboard completo no debe caerse, solo ese widget muestra
cero) -- **no se clasifica como bug**, pero la ausencia de logging
significa que un error real (bug, schema roto, timeout) queda
completamente silencioso -- el dashboard mostraria "0" indefinidamente
sin que nadie se entere de que algo esta fallando.

## FASE 12/13 — Codigo muerto

Sin hallazgos nuevos. `services.py`/`services/` ya investigado a
fondo en la pasada anterior, confirmado vivo (workaround deliberado
con `importlib`).

## Deferred (nuevo item de esta pasada)

| # | Item | Prioridad |
|---|---|---|
| 1 | 7 extractores del dashboard silencian excepciones sin loguearlas (`except Exception: return <ceros>`) -- patron de resiliencia correcto, pero sin observabilidad. Agregar `logger.warning(exc_info=True)` antes del `return` seria una mejora de bajo riesgo | P3 |

## Cambios realizados en esta pasada

**Ninguno** (el hallazgo de logging se documenta como deferred, no se
corrige en esta pasada -- cambio de bajo riesgo pero afecta 7
archivos, se prefiere agrupar en una sesion de limpieza dedicada en
vez de tocarlo de forma aislada al cierre de la mision).

## FASE 22 — Release Gate

- [x] N+1 -- confirmado ausencia de select_related es correcta por diseño (agregaciones puras)
- [x] Manejo de errores -- patron de resiliencia identificado, gap de observabilidad documentado (P3)
- [x] Codigo muerto -- sin hallazgos nuevos
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED_WITH_DEFERRED** (1 item P3 nuevo, informativo, sin
riesgo funcional).

---

## Cierre de F34 (16/16 apps)

Con `dashboard` se completan las 16 apps del orden de F34. Ver
`documentacion/audits/apps/F34_MASTER_STATUS.md` para el resumen
consolidado.
