# PLAN ÚNICO DE CORRECCIONES — SINTEL ERP

**Fecha:** 2026-08-03
**Fuente de hallazgos:** `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md` (≈158 hallazgos: 15 CRÍTICO + 36 ALTO + 42 MEDIO + ≈65 BAJO/INFORMATIVO)
**Documentos relacionados:** `documentacion/PLAN_REMEDIACION.md` (preparación de Fase 1), `documentacion/REPORTE_FASE_{1,2,3,4}.md` (trabajo ya ejecutado), `MEMORY.md`, `AGENTS.md`
**Propósito de este documento:** consolidar en un único plan, por fases, **todo** lo que queda abierto de la auditoría — cerrando además el hueco de cobertura detectado en el plan original (`AUDITORIA_ENTERPRISE_2026-07-26.md` §8), donde varios hallazgos ALTO/MEDIO de Frontend, DevOps, Dependencias, Documentación y Arquitectura-MEDIO no tenían ninguna fase asignada explícitamente.

---

## 0. Estado actual — qué ya está corregido

Cuatro fases del plan original ya se ejecutaron y tienen reporte propio con evidencia línea-por-línea. **No se repite trabajo ya hecho en este documento.**

| Fase ejecutada | Alcance | Hallazgos cerrados | Reporte |
|---|---|---|---|
| **Fase 1** | Los 15 CRÍTICOS completos | SEC-C1, SEC-C2, PERF-C1, PERF-C2, PERF-C3, FE-C1, FE-C2, FE-C3, ARQ-C1, ARQ-C2, TEST-C1, DEVOPS-C1, DOC-C1, DOC-C2 | `REPORTE_FASE_1.md` |
| **Fase 2** | Arquitectura ALTO | ARQ-A1, ARQ-A2 (documentado como excepción, no revertido), ARQ-A3 (parcial, con razones técnicas documentadas), ARQ-A4 | `REPORTE_FASE_2.md` |
| **Fase 3** | Seguridad ALTO + MEDIO | SEC-A1, SEC-A2, SEC-A3, SEC-A4, SEC-M1..M7 | `REPORTE_FASE_3.md` |
| **Fase 4** | Performance ALTO + MEDIO | PERF-A1 (N+1 Facturas, recuperado — ver `REPORTE_FASE_4.md` §0), PERF-A2, PERF-A3, PERF-M1..M7 | `REPORTE_FASE_4.md` |
| **Fase 5** | Frontend (FE-A1..A9, FE-M1..M6) | FE-A1, FE-A3, FE-A4, FE-A5, FE-A6, FE-A7, FE-A8, FE-A9 cerrados; FE-A2 resuelto (era consecuencia de FE-A1 en la mayoría de casos, más 1 fix puntual en `proyectos_editor.js`); FE-M1/M2/M3 investigados y diferidos a Fase 6 (código muerto); FE-M4 documentado; FE-M5 no localizado en el estado actual; FE-M6 ya estaba resuelto por Fase 2 | `REPORTE_FASE_5.md` |
| **Fase 5-BIS (parcial)** | Piloto Tabulator→django-tables2 | `gastos`, `facturas`, `compras` migrados; `contabilidad` migrado 5/8 grillas (3 fuera de alcance, ver `REPORTE_FASE_5_BIS_CONTABILIDAD.md` §2); `ventas` migrado 1/1 grilla real (2 archivos del plan resultaron ser codigo no conectado, ver `REPORTE_FASE_5_BIS_VENTAS.md` §0); `bancos` migrado 2/2 grillas reales (1 archivo del plan nunca existió, ver `REPORTE_FASE_5_BIS_BANCOS.md`); `empleados` migrado 5/5 grillas, incluidas las 2 Master-Detail (Nóminas/Liquidaciones, resueltas con `row_attrs` de django-tables2, ver `REPORTE_FASE_5_BIS_EMPLEADOS.md` §3) | `REPORTE_FASE_5_PILOTO_TABLAS.md`, `REPORTE_FASE_5_BIS_CONTABILIDAD.md`, `REPORTE_FASE_5_BIS_VENTAS.md`, `REPORTE_FASE_5_BIS_BANCOS.md`, `REPORTE_FASE_5_BIS_EMPLEADOS.md` |
| **Fase 6** | Simplificación/Dedup/Código muerto | DEAD-A1 unificado (20/200, decisión de usuario); 50 archivos huérfanos eliminados (JS/CSS/templates); PERF-M3 no reproducible; `squashmigrations` sigue bloqueado (Docker/venv) | `REPORTE_FASE_6.md` |
| **Fase 8** | DevOps y Dependencias | DEVOPS-A1..A5, M1..M3 cerrados (M4 sin acción, falta info de infra); DEP-A1, M1..M3 acotados; DEP-A2 y `continue-on-error` de CI siguen bloqueados (Docker/venv) | `REPORTE_FASE_8.md` |
| **Fase 9** | Documentación — ✅ completada | DOC-A1..A5, M1..M3 cerrados; incidente de los 46 archivos `.py` con indentación corrompida **resuelto** (restaurados desde backup del usuario, `py_compile` limpio); ARQ-M (emojis en `.py`, naming, FK sin `.only()`) sin reintentar, deliberadamente | `REPORTE_FASE_9.md` |

**Limitación de entorno que aplica a las cuatro fases (y sigue aplicando a este plan):** no hay Docker/venv funcional en este host (red de contenedores rota, puertos ocupados por otro proyecto, `venv` apunta a un intérprete inexistente). Toda corrección se verificó por `py_compile`/`node --check` + lectura manual de consumidores, **no** por `make dj-check`/`make test` reales. **Antes de dar por cerrada cualquier fase (incluidas las 4 ya hechas), se debe ejecutar `make dj-check && make test` en un entorno funcional.** Esto es un bloqueante transversal, no específico de una fase.

**Cambios no relacionados presentes en el árbol:** el repositorio ya tenía ~450 cambios sin commitear antes de iniciar la Fase 1 (ver `REPORTE_FASE_1.md` §0). Ninguna fase ejecutada los tocó. Este plan asume la misma disciplina: cada fase nueva debe declarar explícitamente qué archivos tocó y confirmar que no mezcló los cambios preexistentes.

---

## 1. Alcance de este plan — mapa de cobertura completo

Todo hallazgo de la auditoría que **no** aparece en la tabla de la Sección 0 se cubre en una de las Fases 5–10 de este documento. Tabla de trazabilidad completa (cierra el hueco del plan original, donde `FE-A2/A3/A4/A6/A7/A8`, `FE-M*`, `ARQ-M*`, `TEST-A*`, `DEVOPS-A*/M*`, `DEP-*`, `DOC-A*/M*` y los ≈65 BAJO/INFO no tenían fase asignada):

