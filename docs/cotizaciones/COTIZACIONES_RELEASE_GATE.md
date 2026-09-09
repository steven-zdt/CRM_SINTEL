# Cotizaciones — Release Gate (misión de modernización integral, FASE 55/56)

**Fecha:** 2026-08-27

---

## Veredicto: `COTIZACIONES = COMPLETED_WITH_DEFERRED`

No se usa `PRODUCTION_READY` (prohibido por la propia misión mientras exista deuda), pero tampoco `BLOCKED_SAFE` — no hay ningún bloqueo real de CRUD, fuga de tenant, bypass de autorización, corrupción de relaciones ni pérdida de datos confirmada. El flujo principal (crear/editar/eliminar Cotización con items, PDF, numeración) funciona de punta a punta, verificado en vivo.

---

## Checklist (FASE 55)

- [x] CREATE backend — confirmado atómico, con DSV real (auditoría CRUD previa + confirmado de nuevo hoy por agente de seguridad).
- [x] CREATE frontend — bug real de `Content-Type` (415) corregido y verificado en vivo hoy (commit `3aff2b9`).
- [x] READ — selectors correctos, sin N+1 en list/detail (confirmado 2 veces, auditoría CRUD + agente de performance de hoy).
- [x] UPDATE — funcional; `estado` es editable sin validación de transición (**deuda documentada, no cerrada — ver abajo**).
- [x] DELETE/ANULAR — corregido hoy (protección contra romper trazabilidad si hay Factura vinculada) y en la auditoría CRUD previa (Service Layer).
- [x] Items CRUD — atómico, snapshot pattern intacto, N+1 de recálculo corregido hoy.
- [x] Configuración CRUD — corregido hoy: DELETE vía Service Layer, TOCTOU de `nombre_configuracion` cerrado con `UniqueConstraint`, bug de `reload()` corregido.
- [x] Producto CRUD — backend completo; frontend corregido hoy (fallo silencioso, doble-submit, botón "Editar" inerte) — **pero ver hallazgo nuevo abajo: la UI del catálogo es inalcanzable hoy**.
- [x] Servicio CRUD — mismo estado que Producto.
- [x] Cálculos — backend es SSoT confirmado; frontend recalcula en paralelo con la misma fórmula (no inventa reglas), un bug real de filtro corregido hoy (`INFRAESTRUCTURA`→`MATERIAL`).
- [x] Fechas — bug real de `fecha_emision` corregido (con una regresión real detectada y corregida en la misma pasada, documentada).
- [x] Numeración — atómica (`select_for_update`), sin hallazgos nuevos.
- [x] PDF — sin duplicación activa; un método muerto ya eliminado.
- [x] Permisos — reutiliza infraestructura existente, sin RBAC nuevo.
- [x] Tenant/Empresa — confirmado seguro (DSV real en toda la cadena, incluido el código nuevo de hoy) por auditoría dedicada.
- [x] Sede — opcional/informativa, sin cambios necesarios.
- [ ] Área — no aplica al dominio (sin evidencia de que se necesite, no se inventó).
- [x] Cliente — SSoT respetado, DSV confirmado y ahora con test real.
- [ ] Proyecto — no aplica (confirmado, el modelo real no tiene este campo).
- [x] Integraciones — confirmado con evidencia negativa que Cotización→Venta no existe; no se inventó.
- [x] Frontend — auditado exhaustivamente (FASES 27-39); bugs reales corregidos, fricción documentada donde no se corrigió.
- [x] Responsive — auditado, sin bugs reales (una fricción documentada en móvil, no crítica).
- [x] Accesibilidad — auditado, cumple el mínimo (`title` en botones de icono); mejora opcional documentada (`aria-label`).
- [x] Performance — N+1 real corregido hoy; un patrón de petición redundante documentado, no corregido (friccion menor).
- [x] Tests existentes saneados — inventariados, ninguno duplicado/obsoleto; ampliados con 5 tests nuevos reales hoy.
- [x] Governance — `manage.py check` limpio, 2 migraciones nuevas generadas/aplicadas a los 3 tenants reales sin conflicto, verificadas contra duplicados existentes antes de aplicar.
- [ ] Documentación — este documento + `COTIZACIONES_AUDIT_BASELINE.md` (completos). `COTIZACIONES_END_TO_END.md`/`COTIZACIONES_UI_GUIDE.md` — ver estado abajo.

