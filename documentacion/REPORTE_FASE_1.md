# REPORTE FASE 1 — Corrección de Hallazgos Críticos

**Fecha:** 2026-07-26
**Alcance:** Los 15 hallazgos CRÍTICOS de `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md` (SEC-C, PERF-C, FE-C, TEST-C, DEVOPS-C, DOC-C, ARQ-C). No se tocó ningún hallazgo ALTO.
**Metodología aplicada por hallazgo:** analizar → validar contra el código real → confirmar evidencia (file:line) → mapear dependencias/consumidores → diseñar la corrección más quirúrgica posible → verificar que no exista ya un patrón correcto equivalente en otra app → aplicar → releer el archivo completo → verificar sintaxis.

---

## 0. Limitación de entorno (aplica a toda la fase)

No fue posible ejecutar `make dj-check` / `make test` / aplicar migraciones reales en este entorno:

- **Docker:** el stack `crm_sintel` (dev) no resolvía nombres de host entre contenedores (`could not translate host name "db"`) incluso tras recrear la red desde cero (`docker compose down && docker compose up -d`). Además, los puertos `5432`/`8000` ya estaban ocupados por otro proyecto no relacionado (`ecommerce_sintel_*`) corriendo en el mismo host, y existe un stack `sintel_prod_*` en paralelo que no se tocó. Se dejó el stack `crm_sintel` completamente detenido (`docker compose down`, sin `-v`) al terminar, igual que se encontró.
- **venv:** `venv/pyvenv.cfg` apunta a `C:\Python314\python.exe`, que no existe en este host. Se usó un Python 3.13 del sistema (`AppData\Local\Programs\Python\Python313`) solo para `py_compile` (sin las dependencias del proyecto instaladas).

**Verificación real aplicada en su lugar:**
- `python -m py_compile` sobre los 15 archivos `.py` tocados → **todos limpios, 0 `SyntaxError`**.
- `node --check` sobre los 2 archivos `.js` tocados → **limpios**.
- Lectura completa de cada archivo modificado y de sus consumidores directos (imports, call sites, templates/JS que llaman al endpoint) para razonar manualmente la corrección — documentado punto por punto abajo.
- Validación de YAML del nuevo workflow de CI con `PyYAML` (confirmando que la única discrepancia — `on:` interpretado como `True` — es un artefacto conocido de PyYAML compartido por los otros dos workflows ya existentes en el repo, no un error real).

**Recomendación antes de continuar a Fase 2:** ejecutar `make dj-check && make test` (o al menos `pytest apps/tenant/ventas/tests/test_multitenant_isolation.py apps/tenant/facturas apps/tenant/contabilidad apps/tenant/inventario -q`) en un entorno con Docker/venv funcional. Esta fase se entrega con alta confianza de corrección por lectura y trazado manual de dependencias, pero **sin confirmación de ejecución real**.

---

## 1. Hallazgos resueltos

### SEC-C1 — `DJANGO_DEBUG` por defecto inseguro
**Archivo:** `config/settings.py:28`
**Cambio:** `os.getenv('DJANGO_DEBUG', 'True')` → `os.getenv('DJANGO_DEBUG', 'False')`.
**Por qué es seguro:** `.env` (desarrollo local) ya fija `DJANGO_DEBUG=True` explícitamente, y `.env.example` (plantilla para nuevos despliegues) ya documentaba `False` como el valor correcto — el código estaba en contradicción con su propia plantilla. El cambio no afecta el flujo de desarrollo local (sigue en `True` vía `.env`); solo corrige el *fallback* cuando la variable no está definida en absoluto.
**No se tocó** la lógica de bypass en `apps/tenant/api/permissions.py` / `apps/tenant/api/mixins.py` / `apps/public/core/middleware.py` (desacoplar esos bypasses del flag `DEBUG` es un cambio de arquitectura de seguridad más profundo — se deja para Fase 3, `SEC-A`/`SEC-M`, para no mezclar una corrección de configuración con un rediseño de permisos en la misma fase).