| Categoría de hallazgos | IDs | Fase de este plan |
|---|---|---|
| Frontend ALTO (9) | FE-A1..A9 | **Fase 5** |
| Frontend MEDIO (6) | FE-M1..M6 | **Fase 5** |
| Duplicación de comportamiento cross-app | DEAD-A1 (paginación), `mostrarOffcanvasSeguro` (parte de FE-A5) | **Fase 5** (helper JS) + **Fase 6** (paginación SSoT) |
| Reemplazo de Tabulator/DataTables (decisión 2026-08-03, fuera de la auditoría original) | 56 archivos JS en ~20 apps — causa raíz de `DEAD-A1`/`FE-A6`/`FE-A9` | **Fase 5-BIS** (piloto `gastos` ya implementado; expansión al resto pendiente de validación) |
| Arquitectura MEDIO (6) | ARQ-M1..M6 | **Fase 6** (deriva doc.) + **Fase 8** (tests) |
| Código muerto / duplicidad ALTO+MEDIO | DEAD-A1, DEAD-M1..M8 | **Fase 6** |
| Limpieza de repositorio (BAJO) | ~15 ítems (§3.4 auditoría) | **Fase 6** |
| Tests ALTO + MEDIO | TEST-A1, TEST-A2, TEST-A3, TEST-M1 | **Fase 7** |
| Backfill de aislamiento multi-tenant | TEST-C2 (14 apps restantes) | **Fase 7** |
| DevOps ALTO + MEDIO | DEVOPS-A1..A5, DEVOPS-M1..M4 | **Fase 8** |
| Dependencias ALTO + MEDIO | DEP-A1, DEP-A2, DEP-M1..M3 | **Fase 8** |
| Documentación ALTO + MEDIO | DOC-A1..A5, DOC-M1..M3 | **Fase 9** |
| Gobernanza CI final | Quitar `continue-on-error` de ruff/bandit (deuda dejada explícita en `REPORTE_FASE_1.md` §"DEVOPS-C1") | **Fase 9** |
| Higiene de datos / dependencias (BAJO) | ~20+~10 ítems (§3.4 auditoría) | **Fase 9** |

---

## FASE 5 — Frontend (FE-A + FE-M, 15 hallazgos) — ✅ COMPLETADA (2026-08-03)

**Estado: ejecutada.** Ver `REPORTE_FASE_5.md` para el detalle archivo por archivo. Resumen: los 9 hallazgos ALTO (FE-A1..A9) y el más urgente de los MEDIO (FE-M4) se cerraron; FE-M1/M2/M3 se investigaron a fondo y resultaron apuntar a código huérfano (no a un bug activo) — se documentan como hallazgo de código muerto y se difieren a Fase 6 en vez de borrarse sin la verificación adicional que esa fase exige; FE-M5 no se pudo localizar en el estado actual del repositorio; FE-M6 ya estaba resuelto por la Fase 2 (ARQ-A1). La sección original de la fase queda abajo como referencia de lo que se planificó.

**Objetivo:** cerrar la categoría con mayor volumen de hallazgos ALTO de toda la auditoría (9 de 36) — todos relacionados con inicialización duplicada de Offcanvas/formularios, un helper reimplementado 16 veces, y desviaciones de convención de rutas.

**Por qué es su propia fase (y no parte de "Simplificación" como sugería el plan original):** el plan original (`AUDITORIA_ENTERPRISE_2026-07-26.md` §8, Fase 5) solo asignaba explícitamente FE-A5 y FE-A9 a una fase; FE-A2, FE-A3, FE-A4, FE-A6, FE-A7, FE-A8 y los 6 FE-M no tenían dueño. Se agrupan aquí porque comparten el mismo dominio (JS de features + templates) y varios se tocan en los mismos archivos.

### 5.1 Hallazgos y acción concreta

| ID | Hallazgo | Archivo(s) | Acción concreta | Criterio de aceptación |
|---|---|---|---|---|
| FE-A1 | Guard `data-editor-initialized` ausente en 34/36 `*_editor.js` | Listado completo en Track D del informe fuente | Aplicar el guard ya presente en `facturas`/`inventario/categorias` (los 2 archivos correctos) como plantilla: `if (el.dataset.editorInitialized) return; el.dataset.editorInitialized = '1';` al inicio del listener de submit | Los 36 archivos tienen el guard; `grep -L data-editor-initialized` sobre `*_editor.js` devuelve 0 resultados |
| FE-A2 | Doble-init confirmada: `MutationObserver` + `DOMContentLoaded` + `htmx:afterSettle` registran el mismo listener sin guard | `empresa/empresa_editor.js:186-227`, `proyectos/proyectos_editor.js:1030-1343` | Se resuelve como efecto colateral de FE-A1 en estos 2 archivos (el guard es agnóstico a cuántas veces se dispara el evento de entrada) — verificar explícitamente con un test manual: abrir el offcanvas 3 veces seguidas y confirmar un solo `POST` por submit | Sin duplicación de `POST` en Network tab tras abrir/cerrar el offcanvas repetidamente |
| FE-A3 | Patrón anti-backdrop evitado en templates (`getOrCreateInstance().show()` crudo en `hx-on::after-request`) | `perfil/.../partials/list.html:17`, `inventario/list_categorias.html:15` | Reemplazar por el patrón canónico documentado en `AGENTS.md` (dispose previo + instancia nueva vía helper, no invocación cruda en el atributo HTMX) | 0 ocurrencias de `getOrCreateInstance().show()` inline en `hx-on::after-request` en los 2 templates |
| FE-A4 | Anti-backdrop evitado en JS sin `.dispose()` previo | `empleados/contrato_editor.js:59-67`, `empleados/empleado_editor.js:44-52`, `empleados/liquidacion_list.js:158-172`, `empleados/nomina_historial.js:56-59`, `proveedores/proveedores_form.js:74` | Agregar `bootstrap.Offcanvas.getInstance(el)?.dispose()` antes de crear la instancia nueva, mismo patrón que las apps ya correctas | Abrir/cerrar el offcanvas 5 veces seguidas no deja backdrops (`.offcanvas-backdrop`) huérfanos en el DOM |
| FE-A5 | `mostrarOffcanvasSeguro` reimplementado 16 veces, 2 rotas (mismos archivos de FE-A4) | 16 archivos en `ventas`, `empleados`, `inventario`, `empresa` | Crear `apps/tenant/core/static/core/js/common/offcanvas.helper.js` con una única `window.Sintel.Core.mostrarOffcanvasSeguro(id)` (incluye el fix de FE-A4 una sola vez) y reemplazar las 16 copias por una llamada al helper | 1 sola implementación en el árbol; 0 funciones locales `mostrarOffcanvasSeguro`/equivalente fuera del helper (`grep -c "function mostrarOffcanvasSeguro"` = 0) |
| FE-A6 | `setData()` en vez de `replaceData()` obligatorio, uno dentro de un click handler sin `setTimeout` | `dashboard/dashboard_main.js:290,346`, `empleados/empleado_list.js:403`, `empleados/contrato_list.js:255`, `proveedores/cuentas_pagar_list.js:165`, `cotizaciones/servicio_editor.js:42`, `producto_editor.js:42` | Reemplazar cada `.setData(` por `.replaceData(`; envolver en `setTimeout(() => tabla.replaceData(...), 0)` donde el hallazgo original señala falta de diferimiento | 0 usos de `.setData(` en los 7 archivos; tabla se re-renderiza sin parpadeo/estado inconsistente al probar manualmente |
| FE-A7 | Assets de `facturas` en `static/js/facturas/` en vez de `static/facturas/js/` | `apps/tenant/facturas/static/js/facturas/...` | Mover archivos a `apps/tenant/facturas/static/facturas/js/...`; actualizar cada `{% static %}` que los referencia en templates de `facturas` | `collectstatic` no reporta rutas duplicadas; 0 referencias residuales a `static/js/facturas/` |
| FE-A8 | 12 templates de `inventario` sin prefijo `tenant/` obligatorio | `apps/tenant/inventario/templates/inventario/*.html` | Mover a `apps/tenant/inventario/templates/tenant/inventario/*.html`; actualizar cada `render()`/`{% include %}`/`{% extends %}` que referencia la ruta vieja en `views.py`/otros templates | Estructura de directorio conforme a la plantilla FSD (`templates/tenant/<app>/`) documentada en `CLAUDE.md`; 0 referencias rotas (grep de la ruta vieja) |
| FE-A9 | `getHeaders()`/CSRF duplicado y divergente; `ventas.api.js` depende de un input oculto no garantizado | `compras/compras.api.js:143-155`, `ventas/ventas.api.js:14-25`, `gastos/gastos.api.js:136-148` | Centralizar `getHeaders()` en `core/static/js/http.js` (ya SSoT tras Fase 1/FE-C3) o en el nuevo `common/`; `ventas.api.js` deja de leer el input oculto y usa `window.getCookie('csrftoken')` (ya disponible globalmente, confirmado en `REPORTE_FASE_1.md` FE-C3 §3) | Los 3 archivos delegan a la misma función; página de `ventas` sin el input de formulario tradicional sigue enviando CSRF válido |
| FE-M1/M2 | Contaminación de namespace global fuera de `window.Sintel.*` | `core/workspace.js`, `landing/facturas.js` | Envolver en el namespace correspondiente (`window.Sintel.Core.Workspace`, o mover a `landing` si aplica tras FE-M3) | 0 variables/funciones globales nuevas fuera de `window.Sintel.*` (verificado con `grep -E "^(function|var|let|const) " ` a nivel de módulo, sin IIFE) |
| FE-M3 | 1.676 líneas de JS huérfano de Facturas en `landing` | `apps/tenant/landing/static/.../facturas.js` (o ruta equivalente) | Confirmar por grep que 0 templates lo referencian; si es huérfano, eliminar (coordinar con Fase 6 — mismo criterio que código muerto) | Archivo eliminado o, si tiene uso real no detectado, documentado como excepción con la referencia encontrada |
| FE-M4 | `http.js`/`ui-manager.js` obsoletos en `core/js/lib/` no documentada | `core/static/core/js/lib/` | Documentar en `arquitectura_general.md` la existencia intencional de este directorio "legacy" (ver razón por la que NO se eliminó en `REPORTE_FASE_1.md` FE-C3 — maneja `FormData`) hasta que Fase 6/7 lo consolide | Referencia explícita en `arquitectura_general.md` §Frontend explicando el estado dual de `http.js` |
| FE-M5 | `dashboard` con 2 raíces estáticas desconectadas; 1 hardcodea ruta absoluta sin `{% static %}` | `apps/tenant/dashboard/static/...`, template con `/static/core/js/lib/http.js` hardcoded | Reemplazar el `src` hardcoded por `{% static 'core/js/lib/http.js' %}`; evaluar si las 2 raíces se pueden unificar (bajo riesgo, documentar si no) | 0 rutas `/static/...` hardcoded en templates de `dashboard` |
| FE-M6 | `contabilidad` mezcla `lookup_field='uuid'`/`='id'` en el mismo archivo de ViewSets | `apps/tenant/contabilidad/api/viewsets.py` | Aplicar el mismo patrón de 4 pasos usado en Fase 2 (ARQ-A1) a los ViewSets restantes con `='id'`, coordinando el cambio de frontend en el mismo commit (a diferencia de ARQ-A1 que era self-contained) | 0 `lookup_field='id'` remanente en `contabilidad/api/viewsets.py`; frontend de `contabilidad` actualizado en la misma fase |

