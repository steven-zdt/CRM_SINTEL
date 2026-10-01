# REQUISICIONES_PRE_TEST_AUDIT.md — Autoauditoria Final Sin Tests (Fase 10)

Revision estatica (grep repo-wide, inspeccion de imports/migraciones/referencias, sin ejecutar pytest) antes de pedir autorizacion de tests (Fase 11).

## 1. Consistencia de referencias

- `RequisicionOrdenCompra` (descartado en el diseño, ver `REQUISICIONES_DESIGN.md` #7): **0 referencias** en `apps/`, `docs/` — confirmado via grep, no quedo codigo muerto apuntando a un modelo que nunca se creo.
- `ProyectoSelector` (import erroneo temprano, corregido antes de generar codigo): **0 referencias** residuales.
- `filter_by_scope(queryset, empresa_id, sede_ids=, area_ids=)`: firma real confirmada en `apps/tenant/core/services/organizational_filters.py:34`, coincide con el uso en `RequisicionCompraSelector`.
- `Factura.numero`: campo real confirmado (`apps/tenant/facturas/models.py:89`), usado correctamente en `RequisicionFacturaSerializer`.

## 2. Bugs reales encontrados y corregidos durante esta mision (antes de cualquier test)

| # | Hallazgo | Causa | Fix | Como se detecto |
|---|---|---|---|---|
| 1 | `TenantProfile has no field named 'apellidos'` (500 en `/dt/`) | `_SOLICITANTE_TRAVERSALS`/`_RESPONSABLE_TRAVERSALS` en `selectors.py` asumian campos `nombres`/`apellidos` que no existen en `TenantProfile` (su `__str__` usa `user.email` + `cargo`) | Se eliminaron esos traversals de `.only()` -- sin restriccion, Django carga el objeto relacionado completo en vez de fallar | Playwright contra tenant `admin` real (error 500 visible en consola del navegador) |
| 2 | `405 Metodo "POST" no permitido` en `/api/v1/compras/requisiciones/` | `config/api_urls.py` montaba `compras/` ANTES que `compras/requisiciones/` -- por resolucion de prefijo en orden de registro, toda request a `compras/requisiciones/...` caia en el catch-all de detalle de `OrdenCompraViewSet` (`^(?P<uuid>[^/.]+)/$`, leyendo "requisiciones" como uuid) | Reordenado: `compras/requisiciones/` se registra ANTES que `compras/` | Playwright (creacion de requisicion fallaba con 405) |
| 3 | `TemplateDoesNotExist: tenant/compras/requisiciones/partials/tabla_requisiciones.html` | El proceso `runserver` no recarga automaticamente `INSTALLED_APPS`/`TENANT_APPS` al agregar una app nueva (solo autoreload de cambios `.py` en apps ya registradas) | Restart de `docker compose restart web` tras agregar `apps.tenant.compras.requisiciones` a `TENANT_APPS` | Primera carga de `workspace/#compras` tras el cambio |
| 4 | Regla de negocio "requisicion obligatoria en OrdenCompra" implementada de forma demasiado agresiva en el primer borrador (bloqueaba TODA creacion de OC existente sin requisicion) | Lectura inicial demasiado literal del plan original §4, sin considerar el rollout por fases del mismo plan (§37, FASE A vs FASE C) | Auto-corregido antes de verificar en vivo: `requisicion` es opcional en `crear_orden_compra()`; solo se exige `requisicion.estado == APROBADA` cuando la orden SI tiene una requisicion vinculada | Auto-revision del propio codigo contra el diseño documentado, antes de cualquier ejecucion |
| 5 | 2 imports sin usar (`ValidationError` en `api_mixins.py`, `RequisicionCompraItem`/`RequisicionCompraSelector` en `business_service.py`) | Cruft de iteracion | Eliminados | `ruff check` |

Ningun otro hallazgo de `ruff check` en los archivos nuevos mas alla de estilo `Tuple` vs `tuple` (consistente con el resto del archivo `compras/services/business_service.py`, no introducido por esta mision).

## 3. Checklist arquitectonico (regla de oro, aplicada campo por campo)

- [x] `SedeAwareModel`/`SintelTenantBaseModel` en todos los modelos nuevos (nunca `models.Model` bare).
- [x] `empresa_id` explicito en toda query de servicio (grep confirmado, `REQUISICIONES_RELEASE_GATE.md` #7).
- [x] `.only()`/`.defer()` en selectors, `queryset = Model.objects.none()` en el ViewSet.
- [x] Sin signals — toda logica de negocio vive en `business_service.py`.
- [x] `lookup_field = "uuid"` heredado de `BaseTenantViewSet`, sin exponer PK entero.
- [x] FK a `perfil.TenantProfile`, nunca a `settings.AUTH_USER_MODEL` directo.
- [x] `estado` nunca escribible via serializer de creacion/edicion generico.
- [x] Ninguna migracion historica inventada (`OrdenCompra.requisicion` queda `NULL` en filas existentes, sin heuristicas).
- [x] No se creo ninguna entidad `CentroCosto`.
- [x] No se repropositó `Cotizacion` como cotizacion de proveedor.
- [x] Sin `GenericForeignKey` (soft references con `UUIDField` donde aplica, FK real donde hay certeza del modelo destino).

## 4. Regresion de UI existente

`compras_list.html`/`compras.api.js`/`compras_list.js` (Ordenes de Compra, Plantillas) **no se modificaron en su logica** — solo se agrego una tercera pestaña y 2 nuevos `<script>` tags en `assets_compras.html`. Verificado visualmente en el mismo Playwright run: la pestaña "Ordenes de Compra" siguio mostrando su unica orden preexistente (`OC-2` antes de la limpieza) sin errores.

## 5-BIS. Fase 12 (Testing Final) — hallazgos reales encontrados DURANTE la ejecucion autorizada

Autorizacion recibida del usuario 2026-09-25 ("si, por ahora ejecuta"). Resultados:

| Suite | Resultado |
|---|---|
| `apps/tenant/compras/requisiciones/tests/` (50 tests, todos nuevos) | 50 passed |
| `apps/tenant/compras/tests/` (suite completa preexistente) | 84 passed (incluye los 50 anteriores + regresion) |
| `apps/tenant/cotizaciones/tests/` (suite completa) | 68 passed, 2 failed -> corregido -> 26/26 passed en los 2 archivos afectados |
| `apps/tenant/proveedores/tests/` + `apps/tenant/clientes/tests/` | en curso |

**Bug real #1 encontrado en produccion durante esta sesion (no por pytest, reportado en vivo por
el usuario):** `POST /api/v1/cotizaciones/{uuid}/generar-pdf/` devolvia 500
(`AssertionError: Header names/values must be of type str`). Causa: `CotizacionService.
generar_pdf_y_enviar()` pasaba el ENUM `Cotizacion.Estado.ENVIADA` (subclase de `str`, no `str`
exacto) a `cambiar_estado()`, que lo asignaba tal cual a `cotizacion.estado`; el viewset luego
usaba ese valor en un header HTTP, que wsgiref rechaza por no ser `str` exacto. El cambio de
estado en BD SI se completaba correctamente -- solo la respuesta HTTP fallaba. **Fix:** `nuevo_estado
= str(nuevo_estado)` en el unico punto de entrada real de `CotizacionService.cambiar_estado()`
(`apps/tenant/cotizaciones/services/business_service.py`), protegiendo tambien los otros 4
call-sites con el mismo patron de riesgo. Verificado con una cotizacion de prueba desechable
(creada, enviada, verificada, eliminada) contra el tenant `admin` real.

**Bug real #2 encontrado por la propia suite de tests de Cotizaciones:** `apps/tenant/
cotizaciones/tests/conftest.py` migra selectivamente una lista fija de apps tenant
(`required_apps`) al crear el schema de test, en vez de migrar todas las apps registradas. Las
nuevas FK `RequisicionCotizacion.cotizacion` (PROTECT) hacen que CUALQUIER `DELETE` de una
`Cotizacion` dispare el collector de Django a consultar esa tabla -- que no existia en el schema
de test porque `tenant_compras_requisiciones` no estaba en esa lista. Mismo sintoma exacto,
documentado en el propio historial de ese archivo, que ya habia ocurrido antes con `tenant_gastos`.
**Fix:** se agrego `tenant_compras`/`tenant_compras_requisiciones` a `required_apps`. Confirmado:
los 2 tests que fallaban (`test_eliminar_cotizacion_sin_factura_vinculada_funciona`,
`test_borrador_sigue_siendo_eliminable`) pasan despues del fix (26/26 en los archivos afectados).

**Auditoria proactiva del mismo patron:** se grepeo todo `apps/*/tests/conftest.py` en busca de
migraciones selectivas (`migrate_schemas ... -s <schema> <app>` con app explicito, no migracion
completa). Solo 3 conftest tenian el mismo riesgo real (dependencia a `facturas` o
`tenant_cotizaciones` sin incluir la nueva app): `cotizaciones` (ya corregido arriba),
`proveedores` y `clientes` (ambos con `facturas` en su lista -- corregidos preventivamente,
agregando `tenant_compras_requisiciones` con el mismo criterio). El resto de conftest.py del
proyecto migra TODAS las apps tenant sin filtrar (`migrate_schemas --tenant -s <schema>
--noinput` sin nombre de app) -- no tienen este riesgo, no se tocaron.

## 5. Estado final

Sin bloqueadores para Fase 11. Todo lo listado en "DEFERRED" (`REQUISICIONES_RELEASE_GATE.md`) esta documentado explicitamente, no oculto ni marcado como completado.
