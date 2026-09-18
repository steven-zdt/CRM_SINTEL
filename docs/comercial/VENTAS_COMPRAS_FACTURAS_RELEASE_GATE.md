# VENTAS_COMPRAS_FACTURAS_RELEASE_GATE

Mision VENTAS-COMPRAS-FACTURAS-01 (2026-09-09). Ver `VENTAS_COMPRAS_FACTURAS_FLOW.md`
(flujo real/objetivo) y `VENTAS_COMPRAS_FACTURAS_DEPENDENCIES.md` (matriz
completa). Decision critica confirmada explicitamente por el usuario antes
de tocar codigo (bloquear por completo, no dejar flag reactivable por
entorno).

## Veredicto

```
VENTAS_COMPRAS_FACTURAS_01 = COMPLETED_WITH_DEFERRED
```

## Hallazgos (formato ID/APP/ARCHIVO/SIMBOLO/LINEAS/SEVERIDAD/REGLA/RIESGO/ACCION/TEST/EVIDENCIA/ESTADO)

### VCF-001 — Ventas emitia Facturas electronicas reales (CRITICO)

```
APP: ventas
ARCHIVO: apps/tenant/ventas/services/business_service.py
SIMBOLO: VentaBusinessService.procesar_y_facturar_venta()
LINEAS: 491-698 (metodo completo, pipeline DIAN en pasos 5a-5d)
SEVERIDAD: CRITICO
REGLA AFECTADA: "VENTAS -X-> CREAR FACTURA" (Fase 2 de la mision)
DEPENDENCIAS: cotizaciones (facturar_venta_de_cotizacion hereda el camino),
              facturas (crear_factura_desde_venta), core.dian (XadesSignerService,
              AttachedDocumentService)
RIESGO: emision fiscal no autorizada por la DIAN, expuesta via HTTP real
        (POST /api/v1/ventas/{uuid}/procesar-facturar/) y usada activamente
        en tests de regresion (COMERCIAL-04, F23)
ACCION: barrera de codigo (EMISION_FISCAL_VENTA_AUTORIZADA = False),
        rechazo 403 antes de cualquier escritura, codigo DIAN no eliminado
TEST: apps/tenant/ventas/tests/test_bloqueo_emision_fiscal.py (nuevo)
EVIDENCIA: ver "Corrida real de tests" abajo
ESTADO: RESUELTO
```

### VCF-002 — UI ofrecia "Facturar DIAN"/"Guardar y Facturar DIAN" en Ventas (ALTO)

```
APP: ventas
ARCHIVO: apps/tenant/ventas/templates/tenant/ventas/offcanvas_detalle_venta.html,
         offcanvas_crear_venta.html
SIMBOLO: boton [data-venta-action="facturar-dian"], boton #btn-facturar-dian
LINEAS: offcanvas_detalle_venta.html (bloque BORRADOR), offcanvas_crear_venta.html (footer)
SEVERIDAD: ALTO
REGLA AFECTADA: Fase 12 ("la UI NO debe mostrar botones Crear/Generar/Emitir/
                Transmitir Factura en Ventas")
DEPENDENCIAS: venta_editor.js (ya usaba `if (btnDian)` -- verificado seguro
              remover el boton sin tocar JS)
RIESGO: UX rota -- el usuario podia clickear un boton que ahora siempre
        devuelve 403, sin explicacion
ACCION: botones removidos del HTML (comentario explicativo dejado en su
        lugar), JS intacto (guards ya defensivos)
TEST: N/A (cambio de UI puro, sin logica) -- verificado manualmente que
      venta_editor.js no rompe (grep confirmando `if (btnDian)`/`if (btnD)`)
EVIDENCIA: diff de ambos templates
ESTADO: RESUELTO
```

### VCF-003 — Compras nunca tuvo relacion con Facturas (INFORMATIVO)

```
APP: compras
ARCHIVO: apps/tenant/compras/ (todo el modulo)
SIMBOLO: N/A
LINEAS: N/A
SEVERIDAD: INFORMATIVO
REGLA AFECTADA: "COMPRAS -X-> CREAR FACTURA" (ya cumplida)
DEPENDENCIAS: ninguna con facturas
RIESGO: ninguno
ACCION: ninguna -- confirmado con auditoria completa (405 lineas de
        AUDITORIA_FLUJO_COMPRAS.md, grep exhaustivo 0 resultados de codigo
        real relacionado con Factura)
TEST: N/A
EVIDENCIA: apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md
ESTADO: CONFIRMADO SIN CAMBIOS
```

### VCF-004 — No existe contrato de consumo Factura->Ventas/Compras (DEFERRED)