### 5.2 Orden interno recomendado
1. FE-A1 (guard) primero — resuelve FE-A2 como efecto colateral, y varios archivos de FE-A1 se solapan con FE-A4/A5 (mismo bloque de código).
2. FE-A4 + FE-A5 juntos (mismos 5+16 archivos, mismo helper nuevo).
3. FE-A3 (patrón equivalente en templates, mismo criterio ya validado en 1-2).
4. FE-A6, FE-A9 (independientes entre sí).
5. FE-A7, FE-A8 (moves de archivos — bajo riesgo pero requieren grep exhaustivo de referencias antes de mover).
6. FE-M1..M6 (menor severidad, en paralelo a lo anterior si hay más de una persona).
7. FE-M6 al final — depende de que el patrón de Fase 2 (ARQ-A1) ya esté probado en producción, por tocar lookup_field en un ViewSet vivo.

### 5.3 Riesgos
- Mover archivos estáticos (FE-A7/A8) sin actualizar **todas** las referencias produce 404 silenciosos en producción (WhiteNoise no falla el build, solo el request). Grep exhaustivo obligatorio antes de mover, no después.
- El helper centralizado de FE-A5 debe probarse contra las 16 apps que lo usan antes de eliminar las copias locales — un helper único con un bug afecta a las 16 en vez de a 1.
- FE-M6 (lookup_field en contabilidad) es el único ítem de esta fase con riesgo de romper un flujo en producción si el frontend no se actualiza en el mismo cambio — replicar la lección de ARQ-A1 (Fase 2 §"Paso 4").

**Archivos afectados (agregado):** ~50 archivos JS + ~15 templates + 1 archivo nuevo (`offcanvas.helper.js`) + `contabilidad/api/viewsets.py` y su frontend.
**Tiempo estimado:** 6–8 días-persona.

---

## FASE 5-BIS — Reemplazo de Tabulator/DataTables por tecnología nativa Django

**Origen:** decisión explícita del usuario (2026-08-03), fuera del alcance original de la auditoría de 2026-07-26: Tabulator genera fricción recurrente con el backend porque exige mantener sincronizados **dos contratos independientes** — el JSON que serializa DRF y el formato de paginación/orden/filtro que la librería espera del lado del cliente. Esto es la causa raíz de hallazgos ya documentados como `DEAD-A1` (3 implementaciones divergentes de `StandardResultsSetPagination`) y buena parte de `FE-A6`/`FE-A9`.

**Inventario real (grep de todo el árbol, 2026-08-03):** Tabulator se usa en **56 archivos JS**, repartidos en prácticamente las ~20 apps tenant (`ventas`, `compras`, `contabilidad`, `bancos`, `empleados`, `clientes`, `facturas`, `proveedores`, `inventario`, `gastos`, `cotizaciones`, `proyectos`, `empresa`, `perfil`, `dashboard`, `core`). Reemplazarlo es una migración de arquitectura frontend, no un hallazgo puntual — de ahí que tenga su propia fase, insertada entre Fase 5 y Fase 6 en vez de mezclarse con FE-A6 (que ya cubría `setData` vs `replaceData` dentro del propio Tabulator).

### Tecnología elegida: `django-tables2` + `django-filter` + HTMX

**Por qué (decisión validada con el usuario, ver preguntas de alcance de esta sesión):** `django-tables2` renderiza la tabla directamente desde el `QuerySet` en el servidor — no existe un segundo contrato JSON que pueda desincronizarse. Encaja de forma nativa con HTMX, que el proyecto ya usa y aprueba en el Console público (`CLAUDE.md` §Frontend). Es la opción "más apropiada y compatible con Django" en sentido literal: es una librería de Django, no un adaptador sobre una librería JS externa.

**Alternativas evaluadas y descartadas para este caso:**
- **AG Grid Community (server-side row model):** grid más rico visualmente, pero conserva el mismo problema estructural (un contrato JSON independiente del backend) — solo cambia qué adaptador hay que mantener sincronizado, no elimina la clase de bug.
- **HTML nativo + HTMX sin librería:** más simple aún, pero obliga a reescribir a mano ordenar/paginar/filtrar por columna en cada listado — mayor código repetido que `django-tables2`, que ya resuelve eso de forma declarativa.

### Alcance decidido: piloto en 1 app antes de expandir