### SEC-C2 — IDOR en `ItemFacturaViewSet` / `NotaCreditoViewSet`
**Archivo:** `apps/tenant/facturas/api/viewsets.py:1016,1072`
**Cambio:** `permission_classes = [IsAuthenticated]` → `[IsTenantMember, IsAuthenticated]` en ambos ViewSets (`IsTenantMember` ya estaba importado en el archivo y usado correctamente en otro ViewSet del mismo módulo — patrón ya presente, solo faltaba aplicarlo aquí).

### PERF-C1 — `AsientoContable` sin `UniqueConstraint` de idempotencia
**Archivos:** `apps/tenant/contabilidad/models.py` (constraint agregada), `apps/tenant/contabilidad/integracion/contabilizador.py` (captura `IntegrityError` como respaldo), migración nueva `apps/tenant/contabilidad/migrations/0014_asientocontable_uniq_documento_origen.py`.
**Cambio:** `UniqueConstraint(fields=['empresa','documento_origen_app','documento_origen_modelo','documento_origen_id'], condition=Q(documento_origen_reversado=False, documento_origen_id__isnull=False))`. Se excluyen los reversales porque `Contabilizador.reversar_asiento()` reutiliza intencionalmente el mismo `documento_origen_*` que el asiento original (verificado leyendo el método completo).
**Riesgo a validar antes de aplicar la migración en cualquier esquema con datos reales:** si algún tenant ya tiene asientos duplicados por la misma condición de carrera que esta constraint previene, `migrate_schemas --tenant` fallará al aplicar `0014`. Recomendación: correr esta consulta contra cada esquema tenant antes de migrar en producción:
```sql
SELECT empresa_id, documento_origen_app, documento_origen_modelo, documento_origen_id, COUNT(*)
FROM contabilidad_asientocontable
WHERE documento_origen_reversado = false AND documento_origen_id IS NOT NULL
GROUP BY 1,2,3,4 HAVING COUNT(*) > 1;
```
Si esa consulta devuelve filas, hay que resolver los duplicados existentes (fusionar/anular) antes de migrar.

### PERF-C2 — Race condition en `Factura.consecutivo`
**Archivo:** `apps/tenant/facturas/services/business_service.py:88-93`
**Cambio:** se agregó `Empresa.objects.select_for_update().get(pk=empresa.pk)` antes de calcular `Max(consecutivo)`, replicando el mismo patrón (lock sobre una entidad contenedora estable, no sobre la tabla que crece sin límite) ya usado correctamente en `gastos/services/crud_service.py:_obtener_siguiente_consecutivo` (bloquea `ResolucionDIAN`, no `DocumentoSoporte`). La función ya estaba decorada `@transaction.atomic`, así que el lock se libera correctamente al finalizar.

### PERF-C3 — Bug de tipo + escritura no atómica en `importar_factura_desde_ubl`
**Archivos:** `apps/tenant/facturas/utils/ubl_parser.py`, `apps/tenant/facturas/services/services_mail_ingestion.py`.
**Hallazgo ampliado durante el análisis de dependencias:** la función tiene **dos** call sites en el mismo archivo, no solo el de importación real:
1. Línea ~314 (antes 301): ruta de importación real — `importar_factura_desde_ubl(xml_text)` (persist=True, comportamiento sin cambios).
2. Línea ~700: ruta de **previsualización** ("PASO 4.1: extraer solo metadatos, sin persistir") — con el código anterior, esta ruta **también persistía una Factura real** en cada previsualización, porque `importar_factura_desde_ubl` siempre persiste. Esto es más grave que el `AttributeError` original: no solo fallaba, sino que además creaba registros reales antes de que el usuario confirmara nada.

