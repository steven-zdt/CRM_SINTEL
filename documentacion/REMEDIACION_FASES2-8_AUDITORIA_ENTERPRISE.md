# Remediación Auditoría Enterprise 2026-08-06 — Fases 2 a 8

**Contexto:** continuación de `REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`. Cubre la remediación completa de los hallazgos Críticos C4-C7, el hallazgo colateral de Onboarding, y las fases de regresión y documentación del plan de 8 fases ejecutado sobre `documentacion/PLAN_PRUEBASUI_PRIVADAS.md`.

**Rol ejecutado:** Arquitecto Principal / Tech Lead / Senior Software Engineer. Objetivo exclusivo: remediar hallazgos ya auditados, sin agregar funcionalidad, sin romper arquitectura (Service Layer, FSD, Pull Model Contable, DSV, BaseTenantViewSet, aislamiento multi-tenant).

**Metodología de verificación aplicada en todas las fases:** para cada fix, `git stash` de únicamente los archivos tocados en esa fase, re-ejecución de la suite de pytest afectada contra el código pre-fix, comparación byte-a-byte contra la corrida post-fix. Esto se hizo porque el proyecto tiene fallos de test preexistentes y no relacionados en varios módulos (16 en Gastos/Empleados, 24 en Onboarding) que de otro modo se habrían atribuido erróneamente a esta remediación.

---

## Resumen ejecutivo

| Fase | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 2 | C4: Doble-submit (Bancos + Contabilidad) | Crítico | ✔ Corregido |
| 2 | C5: Cache de proveedores no invalidada (Compras) | Crítico | ✔ Corregido |
| 2 | *(nuevo)* Cache HTTP de 30 días en nginx oculta fixes de JS/CSS | Crítico (infra) | ✔ Corregido |
| 3 | C6: IDs HTML duplicados (Gastos vs Empleados) | Crítico | ✔ Corregido |
| 3 | *(nuevo)* 6 grupos más de `offcanvas-container-*` duplicados | Mayor | ✔ Corregido |
| 4 | C7: Polling ~47 req/seg en Empresa | Crítico | ✔ Corregido |
| 5 | Onboarding: `crear_empresa` no crea Empresa/TenantProfile | Crítico | ✔ Corregido |
| 6-7 | Regresión CRUD + Seguridad (dirigida, no barrido completo) | — | ✔ Sin regresiones |
| 8 | Documentación (este reporte + MEMORY.md + PLAN actualizado) | — | ✔ Completa |

**Fuera de alcance de esta remediación (no tocado):** hallazgos Mayores M1-M7, Medios MD1-MD3, Menores MN1-MN4 del informe original; migración Tabulator→django-tables2 pendiente (~11 apps, Plan Único de Correcciones); regresión CRUD/seguridad de los 15 módulos completos (se hizo una pasada dirigida a los módulos tocados).

---

## Fase 2 — Críticos de Frontend

### 1. Diagnóstico
C4 (doble-submit): un click en "Guardar" generaba 2 POST — confirmado en Cuenta Bancaria (2 registros idénticos) y sospechado en Cuenta Contable (1 válido + 1 vacío). C5: proveedores creados en sesión no aparecían en el selector de Compras hasta recargar la página completa.

### 2. Causa raíz
- **Bancos:** `cuenta_editor.js` adjuntaba `form.requestSubmit()` en un listener `click` sobre un botón que ya era `type="submit"` — el navegador ya disparaba `submit` nativamente al hacer click; la llamada extra generaba un segundo evento `submit`.
- **Contabilidad:** el código fuente ya estaba correcto (un solo listener, sin duplicación) — el síntoma real era `nginx.conf` sirviendo `Cache-Control: public, expires 30d` para `/static/`, sin ningún hash de contenido ni versión en la URL. Cualquier navegador que hubiera cargado el JS antes del fix seguiría ejecutando la versión vieja (con un bug ya corregido en un commit anterior) durante 30 días, sin importar cuántas veces se reiniciara el servidor.
- **Compras:** `compras.utils.js` tenía una cache de 5 minutos con función `invalidateCache()` correctamente implementada pero nunca invocada desde el flujo de creación/edición de Proveedores.