---

## Hallazgo nuevo más importante de esta pasada: el catálogo Producto/Servicio es inalcanzable en la UI real

Durante la verificación en vivo del fix del botón "Editar" (que sí corregí y verifiqué funcionando a nivel de API), se descubrió algo más profundo: **ningún template real de la aplicación contiene los contenedores `#table-productos` / `#table-servicios`** que `cotizaciones.main.js` busca para inicializar las grillas (`grep` de `table-productos`/`table-servicios` en todo `templates/tenant/cotizaciones/` → 0 resultados). El código de inicialización ya es defensivo (`if (features.productoList && d.getElementById('table-productos'))`), así que no falla — simplemente nunca se ejecuta.

**Esto significa que hoy, en la aplicación real, no hay ningún punto de entrada de UI para ver, crear o editar Productos/Servicios del catálogo propio de Cotizaciones.** El backend completo existe y funciona (confirmado con pruebas reales), los formularios existen y ahora están corregidos (create y editar), pero no hay ninguna pestaña/sección que los muestre.

Esto es coherente con otro hallazgo ya confirmado hoy por el agente de seguridad (FASE 43.3): el picker de ítems del editor de Cotización (`editor_cotizacion.html`) **no usa este catálogo en absoluto** — los ítems se ingresan como texto libre (descripción/cantidad/costo/utilidad), no seleccionando un Producto/Servicio existente. El catálogo y el flujo real de creación de ítems están completamente desconectados entre sí.

**Decisión de esta auditoría: no se construyó una pestaña/sección nueva para el catálogo.** Construir una UI nueva (navegación, tab, botones "Nuevo Producto"/"Nuevo Servicio" reales) es una pieza de trabajo genuinamente nueva, no una corrección — y la Regla Absoluta #4 pide no inventar sin evidencia de necesidad real de negocio. No hay evidencia de que los usuarios reales necesiten un catálogo separado de Producto/Servicio si el flujo real de creación de cotizaciones nunca lo consume. **Se deja como GAP_DE_NEGOCIO explícito, con dos preguntas reales para quien decida el rumbo del producto:**
1. ¿Debe existir un catálogo Producto/Servicio navegable independientemente (y si es así, dónde en la navegación)?
2. ¿Debe el picker de ítems de Cotización consumir este catálogo (autocompletar desde Producto/Servicio) en vez de solo texto libre?

Los fixes de backend/frontend que sí se hicieron hoy (DELETE vía Service Layer, botón Editar conectado, manejo de errores corregido, bug de locale en el value del input) siguen siendo correctos y quedan listos para el día en que exista un punto de entrada real — no se revirtió nada, solo se documenta que hoy no son alcanzables por un usuario real.

---

## Otra deuda documentada explícitamente (no inventada, no cerrada)