**Cambios:**
- `importar_factura_desde_ubl(xml_text, empresa_id=None, persist=True)`: nuevo parámetro `persist`. Si `False`, retorna el `dict` de datos parseados sin tocar la base de datos (restaura el contrato original que ambos call sites ya asumían).
- Persistencia de Factura + Items envuelta en `transaction.atomic()` (antes: `FacturaCRUDService.crear()` confirmaba inmediatamente y el loop de items podía fallar a medio camino, dejando una factura huérfana).
- Ruta de importación real (línea ~314): reemplaza la reconstrucción manual de un `dto` (que llamaba `.get()` sobre lo que ya era una instancia `Factura`, garantizando `AttributeError`) por el manejo directo del objeto `Factura` retornado, con mapeo explícito a `(payload, status_code)` — éxito→201, `IntegrityError` (numero/cufe duplicado)→409, `ValueError`→422 — consistente con el contrato que ya consume el código de manejo de resultados más abajo en el mismo archivo.
- Ruta de previsualización (línea ~700): ahora llama `importar_factura_desde_ubl(xml_text, persist=False)`, restaurando el comportamiento "solo lectura" que su propio comentario ya prometía.

**No resuelto en esta fase (fuera de alcance de un CRÍTICO puntual):** esta ruta de respaldo no replica la validación de NIT-tenant (`document_not_for_tenant`) que sí aplica la ruta principal `document_ingest`. Queda como nota para quien la use: solo se activa cuando el paquete `document_ingest` no está disponible.

### FE-C1 — `parseInt()` sobre UUID en `inventario_editor.js`
**Archivo:** `apps/tenant/inventario/static/inventario/js/features/inventario_editor.js:50`
**Cambio:** eliminada la línea `data.producto = parseInt(data.producto);`. Confirmado contra el serializer real (`ProductoListSerializer.id = UUIDField(source='uuid')`) que `producto` es un UUID, no un entero.

### FE-C2 — `name="producto"` duplicado en `offcanvas_producto.html`
**Archivo:** `apps/tenant/inventario/templates/inventario/offcanvas_producto.html`
**Cambio:** el `<input type="hidden" name="producto">` se movió de estar siempre presente a vivir únicamente dentro de la rama `{% else %}` (cuando ya hay un producto pre-seleccionado), mutuamente excluyente con el `<select name="producto">` de la rama sin producto. Verificado contra el JS consumidor (`cargarProductosEnAjuste()` ya comentaba explícitamente "Si no hay select, significa que el producto ya viene pre-seleccionado" — el JS ya asumía esta exclusión mutua; el template era el que la violaba).

### FE-C3 — Colisión entre dos `http.js` anulaba el JWT
**Archivo:** `apps/tenant/core/static/core/js/lib/http.js`
**Decisión de diseño (importante, se aparta de la sugerencia literal de la auditoría):** la auditoría sugería "borrar `core/js/lib/http.js`". Al investigar los consumidores reales se encontró que:
1. Este archivo **es el que efectivamente gana** en el shell SPA (`assets_core.html` lo carga después del `http.js` correcto) y en el shell estático del dashboard (`apps/tenant/core/static/tenant/core/dashboard/index.html:559`, servido en producción vía `RedirectView` en `config/urls_tenant.py:140`).
2. Este archivo (y solo este) maneja `FormData` correctamente (subida de logo de empresa, adjuntos de facturas/empleados/cotizaciones — al menos 20 archivos JS en el repo llaman `window.http('POST', url, formData)`). La versión "correcta" (`core/static/js/http.js` v3.4) **no tiene ninguna rama para `FormData`** — le haría `JSON.stringify()` a un objeto `FormData`, lo que serializa a `"{}"` y destruiría cualquier subida de archivo.
3. Dos archivos más (`empleados/devengo_editor.js`, `facturas/facturas.api.js`) dependen del global `window.getCookie` que solo exporta este archivo.