**App piloto: `gastos`** (0 hallazgos ALTO en la auditoría, único ejemplo — junto a `bancos` — de `test_multitenant_isolation.py` completo; superficie de riesgo mínima para validar el patrón).

**Estado: piloto (`gastos`) + expansión a `facturas`, `compras`, `contabilidad` (5/8 grillas), `ventas` (1/1 grilla real), `bancos` (2/2 grillas reales) y `empleados` (5/5 grillas, incluidas 2 Master-Detail) implementados (2026-08-03/04), todos pendientes de validación en runtime real** (ver "Validación final" más abajo — deliberadamente diferida al cierre de la expansión completa, no antes). Ver `REPORTE_FASE_5_PILOTO_TABLAS.md` para el detalle completo archivo por archivo de las primeras 3 apps, `REPORTE_FASE_5_BIS_CONTABILIDAD.md` para `contabilidad` (incluye por qué 3 de sus 8 grillas quedan deliberadamente fuera de este patrón), `REPORTE_FASE_5_BIS_VENTAS.md` para `ventas` (incluye por qué 2 de los 3 archivos que el plan original le asignaba resultaron ser código no conectado), `REPORTE_FASE_5_BIS_BANCOS.md` para `bancos`, y `REPORTE_FASE_5_BIS_EMPLEADOS.md` para `empleados` (incluye cómo se resolvió el patrón Master-Detail con `row_attrs` de django-tables2, sin JS de terceros). Resumen del piloto original (`gastos`):
- `apps/tenant/gastos/tables.py` (nuevo): `DocumentoSoporteTable` y `ResolucionDIANTable`, usando los `Selector.get_list()` ya existentes (`.only()` intacto, cero cambios al Service Layer).
- `apps/tenant/gastos/views.py` (nuevo): `DocumentoSoporteTableView`/`ResolucionDIANTableView`, `LoginRequiredMixin` + `SintelDSVMixin.get_empresa_id()` (misma fuente de verdad de aislamiento que `BaseTenantViewSet`, no una reimplementación paralela).
- 2 templates parciales nuevos (`partials/tabla_gastos.html`, `partials/tabla_resoluciones.html`) que renderizan `{% render_table table %}`.
- `gastos_list.html`: los contenedores `#grid-gastos`/`#grid-resoluciones` (vacíos, poblados por Tabulator via JS) se reemplazan por `#gastos-panel`/`#resoluciones-panel` con `hx-get`/`hx-trigger="load, gasto-created from:body, ..."`/`hx-boost="true"` — el HTML llega ya armado del servidor.
- `gasto_list.js`: se elimina toda la inicialización de Tabulator (columnas, formatters, KPIs client-side) — el archivo queda reducido a la delegación de eventos de los botones de acción (view/edit/anular/eliminar) y el manejo de offcanvas, que no cambian porque el HTML server-rendered usa las mismas clases/`data-uuid` que generaba Tabulator antes.
- **La API DRF (`apps/tenant/gastos/api/viewsets.py`) no se tocó** — sigue viva para los tests de IDOR existentes y para cualquier consumidor API-first. Las vistas nuevas son un camino de renderizado paralelo, no un reemplazo del backend.
- Nuevo test `test_multitenant_isolation_gastos_tabla_html` (en el archivo ya existente `test_multitenant_isolation.py`) — cubre las 2 vistas HTML nuevas específicamente, porque no son ViewSets DRF y no heredan la cobertura de aislamiento que ya tenía `/api/v1/gastos/`.
- `requirements.txt` + `config/settings.py` (`TENANT_APPS`, `DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"`): dependencia nueva agregada.

**Bloqueante explícito (misma limitación de entorno de la Sección 0):** no hay Docker/venv funcional en este host — el piloto se verificó con `py_compile`/`node --check`/lectura manual de consumidores, **no** se ejecutó nunca contra una base de datos real ni se visualizó en un navegador. Antes de dar el piloto por validado, ejecutar como mínimo:
```
pytest apps/tenant/gastos/tests/test_multitenant_isolation.py -v
```
y abrir manualmente el módulo Gastos en el workspace (ambas pestañas, buscar, paginar, ordenar por columna, crear/editar/anular/eliminar un registro) para confirmar paridad visual y funcional con la versión Tabulator que reemplaza.

### Criterio de expansión al resto de apps

**Decisión del usuario (2026-08-03): no gatear la expansión con la validación en runtime.** La expansión a las apps restantes se ejecuta primero (app por app, mismo patrón: `tables.py` + `views.py` + partial + editar `*_list.html` + recortar `*_list.js`), priorizando por el mismo criterio ya usado en Fase 7 (apps que tocan dinero primero: `facturas`, `contabilidad`, `ventas`, `compras`, luego el resto). La validación real en navegador/`pytest` de que las tablas cargan, ordenan, paginan y buscan igual que con Tabulator **se hace una sola vez, al final de toda la migración** (ver "Validación final", al cierre de esta fase) en vez de repetirse app por app como gate intermedio — así se aprovecha una sola sesión de acceso a un entorno Docker/venv funcional para validar todo el lote de una vez, en lugar de bloquear cada app individualmente.

**Riesgo aceptado explícitamente por el usuario:** si el patrón tiene un defecto sistémico no detectable por lectura de código (p. ej. la plantilla `django_tables2/bootstrap5.html` no existe en la versión instalada, o `hx-boost` no intercepta los enlaces de orden/paginación como se espera), ese defecto se replica en todas las apps migradas antes de descubrirse en la validación final, en vez de detectarse en el piloto único. La mitigación es que el patrón (selectors ya existentes + `SintelDSVMixin` + `SingleTableView`) es mecánico y ya se aplicó una vez sin sorpresas estructurales en `gastos`.

Cada app migrada debe declarar en su propio reporte qué columnas/formatters de Tabulator no tuvieron equivalente 1:1 (ej. KPIs calculados client-side desde filas cargadas, que en el patrón nuevo se recalculan server-side sobre el queryset completo — ver `views.py` de `gastos`, cambio de comportamiento **deseado**, no un defecto: el nuevo cálculo es más correcto porque no depende de cuántas filas haya cargado el grid).

**Progreso de la expansión:**

