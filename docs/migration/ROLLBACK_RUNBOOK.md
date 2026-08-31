# ROLLBACK_RUNBOOK (migración de servidor) — Fase 53

Complementa (no reemplaza) `docs/production/ROLLBACK_RUNBOOK.md`
(rollback de un release de código) -- este runbook es específico para
**rollback de una migración de servidor completa** (Fase 53-59).

## Regla #1 de la misión, recordatorio operativo

SOURCE **no se apaga, no se destruye, no se sobrescribe** hasta que
`MIGRATION_RELEASE_GATE.md` = todos los ítems en `[x]`. Mientras eso no
sea cierto, el rollback es trivial por definición: **SOURCE sigue
siendo el sistema real, no hay nada que revertir.**

## Disparadores de rollback (Fase 59, no continuar si ocurre)

- Pérdida de datos detectada en TARGET (conteos, checksums, o
  relaciones huérfanas de `POST_MIGRATION_VALIDATION.md` fallan).
- Resolución de tenant incorrecta (Fase 33/38 -- un tenant ve datos de
  otro).
- 500 masivos en smoke test.
- DB inconsistente (constraint violations, secuencias desalineadas).
- Middleware de tenant resolviendo distinto en TARGET que en SOURCE.

## Procedimiento de rollback (si ya se cambió DNS -- Fase 56 ya ejecutada)

```
1. Revertir el registro DNS al valor apuntando a SOURCE
   (mismo TTL bajo usado para el cutover -- ver CUTOVER_RUNBOOK.md)
2. Verificar propagación: nslookup desde al menos 2 resolutores
   distintos (ej. router LAN + 1.1.1.1)
3. Confirmar SOURCE sigue healthy (docker compose ps) -- nunca se
   detuvo, solo dejó de recibir tráfico nuevo durante la ventana
4. Smoke test contra SOURCE (mismo checklist que POST_MIGRATION_VALIDATION.md)
5. Documentar el incidente: que fallo, en que fase, evidencia
6. TARGET queda aislado para diagnostico -- no se borra
```

## Procedimiento de rollback (si el fallo se detecta ANTES de cambiar DNS)

Trivial: nadie apunta a TARGET todavía. Detener el trabajo en TARGET,
corregir el hallazgo, repetir desde la fase que falló. SOURCE nunca
estuvo en riesgo.

## Estado tras rollback

`ROLLED_BACK` (vocabulario Fase 64) -- no `FAILED` a secas: se
documenta la causa raíz encontrada y el plan de corrección antes de
reintentar, igual que el resto de esta sesión (DETECTAR → REPRODUCIR →
AISLAR → CORREGIR → VALIDAR → DOCUMENTAR).
