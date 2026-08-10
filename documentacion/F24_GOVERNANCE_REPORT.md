# F24 — Reporte de Governance

**Fecha:** 2026-08-10

## Baseline (F24.0, antes de tocar codigo)

```
python -m tools.organizational_governance.cli --report
```

```
KNOWLEDGE GRAPH: Entities: 160, Relations: 168
ARCHITECTURE:    PASS: 1  WARN: 0  FAIL: 0
SECURITY:        PASS: 3  WARN: 0  FAIL: 0
MULTI TENANT:    PASS: 0  WARN: 0  FAIL: 0
ORGANIZATIONAL:  PASS: 4  WARN: 0  FAIL: 0
INTEGRATIONS:    PASS: 1  WARN: 0  FAIL: 0
SERVICE LAYER:   PASS: 0  WARN: 0  FAIL: 0
DOCUMENTATION:   PASS: 0  WARN: 0  FAIL: 0
TEST COVERAGE:   PASS: 1  WARN: 0  FAIL: 0

FINAL STATUS: PASS
```

`makemigrations --check --dry-run`: "No changes detected".
`manage.py check`: "System check identified no issues (0 silenced)".

## Dependency Graph (F24.1/F24.34)

375 edges totales, **0 FORBIDDEN**. Edges relevantes al circuito F21-F23:

```
compras   -> inventario     CONTROLLED / PUSH_CONTROLLED
facturas  -> contabilidad   PULL (x9)
facturas  -> inventario     CONTROLLED (x2)
ventas    -> inventario     CONTROLLED (x2) / PUSH_CONTROLLED (x1, F23)
ventas    -> facturas       UNKNOWN (x4, ver F24-004) / PUSH_CONTROLLED (x1)
```

**Ninguna edge `ventas -> contabilidad` ni `inventario -> contabilidad` existe en el
grafo** (confirmado por inspeccion directa, no solo por ausencia en `FORBIDDEN`) --
Contabilidad consume exclusivamente via Pull (`ExtractorInventario`), tal como F22
establecio y F23 preservo.

## Auditoria final (F24.52, despues de los 2 fixes de codigo)

```
manage.py check                                -> System check identified no issues
manage.py makemigrations --check --dry-run     -> No changes detected
python -m tools.organizational_governance.cli --report -> FINAL STATUS: PASS
```

(Los 2 archivos de produccion modificados por F24 --
`apps/tenant/compras/services/business_service.py` y
`apps/tenant/contabilidad/integracion/validadores.py` -- no alteran modelos, imports
entre apps, ni estructura de Service Layer: ambos cambios son correcciones de 1-3
lineas dentro de metodos ya existentes.)

## Service Layer (F24.36)

`ViewSet -> ServiceMixin -> BusinessService -> CRUDService` confirmado intacto en
`OrdenCompraViewSet`, `RecepcionCompraViewSet`, `VentaViewSet`,
`MovimientoInventarioViewSet`, `FacturaViewSet` (todas heredan `BaseTenantViewSet` +
su `*ServiceMixin` correspondiente). 0 signals (`post_save`/`pre_save`/`post_delete`/
`@receiver`) encontrados en `compras/inventario/ventas/facturas`.

## Veredicto

Governance PASS sostenido antes y despues de las correcciones de F24. Ningun finding
oculto ni regla desactivada para forzar el PASS.