| App | Archivos Tabulator | Estado |
|---|---|---|
| `gastos` | `gasto_list.js` (2 grillas) | Migrado (piloto, 2026-08-03) |
| `facturas` | `facturas_list.js` (2 grillas: Ventas/Compras, misma tabla parametrizada por `naturaleza`) | Migrado (2026-08-03) |
| `compras` | `compras_list.js` | Migrado (2026-08-03) |
| `ventas` | `venta_list.js`, `resolucion_list.js`, `orden_list.js` | **Migrado 1/1 grilla real** (`venta_list.js`, 2026-08-04). `resolucion_list.js` y `orden_list.js` resultaron ser codigo no conectado al DOM actual (no arquitectura abandonada -- `orden_list.js`/`orden_editor.js` son de los commits mas recientes del repo, "OrdenVenta v3.10.5" en progreso) — ver `REPORTE_FASE_5_BIS_VENTAS.md` §0, decision de que hacer con ellos queda para el usuario |
| `contabilidad` | 8 archivos (`plantilla`, `retencion`, `libro_diario`, `periodo`, `cuenta`, `asiento`, `reporte`, `pendiente`) | **Migrado 5/8** (`plantilla`, `retencion`, `periodo`, `cuenta`, `asiento` — 2026-08-04). `libro_diario`, `reporte`, `pendiente` fuera de alcance deliberado: son vistas agregadas cross-app, no listados CRUD de un solo modelo — ver `REPORTE_FASE_5_BIS_CONTABILIDAD.md` §2 |
| `bancos` | `extracto_list.js`, `transaccion_list.js`, `cuenta_list.js` | **Migrado 2/2 grillas reales** (`cuenta_list.js`, `extracto_list.js`, 2026-08-04). `transaccion_list.js` nunca existió en el repo -- las transacciones ya se renderizan server-side dentro del offcanvas de detalle de extracto, sin Tabulator, desde antes de este plan. Ver `REPORTE_FASE_5_BIS_BANCOS.md` |
| `empleados` | 6 archivos | **Migrado 5/6** (`empleado_list.js`, `contrato_list.js`, `resolucion_list.js`, `nomina_list.js`, `liquidacion_list.js`, 2026-08-04). `nomina_historial.js` resultó ser código muerto (cargado pero sin ningún botón que lo invoque) -- no tocado, ver `REPORTE_FASE_5_BIS_EMPLEADOS.md` §4 |
| `inventario` | 6 archivos | Pendiente |
| `cotizaciones` | 6 archivos | Pendiente |
| `proveedores` | `proveedores_main.js`, `proveedores_form.js`, `cuentas_pagar_list.js` | Pendiente |
| `empresa` | 4 archivos | Pendiente |
| `proyectos` | `proyectos_list.js`, `nueva_tarea_list.js` | Pendiente |
| `clientes` | `clientes.cartera.js`, `clientes.list.js` | Pendiente |
| `dashboard` | `dashboard_main.js` | Pendiente |
| `perfil` | `perfil.page.js` | Pendiente |
| `core` | `mailinbox.page.js` | Pendiente |

**No se elimina Tabulator del proyecto hasta cerrar toda la tabla anterior.** `core/static/core/js/common/tabulator.factory.js` sigue disponible y en uso por las apps aún no migradas — es un rollout incremental, no un big-bang; cada fila de la tabla es un cambio aislado por app, revertible independientemente de las demás.

### Validación final (al cierre de la expansión completa, no antes)

Una sola vez, cuando la tabla de progreso de arriba esté 100% en "Migrado", ejecutar en un entorno Docker/venv funcional:
1. `pytest` completo de las apps migradas (incluye los `test_multitenant_isolation_*_tabla_html` nuevos de cada una).
2. Recorrido manual en navegador de cada grid migrado: carga inicial, orden por columna, paginación, búsqueda, y las acciones de fila (ver/editar/anular/eliminar u equivalentes por app) — confirmando paridad con el comportamiento que tenía Tabulator.
3. Confirmación explícita del usuario de que la paridad visual es aceptable (django-tables2 + Bootstrap 5 no replica pixel-a-pixel el diseño de tarjetas/badges que tenían los `formatter` de Tabulator).

Si esta validación final encuentra un defecto sistémico, se corrige una vez en el patrón compartido y se reaplica a las apps ya migradas — no se re-descubre app por app.

**Archivos afectados (piloto, ya aplicado):** `requirements.txt`, `config/settings.py`, `apps/tenant/gastos/tables.py` (nuevo), `apps/tenant/gastos/views.py` (nuevo), `apps/tenant/gastos/urls.py`, `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html`, `apps/tenant/gastos/templates/tenant/gastos/partials/tabla_gastos.html` (nuevo), `apps/tenant/gastos/templates/tenant/gastos/partials/tabla_resoluciones.html` (nuevo), `apps/tenant/gastos/static/gastos/js/features/gasto_list.js`, `apps/tenant/gastos/tests/test_multitenant_isolation.py`.
**Tiempo estimado (expansión completa, tras validar el piloto):** 10–14 días-persona para las ~19 apps restantes (más que Fase 5 original porque cada app requiere su propio `tables.py`+`views.py`, no solo tocar el archivo existente).

---

## FASE 6 — Simplificación, Deduplicación y Código Muerto — ✅ COMPLETADA (2026-08-03)

**Estado: ejecutada.** Ver `REPORTE_FASE_6.md` para el detalle completo. Resumen: DEAD-A1 unificado a 20/200 (decisión del usuario) con un hallazgo adicional más grave que lo reportado (`clientes/api/viewsets.py` importaba la SSoT correctamente pero una clase local del mismo nombre la sombreaba, anulando el import en silencio); cerrados los 2 hallazgos de código muerto que Fase 5 dejó documentados (FE-M1/M2/M3), que al investigarse revelaron un cluster mucho mayor — 50 archivos eliminados en total (JS/CSS/templates huérfanos de una arquitectura "workspace" alternativa abandonada, más limpieza de raíz); PERF-M3 no reproducible en el estado actual; `squashmigrations` de `gastos`/`proveedores` sigue bloqueado por falta de entorno Docker/venv.

**Objetivo:** fusiona las Fases 5–7 del plan original (Simplificación, Eliminación de Código Muerto, Eliminación de Duplicidad estructural) porque comparten el mismo criterio de decisión ("¿está referenciado? ¿hay una sola versión correcta?") y en varios casos los mismos archivos.

### 6.1 Deduplicación de comportamiento

| ID | Hallazgo | Acción | Criterio de aceptación |
|---|---|---|---|
| DEAD-A1 | `StandardResultsSetPagination` en 4 variantes con `page_size` distinto (10/100 vs. SSoT 20/200) | **Requiere decisión de producto, no solo técnica** (cambia el comportamiento visible de los grids) — llevar a quien apruebe antes de tocar código: ¿unificar a 20/200 en `proyectos`/`inventario`/`clientes`, o formalizar que esas 3 apps tienen un tamaño de página distinto a propósito? | Decisión documentada en este archivo con fecha y quién la tomó, antes de cualquier cambio de código |
| — | Tras decisión: eliminar las 3 clases duplicadas, importar la SSoT desde `apps/tenant/api/base.py` (o donde viva hoy) | `proyectos/api/viewsets.py:64`, `inventario/api/viewsets.py:40`, `clientes/api/viewsets.py:42` | 1 sola definición de `StandardResultsSetPagination` en el árbol |

### 6.2 Eliminación de código muerto (DEAD-M1..M8 + limpieza BAJO)

| Ítem | Acción | Verificación previa obligatoria |
|---|---|---|
| Apps huérfanas `apps/tenant/templates/` (además de `mail`/`mailinbox`, ya eliminadas en Fase 2) | Eliminar si confirma 0 referencias, igual que ARQ-A4 | Grep de 0 resultados en todo `apps/`/`config/` antes de `git rm` |
| ~25 plantillas huérfanas (`dashboard`, `contabilidad`, `empresa` — naming de generaciones anteriores) | Eliminar cada una tras confirmar 0 `{% include %}`/`{% extends %}`/`render()` que la referencie | Listado explícito por archivo antes de borrar, con el comando grep usado documentado en el reporte de esta fase |
| ~12 archivos JS huérfanos (`router.js`, `clientes.module.js`, `_csrf.js` marcado obsoleto) | Igual criterio — eliminar si 0 `<script src>` los referencia | Idem |
| 2 migraciones de `gastos` creadas el mismo día que se revierten entre sí | Evaluar `squashmigrations gastos` acotado a ese rango, no a todo el historial | Confirmar en un tenant de prueba que el esquema resultante es idéntico antes/después del squash |
| Alta rotación de migraciones en `proveedores` (18 migraciones para 1 modelo) | `squashmigrations proveedores` completo | **Requiere Docker/venv funcional para validar** — no ejecutar a ciegas; ver bloqueante de entorno en Sección 0. Coordinar con tenants ya provisionados (`django_migrations` de cada esquema) |
| Limpieza de raíz (~15 ítems BAJO): `test_output.txt`, `test_run*.txt`, `documentacion/_archive/` (276 archivos), `... copy.md`, `check_schema.py`, `clean_emojis.py`, `reset_migrations.sh` sueltos | `git rm` de lo que no tiene referencia en Makefile/CI; agregar `test_output.txt`/`test_run*.txt` a `.gitignore` (evita que vuelva a colarse — ya se coló una vez con 3 tests fallando documentados, ver TEST-A3) | Confirmar que ningún script de CI/Makefile invoca estos archivos antes de borrar |
| `PERF-M3` — código muerto con patrón N+1 (`get_balance_prueba`/`calcular_saldos_cuenta`) exportado como superficie pública | Eliminar o marcar `@deprecated` con fecha de remoción si algún consumidor externo aún podría usarlo | Grep de 0 llamadas internas; si se usa desde fuera del repo (API pública), no eliminar — deprecar |