Borrar el archivo hubiera **arreglado el JWT pero roto las subidas de archivos en ~20 features y el shell de dashboard en producción** — una regresión peor que el bug que se estaba corrigiendo.
**Cambio aplicado:** se inyectó la misma lógica de `Authorization: Bearer` (via `window.jwtAuth.getValidAccessToken()`, verificado que el método existe y se usa igual en `tabulator.factory.js`) directamente en la función `http()` de este archivo, sin tocar el resto de su lógica (FormData, CSRF, manejo de 401/403 intactos). No se tocó `assets_core.html`, `window.getCookie`, ni el shell del dashboard — cero riesgo de regresión en subida de archivos.
**Deuda documentada para fases posteriores:** sigue existiendo un ecosistema duplicado de scripts "legacy" (`core/js/lib/*.js`, `core/js/helpers/*.js`) cargado en paralelo al SSoT moderno (`core/static/js/http.js`). Consolidar esto es trabajo de Fase 5/7 (Frontend/Duplicidad), no de un fix crítico puntual.

### ARQ-C1 — Import directo de `contabilidad.models.Retencion` desde `facturas`
**Archivo:** `apps/tenant/facturas/models.py` (6 ocurrencias: 3 en `Factura`, 3 en `ItemFactura`)
**Cambio:** las 6 propiedades (`total_retencion_fuente`, `total_reteica`, `total_reteiva`, `total_retefuente_item`, `total_reteiva_item`, `total_reteica_item`) ahora llaman a `RetencionesService.total_retenciones_por_documento(...)` (API de servicio ya existente en `contabilidad/services/retenciones_service.py`, documentada en `CLAUDE.md`) en vez de construir el `QuerySet` directamente sobre el modelo `Retencion` de otra app.
**Beneficio adicional no buscado pero confirmado:** el código anterior **no filtraba por `empresa_id`** en ninguna de las 6 consultas — un gap de Zero-Trust real, aunque mitigado en la práctica por el aislamiento de esquema PostgreSQL. `RetencionesService.total_retenciones_por_documento()` exige `empresa_id` y lanza `ValueError` si falta, cerrando ese gap como efecto colateral positivo de usar la capa de servicio correcta.
**Verificado:** sin import circular (`retenciones_service.py` no importa de `facturas`).

### ARQ-C2 — `inventario` sin `services/api_mixins.py`
**Archivos:** `apps/tenant/inventario/services/business_service.py` (6 clases `*ServiceMixin` removidas, 707→423 líneas), `apps/tenant/inventario/services/api_mixins.py` (nuevo, 6 clases movidas sin cambios de comportamiento), `apps/tenant/inventario/services/__init__.py` (import actualizado).
**Cambio puramente estructural:** las 6 clases (`CategoriaItemServiceMixin`, `ProductoServiceMixin`, `ServicioServiceMixin`, `ActivoFijoServiceMixin`, `MovimientoServiceMixin`, `HistorialServiceMixin`) se movieron byte-a-byte, sin modificar ningún método ni cambiar su clase base. `apps/tenant/inventario/api/viewsets.py` no requirió ningún cambio porque importa los mixins vía `apps.tenant.inventario.services` (el paquete), no directamente de `business_service` — verificado leyendo el import (`from apps.tenant.inventario import services as inv_services`) y confirmando que `__init__.py` sigue re-exportando los mismos nombres.
**Verificado:** cada símbolo importado en el nuevo `api_mixins.py` se usa al menos una vez (sin imports muertos); 0 clases `*ServiceMixin` remanentes en `business_service.py`.