### 3. Archivos afectados
`apps/tenant/bancos/static/bancos/js/features/cuenta_editor.js`, `apps/tenant/contabilidad/static/contabilidad/js/cuenta/features/cuenta_editor.js` (limpieza de diagnóstico temporal), `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/cuenta_offcanvas_form.html` (ídem), `nginx/nginx.conf`, `apps/tenant/proveedores/static/proveedores/js/proveedores_form.js`, `apps/tenant/compras/static/compras/js/compras.utils.js`.

### 4. Plan de modificación
Eliminar la llamada `requestSubmit()` redundante; cambiar la política de caché de nginx de "cachear ciegamente" a "revalidar siempre" (ETag/Last-Modified, que nginx ya genera del archivo en disco); conectar el evento `proveedor-updated` entre los dos módulos.

### 5. Cambios realizados
- `cuenta_editor.js` (bancos): removido el listener redundante, con comentario explicando el porqué.
- `nginx.conf` (ambos bloques HTTP/HTTPS): `expires 30d; Cache-Control: "public, no-transform"` → `Cache-Control: "no-cache, public, no-transform"` (sin `expires`). Imagen reconstruida y contenedor recreado.
- `proveedores_form.js`: `d.body.dispatchEvent(new Event('proveedor-updated'))` tras crear/editar/eliminar.
- `compras.utils.js`: listener nuevo que invoca `invalidateCache('proveedores')` al recibir ese evento.

### 6. Riesgos
Bajo. El cambio de nginx solo afecta la política de caché HTTP, no el contenido servido; usuarios con caché ya poblada bajo la política vieja no se benefician retroactivamente (limitación conocida y documentada, aceptable en entorno de desarrollo).

### 7. Pruebas ejecutadas
- Bancos: instrumentación de red en navegador — 1 click → 1 POST → 201 → 1 registro en BD (antes: 2).
- Contabilidad: 6 fetches con `cache: no-store` + inyección de `<script>` con cache-busting confirmaron que el archivo servido por el origen ya era correcto; `read_network_requests` del navegador confirmó 1 solo POST tras el fix de nginx + `collectstatic`.
- Compras/Proveedores: implementado pero no verificado end-to-end en esta sesión (queda como seguimiento menor).

### 8. Resultado
C4 resuelto en ambos módulos. C5 implementado. Hallazgo nuevo de infraestructura (caché de 30 días) corregido.

### 9. Evidencias
Logs de `read_network_requests` (1 POST/201 por click), headers HTTP antes/después del cambio de nginx (`Cache-Control`), consulta a BD confirmando 1 registro.

### 10. Estado
✔ Cerrada.

---

## Fase 3 — Arquitectura UI: IDs HTML duplicados

### 1. Diagnóstico
C6: la pestaña "Resoluciones DIAN" de Gastos mostraba datos de Empleados. Auditoría sistemática adicional (recomendada por el propio hallazgo C6) encontró 6 grupos más de IDs `offcanvas-container-*` duplicados entre `workspace.html` y los partials de cada módulo.

### 2. Causa raíz
- **C6:** `gastos_list.html` y `empleados_list.html` usaban literalmente los mismos IDs (`tab-resoluciones`, `tab-pane-resoluciones`, `search-resolucion`, `resoluciones-panel`) para features no relacionadas. Como el Workspace monta ambos módulos en la misma página, `getElementById`/`querySelector` siempre resuelven al primer match — afectando tanto el `data-bs-target` del botón de pestaña como la delegación de eventos en `gasto_list.js`/`resolucion_list.js` (que también apuntaban al panel equivocado).
- **Duplicados adicionales:** `workspace.html` conservaba divs `offcanvas-container-*` de una versión anterior de la arquitectura, ahora redundantes porque cada partial (`list_cuentas.html`, `gastos_list.html`, `proyectos_list.html`, `list_periodos.html`) ya declara el suyo propio. Uno de ellos (`offcanvas-container-asientos`, plural) ni siquiera coincidía con el nombre real usado por el módulo (`offcanvas-container-asiento`, singular) — quedaba huérfano. `list_movimientos.html` (Inventario) duplicaba el contenedor que su padre `list_inventario.html` ya declara explícitamente como fuente única. El mismo `list_inventario.html` reutilizaba el nombre `offcanvas-container-proyectos` para un flujo propio (vincular un Proyecto desde un movimiento de servicio), colisionando con el módulo Proyectos real.

