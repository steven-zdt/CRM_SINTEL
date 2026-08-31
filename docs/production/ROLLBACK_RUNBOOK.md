# ROLLBACK_RUNBOOK

## Regla dura (Fase 35, explícita en el plan)

**NUNCA revertir una migración de BD automáticamente si puede destruir
datos posteriores al release.** Si el rollback de esquema no es
seguro (columnas eliminadas, datos ya escritos con el nuevo esquema),
la respuesta es un **forward fix** (una migración nueva que corrija el
problema), no un `migrate` hacia atrás.

## Procedimiento

```
release desplegado
   │
   ▼
detectar fallo (health check falla / smoke test falla / 5xx crítico)
   │
   ▼
FREEZE — no desplegar nada más, no tocar datos manualmente
   │
   ▼
clasificar: ¿el fallo es de CÓDIGO o de DATOS/MIGRACIÓN?
   │
   ├── CÓDIGO (sin migración nueva, o migración es aditiva/segura):
   │      → revertir imagen/código al tag anterior
   │      → docker compose up -d --no-deps web celery nginx (con imagen anterior)
   │      → validar health + smoke
   │
   └── DATOS/MIGRACIÓN (migración destructiva o con datos nuevos ya escritos):
          → NO hacer `migrate` hacia atrás automáticamente
          → evaluar forward fix (nueva migración correctiva)
          → si es irrecuperable de otra forma: restaurar desde el backup
            del paso 2 del DEPLOYMENT_RUNBOOK (implica pérdida de datos
            escritos DESPUÉS del backup — decisión que requiere
            autorización explícita, nunca automática)
```

## Qué conservar de cada release (para poder revertir)

- Tag de imagen Docker anterior (nunca solo `latest`).
- Backup de BD tomado inmediatamente antes del release.
- Commit exacto desplegado (`docs/production/PRODUCTION_CHECKLIST.md`
  registra esto por release).

No existe hoy un mecanismo automatizado de rollback de un solo comando
— es un procedimiento manual documentado, apropiado para la escala
actual (Docker Compose, sin orquestador). Automatizarlo es una mejora
futura razonable, no un requisito de esta misión.
