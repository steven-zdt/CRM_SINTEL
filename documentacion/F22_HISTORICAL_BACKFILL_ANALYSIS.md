# F22.28-29 — Analisis de Backfill Historico (Inventario -> Contabilidad)

**Fecha:** 2026-08-09. Metodo: `--dry-run` real contra los tenants reales de este entorno de
desarrollo (`home`, `qaisotest`, `shelltest1`), mas conteo directo de `MovimientoInventario` y
`PeriodoContable` por schema.

## 1. Inventario real de datos (antes de cualquier backfill)

```bash
docker compose exec web python manage.py backfill_contabilidad --extractores=inventario --dry-run
```

```
Tenant: home (id=3)        [inventario] 0 pendientes encontrados
Tenant: qaisotest (id=4)   [inventario] 0 pendientes encontrados
Tenant: shelltest1 (id=6)  [inventario] 0 pendientes encontrados
Resumen: DRY RUN — pendientes=0 omitidos=0 errores=0
```

Conteo directo (`MovimientoInventario.objects.filter(producto__isnull=False)`, por schema):

| Tenant | Movimientos de Producto (contabilizables) | `PeriodoContable` configurados |
|---|---|---|
| `home` | 0 | 0 |
| `qaisotest` | 0 | 0 |
| `shelltest1` | 0 | 0 |

## 2. Conclusion

**No existe deuda historica real que contabilizar en este entorno.** Los 3 tenants reales de
desarrollo no tienen ningun `MovimientoInventario` con `producto` asignado (consistente con que
`RecepcionCompra`/F21 se implemento en esta misma sesion de trabajo, sin datos de prueba
persistidos en estos schemas todavia) y **ninguno tiene siquiera un `PeriodoContable`
configurado** — aunque hubiera movimientos, `Contabilizador._resolver_periodo()` fallaria con
`ValueError` (periodo no encontrado) hasta que el tenant corra `seed_periodos_contables` o cree
sus periodos manualmente.

## 3. Periodos, movimientos y estado de contabilizacion — no aplica

Los puntos 1-5 del prompt maestro (§22.28: identificar cantidad, periodos, movimientos, cuales ya
fueron contabilizados, periodos cerrados) resultan en **cero para los tres** dado el punto 1: no
hay filas que clasificar.

## 4. Decision

**No se ejecuta ningun backfill** (ni siquiera en modo seguro) porque no hay nada que backfillear
hoy. Esta conclusion es el resultado de un `--dry-run` real, no una suposicion. Cuando el flujo de
Recepcion de Compras empiece a generar `MovimientoInventario` reales en produccion (fuera de esta
sesion de desarrollo), el mismo comando (`backfill_contabilidad --extractores=inventario
--dry-run`, ya generalizado para incluir `inventario` en F22.8) sirve para volver a auditar antes
de cualquier backfill real — no requiere cambios adicionales, el mecanismo ya esta listo y
verificado.

## 5. Prerequisito operativo para produccion (no una accion de F22, una nota operativa)

Cualquier tenant real que quiera que las Recepciones de Compra generen asientos debe, en este
orden: (1) tener al menos 1 `Sede`/`Empresa` configurada (ya obligatorio); (2) correr
`python manage.py seed_reglas_contables` (idempotente, ya existente, no modificado por F22); (3)
tener `PeriodoContable` abiertos para las fechas de sus movimientos (`seed_periodos_contables`,
existente); (4) ejecutar `python manage.py backfill_contabilidad --extractores=inventario`
(o esperar a que exista una tarea periodica — ver `F22_FINAL_REPORT.md` §Celery para la decision
de no crear una en esta fase).
