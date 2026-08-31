# INCIDENT_RUNBOOK

## Flujo (Fase 64)

```
detectar (health check falla / 5xx crítico / Celery detenido / reporte de usuario)
   ↓
clasificar severidad:
   - CRÍTICO: servicio caído, fuga cross-tenant, pérdida de datos
   - ALTO: una funcionalidad crítica rota (facturación, login)
   - MEDIO: degradación parcial
   ↓
FREEZE — no desplegar cambios no relacionados durante la ventana de incidente (Fase 63)
   ↓
rollback/fix forward (ver ROLLBACK_RUNBOOK.md — la BD nunca se revierte
   automáticamente si es destructivo)
   ↓
validar (health + smoke + el flujo específico afectado)
   ↓
documentar: qué pasó, causa raíz, corrección, evidencia, tiempo de resolución
```

## Señales a vigilar (Fase 24-25) — sin infraestructura de alertas real hoy

**Estado honesto:** no existe un sistema de monitoreo/alertas activo en
este proyecto (confirmado: sin Sentry ni equivalente, sin
`CELERY_BEAT_SCHEDULE`, sin agente de métricas en
`docker-compose.yaml`). Los indicadores abajo son los que SE
RECOMIENDAN vigilar el día que exista esa infraestructura — no se
implementa un sistema de alertas nuevo en esta pasada (evitar
dependencia externa no solicitada, per Fase 23).

| Señal | Dónde se observa hoy (manual) |
|---|---|
| HTTP 5xx | `docker compose logs web \| grep "500\|ERROR"` |
| DB no disponible | `GET /health` → `{"database": "error"}` |
| Celery detenido | `docker compose exec celery celery -A config inspect ping` |
| Tareas fallidas | `FailedTenantTask` (tabla, consultable vía Django admin/shell) |
| Tenant provisioning fallido | Ausencia de `TENANT_CREATE` en `ConsoleActionLog` tras un intento, o excepción en logs de `crear_tenant_con_owner` |
| Trial mal reconciliado | `ConsoleActionLog` sin entradas `EXTEND_TRIAL`/`TENANT_UPDATE` esperadas |

## Mínimo mecanismo de error tracking (Fase 23)

No se incorpora Sentry ni servicio externo en esta pasada (no hay
evidencia de que el negocio ya lo haya decidido). El logging estructurado
existente (`apps/public/tenants/tasks.py::_registrar_dlq`,
`ConsoleActionLog`, logs de Django con niveles ERROR/WARNING/INFO) es el
mecanismo mínimo real disponible hoy — suficiente para diagnóstico
manual, no para alertas proactivas automáticas.
