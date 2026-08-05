# REPORTE FASE 9 — Documentación y Gobernanza Final

**Fecha:** 2026-08-03 (incidente resuelto 2026-08-04)
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 9" — DOC-A1..A5, DOC-M1..M3, ARQ-M1..M6.
**Estado: COMPLETADA.** El incidente de §0 quedó resuelto el 2026-08-04 — los 46 archivos fueron restaurados y verifican `py_compile` limpio. Ver §0.1.

---

## 0. Incidente — corrupción de 46 archivos `.py`

**Qué pasó:** al ejecutar la limpieza de emojis en archivos `.py` (parte de ARQ-M, regla `[CRITICAL] 0` de `AGENTS.md` — "Cero Caracteres Especiales en Código Python"), se usó un script en dos pasos: (1) eliminar los caracteres emoji, (2) colapsar espacios dobles residuales que quedaban donde antes había `"✅ texto"` → `" texto"`. El paso (2) se aplicó con una expresión regular sin anclar a inicio de línea, sobre el **archivo completo**, no solo cerca de donde se había borrado un emoji. Esto colapsó **toda la indentación de Python** (4, 8, 12 espacios) a un solo espacio en cada línea que tenía 2 o más espacios de indentación, en los 46 archivos que contenían al menos un emoji.

**Detección:** `python -m py_compile` sobre los 46 archivos modificados — todos fallan con `IndentationError`/`SyntaxError`.

**Por qué no se pudo revertir automáticamente:** los 46 archivos ya tenían cambios del usuario sin commitear **antes** de que este script los tocara (confirmado con `git status` — todos marcados `M` contra HEAD, algunos con >1000 líneas de diferencia, ej. `apps/tenant/core/api/viewsets.py`). `git checkout -- <archivo>` habría revertido a HEAD, descartando tanto la corrupción como ese trabajo previo del usuario — la única fuente de verdad disponible (git) no permite distinguir "cambio previo legítimo" de "corrupción de este script", porque ambos son modificaciones sin commitear sobre el mismo archivo.

**Recuperación intentada antes de escalar al usuario:**
1. Historial local de editores (`AppData/Roaming/{Code,Antigravity,Windsurf}/User/History`) — sin coincidencias para los nombres de archivo afectados.
2. `git fsck --unreachable --dangling` — 0 blobs sueltos recuperables (los archivos nunca se llegaron a `git add`).
3. Reconstrucción automática de indentación — **descartada deliberadamente**: dado que la transformación colapsó TODOS los niveles de indentación a 1 espacio por igual, no hay información suficiente para inferir si una línea era de profundidad 1, 2 o 3. Un intento automático podría producir un archivo sintácticamente válido pero con bloques mal anidados — un bug silencioso, potencialmente peor que el `SyntaxError` actual (que al menos es imposible de pasar desapercibido).

**Decisión (usuario, 2026-08-03):** el usuario tiene una copia/backup propio y va a restaurar los 46 archivos por su cuenta. No se tomó ninguna acción adicional sobre ellos.

