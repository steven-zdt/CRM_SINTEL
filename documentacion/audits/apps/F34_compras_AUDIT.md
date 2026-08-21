# F34_compras_AUDIT — Auditoria integral de negocio/arquitectura (app 7/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_compras_AUDIT.md` (0 codigo muerto, 2 correcciones de seguridad
re-verificadas vigentes).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** por instruccion explicita del usuario, esta pasada NO
ejecuta tests -- validacion por evidencia estatica unicamente
(`py_compile` + grep repo-wide de consumidores).

---

## Resumen ejecutivo

`compras` gestiona el ciclo de vida de Ordenes de Compra
(`BORRADOR -> PENDIENTE -> APROBADA -> RECIBIDA/ANULADA`) y
Recepciones. Sin cambios de codigo en esta pasada -- barrido fresco
simbolo-por-simbolo (mismo rigor que encontro el hallazgo en
`inventario`) NO encontro el patron de "facade de conveniencia nunca
adoptado" aqui.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| `sede` se resuelve UNA vez en la capa API (`SintelDSVMixin.get_sede_id()`) y se pasa explicito a `crear_orden()` -- la capa CRUD nunca re-deriva sede | **CRITICAL** (ADR-003) | Comentario explicito en `crud_service.py:90-98` |
| Edicion de cabecera/items bloqueada segun estado (`BORRADOR`/`PENDIENTE`=solo admin editable, `APROBADA`+=inmutable salvo asociar DocSoporte) | **CRITICAL** | `.agent/` doc, tabla de estados |
| Consecutivo asignado atomicamente con `select_for_update()` + `F('consecutivo_actual')+1` | **CRITICAL** | `business_service.py`, ya verificado vigente en auditoria previa |
| Una orden de compra debe tener al menos 1 item (`ValidationError` si `items_a_crear` vacio) | **IMPORTANT** | `crud_service.py:157` |
| Totales de cabecera (subtotal/impuestos/total) se derivan SIEMPRE de la suma de items, nunca se aceptan del payload directamente | **IMPORTANT** | `crear_orden()`, recalculo explicito linea por linea |
| `get_permissions()` nunca debe tener un bypass `if settings.DEBUG: return []` | **CRITICAL** (leccion de un bug real, BUG-04) | Re-verificado ausente en esta pasada tambien (ver FASE 9) |

## FASE 2 — Mapa de dominio

```
PlantillaOrdenCompra (perfil de numeracion: prefijo+rango+consecutivo)
  `-- OrdenCompra (BORRADOR|PENDIENTE|APROBADA|RECIBIDA|ANULADA)
        |-- ItemOrdenCompra (1..N, subtotal/iva/total calculados)
        `-- RecepcionCompra (0..N, confirma/anula, vincula a Kardex via item_inventario_uuid)
```

## FASE 6 — ORM/BD: verificacion N+1

- `OrdenCompraSelector.get_list()`/`get_detail()`: `select_related`
  (proveedor/proyecto/documento_soporte/plantilla) +
  `prefetch_related('items')` en detalle -- confirmado.
- `RecepcionCompraSelector.get_list()`/`get_detail()`: mismo patron,
  `select_related` + `prefetch_related('items')`.
- `OrdenCompraCRUDService.crear_orden()`: usa `ItemOrdenCompra.objects.
  bulk_create(items_a_crear)` -- NO crea items uno por uno en un loop
  con `.save()` individual. **Sin hallazgos de N+1.**

## FASE 9 — Permisos (re-verificacion puntual)

Re-confirmado en esta pasada (grep de `settings.DEBUG` en
`api/viewsets.py`): **sin bypass**. Los 3 `get_permissions()` del
archivo usan el patron correcto `[IsTenantMember(),
IsTenantAdminOrReadOnly()]`.

## FASE 12/13 — Codigo muerto / duplicacion

Barrido fresco de `services/business_service.py` y
`services/crud_service.py`: **sin funciones module-level sueltas
duplicando metodos de clase** (a diferencia de lo encontrado en
`inventario`) -- toda la logica vive dentro de
`OrdenCompraBusinessService`/`RecepcionCompraBusinessService`/
`*CRUDService`, todos exportados 1:1 en `services/__init__.py` y
consumidos por `api_mixins.py`. **Sin hallazgos nuevos.**

## Normativa (FASE 14)

Sin cambios -- confirmado en la mision anterior que `compras` es
workflow puro (sin logica de retencion). `porcentaje_iva` sin validar
tarifas vigentes sigue como deferred P3 conocido, sin accion en esta
pasada (bajo riesgo, documento interno).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio
- [x] N+1 verificado -- `select_related`/`prefetch_related`/`bulk_create` consistentes
- [x] Permisos re-verificados -- sin bypass
- [x] Codigo muerto -- barrido fresco, sin hallazgos nuevos
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
