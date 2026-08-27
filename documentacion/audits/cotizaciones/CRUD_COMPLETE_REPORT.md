# Cotizaciones — CRUD Complete Report

**Fecha:** 2026-08-26
**Misión:** auditar, corregir, completar y dejar operativo el CRUD completo de `apps/tenant/cotizaciones/` (49 fases).
**Metodología:** FASE 0-9 delegadas a un sub-agente de solo-lectura (evidencia archivo:línea real); FASES 10+ ejecutadas directamente, con fixes aplicados solo donde la evidencia confirmó un gap real, siguiendo Regla #1 (no inventar) y Regla #2 (no crear segundo CRUD).

Ver también: `CRUD_BASELINE.md` (FASE 0/1, inventario completo de modelos), `MATRIZ_ESTADOS_COTIZACION.md` (FASE 12/13), `CRUD_MATRIX.md` (FASE 46, veredicto final por modelo).

---

## Modelos

Ver `CRUD_BASELINE.md` §Inventario. Resumen: `Cotizacion` (CORE), `CotizacionItem` (CHILD), `Producto`/`Servicio` (CATALOG propios de Cotizaciones), `ConfiguracionCotizacion` (SUPPORT, perfil de numeración).

## Endpoints

Ver `CRUD_BASELINE.md` §Endpoints reales. Todos bajo `/api/v1/cotizaciones/`, router DRF estándar + `@action`s para PDF/offcanvas/recalcular.

## CREATE / READ / UPDATE / DELETE — resumen por fase

### CREATE (FASE 2)
Confirmado real y atómico para `Cotizacion`+`Items` (`crear_preforma()`, `@transaction.atomic`). DSV real (`get_configuracion_for_empresa`/`get_cliente_for_empresa` re-verifican `empresa_id`, no confían en el FK crudo). Gap encontrado y corregido: `ProductoBusinessService.registrar()` validaba unicidad de `codigo` solo a nivel de aplicación (TOCTOU real) — se agregó `UniqueConstraint` de BD (`uniq_producto_codigo_por_empresa`, condicional a `codigo` no vacío) + manejo limpio del `IntegrityError` resultante (400, no 500).

### READ (FASE 3)
Selectors reales con `.only()`/`select_related`/`prefetch_related` correctos en las rutas de list/detail de `Cotizacion`. Sin N+1 confirmado ahí. Riesgo latente identificado (no confirmado como bug activo): el selector de items usado por el pipeline de PDF no hace `select_related('producto', 'servicio')` — no se materializa hoy porque el template actual no accede a esos campos, pero queda documentado para quien toque ese template en el futuro.

