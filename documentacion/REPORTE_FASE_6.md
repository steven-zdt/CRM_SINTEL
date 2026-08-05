# REPORTE FASE 6 — Simplificación, Deduplicación y Código Muerto

**Fecha:** 2026-08-03
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 6" — DEAD-A1 (paginación), código muerto (DEAD-M + hallazgos de Fase 5 diferidos), limpieza de raíz, PERF-M3, migraciones de `gastos`/`proveedores`.

---

## 0. Limitación de entorno

Misma de todas las fases anteriores: sin Docker/venv funcional. Verificación por `py_compile` + grep exhaustivo de referencias antes de cada eliminación (documentado punto por punto abajo) — **no** se pudo ejecutar `collectstatic`/`manage.py check`/`pytest` reales para confirmar en runtime que ninguna eliminación rompe algo no detectable por grep estático.

---

## 1. DEAD-A1 — Unificación de `StandardResultsSetPagination`

**Decisión de producto (requerida por el propio plan antes de tocar código):** el usuario eligió unificar a 20/200 (el SSoT ya usado por las otras 13 apps tenant) en vez de mantener 10/100 en `proyectos`/`inventario`/`clientes`.

**Hallazgo adicional durante la implementación, más grave que lo que describía el audit:** `clientes/api/viewsets.py` **ya importaba correctamente** la SSoT (`from apps.config.api.pagination import StandardResultsSetPagination`, línea 16) — pero 26 líneas más abajo **redeclaraba una clase local con el mismo nombre**, que sombreaba el import en el resto del módulo. El resultado: el import nunca tuvo efecto, y las 2 `pagination_class = StandardResultsSetPagination` de ese archivo apuntaban silenciosamente a la clase local (10/100), no a la SSoT. Un caso de duplicación más peligroso que "no importa la SSoT": *sí* la importa, pero un shadow la anula sin ningún error ni warning.

**Cambio aplicado en los 3 archivos:** eliminada la clase local duplicada; `inventario`/`proyectos` ahora importan `StandardResultsSetPagination` desde `apps.config.api.pagination` (mismo patrón que las 13 apps ya correctas); `clientes` solo necesitó que se le quitara el shadow, su import ya era correcto. Los `pagination_class = StandardResultsSetPagination` existentes no se tocaron — ahora resuelven a la SSoT (20/200) automáticamente.

**Verificado:** `page_size`/`max_page_size` no se sobrescriben en ningún otro punto de los 3 archivos (grep de `page_size` sin más ocurrencias que el comentario de un docstring). `py_compile` limpio en los 3.

---

## 2. Código muerto — cierre de los hallazgos de Fase 5 (FE-M1/M2/M3) + barrido ampliado

Al investigar los 2 archivos que Fase 5 dejó documentados como candidatos a código muerto, la verificación reveló un cluster mucho más grande de lo esperado — una arquitectura de "workspace" alternativa (ES modules con `import`, prefijo `hydrateView`) que fue completamente abandonada mucho antes de esta auditoría y nunca se limpió. Todo lo eliminado en esta sección se verificó con grep exhaustivo de 0 referencias en `apps/`/`config/` (`.py`/`.html`/`.js`) antes de borrar.

### 2.1 `apps/tenant/core/static/tenant/core/workspace.js` (111 líneas)
Módulo ES (`import ... from "./inventario/ui.js"`) que expone `window.cargarResumen`/`window.initInventario`/`window.initActivosCRUD` sin namespace (el bug literal de FE-M1). **0 templates lo cargan** con `<script>`. Además, sus propios imports (`./inventario/ui.js`, `catalogo.crud.js`, `activos.crud.js`) **no existen en el árbol** — el archivo está roto incluso si algo lo cargara. Eliminado.

### 2.2 `apps/tenant/core/static/tenant/core/workspace/` (directorio completo, 7 archivos)
Al verificar el directorio hermano de `workspace.js` se encontró que **los 7 archivos que contiene también tienen 0 referencias**: `empresa.mailbox.js`, `facturas.refresh.js`, `inventario.page.js`, `maildigester.details.modal.js`, `maildigester.panel.js`, `maildigester.styles.css`, `maildigester.xml.modal.js`. Ninguno se carga desde ningún template (`grep` por nombre exacto de archivo, 0 resultados cada uno). Directorio completo eliminado.