```
APP: ventas, compras, facturas
ARCHIVO: N/A (no implementado)
SIMBOLO: N/A
LINEAS: N/A
SEVERIDAD: MEDIO (funcionalidad faltante, no un bug)
REGLA AFECTADA: Fase 4/8/9 de la mision (contrato de consumo Factura -> Ventas/Compras)
DEPENDENCIAS: FacturaInterAppAPI (existe, candidato correcto, 0 imports desde
              ventas/compras hoy)
RIESGO: ninguno inmediato -- no implementar nada es mas seguro que inventar
        una regla de matching sin evidencia
ACCION: DEFERRED explicito -- decisiones de negocio pendientes documentadas
        en VENTAS_COMPRAS_FACTURAS_FLOW.md seccion "DEFERRED"
TEST: N/A
EVIDENCIA: grep FacturaInterAppAPI en apps/tenant/{ventas,compras}/ -> 0 resultados
ESTADO: DEFERRED (requiere decision del usuario)
```

### VCF-005 — `Venta.factura_asociada` es FK directa, no soft-reference (BAJO)

```
APP: ventas
ARCHIVO: apps/tenant/ventas/models.py
SIMBOLO: Venta.factura_asociada
LINEAS: 174-181
SEVERIDAD: BAJO
REGLA AFECTADA: Bounded Context §18 (patron de soft-reference UUID sin FK,
                usado consistentemente por facturas.cliente_uuid/proveedor_uuid/
                cotizacion_uuid)
DEPENDENCIAS: ninguna nueva -- ya existente, on_delete=SET_NULL
RIESGO: bajo -- no genera import circular real (ventas no importa modelos.py
        de facturas en codigo Python, solo en la migracion Django), pero es
        inconsistente con el patron establecido
ACCION: ninguna en esta mision -- cambiar a soft-reference es un refactor de
        esquema con riesgo de datos no justificado sin evidencia de un
        problema real
TEST: N/A
EVIDENCIA: apps/tenant/ventas/models.py:174
ESTADO: DEFERRED (documentado, no bloqueante)
```

## Prohibiciones verificadas (Fase 25 de la mision)

```
[x] No se creo un segundo FacturaService
[x] No se creo un segundo parser XML
[x] No se creo otra relacion paralela Factura/Venta
[x] No se creo otro mecanismo de Inventario
[x] No se creo otro mecanismo contable
[x] No se creo otro dependency graph
[x] No se introdujo un RBAC nuevo
[x] No se modifico Contabilidad (sin necesidad demostrada)
[x] No se elimino codigo DIAN existente (CUFE/UBL/XAdES intactos, solo inalcanzables)
```

## Corrida real de tests

```
apps/tenant/ventas/tests/test_bloqueo_emision_fiscal.py -- 6 passed (0:19:59)
  incluye test_http_procesar_facturar_no_crea_factura_nueva (la prueba
  explicita que pide la Fase 8: POST Venta -> NO aparece nueva Factura)

apps/tenant/ventas/tests/test_comercial_04_idempotencia.py
apps/tenant/ventas/tests/test_f23_venta_inventario.py
apps/tenant/ventas/tests/test_f23_venta_inventario_multitenant.py
apps/tenant/cotizaciones/tests/test_facturar_venta.py
  -- 16 passed (0:35:15) -- pipeline DIAN interno (CUFE/XML/firma) y
  salida de inventario siguen intactos con el flag mockeado a True

apps/tenant/contabilidad/tests/test_f24_e2e_multitenant_dsv.py
apps/tenant/contabilidad/tests/test_f24_e2e_circuito_completo.py
  -- 10 passed (0:25:30) -- circuito completo Compra+Venta+Contabilidad
  sin romperse, aislamiento multi-tenant intacto

TOTAL: 32 passed, 0 failed
```

`manage.py check`: **PASS** ("System check identified no issues").
`manage.py makemigrations --check --dry-run`: **PASS** ("No changes
detected") -- confirma 0 cambios de esquema, como se esperaba (esta
mision es puramente Service Layer + UI).

## DEFERRED (resumen)

1. Contrato de consumo `Factura VENTA -> Venta` (matching, creacion/actualizacion) -- VCF-004
2. Contrato de consumo `Factura COMPRA -> Compra/Recepcion` -- VCF-004
3. `Venta.factura_asociada` como soft-reference (consistencia arquitectonica) -- VCF-005

## Siguiente mision natural

Con la barrera de emision fiscal cerrada (bloqueante resuelto), el
siguiente paso real -- SOLO si el usuario decide las preguntas abiertas de
VCF-004 -- seria una mision dedicada exclusivamente al contrato de consumo
`Factura -> Ventas/Compras`, reutilizando `FacturaInterAppAPI` como base.
No debe iniciarse sin que el usuario responda las preguntas de matching/
idempotencia documentadas en `VENTAS_COMPRAS_FACTURAS_FLOW.md`.
