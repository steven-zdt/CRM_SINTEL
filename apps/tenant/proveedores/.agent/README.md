# Documentación Módulo Proveedores

**Última actualización:** 2026-09-15 (PROVEEDORES-02, ver `docs/proveedores/PROVEEDORES_FLOW.md` §8) — histórico: 2026-09-08 (PROVEEDORES-01, auditoría integral)
**Status:** ✅ Verificado con evidencia real — `pytest apps/tenant/proveedores/tests` 53 passed, 0 failed; `manage.py check`/`makemigrations --check` limpios. Ver `docs/proveedores/PROVEEDORES_RELEASE_GATE.md`

---

## Inicio rápido

| Necesitas... | Ve a... |
|---|---|
| 🔍 **Auditoría integral (código real, no aspiracional)** | `docs/proveedores/PROVEEDORES_AUDIT.md` ⭐ |
| 🗺️ **Flujo real (CRUD, integraciones, permisos)** | `docs/proveedores/PROVEEDORES_FLOW.md` ⭐ |
| ✅ **Veredicto final / gate** | `docs/proveedores/PROVEEDORES_RELEASE_GATE.md` |

Los documentos anteriores de este directorio (`AUDITORIA_FLUJO_PROVEEDORES.md`,
`AUDITORIA_CODIGO_COMPLETA.md`, `RESUMEN_EJECUTIVO.md`, `docs/proveedores_*.md`,
`PLAN_CARTERA_UI.md`) quedan como **archivo histórico** — varios describen un
frontend Tabulator que ya no existe (migrado a server-rendered
django-tables2+HTMX) y campos/endpoints ya renombrados o eliminados. No usarlos
como referencia del estado actual; `PROVEEDORES_AUDIT.md`/`PROVEEDORES_FLOW.md`
los reemplazan como fuente de verdad.

---

## Stack real (verificado 2026-09-08)

```
Backend
├─ Django DRF (REST API), lookup_field='uuid' en los 3 ViewSets
├─ django-tenants (Multi-tenant PostgreSQL, empresa_id en todo selector)
└─ Service Layer: selectors.py / crud_service.py / business_service.py / api_mixins.py

Frontend
├─ Directorio y Cuentas por Pagar: server-rendered (django-tables2 + HTMX)
├─ Representantes: Tabulator (directorio global) + tabla HTML simple (por proveedor)
├─ Vanilla JS ES6+, namespace window.Sintel.Proveedores / window.Sintel.Representante
└─ Bootstrap 5.3.2 (offcanvas via mostrarOffcanvasSeguro)
```

## Modelos (3)

- **`Proveedor`** — maestro. `uuid`, `empresa` FK (PROTECT), soft-delete
  (`activo`), único por (empresa, tipo_documento, numero_documento). Campos
  de retención (`retefuente_porcentaje` y similares) existen en el modelo
  pero son **read-only en la API desde PROVEEDORES-01** — ningún cálculo real
  los usa (ver retenciones abajo).
- **`Representante`** — 1 Proveedor → N Representantes (FK CASCADE),
  `es_principal` marca el principal, único por (empresa, proveedor,
  numero_documento). No se puede eliminar el único principal de un proveedor.
- **`CuentasPagar`** — persiste abonos y CxP generadas desde Compras sin
  factura. El listado real (`qs_list_unificado`) combina esto con
  `Factura.naturaleza='COMPRA'` leída directamente — no hay FK entre ambas
  fuentes (ver limitación conocida en `PROVEEDORES_AUDIT.md` H6).

## Retenciones — NO se calculan aquí

El cálculo real de retenciones vive en `contabilidad.RetencionesService` /
`ConfiguracionRetenciones` (indexado por NIT, Pull Model — ver
`docs/ADR-001-retention-pull-model.md`). `Proveedor` nunca crea
`AsientoContable`/`MovimientoContable` ni importa `apps.tenant.contabilidad`.

## Permisos

`IsTenantMember` (lectura, cualquier miembro) + `IsTenantAdminOrReadOnly`
(escritura, incluye `registrar-abono` = pagar, solo ADMIN). Binario y
deliberado — no hay niveles OPERADOR intermedios.

## Rutas principales

- API: `/api/v1/proveedores/`, `/api/v1/proveedores/representantes/`,
  `/api/v1/proveedores/cuentas-pagar/` (+ `registrar-abono/` como acción).
- UI server-rendered: `/ui/proveedores/tabla/`, `/ui/proveedores/cuentas-pagar/tabla/`.
- Frontend FSD: `templates/tenant/proveedores/`, `static/proveedores/js/`.

## Tests

Ver el inventario completo (qué cubre cada archivo, qué gaps se cerraron en
PROVEEDORES-01) en `docs/proveedores/PROVEEDORES_AUDIT.md` §5.

---

**Para cambios en este módulo:** lee `PROVEEDORES_AUDIT.md` y
`PROVEEDORES_FLOW.md` primero, y `AGENTS.md` §5 (CRUD-E2E) / §13 (IDOR) /
§15 (SECURITY) / §17 (BRIDGE) / §18 (CONTAB).