**Nota importante — no confundir con los shells estáticos que SÍ están vivos:** `apps/tenant/core/static/tenant/core/{dashboard,empresa,facturas,contabilidad,perfil,auth}/index.html` (y sus `.js` asociados) siguen activos — confirmados con `RedirectView` reales en `config/urls_tenant.py` (`/dashboard/`, `/empresa/`, `/facturas/`, `/contabilidad/`, `/perfil/`, `/login/`, etc.). **No se tocó ninguno.** Solo el subdirectorio `workspace/` (sin relación con esos shells) estaba muerto.

### 2.3 `apps/tenant/landing/static/tenant/landing/workspace/` (directorio completo, 4 archivos = 1.676 líneas exactas de FE-M3)
`facturas.js` (458 líneas) + `facturas.page.js` (1.218 líneas) = exactamente las 1.676 líneas que describía el hallazgo original. Se agrega `facturas.styles.css`, hermano sin referencias tampoco. **0 templates reales cargan ninguno** de los 3 (el único "hit" de un grep amplio fue un falso positivo por substring en un archivo no relacionado de `inventario`). Directorio completo eliminado.

**Sobre los 3 tests que referencian `facturas.page.js` por string (`apps/tenant/core/tests/test_workspace_facturas_*.py`):** su aserción (`assertIn('/static/tenant/landing/workspace/facturas.page.js', html, ...)`) ya fallaba **antes** de esta eliminación — ningún template real incluye ese script, así que el HTML de respuesta nunca contuvo esa cadena, con o sin el archivo presente en disco. Borrar el archivo no cambia el resultado de esos tests (no dependen de la existencia del archivo, sino de una aserción sobre el HTML renderizado, que ya era falsa). Se documenta aquí en vez de tocar los tests — por instrucción explícita del usuario, testing queda para el final (Fase 7).

### 2.4 App huérfana `apps/tenant/templates/` (no registrada, no es un app real)
No está en `TENANT_APPS`/`SHARED_APPS` (confirmado por grep). Contenía solo `migrations/__init__.py` (vestigial — sin `models.py`, nunca corre) y una copia **obsoleta** de `tenant/cotizaciones/pdf/formato_profesional.html`. La copia real y viva vive en `apps/tenant/cotizaciones/templates/tenant/cotizaciones/pdf/formato_profesional.html` (confirmado que `cotizaciones/services/pdf_export_service.py` usa `get_template()` sobre esa ruta, resuelta vía el app-loader de `cotizaciones`, que sí está registrado). Un `diff` entre ambas versiones confirmó que la copia huérfana es una versión **más antigua** (sin frames de header/footer, sin fallback de `default:"S/N"`) — no había nada que rescatar. Directorio completo eliminado.

---

## 3. Plantillas huérfanas — `dashboard`, `contabilidad`, `empresa` (19 archivos)

Verificación app por app (grep de 0 `{% include %}`/`{% extends %}`/`template_name=`/`render()` referenciando cada archivo, antes de borrar):

**`dashboard` (3):** `partials/{charts,kpis,table}.html`. Doblemente confirmado huérfano: además de 0 referencias, las únicas rutas que suenan relacionadas (`urls_ui.py`, `/partials/kpis/`, `/partials/charts/`, `/partials/table/`) apuntan a `deprecated_view()`, una función que **siempre devuelve 404** sin renderizar nada (comentario explícito en el código: "Todas las rutas retornan 404").

**`contabilidad` (8):** `asiento_page.html`, `cuenta_page.html`, `periodo_page.html`, `partials/{assets_contabilidad,assets_periodo,contabilidad_asientos_list,contabilidad_cuentas_list,summary}.html`. 0 referencias — reemplazadas hace tiempo por el patrón `assets_<submódulo>.html` que sí está activo (`assets_asiento.html`, `assets_cuenta.html`, etc., no tocados).

**`empresa` (8):** `offcanvas_{area,sede,mailinbox}.html` y `offcanvas_detalle_{area,sede,mailinboxconfig}.html` — reemplazados por el patrón `offcanvas_crear_<x>.html`/`offcanvas_editar_<x>.html` que sí usa `empresa/api/viewsets.py` (verificado leyendo los 3 `template_name` dinámicos reales del archivo). `partials/offcanvas_quick_edit.html` y `partials/quick_edit_form.html` — el primero trae su propio comentario "Placeholder creado por FRONTEND_SYNC_AGENT", nunca conectado.

