# F34_clientes_AUDIT — Auditoria integral de negocio/arquitectura (app 4/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_clientes_AUDIT.md` (39 lineas de codigo muerto ya eliminadas en
`services/services.py`; Pull Model Cartera confirmado).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`clientes` es la SSoT de identidad legal de clientes por empresa,
gestion de contactos, configuracion (no calculo) de retenciones, y
Cartera/CxC via Pull Model desde `Factura`. Sin cambios de codigo en
esta pasada.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| Identidad unica por `(empresa, tipo_documento, numero_documento)` | **CRITICAL** | `UniqueConstraint` en `models.py` |
| `es_retenedor=False` fuerza todos los flags/porcentajes de retencion a 0/False (Zero Trust) | **CRITICAL** | `_sanitize_retenciones()`, verificado en auditoria previa |
| Cartera (listado) se lee de `Factura.naturaleza='VENTA'`, nunca del modelo `Cartera` directamente -- Pull Model | **CRITICAL** (arquitectonica) | `CarteraSelector.qs_list_facturas_venta()`, ADR-001 §18 |
| `registrar_abono()` usa `select_for_update()` -- anti race-condition en pagos concurrentes | **CRITICAL** | `business_service.py` |
| `resolver_o_crear_desde_factura_venta()` es idempotente (upsert por NIT normalizado) -- seguro para reintentos de ETL | **IMPORTANT** | `ClienteBusinessService`, verificado en tests de idempotencia |
| Contacto principal: `is_principal` marca el contacto de correspondencia oficial, unicidad `(cliente, email)` | **SUPPORTING** | `models.py` |
| `crear_cliente()` (shim legacy) sigue en uso por 2 tests, marcado deprecado en su propio docstring | **DERIVED/deuda** | Ya documentado en auditoria previa, P3 |

## FASE 2 — Mapa de dominio

```
Cliente (identidad legal, 1 por documento+empresa)
  |-- ContactoCliente (0..N, is_principal marca 1 preferido)
  `-- Cartera (0..N, escritura -- registrar_abono/registrar_cartera)
        (el LISTADO real viene de Factura.naturaleza='VENTA', no de aqui)
```

**Estados:** `Cliente.activo` (bool). `Cartera.estado_pago`
(`SIN_PAGO -> PARCIAL -> PAGADA`, transicion automatica en `save()`
segun `valor_pagado` vs `valor_total` -- sin transiciones invalidas
posibles porque se recalcula siempre desde los montos, no se setea
manualmente).

## FASE 6 — ORM/BD: verificacion N+1

Confirmado intacto el patron anti-N+1 explicito de esta app:
`ClienteViewSet.list()` hace **exactamente 2 queries por pagina**
(clientes paginados + `get_cartera_resumen()` bulk para todos los
UUIDs de la pagina en una sola query de agregacion), pasado via
`context['cartera_map']` al serializer -- el serializer NO ejecuta
queries adicionales por fila. Verificado en
`api/viewsets.py:164-167` y `selectors.py:115`. **Sin hallazgos de
N+1.**

## FASE 11 — Frontend

Sin auditoria linea por linea en esta pasada (app ya paso por
refactor v2.61 "Clean Code" documentado en `_archive/`). Estructura
modular confirmada en la auditoria previa (8 modulos JS por
responsabilidad).

## Codigo muerto / duplicacion / normativa

Sin hallazgos nuevos. `crear_cliente()` sigue como deuda P3 conocida
(2 tests la usan, no bloqueante). Normativa: confirmado que `clientes`
es solo configuracion, el calculo real vive en `contabilidad`
(ya verificado end-to-end en la mision anterior).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio construido
- [x] N+1 verificado -- patron anti-N+1 explicito confirmado intacto
- [x] Frontend -- bajo riesgo, ya refactorizado
- [x] Sin cambios de codigo -> sin necesidad de validacion puntual nueva

**APP = COMPLETED.**