### 6.3 Orden interno
1. Decisión de producto sobre `page_size` (bloquea DEAD-A1 pero no bloquea el resto de la fase).
2. Eliminación de código muerto de bajo riesgo (limpieza de raíz, apps huérfanas ya verificadas) — en paralelo a lo anterior.
3. `squashmigrations` al final, y solo con Docker/venv funcional disponible — es la única acción de esta fase con riesgo real sobre datos de tenants ya provisionados.

**Archivos afectados:** ~10 archivos de ViewSets/pagination, ~40 archivos/templates a eliminar, migraciones de `gastos`/`proveedores`.
**Tiempo estimado:** 4–6 días-persona (sin contar el tiempo de espera por acceso a un entorno Docker funcional para el squash).

---

## FASE 7 — Deuda de Testing

**Objetivo:** cerrar TEST-A1..A3, TEST-M1, y el backfill sistémico de TEST-C2 (14 de las ~16 apps calificadas aún sin `test_multitenant_isolation.py`).

### 7.1 Hallazgos puntuales

| ID | Hallazgo | Acción |
|---|---|---|
| TEST-A1 | `ventas` (0→ya tiene 3 tests desde Fase 1) / `compras` (1 archivo) — `compras` sigue con cobertura mínima | Backfill de `compras` con el mismo patrón usado para `ventas` en Fase 1 (fixtures `tenant1`/`tenant2`, 3 niveles: listado, IDOR directo, IDOR en FK) |
| TEST-A2 | Assertion tautológica `try/except Exception: pass` + `assert True` | `tests/public/tenants/test_integrity.py:328` — reemplazar por una aserción real que falle si la garantía atómica se rompe (ej. forzar la excepción esperada y verificar el estado de rollback, no solo "no crasheó") |
| TEST-A3 | `test_output.txt` (181 KB) rastreado en git, documenta 3 tests fallando en un commit pasado | Se resuelve junto con Fase 6 (limpieza de raíz) — `git rm` + `.gitignore`. **Antes de borrar**, triar si esos 3 tests siguen fallando hoy (correr la suite si hay entorno disponible) — si siguen rojos, abrir su propio hallazgo de seguimiento en vez de solo ocultar la evidencia |
| TEST-M1 | 26 tests con `@skip`/`skipTest` en 11 archivos, incluyendo pipeline XML DIAN | Triar uno por uno: reactivar los que ya no aplican razón de skip, documentar con comentario el motivo de los que deben seguir skippeados (financieramente crítico → no dejar sin explicación) |

### 7.2 Backfill de `test_multitenant_isolation.py` (TEST-C2)

**14 apps pendientes** (de ~16 calificadas; `gastos`/`bancos` ya lo tienen, `ventas` se agregó en Fase 1): `facturas`, `contabilidad`, `inventario`, `core`, `empresa`, `perfil`, `empleados`, `proyectos`, `proveedores`, `clientes`, `cotizaciones`, `dashboard`, `compras`, y las que falten según recuento real al momento de ejecutar esta fase.

**Priorización explícita (tocan dinero primero, per conclusión de la auditoría §9):**
1. `compras` (documento financiero con DSV, ya con cobertura mínima — sube de 1 a 3+ tests)
2. `facturas`, `contabilidad` (núcleo financiero, mayor LOC, mayor superficie de IDOR)
3. `inventario` (0 cobertura propia confirmada, además del bug FE-C1 ya corregido — validar que el fix no regresionó)
4. Resto de apps en cualquier orden

**Patrón obligatorio (no genérico, por app — repetir el proceso que documentó `REPORTE_FASE_1.md` para `ventas`):** leer el `business_service.py`/DSV real de cada app antes de escribir el test, para que las 3 aserciones (listado no cruza tenants, acceso directo por UUID de otro tenant → 404, IDOR vía FK relacionado → 400/404) reflejen el contrato real y no sean tautológicas (ver TEST-A2 como ejemplo explícito de qué NO hacer).

**Archivos afectados:** ~14 archivos nuevos `test_multitenant_isolation.py` + `conftest.py` donde falte, `tests/public/tenants/test_integrity.py`, limpieza de `@skip`.
**Tiempo estimado:** 6–10 días-persona (la mayor parte en backfill; puede paralelizarse entre 2-3 personas, una app por persona).

---

## FASE 8 — DevOps y Dependencias — ✅ COMPLETADA (2026-08-03)

**Estado: ejecutada.** Ver `REPORTE_FASE_8.md` para el detalle completo. Resumen: DEVOPS-A1..A5 y M1..M3 cerrados; M4 sin acción (requiere límites reales de infraestructura, no se especuló); DEP-A1 y M1..M3 acotados con límite superior (verificando primero que `django-rest-framework-mcp` sigue en uso real); DEP-A2 y el cierre de `continue-on-error` en CI siguen bloqueados por falta de Docker/venv. El cambio de mayor riesgo (DEVOPS-A1, usuario no-root) queda explícitamente sin verificar en runtime — requiere un build+up real antes de desplegar.

**Objetivo:** cerrar DEVOPS-A1..A5, DEVOPS-M1..M4, DEP-A1/A2, DEP-M1..M3, y quitar la deuda explícita dejada en Fase 1 (`continue-on-error: true` en `ruff`/`bandit` del nuevo CI).