**Lista completa de los 46 archivos afectados:**
```
apps/public/tenants/management/commands/auditar_dominios_tenants.py
apps/public/impuestos/management/commands/poblar_catalogo_dian.py
apps/public/tenants/management/commands/auditar_tenant.py
apps/tenant/core/tests/test_architecture_ssot.py
apps/public/impuestos/api/datatables.py
apps/public/tenants/middleware_urlconf.py
apps/public/tenants/management/commands/verificar_eliminacion_tenant.py
apps/tenant/landing/api/serializers.py
apps/public/tenants/management/commands/ensure_public_domains.py
apps/public/tenants/management/commands/setup_public_tenant.py
apps/tenant/landing/views_ui.py
apps/public/console/management/commands/debug_tenant_creation.py
apps/public/tenants/management/commands/auditar_referencias_admin_login.py
apps/public/tenants/management/commands/backup_tenant.py
apps/public/console/management/commands/diagnostico_tenant.py
apps/public/tenants/management/commands/fix_all_tenant_domains.py
apps/public/tenants/management/commands/fix_tenant_domains.py
apps/public/tenants/management/commands/generar_tenants_prueba.py
apps/public/core/management/commands/test_email.py
apps/public/tenants/management/commands/analizar_tenants_prueba.py
apps/public/tenants/management/commands/backup_all_tenants.py
apps/public/tenants/management/commands/crear_empresa.py
apps/public/tenants/management/commands/diagnostico_404.py
apps/public/tenants/management/commands/fix_dev_domains.py
apps/tenant/landing/forms.py
apps/tenant/landing/api/viewsets.py
apps/public/tenants/management/commands/ensure_public_domain.py
apps/public/tenants/management/commands/fix_migration_history.py
apps/public/tenants/management/commands/inspect_tenant_columns.py
apps/tenant/core/services/activation_service.py
apps/tenant/landing/api/urls.py
apps/public/accounts/management/commands/sanitize_empty_usernames.py
apps/public/impuestos/management/commands/impuestos_seed.py
apps/public/impuestos/management/commands/impuestos_smoke.py
apps/public/tenants/management/commands/cleanup_tenant_duplicates.py
apps/public/tenants/management/commands/migrate_tenant_if_needed.py
apps/public/tenants/management/commands/restore_tenant.py
apps/tenant/core/api/viewsets.py
apps/public/impuestos/management/commands/impuestos_export_json.py
apps/public/tenants/api/viewsets.py
apps/public/tenants/management/commands/validate_domain_correspondence.py
apps/public/tenants/services/deletion_service.py
apps/tenant/contabilidad/admin.py
apps/tenant/landing/urls_ui.py
apps/tenant/landing/services/landing_info_service.py
apps/tenant/landing/services/__init__.py
```

**Ningún otro archivo de esta fase, ni de fases anteriores, se vio afectado** — el daño está contenido a exactamente estos 46 archivos, todos tocados por el mismo script en la misma operación.

---

## 0.1. Resolución (2026-08-04)

El usuario restauró los 46 archivos desde dos backups propios, en dos rondas:

1. **`C:\Users\Administrator\Documents\Backup\crm_sintel-01-06-2026`** — 45 de los 46 archivos copiados directamente, cada uno verificado individualmente con `python -m py_compile` (todos OK).
2. **`apps/tenant/core/api/viewsets.py`** (el archivo restante) no se restauró desde el backup del 1 de junio: la comparación de líneas (backup=898, HEAD=1016, estado pre-corrupción=1173) y un `diff` directo contra HEAD mostraron que ese backup era una versión **estructuralmente distinta**, no una evolución incremental — restaurarlo habría descartado ~275 líneas de trabajo legítimo (evolución de HEAD + cambios previos sin commitear). Se le pidió al usuario un backup más reciente.
   El usuario indicó **`C:\Users\Administrator\Documents\Backup\crm_sintel_antesde_despliegue`** (archivo fechado 9-jun, 1123 líneas — mucho más cerca de las 1173 del estado pre-corrupción). Un primer `diff` sin normalizar mostró el archivo completo como distinto (`1,1016c1,1123`), pero esto resultó ser un falso positivo: el backup tenía terminadores de línea CRLF y HEAD LF, así que **cada línea** difería por el `\r` final. Repitiendo el diff con `--strip-trailing-cr` se confirmó que es una evolución incremental limpia de HEAD (134 inserciones, 27 eliminaciones): agrega el endpoint `resend_activation_code` y el flujo dual-schema de `activate_with_code` (resolución de tenant desde el payload en schema público) — exactamente el patrón `ADR-002-public-schema-api-dual-registration.md` referenciado en `CLAUDE.md`. Restaurado con normalización de `\r\n`→`\n` para consistencia con el resto del repo, verificado con `python -m py_compile` (OK).

**Verificación final:** los 46 archivos de la lista de §0 fueron recorridos con `python -m py_compile` en una sola pasada — **los 46 compilan sin error.**

**Lección para futuras limpiezas de emojis en batch (si se retoma ARQ-M):** hacerlo archivo por archivo con verificación `py_compile` inmediata tras cada uno, nunca con una regex de colapso de espacios sin anclar a inicio de línea aplicada al archivo completo.