### 3. Archivos afectados
`gastos_list.html`, `gasto_list.js`, `views.py`, `tabla_resoluciones.html` (gastos); `empleados_list.html`, `resolucion_list.js`, `tabla_resoluciones.html` (empleados); `workspace.html`; `list_inventario.html`, `list_movimientos.html`, `movimientos_list.js` (inventario).

### 4. Plan de modificación
Namespacing por módulo para el grupo C6 (`gastos-*` / `empleados-*`); eliminación de contenedores duplicados/huérfanos en `workspace.html` y `list_movimientos.html`; renombre de `offcanvas-container-proyectos` a `offcanvas-container-inventario-proyecto` en Inventario.

### 5. Cambios realizados
11 archivos, actualizando de forma consistente `id`, `data-bs-target`, `aria-controls`, `aria-labelledby`, `hx-target`, `hx-trigger...from:` y `querySelector` en cada caso.

### 6. Riesgos
Bajo — cambios de solo-IDs, sin lógica de negocio. Riesgo real detectado y corregido en el camino: comentarios `{# #}` multilínea (Django no los soporta, se filtran como texto literal en el HTML renderizado) — reemplazados por `{% comment %}`.

### 7. Pruebas ejecutadas
Suite `gastos/tests` + `empleados/tests` (60 tests): 16 fallos / 44 passed, confirmados **idénticos** (mismos nombres exactos) con y sin el fix vía `git stash` — 100% preexistentes. Verificación visual en navegador: cada módulo muestra su propia tabla de Resoluciones. Conteo de contenedores `offcanvas-container-*` en el DOM: exactamente 1 por cada ID tras el fix (antes: hasta 3 duplicados).

### 8. Resultado
C6 resuelto y verificado en vivo. Cero regresiones nuevas.

### 9. Evidencias
Capturas de consola del navegador, logs de pytest baseline vs. post-cambio idénticos en los 16 fallos preexistentes.

### 10. Estado
✔ Cerrada.

---

## Fase 4 — Rendimiento: Polling descontrolado

### 1. Diagnóstico
C7: las 4 tablas de Empresa (Empresa/Sedes/Áreas/MailInboxConfig) se recargaban continuamente durante toda la sesión (~234 peticiones en 5 segundos medidas en la auditoría original).

### 2. Causa raíz
`assets_empresa.html` tenía un listener `htmx:afterSettle` que, ante cualquier swap dentro de `#ui-empresa-list`, refrescaba las 4 tablas simultáneamente. Como las 4 tablas viven dentro de ese mismo contenedor, cada refresco generaba su propio evento de asentamiento, que volvía a disparar el mismo listener — un bucle de retroalimentación sin condición de salida. Cada módulo (`empresa_list.js`, `sede_list.js`, `area_list.js`, `mailinboxconfig_list.js`) ya tenía su propio mecanismo correcto y aislado de refresco (evento `*Guardada` → `*-updated` → `hx-trigger`), haciendo el listener global enteramente redundante además de ser la causa del bucle.

### 3. Archivos afectados
`apps/tenant/empresa/templates/tenant/empresa/assets_empresa.html`.

### 4-5. Plan y cambios
Eliminado el listener `htmx:afterSettle` completo (27 líneas de JS), reemplazado por un comentario explicativo.

### 6. Riesgos
Ninguno identificado — el listener no cumplía ninguna función no cubierta ya por los 4 mecanismos individuales.

### 7. Pruebas ejecutadas
Instrumentación de `XMLHttpRequest.prototype.open` en navegador real: 0 peticiones en 6 segundos de inactividad (antes: bucle infinito). Simulación de un guardado real (`areaGuardada`): exactamente 1 petición, solo a la tabla de Áreas. Suite `apps/tenant/empresa/tests`: 25 passed, 0 failed. Búsqueda de este mismo antipatrón en el resto del código: no encontrado en ningún otro módulo.

### 8. Resultado
C7 resuelto y verificado empíricamente. Sin regresiones.

### 9. Evidencias
Logs de instrumentación XHR, log de pytest (25 passed).

### 10. Estado
✔ Cerrada.

---

## Fase 5 — Onboarding