| ID | Hallazgo | Acción | Riesgo |
|---|---|---|---|
| DEVOPS-A1 | `Dockerfile` sin `USER` — corre como root | Agregar usuario no-root (`RUN useradd -m appuser` + `USER appuser`) al final del `Dockerfile`, después de instalar dependencias que requieren permisos | Verificar que `collectstatic`/permisos de volúmenes montados no rompan con el usuario no-root — probar build completo antes de mergear |
| DEVOPS-A2 | Sin `.dockerignore` — `.env`, `.git/`, `venv/` se copian a cada capa | Crear `.dockerignore` con `.env`, `.git`, `venv`, `__pycache__`, `*.pyc`, `documentacion/_archive` | Ninguno — es puramente aditivo |
| DEVOPS-A3 | Ningún compose fija `DJANGO_DEBUG=False` explícito para producción | Agregar `DJANGO_DEBUG=False` explícito en `docker-compose.prod.yaml` (no depender solo del fallback ya corregido en Fase 1/SEC-C1 — defensa en profundidad) | Ninguno |
| DEVOPS-A4 | Sin escaneo de dependencias vulnerables | Agregar `pip-audit` (o `safety`) a `Makefile` (`make audit`) y al workflow de CI (`ci-quality-gate.yml` de Fase 1, mismo patrón `continue-on-error` inicial hasta triar hallazgos preexistentes) | Bajo — mismo patrón ya usado para ruff/bandit |
| DEVOPS-A5 | `make down` ejecuta `docker compose down -v`, borra el volumen de Postgres | Separar en `make down` (sin `-v`) y `make down-full`/`make reset-db` (con `-v`, con confirmación explícita) | **Cambio de comportamiento de un comando ya usado por el equipo** — comunicar el cambio antes de mergear, no solo en el commit message |
| DEVOPS-M1 | Contraseña de Postgres con fallback débil (`sintel`) | Quitar el fallback, forzar que `POSTGRES_PASSWORD` sea obligatorio (falla explícito si falta, no un valor débil silencioso) | Requiere que todo `.env` de desarrollo ya tenga el valor seteado — verificar `.env.example` primero |
| DEVOPS-M2 | Puertos 5432/6379 expuestos a `0.0.0.0` en compose base | Cambiar a `127.0.0.1:5432:5432` en `docker-compose.yaml` (dev); confirmar que `docker-compose.prod.yaml` ya lo mitiga (per hallazgo original) | Verificar que herramientas de desarrollo que se conectan desde otra máquina de la red local (si las hay) no dependan del bind actual |
| DEVOPS-M3 | Sin healthchecks en `web`/`celery`/`nginx` | Agregar `healthcheck:` a los 3 servicios (patrón ya usado en `db`/`redis` si existe, o estándar Docker) | Ninguno — aditivo |
| DEVOPS-M4 | Sin límites de CPU/memoria | Agregar `deploy.resources.limits` en `docker-compose.prod.yaml` | Requiere conocer los límites reales del host de producción — coordinar con quien administra la infraestructura antes de fijar valores, no adivinar |
| DEP-A1 | `django-rest-framework-mcp>=0.1.0a4` — alfa sin límite superior | Fijar límite superior (`>=0.1.0a4,<0.2`) o evaluar si sigue siendo necesario en producción | Ninguno técnico — verificar que el paquete siga siendo usado (grep de imports) antes de solo acotar la versión |
| DEP-A2 | Sin archivo de lock | Generar `requirements.lock`/`pip-compile` a partir del `requirements.txt` actual | Requiere Docker/venv funcional para generar el lock de forma reproducible — bloqueado por la misma limitación de entorno de Sección 0 |
| DEP-M1..M3 | Rangos sin límite superior (`django-filter`, `pdfminer.six`, `xhtml2pdf`), rango amplio del SDK de Anthropic | Acotar límites superiores conservadores (misma versión mayor actual) | Bajo — verificar CHANGELOG de cada paquete por breaking changes antes de acotar demasiado agresivo |
| — | Quitar `continue-on-error: true` de `ruff`/`bandit` en `ci-quality-gate.yml` (deuda de Fase 1) | Correr `ruff check apps config` y `bandit -r apps` una vez, triar el backlog de violaciones preexistentes, corregir o suprimir con justificación (`# noqa`/`# nosec` con comentario), luego quitar el flag | **Requiere Docker/venv funcional** — es la validación explícitamente pendiente desde Fase 1 |

**Orden interno:** DEVOPS-A2 (`.dockerignore`) primero — es el de mayor impacto de seguridad (secretos en capas de imagen) y cero riesgo. Luego DEVOPS-A1/A3/M1..M4 en paralelo. DEP-A2 y el cierre de `continue-on-error` van al final porque ambos requieren el entorno Docker/venv funcional que hoy no está disponible — documentar como bloqueado hasta que se resuelva el acceso al entorno.

**Archivos afectados:** `Dockerfile`, `.dockerignore` (nuevo), `docker-compose.yaml`, `docker-compose.prod.yaml`, `Makefile`, `requirements.txt`, `.github/workflows/ci-quality-gate.yml`.
**Tiempo estimado:** 4–5 días-persona (sin contar el tiempo bloqueado por acceso a entorno para DEP-A2 y el triaje de ruff/bandit).

---

## FASE 9 — Documentación y Gobernanza Final — ✅ COMPLETADA (2026-08-03, incidente resuelto 2026-08-04)

**Estado: ejecutada. Incidente resuelto.** Ver `REPORTE_FASE_9.md` §0/§0.1 — al limpiar emojis de 46 archivos `.py` (ARQ-M, regla `[CRITICAL] 0` de AGENTS.md), un paso de limpieza de espacios colapsó la indentación de Python en los 46 archivos. Todos tenían cambios del usuario sin commitear que no se pudieron separar de la corrupción vía git, así que **el usuario los restauró desde dos backups propios** (validados antes de restaurar: uno resultó estructuralmente distinto de HEAD y se descartó para el único archivo que lo necesitaba, `apps/tenant/core/api/viewsets.py`; el segundo backup para ese mismo archivo sí validó como evolución incremental limpia). Los 46 archivos compilan (`py_compile`) confirmado 2026-08-04. DOC-A1..A5, DOC-M1..M3 cerrados completos. ARQ-M (emojis en `.py`) queda sin reintentar — ver la lección documentada en `REPORTE_FASE_9.md` §0.1 antes de reintentarlo.

**Objetivo:** cerrar DOC-A1..A5, DOC-M1..M3, ARQ-M1..M6 (deriva documental), y dejar `arquitectura_general.md`/`MEMORY.md` alineados al HEAD real — la causa raíz que hizo posible que 2 apps completas (`compras`, `ventas`) pasaran desapercibidas antes de esta auditoría.

| ID | Hallazgo | Acción |
|---|---|---|
| DOC-A1 | Header de `arquitectura_general.md` (v3.10.5) 2 releases mayores atrás del HEAD (v3.16.3) | Actualizar versión/fecha del header tras completar el resto de esta fase (para que quede sincronizado con los cambios reales, no solo el número) |
| DOC-A2 | Tabla de cobertura de tests §10.3 desactualizada | Regenerar contando archivos reales (`find apps -name "test_*.py" -o -name "*_test.py"` o equivalente) tras completar Fase 7 |
| DOC-A3 | Índice §10.2 omite `bancos`, `compras`, `cotizaciones`, `dashboard`, `landing`, `ventas` | Agregar las 6 apps faltantes al índice, con enlace a su `.agent/AUDITORIA_FLUJO_*.md` correspondiente |
| DOC-A4 | Referencia a `REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md` (no existe) citada en 2 documentos canónicos | Quitar la referencia de `AGENTS.md` y `arquitectura_general.md`, o recrear el documento si el contenido sigue siendo relevante (confirmar con quien lo citó originalmente) |
| DOC-A5 | Auditoría previa (`INFORME_AUDITORIA_TENANT_APPS.md`, "99% PRODUCTION READY") con hallazgos propios sin resolver 6+ semanas después, uno de ellos (`servicio_asociado`) ahora contradicho por 15+ referencias activas | Marcar el documento como histórico/superado (mover a `_archive/` o agregar nota al inicio) — no es una fuente canónica confiable hoy |
| DOC-M1 | `AUDITORIA_INVENTARIO.md` citado en `AGENTS.md` no existe | Quitar la referencia o crear el documento si aplica |
| DOC-M2 | `mail`/`mailinbox` sin `.agent/` — ya no aplica, ambas apps se eliminaron en Fase 2 (ARQ-A4) | Cerrar sin acción — documentar en el reporte de esta fase que quedó obsoleto por trabajo previo |
| DOC-M3 | `CLAUDE.md` duplica sustancialmente `AGENTS.md` (segunda superficie de deriva) | Evaluar consolidar `CLAUDE.md` a solo referenciar `AGENTS.md` como fuente canónica, sin repetir contenido — **requiere confirmación del usuario**, ya que `CLAUDE.md` es leído automáticamente por herramientas distintas a `AGENTS.md` y podría ser intencional mantenerlos separados |
| ARQ-M1..M6 | Deriva documental adicional, naming inconsistente en `.agent/` de `ventas`/`bancos`, `.all()` sin `.only()` en validación de FK de serializers, ~30 archivos con emojis en `.py` (management commands) | Triar cada uno; los emojis en `.py` son el único con regla explícita no-negociable en `CLAUDE.md` ("No emojis en .py — causa SyntaxError") — priorizar ese subconjunto primero aunque el hallazgo diga que es "ASCII-safe en Python 3 moderno", para cumplir la regla escrita del proyecto |