### TEST-C1 — `ventas` sin ningún test
**Archivos nuevos:** `apps/tenant/ventas/tests/__init__.py`, `apps/tenant/ventas/tests/conftest.py` (fixtures `tenant1`/`tenant2`, copiadas del patrón canónico de `gastos/tests/conftest.py` per AGENTS.md §24.5), `apps/tenant/ventas/tests/test_multitenant_isolation.py` (3 niveles obligatorios: listado, IDOR directo, IDOR en FK `cliente`).
**Diseñado leyendo el código real, no genérico:** el payload del Nivel 3 usa `cliente` (UUID) porque `VentaBusinessService._dsv_cliente()` es la validación DSV real del flujo `crear_venta_borrador`; se confirmó que un `Cliente` de otro tenant hace que `_dsv_cliente` lance `ValueError`, que la vista traduce a `400` — la aserción del test refleja ese contrato real, no un valor asumido.
**No verificado en este entorno** (ver §0): recomendado ejecutar `pytest apps/tenant/ventas/tests/test_multitenant_isolation.py -v` antes de dar esta corrección por cerrada.
**Explícitamente fuera de alcance de Fase 1:** TEST-C2 (solo 2 de ~16 apps cumplen el estándar de aislamiento obligatorio) es un backfill sistémico de ~14 archivos — corresponde a Fase 9 (Testing) del plan, no a un fix crítico puntual. Se resolvió aquí únicamente el caso más grave y puntual (`ventas`, 0 tests en total, no solo sin el archivo canónico).

### DEVOPS-C1 — CI nunca ejecutaba pytest/ruff/bandit/`manage.py check`
**Archivo nuevo:** `.github/workflows/ci-quality-gate.yml`.
**Diseño:** job con servicios `postgres:16-alpine` y `redis:7.2-alpine` (mismas versiones que `docker-compose.yaml`), instala dependencias del sistema (`libpq-dev`, `libxml2-dev`, `libxslt1-dev`, igual que `Dockerfile`), instala `requirements.txt` + `ruff`/`bandit` (ver hallazgo nuevo abajo), corre `manage.py check`, `ruff check`, `bandit`, y finalmente `pytest`.
**Decisión importante:** `manage.py check` y `pytest` son bloqueantes (fallan el job). `ruff` y `bandit` se dejaron con `continue-on-error: true` porque este entorno no pudo ejecutarlos ni una vez para saber cuántas violaciones preexistentes hay en ~1400 archivos — hacerlos bloqueantes a ciegas podría dejar el pipeline en rojo permanente por deuda no relacionada con ningún PR futuro, entrenando al equipo a ignorar el CI. Recomendación explícita: correr `ruff check apps config` y `bandit -r apps` una vez, triar los hallazgos, y quitar `continue-on-error` en Fase 4/10.
**Hallazgo nuevo descubierto al diseñar este fix:** `ruff` y `bandit` **no están en `requirements.txt`**, pese a que `make ruff`/`make bandit` los invocan (`docker compose exec web python -m ruff...`). Esto sugiere que esos targets del Makefile actualmente **fallan** en cualquier build limpio del contenedor (`ModuleNotFoundError`) a menos que alguien los haya instalado manualmente fuera del `Dockerfile` en algún momento. No se modificó `requirements.txt`/`Dockerfile` en esta fase (fuera de alcance de un CRÍTICO puntual); el nuevo workflow de CI instala ambas herramientas de forma independiente para no depender de ese archivo. Se recomienda agregarlas a `requirements.txt` (o a un `requirements-dev.txt` nuevo) en Fase 10.
**No verificado en este entorno:** no hay ejecutor de GitHub Actions disponible aquí; el YAML se validó sintácticamente con PyYAML pero el workflow **no se pudo dry-run**. Recomendación: vigilar la primera ejecución real en GitHub y estar preparado para ajustar variables de entorno si algo falla por configuración específica de CI no anticipada.

### DOC-C1 — `arquitectura_general.md` no incluía `compras`/`ventas`
**Archivo:** `documentacion/arquitectura_general.md` (§2.2, §9, §10.2).
**Cambio:** se agregaron las filas de `compras` y `ventas` al inventario de apps (§2.2, con conteo real de modelos/migraciones verificado contra el código), a la tabla de endpoints (§9), y al índice de documentos de auditoría por app (§10.2) — donde además se agregó `bancos` (que tampoco estaba indexado ahí, aunque sí en el inventario de §2.2).
**Explícitamente parcial:** se dejó una nota (`WARNING: [DOC-C1]`) indicando que el recuento completo de migraciones/tests de §2 y §10.3 (que la Fase 1 de Track F encontró desactualizado en casi todos los números, no solo en las apps faltantes) queda pendiente para Fase 8 — esta fase solo cerró el caso más grave (apps enteras ausentes del documento canónico).