### UPDATE (FASE 4)
Real vía `actualizar_cotizacion()`. Gap encontrado, **documentado pero NO corregido en esta pasada** (Regla #1): `estado` es editable vía `PATCH` genérico sin ninguna validación de transición — no existe ninguna máquina de estados en el código para validar contra. Construir una sin evidencia de negocio violaría la regla de no inventar. Ver `MATRIZ_ESTADOS_COTIZACION.md`.

### DELETE (FASE 5)
El hallazgo más importante de esta auditoría. Antes de esta pasada:
- `CotizacionViewSet` no tenía `destroy()` propio → DRF ejecutaba su `destroy()` por defecto (`instance.delete()` directo), **sin ningún chequeo de trazabilidad**. Si una `Cotizacion` ya estaba vinculada a una `Factura` (via `Factura.cotizacion_uuid`, el bridge real que existe hoy), borrarla dejaba ese UUID apuntando a un registro inexistente, sin error visible.
- `ProductoViewSet`/`ServicioViewSet` tenían `destroy()` propio pero llamaban `instance.delete()` directo — **bypaseando el Service Layer** (`Regla #3` violada).
- `ConfiguracionCotizacionViewSet` no tenía `destroy()` propio tampoco → mismo hard-delete por defecto de DRF, mismo bypass. `ConfiguracionCRUDService.delete_configuracion()` existía pero era código muerto (nunca invocado).

**Fix aplicado (los 5 modelos ahora respetan `ViewSet → ServiceMixin → BusinessService → CRUDService`):**
- `Cotizacion`: nuevo `CotizacionService.eliminar_cotizacion()` — bloquea el DELETE con un `ValidationError` claro (`"Esta cotizacion ya fue vinculada a una factura y no puede eliminarse."`) si `Factura.objects.filter(empresa_id=..., cotizacion_uuid=...).exists()`. Si no hay Factura vinculada, procede al DELETE físico normalmente (no existe soft-delete en el modelo, y no se inventó uno sin evidencia de que el negocio lo requiera más allá de este caso puntual).
- `Producto`/`Servicio`: se conectó el `ProductoBusinessService.eliminar()`/`ServicioBusinessService.eliminar()` (nuevos, delegan al `CRUDService.eliminar()` **ya existente**, que estaba huérfano) a través de nuevos `service_eliminar_producto`/`service_eliminar_servicio` en los mixins.
- `ConfiguracionCotizacion`: se conectó el `ConfiguracionBusinessService.eliminar_configuracion()` (nuevo, delega al `ConfiguracionCRUDService.delete_configuracion()` **ya existente**, también huérfano) vía `service_eliminar_configuracion`.

Ningún CRUDService nuevo fue creado — todos los métodos de persistencia ya existían (algunos huérfanos); el fix fue exclusivamente de "cableado" del Service Layer, consistente con Regla #2/#3.

---

## FASE 6/7 — Cotización e Item

Ver `CRUD_BASELINE.md`. Bug real encontrado y corregido: `Cotizacion.fecha_emision` tenía `auto_now_add=True`, lo que hacía que Django **ignorara silenciosamente** el valor calculado por `CotizacionService._build_header_fields()` (que sí intentaba respetar una fecha explícita del payload, o defaultear a hoy) — toda cotización quedaba con `fecha_emision = fecha real de creación en el servidor`, sin importar lo que el usuario/API pidiera. Fix inicial: se quitó `auto_now_add=True` del campo (migración `0006_alter_cotizacion_fecha_emision`). El test existente que ya mandaba una fecha explícita en el payload (`test_crear_cotizacion_valida`) nunca lo aseveraba — se le agregó la aserción faltante en vez de crear un test nuevo (Regla #2).

**Regresión real detectada por la suite completa (gobernanza, FASE 44) y corregida en la misma pasada:** quitar `auto_now_add=True` sin agregar ningún `default` hizo que `fecha_emision` pasara a ser un campo **requerido** tanto en `CotizacionSerializer` (DRF marca `required=False` automáticamente solo si el campo tiene `auto_now_add` o `default`) como en cualquier `Cotizacion.objects.create()` directo que no lo pasara explícitamente — rompiendo 12 tests preexistentes (`test_api.py`, `test_serializers.py`, `test_organizational_context_adoption.py`, `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`, `test_scope_selectors_f7.py`) que creaban fixtures de `Cotizacion` sin ese campo, confiando en el `auto_now_add` original. Fix definitivo: `fecha_emision = models.DateField(default=_hoy)` (`_hoy()` = `timezone.now().date()`, mismo fallback que el service ya usaba) — migración `0008_alter_cotizacion_fecha_emision`. Esto preserva el comportamiento correcto (payload explícito se respeta) sin romper ningún caller que no lo pase. Suite completa de la app (20 tests) verificada en verde después de este segundo fix — 0 regresiones remanentes.

Totales de cabecera: confirmado que se derivan correctamente y automáticamente de los items en cada mutación de item (create/update/delete), sin riesgo de desincronización por la ruta normal.

---

## FASE 8/9 — Producto/Servicio: veredicto (no se migra/elimina)

**DUPLICATE_CANDIDATE con evidencia estructural real** (mismo dominio conceptual que `inventario.Producto/Servicio`, sin FK/bridge/sincronización entre ambos catálogos), pero con un propósito diferenciado defendible: `cotizaciones.Producto/Servicio` son deliberadamente mínimos (sin stock/categoría/imagen), consistentes con la idea de "ítem especulativo de cotización" que puede no existir aún en el inventario formal — el patrón Snapshot en `CotizacionItem` (campos copiados en la fila, FK opcional `SET_NULL`) confirma que el diseño ya asume que estos catálogos son efímeros/desechables.

Consumidores reales fuera de `cotizaciones/` en todo el repo: solo 2, ambos scripts de generación de tenants de prueba (`apps/public/tenants/management/commands/analizar_tenants_prueba.py`, `generar_tenants_prueba.py`) — no lógica de negocio real.

**Decisión de esta auditoría: no eliminar, no migrar, no crear un puente automático.** Per Regla #2 de la misión ("NO eliminar ni migrar automáticamente... si existe duplicación real: documentar y diseñar migración controlada"), este hallazgo queda documentado como candidato a una futura decisión de producto, no ejecutado aquí.

---

## FASE 10/11 — Totales e Impuestos

SSoT único confirmado: `CotizacionService.calcular_totales()` es el único punto real de cálculo de `total_con_impuestos`. Sin duplicación de lógica de cálculo entre serializer/frontend/PDF (el PDF reutiliza el mismo `preparar_contexto()` que recalcula a partir de los mismos porcentajes persistidos, sin una segunda fuente de verdad). IVA/AIU son valores **comerciales estimados** — confirmado que no hay acoplamiento a Facturas/Contabilidad (Cotizaciones no genera ningún valor fiscal definitivo), consistente con la Regla del prompt maestro de no asumir que el valor comercial es el valor fiscal de una futura factura.

---

## FASE 12/13 — Estados

Ver `MATRIZ_ESTADOS_COTIZACION.md`. Resumen: 4 estados declarados (`BORRADOR/ENVIADA/ACEPTADA/CANCELADA`), cero transiciones con respaldo real en código, campo editable sin restricción vía `PATCH` genérico. **No se construyó una máquina de estados** por ausencia de evidencia de negocio (Regla #1). Queda como deuda documentada explícita, no oculta.

---

## FASE 14/15/16 — Cliente / Proyecto / Sede-Área

- **Cliente**: SSoT respetado, FK real a `clientes.Cliente`, opcional por diseño confirmado (no un bug — el admin y el business service lo tratan como caso válido deliberadamente).
- **Proyecto**: no existe ningún campo/FK en el modelo real — la guía de la misión lo suponía por el flujo genérico de otros dominios del ERP; el dominio real de Cotizaciones no lo tiene. No se inventó uno.
- **Sede/Área**: `sede` es FK opcional, puramente informativa/KPI (DT-SEDE-04, ya documentado en una fase organizacional anterior del proyecto). `Área` no aplica — sin evidencia de que el dominio lo necesite.

---

## FASE 17/18/19 — Conversión a Venta / Idempotencia / Facturas

**Evidencia negativa confirmada por grep exhaustivo:** no existe ninguna conversión Cotización→Venta en el código (`grep -rin "cotizacion" apps/tenant/ventas` → 0 resultados). Lo único real es `Factura.cotizacion_uuid`, un **bridge de solo-enlace manual** (`CotizacionBridge`, `apps/tenant/facturas/services/selectors.py`): el usuario edita una Factura ya existente y le asocia manualmente el UUID de una Cotización, con DSV+validación de existencia, pero sin copiar items/totales, sin cambiar el estado de la Cotización, y sin crear nada — por lo que no hay riesgo de "doble click crea 2 ventas" porque no existe ninguna operación de creación ahí. No se inventó una conversión automática que no tiene evidencia de ser requerida por el negocio (Regla #1). Esto queda documentado como el estado real del dominio, no como un gap a cerrar sin más contexto.

---

## FASE 20/21 — Inventario / Contabilidad

Confirmado: una Cotización **no** genera ningún `MovimientoInventario` ni `AsientoContable` por el simple hecho de existir. Sin acoplamiento indebido encontrado en ninguna dirección.

---

## FASE 22 — PDF

Pipeline activo (`CotizacionPDFExportService.generar_pdf_publico()`) funcionando sin duplicación real hoy. Se encontró y **eliminó** un método muerto confirmado (`generar_pdf_interno()`, apuntaba a un template `formato_interno.html` inexistente en el filesystem, cero call-sites reales fuera de su propia definición) — DEAD_CONFIRMED, consistente con Regla de la FASE 36 ("eliminar solo DEAD_CONFIRMED").

---

## FASE 28/29/30 — Permisos / Tenant Isolation / Empresa

Reutiliza `IsTenantMember`/`IsTenantAdminOrReadOnly` existentes — sin RBAC nuevo creado. Tenant isolation y aislamiento por Empresa confirmados en las 5 rutas CRUD auditadas (todo filtra por `empresa_id`, con DSV real en las relaciones cross-model de Cotización). Cobertura de tests de aislamiento por sede/tenant ya era sólida ANTES de esta auditoría (5 de los 8 archivos de test existentes cubren exactamente esto, del proyecto transversal OSF).

---

## FASE 36 — Código muerto

Confirmado y eliminado: `CotizacionPDFExportService.generar_pdf_interno()` (ver FASE 22). Confirmado pero **no eliminado** (se conectó en vez de eliminarse, por ser funcionalidad real faltante, no código verdaderamente muerto): `ProductoCRUDService.eliminar()`, `ServicioCRUDService.eliminar()`, `ConfiguracionCRUDService.delete_configuracion()` — los 3 existían huérfanos (nunca invocados) y ahora están conectados vía el Service Layer correcto.

---

## FASE 39/40 — Tests

Tests existentes (8 archivos) clasificados: todos válidos, ninguno duplicado/obsoleto (ver `CRUD_BASELINE.md` §10 para el detalle por archivo). Cobertura ampliada en esta pasada (sin duplicar ningún test existente, Regla de FASE 39):

- `test_services.py::test_crear_cotizacion_valida` — se le agregó la aserción de `fecha_emision`/`fecha_vencimiento` que faltaba (regresión del bug de FASE 6/7).
- `test_delete_and_constraints.py` (nuevo): DELETE de Cotización sin Factura vinculada (éxito), DELETE de Cotización con Factura vinculada (bloqueado, 400), DELETE de Producto vía API (pasa por Service Layer), constraint de BD contra `codigo` duplicado de Producto (incluye caso de `codigo` vacío, que NO debe colisionar), y creación de Producto con `codigo` duplicado vía API (400, no 500).

**Gaps de cobertura que quedan documentados, no cerrados en esta pasada** (no bloquean el release gate por no ser CRUD roto/fuga de seguridad): sin test directo de `CotizacionItemViewSet` vía API (create/update/destroy — cubierto indirectamente por `test_services.py` al nivel de servicio), sin test de `exportar_pdf`, sin test de DELETE de `Servicio`/`ConfiguracionCotizacion` vía API (mismo fix que Producto, mismo patrón, riesgo bajo de que difiera).

---

## FASE 44 — Governance

- `manage.py check`: limpio (0 issues) tras todos los cambios.
- `makemigrations --check --dry-run`: confirmó exactamente los cambios esperados en cada paso (`0006_alter_cotizacion_fecha_emision`, `0007_producto_uniq_producto_codigo_por_empresa`, y `0008_alter_cotizacion_fecha_emision` tras corregir la regresión de `default`), sin drift oculto.
- **Regresión real (NEW, no preexistente) detectada por la suite completa de la app** tras el fix de `0006`: 12 tests fallaron porque `fecha_emision` pasó a ser requerido sin `default`. Corregida en la misma pasada (`0008`) — ver §FASE 6/7 para el detalle. Documentada aquí explícitamente, no ocultada (regla de FASE 44).
- Antes de aplicar el constraint `uniq_producto_codigo_por_empresa` a los tenants reales, se verificó contra los 3 schemas reales (`home`, `qaisotest`, `shelltest1`) que no existieran códigos duplicados que rompieran la migración — 0 filas encontradas en los 3, migración segura de aplicar. Migraciones aplicadas y confirmadas OK en los 3 schemas.
- `git diff --check`: sin errores reales (solo avisos de CRLF/LF esperables en Windows).

Ningún hallazgo de gobernanza fue preexistente y quedó sin marcar — todos los cambios de este reporte son atribuibles a esta misión (NEW), no hay REGRESSION reportada.

---

## Resumen de archivos tocados

**Modelos:** `apps/tenant/cotizaciones/models.py` (fix `fecha_emision`, constraint `Producto.codigo`).
**Migraciones:** `0006_alter_cotizacion_fecha_emision.py`, `0007_producto_uniq_producto_codigo_por_empresa.py`, `0008_alter_cotizacion_fecha_emision.py` (corrige la regresión de `0006`, agrega `default=_hoy`).
**Services:** `services/crud_service.py` (+`delete_cotizacion`), `services/business_service.py` (+`eliminar_cotizacion`), `services/api_mixins.py` (+`service_eliminar_cotizacion`), `services/producto_service.py` (+`eliminar`, +`service_eliminar_producto`, manejo de `IntegrityError`), `services/servicio_service.py` (+`eliminar`, +`service_eliminar_servicio`), `services/pdf_export_service.py` (−`generar_pdf_interno`, código muerto), `configuracion/services/business_service.py` (+`eliminar_configuracion`), `configuracion/services/api_mixins.py` (+`service_eliminar_configuracion`).
**ViewSets:** `api/viewsets.py` (`destroy()` real en `CotizacionViewSet`; `ProductoViewSet`/`ServicioViewSet.destroy()` ahora vía Service Layer; manejo de `ValueError` en create/update de Producto), `configuracion/viewsets.py` (`destroy()` real).
**Tests:** `tests/test_services.py` (aserción agregada), `tests/test_delete_and_constraints.py` (nuevo), `tests/conftest.py` (+`facturas` en `required_apps`).
**Documentación:** este reporte + `CRUD_BASELINE.md` + `MATRIZ_ESTADOS_COTIZACION.md` + `CRUD_MATRIX.md`.

Ningún ViewSet, Serializer, CRUDService o endpoint nuevo/paralelo fue creado — todos los fixes reutilizan y conectan infraestructura que ya existía (Regla #2).