**Total: 19 templates eliminados** (el plan estimaba ~25; la diferencia probablemente incluye plantillas huérfanas en otras apps no cubiertas por esta pasada — no se revisó el árbol completo de las 20 apps tenant, solo las 3 que el hallazgo original nombraba explícitamente).

---

## 4. Archivos JS huérfanos (14 archivos)

Los 3 nombrados explícitamente en el hallazgo original — `router.js` (`core/static/core/js/`), `clientes.module.js`, `_csrf.js` (`landing/static/tenant/landing/`) — más 11 encontrados durante un barrido del resto de `apps/tenant/**/static/**/*.js` verificando cada uno contra el `assets_<app>.html` real de su app:

- `bancos/static/bancos/js/features/transaccion_list.js` (251 líneas) — feature completa de "Transacciones Bancarias con Conciliación" nunca conectada: no está en `assets_bancos.html` (que sí carga `cuenta_list.js`/`extracto_list.js`) y ningún template tiene el contenedor `#grid-transacciones` que el archivo espera. Es el único candidato de este lote con volumen de lógica de negocio real (no un placeholder trivial) — se documenta con más detalle por si representa trabajo en progreso abandonado, no solo deuda.
- `core/static/core/js/lib/helpers_sanity_check.js`, `core/static/core/js/modules/empresa.module.js` — 0 referencias.
- `core/static/core/js/mail/{mail.api,mail.modals,mail.page,mail.ui}.js` (4) y `core/static/core/js/mailinbox/{mailinbox.api,mailinbox.page,mailinbox_offcanvas}.js` (3) — contraparte **frontend** de las apps backend `apps/tenant/mail`/`apps/tenant/mailinbox` que ya se habían eliminado en la Fase 2 (ARQ-A4); esta pasada de Fase 6 encontró que el frontend correspondiente nunca se limpió en esa fase porque vive en una ruta distinta (`core/static/`, no dentro de las apps eliminadas). 0 referencias confirmadas para los 7.
- `core/static/core/js/tests/facturas_client_side_test.js` — archivo de test client-side ubicado en `static/` (no en `tests/`), 0 referencias desde ningún template.

**No se tocó** `core/static/core/js/modules/empleados.module.js` (hermano de `empresa.module.js`) — confirmado con referencia real desde `empleados/assets_empleados.html`. Ni `core/static/core/js/tests/workspace_ux_smoke.js` — confirmado referenciado desde `workspace.html`. Se verificaron explícitamente para no borrar por asociación de carpeta sin comprobar cada archivo individualmente.

---

## 5. Limpieza de raíz

- `test_output.txt` (181 KB, tenía modificaciones locales sin commitear — confirmado que era solo una nueva ejecución de pytest volcada al archivo, no trabajo de código; se forzó su remoción) — eliminado.
- `test_run.txt`, `test_run_utf8.txt` — ya estaban sin trackear (ignorados por el patrón `test_*.txt` que **ya existe** en `.gitignore`); se eliminaron del disco directamente.
- `check_schema.py`, `clean_emojis.py`, `reset_migrations.sh` — 0 referencias en `Makefile`/CI/`Dockerfile`/`docker-compose*.yaml`. Eliminados.
- **No se tocó** `documentacion/_archive/` (333 archivos) — a diferencia de los demás ítems, su propio nombre indica que es un contenedor de archivo histórico deliberado, no clutter accidental; borrar 333 documentos de una vez es una acción de volumen y naturaleza distinta a limpiar scripts sueltos, y no estaba claramente autorizada por el alcance de esta fase. Se deja para una decisión explícita del usuario si se desea vaciarlo o mantenerlo.
- **No se tocó** `entrypoint.sh`/`entrypoint-celery.sh` — confirmados en uso real por `Dockerfile` (`ENTRYPOINT ["/app/entrypoint.sh"]`).
- `.gitignore` — no requirió cambios; el patrón `test_*.txt`/`test_*.log` que hubiera evitado que `test_output.txt` volviera a colarse **ya estaba presente** antes de esta sesión.