### DOC-C2 — `MEMORY.md` congelado desde 2026-05-06
**Archivo:** `MEMORY.md`.
**Cambio:** se agregaron entradas para la incorporación de `bancos`/`compras`/`ventas` (con fechas reales tomadas de `git log`) y una entrada para esta propia sesión de auditoría + Fase 1. Se actualizó "Estado Activo" para reflejar que el plan de remediación está en curso (referenciando `PLAN_REMEDIACION.md`/este reporte) en vez de "Tarea en Curso: Ninguna", y se documentó explícitamente la limitación de entorno (§0 de este reporte) ahí también, para que la próxima sesión no asuma que Fase 1 fue validada en runtime.

---

## 2. Archivos tocados (15 modificados + 6 nuevos)

```
M  MEMORY.md
M  apps/tenant/contabilidad/integracion/contabilizador.py
M  apps/tenant/contabilidad/models.py
M  apps/tenant/core/static/core/js/lib/http.js
M  apps/tenant/facturas/api/viewsets.py
M  apps/tenant/facturas/models.py
M  apps/tenant/facturas/services/business_service.py
M  apps/tenant/facturas/services/services_mail_ingestion.py
M  apps/tenant/facturas/utils/ubl_parser.py
M  apps/tenant/inventario/services/__init__.py
M  apps/tenant/inventario/services/business_service.py
M  apps/tenant/inventario/static/inventario/js/features/inventario_editor.js
M  apps/tenant/inventario/templates/inventario/offcanvas_producto.html
M  config/settings.py
M  documentacion/arquitectura_general.md
?? .github/workflows/ci-quality-gate.yml
?? apps/tenant/contabilidad/migrations/0014_asientocontable_uniq_documento_origen.py
?? apps/tenant/inventario/services/api_mixins.py
?? apps/tenant/ventas/tests/ (__init__.py, conftest.py, test_multitenant_isolation.py)
?? documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md
?? documentacion/PLAN_REMEDIACION.md
```

Ningún archivo fuera de esta lista fue modificado. El repositorio ya tenía ~450 cambios sin commitear antes de iniciar esta sesión (`ARTIFACTS/*`, docs varios) — no se tocaron ni se incluyen en este reporte; siguen exactamente como estaban.

**No se ejecutó ningún `git add`/`git commit`** — todos los cambios quedan en el árbol de trabajo para revisión.

## 3. Criterios de "fase estable" (definidos en `PLAN_REMEDIACION.md` §4) — checklist

- [x] 0 `SyntaxError` en los 15 archivos `.py` tocados (`py_compile` limpio).
- [x] 0 `SyntaxError` en los 2 archivos `.js` tocados (`node --check` limpio).
- [x] Cada `@property`/método reemplazado conserva su firma y tipo de retorno original (ARQ-C1: sigue retornando `Decimal`; PERF-C3: se documentó el cambio de contrato de `importar_factura_desde_ubl` con parámetro nuevo `persist` retrocompatible por defecto).
- [x] Ningún import muerto tras los refactors de ARQ-C1/ARQ-C2 (verificado por conteo de uso de cada símbolo importado).
- [x] La migración `0014` es aditiva (solo agrega una constraint, no toca datos) y reversible (`migrate contabilidad 0013`).
- [x] Documentadas explícitamente las limitaciones de verificación en runtime (§0 de este reporte).

## 4. Siguiente paso

Antes de avanzar a **Fase 2 (Arquitectura — hallazgos ARQ-A)**: confirmar en un entorno con Docker/venv funcional que `make dj-check` y al menos los tests de `facturas`, `contabilidad`, `inventario` y el nuevo test de `ventas` pasan. Si algo falla, corregirlo dentro de esta misma Fase 1 antes de continuar (per la regla "cada fase debe finalizar con un sistema estable").
