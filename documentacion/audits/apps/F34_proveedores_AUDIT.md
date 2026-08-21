# F34_proveedores_AUDIT — Auditoria integral de negocio/arquitectura (app 5/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_proveedores_AUDIT.md` (0 codigo muerto detectado en esa pasada,
pero **hallazgo P1 -> P3**: `obtener_configuracion_retenciones()`/
`calcular_componentes_retencion()` confirmadas dead-code real tras
verificar en `gastos`/`contabilidad` que el mecanismo real vive en
`contabilidad.RetencionesService`). **Esta pasada F34 ejecuta esa
limpieza pendiente.**

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`proveedores` es el directorio de acreedores con conformidad fiscal
(NIT, regimen, CIIU), cuentas por pagar y representantes. La mision
anterior habia dejado como deuda diferida (P3, informativo) la
eliminacion de 2 metodos de calculo de retenciones confirmados como
codigo muerto real (nunca conectados a ningun flujo, con tarifas
hardcodeadas 4%/0.966% que ademas eran normativamente fragiles). F34
ejecuta esa limpieza con el mismo rigor de evidencia, y en el proceso
encuentra un tercer metodo muerto no detectado antes.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| Identidad unica por `(empresa, tipo_documento, numero_documento)` | **CRITICAL** | `UniqueConstraint` |
| `CuentasPagar.estado_pago` se recalcula siempre desde `valor_pagado`/`valor_total` en `save()` (nunca se setea manualmente) | **CRITICAL** | `models.py`, mismo patron que `clientes.Cartera` |
| `registrar_abono()` usa `select_for_update()` | **CRITICAL** | anti race-condition |
| El calculo REAL de retenciones a proveedores vive en `contabilidad.RetencionesService` (Pull Model), NO en `proveedores` | **CRITICAL** (arquitectonica, verificada end-to-end en la mision anterior) | `gastos.business_service.py` llama a `contabilidad.RetencionesService`, no a `proveedores` |
| `Representante.es_principal` marca el contacto para correspondencia oficial | **SUPPORTING** | `models.py` |
| `eliminar_proveedor()` requiere `activo=False` primero | **IMPORTANT** | `business_service.py`, mismo patron que `clientes` |

## FASE 2 — Mapa de dominio

```
Proveedor (identidad legal + perfil fiscal: autoretenedor, gran_contribuyente, responsable_iva)
  |-- Representante (0..N, es_principal marca 1)
  `-- CuentasPagar (0..N, escritura -- registrar_cartera/registrar_abono)
```

## FASE 12/13 — Codigo muerto (ACCION TOMADA EN ESTA PASADA)

Verificado con grep repo-wide (Grep tool, no bash directo por
timeout en un grep recursivo sin filtro de extension) que **ninguno
de los siguientes tiene consumidores fuera de su propio archivo**:

| Metodo | Lineas | Motivo de muerte |
|---|---|---|
| `ProveedorBusinessService.obtener_configuracion_retenciones()` | ~24 | Ya confirmado dead en la auditoria anterior (P3 pendiente) |
| `ProveedorBusinessService.calcular_componentes_retencion()` | ~20 | Idem, unico consumidor real era `obtener_configuracion_retenciones`-adyacente |
| `ProveedorBusinessService.calcular_neto_gasto()` | ~19 | Solo lo llamaba `calcular_componentes_retencion` |
| `ProveedorBusinessService._normalize_percentage_for_calculation()` | ~7 | Solo lo llamaba `calcular_componentes_retencion` |
| `ProveedorBusinessService._format_percentage_choice()` | ~6 | **Hallazgo NUEVO de esta pasada F34** -- cero consumidores en todo el repo (ni siquiera dentro del propio archivo), no detectado en la auditoria anterior porque esa pasada no reviso esta funcion especifica |

**DEAD_CONFIRMED, eliminado:** toda la seccion "2. FINANCIAL
CALCULATIONS (SSoT)" completa (`calcular_neto_gasto`,
`obtener_configuracion_retenciones`, `calcular_componentes_retencion`)
mas los 2 helpers (`_normalize_percentage_for_calculation`,
`_format_percentage_choice`) mas el propio `_to_decimal()` (que
tras la limpieza quedo sin ningun consumidor real -- todas sus
llamadas estaban dentro del cluster eliminado). Imports huerfanos
limpiados: `ROUND_HALF_UP`, `InvalidOperation` (de `decimal`) -- `
Decimal` se conserva, sigue usado en `crud_service`-adyacente
(`registrar_cartera`/`registrar_abono`, lineas 258/290/291).

**Total eliminado: ~76 lineas + 2 imports huerfanos.**

`_sanitize_retenciones()` y `_get_contacto_proveedor_model()`
(vecinos en el archivo) **NO se tocaron** -- confirmados activos en
la auditoria previa y en esta.

## FASE 17 — Validacion puntual

Cambio de codigo real -> regresion ejecutada
(`apps/tenant/proveedores/`): **18 passed, 0 failed, 2 warnings
preexistentes (min_value DRF) en 1657.64s (0:27:37)** -- coincide
exactamente con el baseline conocido, confirma que el codigo muerto
eliminado no tenia ningun efecto en el comportamiento real.

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio
- [x] Codigo muerto eliminado (deuda pendiente de la mision anterior + 1 hallazgo nuevo), evidencia completa
- [x] Regresion puntual -- 18/18 passed, 0 failed
- [x] `py_compile` limpio

**APP = COMPLETED.**