**Cierre final del plan:** regenerar `MEMORY.md` con el estado real post-Fase 9 (todas las fases cerradas, referencias a los 9 reportes), y actualizar `arquitectura_general.md` §2/§9/§10 con el inventario completo de apps/endpoints/tests verificado contra el HEAD de ese momento — no contra el HEAD de esta auditoría (2026-07-26), que para entonces estará desactualizado igual que los documentos que se están corrigiendo.

**Archivos afectados:** `documentacion/arquitectura_general.md`, `MEMORY.md`, `AGENTS.md` (quitar referencia rota), `CLAUDE.md` (pendiente de decisión del usuario), `documentacion/INFORME_AUDITORIA_TENANT_APPS.md` (mover a `_archive/`).
**Tiempo estimado:** 3–4 días-persona.

---

## 2. Orden global de ejecución y dependencias entre fases

```
Fase 5 (Frontend) ──┐
                     ├─→ Fase 6 (Simplificación/Dedup/Dead code) ─→ Fase 7 (Testing) ─┐
Fase 8 (DevOps/Dep) ─┘                                                                ├─→ Fase 9 (Docs finales)
Fase 5-BIS (piloto grid) ──→ validación → expansión (en paralelo a Fase 6/7, app por app)
```

- **Fase 5 y Fase 8 pueden correr en paralelo** entre sí y con el inicio de Fase 6 — no comparten archivos (Frontend vs. Docker/CI/requirements).
- **Fase 5-BIS es independiente de Fase 5**: toca archivos de renderizado de tabla (`tables.py`/`views.py`/templates), no los guards/offcanvas/CSRF de FE-A/FE-M — pueden ejecutarse en paralelo salvo en los archivos que ambas tocan dentro de la misma app (ej. `*_list.js`), donde el orden recomendado es Fase 5-BIS primero (define la estructura final del archivo) y Fase 5 después (aplica guards sobre esa estructura ya reducida).
- **La expansión de Fase 5-BIS al resto de apps no bloquea ni depende de Fase 6/7/8/9** — es un track paralelo propio, gateado únicamente por la validación explícita del piloto (ver checklist en Fase 5-BIS).
- **Fase 6 depende parcialmente de Fase 5**: el helper `offcanvas.helper.js` de FE-A5 y la limpieza de `mostrarOffcanvasSeguro` son el mismo trabajo — no dupliques el análisis de qué copias eliminar.
- **Fase 7 debe ir después de Fase 6**: no tiene sentido escribir `test_multitenant_isolation.py` nuevo contra código que Fase 6 todavía va a mover/eliminar (templates, paginación).
- **Fase 9 va al final siempre**: documentar el estado real solo tiene sentido cuando el estado real ya se estabilizó — y debe incluir la decisión de stack de grillas (`django-tables2` reemplazando a Tabulator como estándar documentado en `CLAUDE.md`, una vez la expansión de Fase 5-BIS esté suficientemente avanzada).
- Los ítems marcados **"requiere Docker/venv funcional"** (squash de migraciones en Fase 6, `pip-compile` y cierre de `continue-on-error` en Fase 8, validación en runtime del piloto de Fase 5-BIS) quedan bloqueados hasta que se resuelva el acceso a un entorno de desarrollo funcional — no son bloqueantes para el resto de cada fase, solo para esos ítems puntuales.

## 3. Tiempo total estimado

| Fase | Tiempo estimado |
|---|---:|
| Fase 5 — Frontend | 6–8 días-persona |
| Fase 5-BIS — Piloto Tabulator→django-tables2 (`gastos`) | Ya implementado (2026-08-03), pendiente de validación en runtime — ver `REPORTE_FASE_5_PILOTO_TABLAS.md` |
| Fase 5-BIS — Expansión a las ~19 apps restantes (post-validación) | 10–14 días-persona |
| Fase 6 — Simplificación/Dedup/Dead code | 4–6 días-persona |
| Fase 7 — Deuda de Testing | 6–10 días-persona |
| Fase 8 — DevOps y Dependencias | 4–5 días-persona |
| Fase 9 — Documentación y Gobernanza | 3–4 días-persona |
| **Total (Fases 5–9 + expansión 5-BIS)** | **33–47 días-persona** |
| Total ya ejecutado (Fases 1–4, referencia) | ≈15–20 días-persona (estimado original del plan fuente) |
| **Total del plan completo (Fases 1–9)** | **≈48–67 días-persona**, paralelizable entre 2–3 personas salvo las dependencias señaladas en la Sección 2 |

## 4. Definition of Done del plan completo

- [ ] Los ≈158 hallazgos de `AUDITORIA_ENTERPRISE_2026-07-26.md` están en uno de estos tres estados, sin excepción: **corregido** (con reporte), **corregido con excepción documentada** (como ARQ-A2), o **bloqueado explícitamente** con la razón (como el squash de migraciones sin entorno Docker).
- [ ] `make dj-check && make test` corre limpio en un entorno funcional — confirmando retroactivamente las Fases 1–4 y validando las Fases 5–9.
- [ ] El CI (`ci-quality-gate.yml`) bloquea el merge si `pytest`, `ruff` o `bandit` fallan (sin `continue-on-error`).
- [ ] `arquitectura_general.md` y `MEMORY.md` reflejan el HEAD real al momento de cerrar Fase 9, incluyendo las 20 apps tenant + 5 públicas.
- [ ] Cada una de las ~16 apps calificadas tiene su `test_multitenant_isolation.py` de 3 niveles.
- [ ] 0 secretos (`.env`) alcanzables desde una imagen Docker construida (`docker history <imagen>` no muestra el archivo).
- [ ] Decisión de stack de grillas cerrada: o bien las ~20 apps migraron de Tabulator a `django-tables2`+HTMX (Fase 5-BIS completa) y `CLAUDE.md` se actualizó para reflejar el nuevo estándar, o bien se documentó explícitamente por qué la migración se detuvo en un subconjunto de apps — nunca un estado ambiguo de "a medias sin decisión".

## 5. Próximos entregables

Cada fase ejecutada debe producir su propio `REPORTE_FASE_N.md` (mismo formato que Fases 1–4: alcance, limitaciones de entorno, hallazgos resueltos con evidencia file:line, archivos tocados, checklist de criterios de cierre) antes de considerarse cerrada y pasar a la siguiente.

---

*Este documento reemplaza la sección "8. Plan de Refactorización" de `AUDITORIA_ENTERPRISE_2026-07-26.md` como fuente operativa para el trabajo restante — esa sección queda como referencia histórica del plan original, este documento es la versión corregida y con cobertura completa (100% de los hallazgos trazables a una fase).*