---

## 1. Trabajo completado en esta fase (fuera del incidente)

### DOC-A1 — Header de `arquitectura_general.md`
Actualizado versión (3.10.5 → 3.16.3) y fecha, con nota explicando que la sincronización se hizo al cerrar las Fases 1-6/8/9 de `PLAN_UNICO_CORRECCIONES.md`.

### DOC-A2 — Tabla de cobertura de tests (§10.3)
Recontada con la metodología real del repositorio (`apps/tenant/<app>/tests/` + `tests/tenant/<app>/`, las 2 ubicaciones donde el proyecto reparte tests por app). Total real de archivos de test en todo el repositorio: **336** (vs. 329 de la auditoría original — la diferencia son los tests nuevos agregados en Fases 5/5-BIS de este plan). Documentado explícitamente que las suites cross-cutting (`tests/api`, `tests/celery*`, `tests/multitenant`, `tests/smoke`, etc.) no están atribuidas a una app específica, y que un recuento final más preciso queda para después de la Fase 7 (cuando el backfill de aislamiento mueva estos números de forma significativa) — tal como pedía la propia acción del hallazgo.

### DOC-A3 — Índice §10.2
Se encontró que `bancos`, `compras`, `cotizaciones`, `dashboard`, `ventas` ya habían sido agregados en una sesión anterior (Fase 1, DOC-C1). Solo faltaba `landing` — agregado, apuntando a `apps/tenant/landing/.agent/AUDITORIA_FLUJO_LANDING.md` (confirmado que existe).

### DOC-A4 — Referencia rota a `REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md`
Eliminada de los 3 sitios donde aparecía (`AGENTS.md` §18.8.4, `arquitectura_general.md` §7 y §10.1). En la tabla de §10.1 se reemplazó la fila rota por una real y previamente ausente: `docs/ADR-002-public-schema-api-dual-registration.md` (confirmado que existe en el repositorio pero no estaba indexado en esa tabla).

### DOC-A5 — `INFORME_AUDITORIA_TENANT_APPS.md`
Se agregó una nota `WARNING` al inicio del documento marcándolo como histórico/no-canónico, explicando por qué (hallazgos propios sin resolver 6+ semanas después, uno contradicho por 15+ referencias activas) y redirigiendo a la auditoría 2026-07-26 y al plan único como fuentes actuales. No se movió a `_archive/` — se optó por la opción más liviana que ya ofrecía el propio hallazgo.

### DOC-M1 — Referencia a `AUDITORIA_INVENTARIO.md`
La regla en `AGENTS.md` §16 nombraba un archivo específico (`AUDITORIA_FLUJO_COMPLETO.md`) que no coincide con el nombre real en la mayoría de las apps (cada una usa su propia convención: `AUDITORIA_FLUJO_COMPLETO_FACTUR.md`, `AUDITORIA_COMPLETA_CONTABILIDAD.md`, etc. — ver tabla §10.2). Se reescribió la regla para apuntar a esa tabla en vez de hardcodear un nombre de archivo que no es universal.

### DOC-M2 — Sin acción
`mail`/`mailinbox` ya no tienen nada que auditar — ambas apps se eliminaron completas en la Fase 2 (ARQ-A4). Hallazgo cerrado por trabajo previo, confirmado y documentado.

### DOC-M3 — Consolidación de `CLAUDE.md`
Por decisión del usuario, se redujo `CLAUDE.md` de 361 a ~130 líneas: se conservó la sección de `Commands` completa (referencia operativa práctica, bajo riesgo de duplicación), el diagrama de estructura FSD, y la tabla de reglas no-negociables (quick-lookup). Se reemplazaron las secciones largas que duplicaban `AGENTS.md` (multi-tenant, DSV, auth, bridge cross-schema, integración contable con ejemplos de código, y las narrativas tipo changelog de v3.7.1/v3.7.3/v3.7.4) por punteros cortos a las secciones numeradas correspondientes de `AGENTS.md` (`§15`, `§17`, `§18`, `§26`). De paso se corrigió la afirmación desactualizada de que Tabulator es el estándar de grillas — ahora refleja la migración a `django-tables2` en curso (Fase 5-BIS), que es justo la staleness que el usuario señaló al tomar la decisión.