---

## 6. PERF-M3 — No reproducible en el estado actual

Las funciones nombradas en el hallazgo original (`get_balance_prueba`, `calcular_saldos_cuenta`) **no existen** en el árbol actual (`grep` de 0 resultados). Existe una función de nombre similar y propósito equivalente, `balance_prueba_selector` (`contabilidad/services/selectors.py:578`), pero **está en uso activo** — invocada desde una acción real de `ContabilidadViewSet` (`api/viewsets.py:403-415`), no es código muerto. No se tomó ninguna acción: no hay nada que coincida con el hallazgo para eliminar o deprecar.

---

## 7. Migraciones de `gastos`/`proveedores` — bloqueado (sin acción)

`gastos` tiene 22 migraciones, `proveedores` 18 (confirmado por conteo real). `squashmigrations` **no se ejecutó** — requiere Docker/venv funcional para validar que el esquema resultante es idéntico antes/después en un tenant de prueba, exactamente la limitación de entorno que bloquea esta fase (documentada desde `REPORTE_FASE_1.md` §0). Queda pendiente para cuando haya acceso a un entorno funcional.

---

## 8. Archivos tocados/eliminados (agregado)

```
# Modificados (pagination SSoT)
M  apps/tenant/clientes/api/viewsets.py
M  apps/tenant/inventario/api/viewsets.py
M  apps/tenant/proyectos/api/viewsets.py

# Eliminados — 50 archivos (git rm, historial preservado)
D  apps/tenant/core/static/tenant/core/workspace.js
D  apps/tenant/core/static/tenant/core/workspace/*  (7 archivos)
D  apps/tenant/landing/static/tenant/landing/workspace/*  (4 archivos)
D  apps/tenant/templates/*  (2 archivos + directorio)
D  apps/tenant/{dashboard,contabilidad,empresa}/templates/.../*.html  (19 archivos)
D  apps/tenant/{bancos,clientes,core}/static/**/*.js  (3 archivos)
D  apps/tenant/core/static/core/js/{mail,mailinbox}/*  (7 archivos)
D  apps/tenant/core/static/core/js/{router.js,lib/helpers_sanity_check.js,modules/empresa.module.js,tests/facturas_client_side_test.js}  (4 archivos)
D  apps/tenant/landing/static/tenant/landing/_csrf.js
D  test_output.txt, check_schema.py, clean_emojis.py, reset_migrations.sh

?? documentacion/REPORTE_FASE_6.md
M  documentacion/PLAN_UNICO_CORRECCIONES.md
```

No se ejecutó ningún `git add`/`git commit`.

## 9. Checklist de cierre

- [x] Decisión de producto de DEAD-A1 documentada (usuario, 2026-08-03, "unificar a 20/200").
- [x] `py_compile` limpio en los 3 archivos de pagination tocados.
- [x] Cada una de las 50 eliminaciones verificada con grep de 0 referencias **antes** de borrar, no después.
- [x] Los shells estáticos legítimos (`dashboard/empresa/facturas/contabilidad/perfil/auth index.html`, wireados via `RedirectView`) se identificaron explícitamente y NO se tocaron, pese a vivir en la misma zona del árbol que el código muerto eliminado.
- [x] `empleados.module.js` y `workspace_ux_smoke.js` verificados como vivos y dejados intactos, pese a ser hermanos directos de archivos eliminados.
- [x] `documentacion/_archive/` dejado intacto deliberadamente (fuera del alcance de esta fase, requiere decisión propia).
- [x] Migraciones de `gastos`/`proveedores`: bloqueo de entorno documentado, sin acción especulativa.
- [ ] **Pendiente (bloqueado por entorno):** `collectstatic` real para confirmar que ninguna eliminación rompe una referencia dinámica no detectable por grep estático (ej. construcción de rutas por f-string con variables no resueltas estáticamente).

## 10. Siguiente paso

Fase 8 (DevOps y Dependencias) es la siguiente en el plan. Fase 7 (Testing) queda para el final, por instrucción explícita del usuario — incluye coordinar qué hacer con los 3 tests de `test_workspace_facturas_*.py` que quedaron documentados en §2.3 de este reporte.