- **Máquina de estados de Cotización**: el campo `estado` (`BORRADOR/ENVIADA/ACEPTADA/CANCELADA`) sigue sin ninguna transición con respaldo en código — confirmado de nuevo hoy (Regla Absoluta #5: no crear estados/transiciones nuevas sin evidencia de qué necesita el negocio realmente).
- **Conversión Cotización→Venta**: confirmado de nuevo con evidencia negativa que no existe. No se inventó.
- **Fricción de UX no corregida** (documentada, no crítica): recarga completa de página tras cada guardado de Cotización; falta de búsqueda en las grillas de Producto/Servicio/Plantilla; petición redundante al abrir "Editar Cotización" (el detalle prefetchea items que se descartan, luego se vuelven a pedir por separado).
- **Item_service.py sin DSV para producto/servicio en items**: confirmado no explotable hoy (el campo no está expuesto en ningún serializer), pero documentado como riesgo latente si se conecta el catálogo a los items en el futuro (ver pregunta 2 de la sección anterior) — quien construya esa conexión deberá agregar el mismo patrón DSV que ya existe en `business_service.py` para cliente/configuración.

---

## Resumen de commits de esta misión

Todos los cambios de código de esta pasada (backend + frontend + 2 migraciones + 5 tests nuevos) se consolidan en un solo commit tras la verificación final de la suite completa (ver mensaje de commit para el detalle línea por línea).

---

## Actualización 2026-09-08 — COTIZACIONES-01: máquina de estados + Cotización→Venta

**Veredicto actualizado:**

```
COTIZACIONES = COMPLETED_WITH_DEFERRED
```

Se mantiene el mismo veredicto (no `VERIFIED` puro) porque el catálogo
Producto/Servicio inalcanzable en UI (arriba) sigue sin resolver — es un
`GAP_DE_NEGOCIO` explícito, no algo que esta misión debía decidir. Pero los
2 gaps más grandes de "Otra deuda documentada" (§61-66 arriba) **se cierran
en esta pasada**:

- ✅ **Máquina de estados**: `CotizacionService.TRANSICIONES_VALIDAS` +
  `cambiar_estado()`. `estado` removido de `allowed_fields` — ya no es
  editable vía `PATCH` genérico. Endpoints `enviar/volver-a-borrador/
  aceptar/cancelar`. Nombres reales (`BORRADOR/ENVIADA/ACEPTADA/CANCELADA`),
  no los `APROBADA/ARCHIVADA` que asumía el mission brief original — decisión
  explícita del usuario tras verificar que esos nombres no existen en el
  dominio real. Detalle completo: `docs/cotizaciones/COTIZACIONES_STATE_MACHINE.md`.
- ✅ **Cotización→Venta**: `CotizacionService.convertir_a_venta()`, endpoint
  `convertir-a-venta`. Solo desde `ACEPTADA`, idempotente (`Venta.
  cotizacion_uuid` nuevo campo `unique=True` + `select_for_update`). Items
  copiados como snapshot (sin vincular catálogo de Inventario — no existe
  mapeo real entre `cotizaciones.Producto/Servicio` e `inventario.Producto/
  Servicio`, ver `COTIZACIONES_INTEGRATIONS.md`).
- ✅ **H8** (gap de aislamiento sin explotar, hallado en esta pasada):
  `get_cotizacion_for_totals`/`get_items_subtotal` ahora exigen `empresa_id`.

**No tocado en esta pasada** (decisión explícita del usuario, ver
`COTIZACIONES_FLOW.md`): el bridge manual `Factura.cotizacion_uuid` (salta
Ventas) se deja como está — ya tiene datos reales en producción. El catálogo
Producto/Servicio inalcanzable en UI sigue como `GAP_DE_NEGOCIO`. Permisos
se mantienen binarios (mismo criterio ya aplicado a `proveedores` en la
misma sesión).

**Governance**: `manage.py check` limpio, `makemigrations --check --dry-run`
limpio, 1 migración nueva (`tenant_ventas.0004_venta_cotizacion_uuid`,
aditiva) aplicada a los 3 tenants reales sin conflicto. Tests: **42 passed,
0 failed** (suite completa de `apps/tenant/cotizaciones/tests/`, venv local
— incluye los 22 preexistentes + 20 nuevos: 13 de máquina de estados, 7 de
conversión a venta).

Documentación nueva de esta pasada: `docs/cotizaciones/
COTIZACIONES_STATE_MACHINE.md`, `COTIZACIONES_INTEGRATIONS.md`,
`COTIZACIONES_FLOW.md`.