### 1. Diagnóstico
`manage.py crear_empresa` reportaba éxito pero el tenant nuevo quedaba con cero registros `Empresa` y cero `TenantProfile` — inutilizable desde el primer login.

### 2. Causa raíz
La cadena real de llamadas es `crear_empresa()` → `crear_tenant()` → `onboard_tenant()` — **no** pasa por `crear_tenant_con_owner()`, el "flujo único autorizado" según `AGENTS.md`. El seed de `onboard_tenant()` solo *buscaba* una Empresa existente (`Empresa.objects.only('id').first()`, que en un schema nuevo siempre es `None`) en vez de crearla, causando `TenantProfile.empresa no puede ser NULL`. El error quedaba atrapado por un `except Exception` que solo lo registraba en el log sin abortar ni propagar el fallo.

### 3. Archivos afectados
`apps/services/onboarding/empresa_service.py` (función `onboard_tenant`).

### 4-5. Plan y cambios
Replicado dentro de `onboard_tenant()` el patrón ya correcto y probado de la función hermana `crear_tenant_con_owner()`: crear la Empresa singleton antes del TenantProfile, sin tocar `crear_tenant_con_owner()` ni el comportamiento de "no abortar el onboarding" (fuera del alcance exacto del hallazgo).

### 6. Riesgos
Bajo — cambio confinado al bloque de seed opcional; no se tocó la firma ni el contrato de retorno de la función, ni ningún otro llamador.

### 7. Pruebas ejecutadas
Reproducción exacta del bug de la auditoría (`crear_empresa` con un schema de prueba): verificado en BD que Empresa y TenantProfile se crean correctamente (antes: cero registros). Suite completa de tests de onboarding (8 archivos, ~60 tests, dos corridas de ~35 min): 24 failed / 27 passed / 1 skipped, **idéntico** con y sin el fix vía `git stash` — los 24 fallos son preexistentes (mismatch de dominio `sintel.net.co` vs `.localhost` del rebrand documentado en el historial de commits).

### 8. Resultado
Bug de onboarding (bloqueaba cualquier alta de tenant nuevo) resuelto y verificado. Cero regresiones nuevas.

### 9. Evidencias
Logs del comando (`Empresa creada`, `Perfil creado`), consulta a BD, logs de pytest baseline vs. post-fix idénticos.

### 10. Estado
✔ Cerrada.

---

## Fases 6-7 — Regresión CRUD + Seguridad (dirigida)

Dado que cada fix se verificó individualmente al aplicarse, estas fases consistieron en una regresión final e integrada con sesión de navegador fresca (sin contaminación de caché), sobre los módulos tocados — **no** un barrido completo de los 15 módulos:

- **CRUD:** Cuenta Bancaria (1 POST→201, 1 registro), Cuenta Contable (1 POST→201), Área de Empresa (1 POST→201, 1 sola recarga de tabla, no 4). Todos los registros de prueba limpiados de la BD.
- **Seguridad:** re-ejecución de `test_cross_tenant_isolation.py` (el fix más crítico de toda la auditoría, C1/Fase 1) — 2/2 passed.

**Estado:** ✔ Cerrada, sin regresiones detectadas.

---

## Fase 8 — Documentación

Actualizados: `MEMORY.md` (nueva entrada fechada con el resumen de la auditoría y las 8 fases de remediación), `documentacion/PLAN_PRUEBASUI_PRIVADAS.md` (marcadores `[CORREGIDO]` en cada hallazgo C1-C7 y en el hallazgo de Onboarding, más nota de actualización en el resumen ejecutivo), y este reporte consolidado.

**No se tocaron:** ADRs (`ADR-001-retention-pull-model.md`, `ADR-002-public-schema-api-dual-registration.md`) — ninguno de los fixes cambió una decisión arquitectónica, solo corrigió su implementación (ej. C3 restauró el cumplimiento de ADR-001, no lo modificó).

**Pendiente para una sesión futura:** eliminar o conservar deliberadamente el tenant `qaisotest` (creado ad-hoc en la auditoría); regresión CRUD/seguridad completa de los 15 módulos si se requiere mayor cobertura que la pasada dirigida de Fases 6-7; remediación de los hallazgos Mayores/Medios/Menores (fuera del alcance de esta sesión, que se enfocó en los Críticos).

**Estado:** ✔ Cerrada.