### ARQ-M — Triage
- **Emojis en `.py` (~30-46 archivos):** intentado, causó el incidente de §0. Sin resolver.
- **Naming inconsistente en `.agent/` de `ventas`/`bancos`:** confirmado (`ventas` usa `ARQUITECTURA_VENTAS.md` en vez del patrón `AUDITORIA_FLUJO_*.md` del resto de apps). **No se tocó** — es un cambio de bajo valor (cosmético, no funcional) que requeriría actualizar la referencia que esta misma fase acaba de agregar en `arquitectura_general.md` §10.2; se decidió no encadenar una operación más de renombrado de archivos inmediatamente después del incidente de §0. Queda documentado para una pasada futura de menor presión.
- **`.all()` sin `.only()` en validación de FK de serializers:** confirmado un patrón real y extendido (`compras`, `empleados`, `empresa`, `inventario`, `perfil`, al menos 5 apps, 15+ sitios) — es el uso estándar de DRF (`PrimaryKeyRelatedField(queryset=Model.objects.all())`) para resolver un FK a partir de un UUID/PK enviado por el cliente, no una fuga de datos: el aislamiento real lo da el esquema PostgreSQL por tenant, exactamente como ya caracterizaba el hallazgo original ("bajo riesgo real por aislamiento de esquema"). Dado el riesgo de tocar ~15 sitios de validación de FK justo después del incidente de §0, se documenta como hallazgo confirmado pero de baja prioridad, sin acción en esta sesión.

---

## 2. Archivos tocados (fuera del incidente)

```
M  documentacion/arquitectura_general.md
M  AGENTS.md
M  documentacion/INFORME_AUDITORIA_TENANT_APPS.md
M  CLAUDE.md
M  MEMORY.md
M  documentacion/PLAN_UNICO_CORRECCIONES.md
?? documentacion/REPORTE_FASE_9.md

# Incidente (§0) — 46 archivos .py, corruptos, el usuario los restaura por su cuenta
```

No se ejecutó ningún `git add`/`git commit`.

## 3. Checklist de cierre

- [x] Incidente detectado, contenido (no se propagó a más archivos), documentado con total transparencia antes de continuar cualquier otro trabajo.
- [x] Se agotaron las vías de recuperación automática razonables antes de escalar al usuario (historial de editores, git fsck) — no se intentó una reconstrucción especulativa de indentación que arriesgara corrupción silenciosa.
- [x] `MEMORY.md` deja constancia explícita del incidente y de su resolución.
- [x] DOC-A1..A5, DOC-M1..M3 cerrados con verificación (grep de 0 referencias rotas remanentes tras cada fix).
- [x] DOC-M3 (CLAUDE.md) aplicado según la decisión explícita del usuario, sin remover contenido operativo genuinamente único de Claude Code.
- [x] **Incidente de §0 resuelto (2026-08-04):** los 46 archivos restaurados desde backups del usuario, verificados uno por uno y en una pasada final conjunta con `py_compile` — todos compilan. Ver §0.1.
- [ ] **ARQ-M (emojis en .py):** sin reintentar — el riesgo que causó el incidente sigue presente si se repite el mismo enfoque; ver la lección en §0.1 antes de reintentar.
- [ ] **ARQ-M (naming `.agent/` ventas, `.all()` en serializers):** documentados, sin acción — bajo riesgo, diferidos deliberadamente.

## 4. Siguiente paso

1. Fase 9 queda cerrada. El único punto pendiente del plan único es **Fase 7 (Testing)**, la última fase por instrucción explícita del usuario.
2. Si se retoma la limpieza de emojis (ARQ-M) en el futuro: hacerlo archivo por archivo con verificación `py_compile` inmediata después de cada uno, nunca en un batch sin punto de control intermedio, y nunca con una regex de colapso de espacios que no esté anclada a inicio de línea.
