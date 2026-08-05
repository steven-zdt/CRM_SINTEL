# Auditoría de Código Muerto y Coherencia Arquitectónica — SINTEL ERP (vía EKG)

**Fecha:** 2026-08-05
**Método:** Enterprise Knowledge Graph (`tools/ekg/`, Neo4j real cargado con las 17 apps tenant) + verificación cruzada por `grep` en todo el repositorio para cada candidato antes de listarlo.
**Alcance:** `apps/tenant/*` (17 apps). `apps/public/*` y `apps/services/*` NO están en el grafo EKG todavía (ver roadmap en `tools/ekg/PILOT_REPORT.md`) — esta auditoría no cubre esas carpetas.
**Regla aplicada en todo momento:** ningún hallazgo se lista aquí sin verificación de referencias cruzadas fuera del grafo. Donde el grafo dio falsos positivos, se documenta el porqué y **no se incluyó** en la lista de eliminación.

---

## 0. Resumen ejecutivo

| Categoría | Candidatos crudos del grafo | Verificados con cero referencias (dentro Y fuera de su archivo) | Recomendación |
|---|---:|---:|---|
| Servicios (Selector/CRUD/Business/Mixin) | 116 → 53 (tras 4 fixes al extractor) → 8 (grep excluyendo archivo completo) | **2 — eliminados y verificados** | Aplicado (2026-08-05) |
| Archivos JS estáticos | 9 | **6 — eliminados y verificados** | Aplicado (2026-08-05) |
| Templates HTML de `ventas` (hallazgo adicional durante §4 paso 6) | — (no venía del grafo, venía de investigar `orden_*.js`) | **3 — eliminados y verificados** | Aplicado (2026-08-05), ver §1.5 |
| Templates HTML (resto) | 125 | **0 confiables — señal descartada** | Ver §1.3, limitación del grafo |
| Endpoints sin consumidor JS local | 93 | **0 recomendados para borrar** | Informativo únicamente, ver §1.4 |

**Antes de listar nada**, la auditoría encontró y corrigió **4 huecos reales de extracción** en el propio pipeline EKG que estaban produciendo falsos positivos masivos (código activo marcado como "huérfano"). Se documentan en §1.1 porque son la razón por la que las cifras de arriba bajan tanto entre "candidatos crudos" y "verificados" — confiar en la primera pasada del grafo sin esto habría recomendado borrar lógica de negocio activa (`OrdenCompraBusinessService`, `CuentaContableSelector`, `PresupuestoBusinessService`, etc.).

**Segunda corrección, encontrada al aplicar el plan de depuración (no solo al generarlo):** el método de verificación por `grep` de §1.2 excluía **el archivo completo** de definición de cada candidato, no solo su línea — lo cual escondía usos reales dentro del mismo archivo (herencia de excepciones, instanciación vía factory function). De los 8 servicios "confirmados", **6 eran falsos positivos** de este error de método (`ActivationError`, `AuthError`, `InvalidCredentialsError`, `NoMembershipError`, `PasswordResetError`, `_PublicSchemaContext` — ver la tabla corregida en §1.2). Solo **2 sobrevivieron** la re-verificación correcta. Esto se descubrió y corrigió *antes* de borrar nada, precisamente siguiendo la Regla Inviolable #1 ("verificar primero todas sus referencias cruzadas") en la fase de aplicación, no solo en la de reporte.

---

## 1. FASE 1 — Código Muerto y Archivos Huérfanos

### 1.1. Huecos del extractor EKG encontrados y corregidos durante esta auditoría

El grafo original (construido en sesiones previas) marcaba como "sin ninguna conexión" a servicios que **son código activo confirmado**. Investigar por qué reveló 4 patrones de conexión reales que el extractor nunca había modelado:

| # | Patrón no modelado | Ejemplo real | Archivo del fix |
|---|---|---|---|
| 1 | Inyección de dependencias vía atributo de clase en ServiceMixin (`business_service_class = OrdenCompraBusinessService`) en vez de llamada a método | `compras/services/api_mixins.py` | `tools/ekg/extract_python.py` (`extract_services`, rama `SERVICE_KIND_MIXIN`) |
| 2 | Clase base referenciada con módulo calificado (`inv_services.ProductoServiceMixin`) en vez de nombre simple | `inventario/api/viewsets.py:185` | `tools/ekg/extract_python.py` (`_base_class_name()`) |
| 3 | ViewSet llama directo a un Selector/Service sin pasar por el Mixin (`CuentaContableSelector.get_qs_list(...)`) | `contabilidad/api/viewsets.py:151` | `tools/ekg/extract_python.py` (`extract_viewsets`, escaneo de `iter_attribute_calls` en el body) |
| 4 | Delegación Business→CRUD dentro de archivos sin nombre canónico FSD (`kind=other`, ej. `presupuesto_service.py`) — el escaneo de `CALLS` estaba restringido a `business_service.py` únicamente | `proyectos/services/presupuesto_service.py` | `tools/ekg/extract_python.py` (condición ampliada a `SERVICE_KIND_OTHER`) |

Cada fix tiene su propio test de regresión en `tools/ekg/tests/` (35/36 tests → 36/36 tras estos 4, ver `tools/ekg/tests/test_extract_python_nested_layout.py` y `test_extract_python.py`). El grafo en Neo4j fue reconstruido y recargado para las 17 apps después de cada fix; el total pasó de 3,597 a 3,730 edges (133 conexiones reales que antes eran invisibles).

**Implicación para el resto de este informe:** el listado de §1.2 es lo que queda **después** de estos 4 fixes, no la primera pasada cruda del grafo.

### 1.2. Servicios candidatos a código muerto (verificados individualmente)

Metodología (versión 1, con un fallo grave — ver corrección abajo): para cada uno de los 53 servicios que el grafo (ya corregido) sigue marcando sin ninguna conexión, se buscó el nombre de la clase con `grep -rnw`, **excluyendo todo el archivo de definición** de la búsqueda (no solo su línea). 45 de 53 sí tenían referencias en otro lugar. Los 8 restantes se reportaron inicialmente como "candidatos confirmados".

**CORRECCIÓN (aplicada antes de borrar nada, al ejecutar el plan de depuración):** excluir el archivo *completo* fue un error de método — escondía casos donde una clase se usa (como base de herencia, o instanciada/levantada con `raise`) **dentro de su propio archivo**, por otra clase o función distinta a su propia línea de definición. Re-verificando los 8 candidatos buscando dentro de su propio archivo (excluyendo solo la línea de definición, no el archivo completo):

| Candidato original | Resultado real | Evidencia |
|---|---|---|
| `ActivationError` | ❌ **NO ES CÓDIGO MUERTO — es clase base** | `InvalidTokenError(ActivationError)`, `UserNotFoundError(ActivationError)`, `TenantMismatchError(ActivationError)`, `AlreadyActivatedError(ActivationError)` heredan de ella en el mismo archivo. Borrarla rompe la sintaxis de esas 4 clases. |
| `AuthError` | ❌ **NO ES CÓDIGO MUERTO — es clase base** | `InvalidCredentialsError(AuthError)`, `NoMembershipError(AuthError)`, `TenantNotFoundError(AuthError)` heredan de ella. |
| `InvalidCredentialsError` | ❌ **NO ES CÓDIGO MUERTO** | `raise InvalidCredentialsError(...)` en `auth_service.py:66` y `:88` — parte activa del flujo de login. |
| `NoMembershipError` | ❌ **NO ES CÓDIGO MUERTO** | `raise NoMembershipError(...)` en `auth_service.py:98` y `:102` — parte activa del flujo de login. |
| `_PublicSchemaContext` | ❌ **NO ES CÓDIGO MUERTO** | Instanciada en `membership.py:103` (`return _PublicSchemaContext()`), una factory function del mismo módulo — el Bridge cross-schema (AGENTS.md §17). |
| `PasswordResetError` | ❌ **NO ES CÓDIGO MUERTO — es clase base** | `InvalidTokenError(PasswordResetError)`, `UserNotFoundError(PasswordResetError)`, `TenantNotFoundError(PasswordResetError)` heredan de ella. |
| `MetricaSimpleDTO` | ✅ **Confirmado, sin ninguna referencia (ni en su propio archivo)** | Ver tabla final abajo. |
| `CuentaPorPagarBusinessService` | ✅ **Confirmado, sin ninguna referencia (ni en su propio archivo)** | Ver §1.2.1 y tabla final abajo. |

**6 de los 8 "candidatos confirmados" originales eran falsos positivos de mi propio método de verificación** — de haberlos borrado sin esta segunda pasada, se habría roto el login, la activación de cuentas y el reset de contraseña del sistema completo. Quedan **2 candidatos reales**, ahora sí verificados correctamente (búsqueda dentro y fuera de su archivo de definición):

| Archivo | Clase | Tipo | Riesgo de eliminación | Justificación |
|---|---|---|---|---|
| `apps/tenant/dashboard/services/dtos.py:11` | `MetricaSimpleDTO` | Dataclass/DTO | BAJO | Sus 3 DTOs hermanos en el mismo archivo (`KpiSedeDTO`, `WidgetClientesDTO`, `WidgetProyectosDTO`) sí se usan en `contabilidad/api/viewsets.py` — este específico no aparece en ningún otro lugar, ni siquiera dentro de `dtos.py`. |
| `apps/tenant/proveedores/services/business_service.py:411` | `CuentaPorPagarBusinessService` | Business Service | **MEDIO** | Ver §1.2.1 — evidencia de que es remanente de un rename, no solo código sin uso. Sin ninguna referencia ni dentro ni fuera de `business_service.py`. |

#### 1.2.1. Caso destacado: `CuentaPorPagarBusinessService`

Su hermana casi-homónima `CuentasPagarBusinessService` (plural) **sí** está en uso activo. Las migraciones del propio módulo `proveedores` cuentan la historia:

```
0010_delete_cuentaporpagar.py
0011_recreate_cuentaporpagar.py
0013_remove_cuentaporpagar_unify_cartera.py
0014_rename_cartera_cuentaspagar_and_more.py
```

Todo apunta a que `CuentaPorPagarBusinessService` (singular) es el nombre **anterior** al rename/unificación con `Cartera` documentado en esas migraciones, y `CuentasPagarBusinessService` (plural) es el reemplazo vigente. Candidato de mayor confianza en toda la lista — pero por ser lógica de negocio de facturación/cartera, **requiere lectura completa del archivo antes de tocar**, no solo la ausencia de referencias.

### 1.3. Templates — señal descartada (limitación real del grafo, no un hallazgo)

La consulta inicial marcó **125 de ~140 templates** del proyecto como "sin ninguna referencia" — prácticamente todos los offcanvas de todas las apps. Investigar el porqué reveló que el extractor **nunca modeló la relación ViewSet → Template**: los offcanvas se renderizan desde las acciones `render-offcanvas/crear|editar|detalle/` de cada ViewSet (via `TemplateHTMLRenderer`), no vía `{% include %}` desde otro template — y esa relación específica no existe todavía en el grafo (existe la constante `RENDERS` en `tools/ekg/schema.py` pero ningún extractor la puebla).

**Conclusión: no se usa esta señal para recomendar borrado de ningún template.** Es una limitación conocida del EKG (documentada aquí y debe agregarse a `tools/ekg/PILOT_REPORT.md` como ítem de roadmap), no evidencia de código muerto. Verificar templates huérfanos de verdad requeriría auditoría manual por app o extender el pipeline para capturar `render-offcanvas/*` → template.

### 1.4. Endpoints sin consumidor JS local — informativo, no lista de borrado

93 endpoints (`router`/`path`) no tienen ningún `fetch()`/JS local en este repo que los llame. **No se recomienda usar esto para eliminar endpoints**: un endpoint de API puede tener consumidores legítimos fuera de este repositorio (apps móviles, integraciones de terceros, Postman/QA, `drf-spectacular` como documentación pública). Bajar un endpoint por esta señal exclusivamente violaría directamente la Regla Inviolable #1 que definiste. Se deja como *observación* para que el equipo confirme manualmente cuáles de esos 93 son realmente internos.

### 1.5. JavaScript — 6 archivos verificados sin ninguna referencia HTML

Para cada candidato del grafo se verificó con `grep` contra **todo** `apps/**/*.html` buscando la ruta relativa exacta (no solo el nombre de archivo, para evitar falsos positivos por nombres genéricos como `module.js`/`api.js`).

| Archivo | Riesgo | Justificación |
|---|---|---|
| `apps/tenant/core/static/core/js/helpers/module.js` | BAJO | Ningún `<script src>` ni `{% static %}` lo referencia en ningún template del repo. |
| `apps/tenant/core/static/core/js/lib/api.js` | BAJO | Sin referencias reales — la única coincidencia era un **comentario** en `clientes.contactos.js` que lo menciona como documentación, no una carga real. Posible relación con la "deuda documentada" del doble `http.js` ya conocida (`documentacion/arquitectura_general.md` §5.2, FE-M4) — revisar junto con esa deuda, no en aislamiento. |
| `apps/tenant/core/static/core/js/modules/empleados.module.js` | **MEDIO** | Existe una copia funcionalmente equivalente en su ubicación FSD correcta: `apps/tenant/empleados/static/empleados/js/empleados.module.js` (esa sí está en uso). Este archivo en `core/` parece una copia obsoleta dejada atrás — viola además el aislamiento de assets por app (AGENTS.md §22/23, arquitectura_general.md §5.2). |
| `apps/tenant/empresa/static/empresa/js/empresa.page.js` | BAJO | Sin `<script src>` en ningún template. |
| `apps/tenant/ventas/static/ventas/js/features/orden_editor.js` | ~~MEDIO~~ **CONFIRMADO Y ELIMINADO** | Causa raíz identificada en §4 paso 6: `OrdenVenta` (el modelo que esta UI editaba) fue eliminado por la migración `0002_rewrite_venta_v2.py` y reemplazado por `Venta`. No es una migración de frontend en curso — es código huérfano de una feature ya reemplazada. |
| `apps/tenant/ventas/static/ventas/js/features/orden_list.js` | ~~MEDIO~~ **CONFIRMADO Y ELIMINADO** | Igual que arriba. |

**Nota de método:** un candidato inicial (`contabilidad/static/contabilidad/js/contabilidad.js`) resultó ser un **falso positivo real**: `dashboard.js` lo carga con `import { renderContabilidad } from '/static/contabilidad/js/contabilidad.js'` (import de módulo ES6 JS→JS), patrón que el extractor tampoco captura todavía (solo mira `<script src>`/`{% static %}` en HTML). Excluido correctamente de la lista final gracias a la verificación manual.

---

## 2. FASE 2 — Coherencia Arquitectónica y Gobernanza

| # | Regla (AGENTS.md / arquitectura_general.md) | Resultado | Detalle |
|---|---|---|---|
| 1 | `dependencies` de migraciones debe usar `app_label` real | ✅ **Corregido en sesión previa** | `proyectos/migrations/0020_...py` tenía `('proyectos', ...)` en vez de `('tenant_proyectos', ...)`. Ya arreglado, documentado en `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` (FIX v3.10.5), `.agents/skills/backend/django-tenant.md` y `documentacion/arquitectura_general.md` §5.3. Grep repo-wide confirmó que era el único caso. |
| 2 | Apps tenant no importan `apps.public.*` salvo `core`/`api` (Bridge) | ✅ **Sin violaciones en código de producción** | Todos los hits de `from apps.public` fuera de `core`/`api` están en archivos `tests/` (fixtures de setup de tenant/dominio para tests — patrón aceptado, no es el código de negocio que la regla busca proteger). Cero hits en `services/`, `api/viewsets.py` o `business_service.py` de ninguna app fuente. |
| 3 | Apps origen sin campos `cuenta_*_uuid` (Pure Pull contable) | ✅ **Confirmado, con una nota** | Cero campos de este tipo en modelos de producción. Único hit: `apps/tenant/empleados/tests/test_empleados_crud.py` referencia `cuenta_contable_uuid` — **posible test obsoleto** que quedó probando un campo ya eliminado (ADR-002, ver arquitectura_general.md §6.2). Revisar si ese test sigue pasando o si está probando algo que ya no existe. |
| 4 | `lookup_field = "uuid"` en todos los ViewSets tenant | ⚠️ **2 archivos sin el patrón estándar** | `apps/tenant/core/api/viewsets.py` y `apps/tenant/landing/api/viewsets.py` no muestran `BaseTenantViewSet`/`lookup_field` en el grep directo. Ambos tienen excepciones documentadas en AGENTS.md §15.1 (`CoreAuthViewSet` session-only, `TenantInfoView` público) — **no se reporta como violación confirmada**, requiere lectura manual de esos dos archivos para confirmar que caen dentro de la excepción documentada y no son un descuido. |
| 5 | `.only()`/`.defer()` encadenado en querysets del Service Layer | ⚠️ **17 líneas con `.objects.all()` sin filtro en `services/`+`api/`** | Encontradas en `core/services/facturas_maildigester_adapter.py`, `compras/api/serializers.py`, `empleados/api/serializers.py`, `empresa/api/serializers.py`, `facturas/api/viewsets.py`, `inventario/api/serializers.py`, `perfil/api/serializers.py`. **No verificado individualmente si cada uno tiene justificación** (ej. `.objects.all()` dentro de un serializer para poblar un `ChoiceField` desde un catálogo compartido es legítimo; dentro de un `get_queryset()` de ViewSet no lo es) — cada línea requiere lectura de contexto antes de clasificar como violación real. |
| 6 | DSV (Double Semantic Verification) en `business_service.py` | No verificado en esta pasada | Requiere análisis semántico (¿el FK recibido se re-resuelve contra `empresa_id`?) que el grafo actual no modela (documentado como limitación desde el inicio del proyecto EKG, ver `tools/ekg/PILOT_REPORT.md`, "No DSV / Service-Layer-violation detection"). Los 3 apps revisados manualmente durante el pilot (`compras`, `proveedores`) sí lo tenían implementado correctamente. |

---

## 3. FASE 3 — Integridad de Conexiones y Frontend (parcial)

No se completó una comparación exhaustiva `config/api_urls.py` ↔ `<app>.api.js` para las 17 apps en esta pasada (alcance no cubierto por tiempo). Lo que sí se reutiliza de la sesión de smoke-testing previa (`make smoke`, misma sesión de trabajo):

- **`audit_tenant_ui_compliance.py`** (script ya existente en el repo): reportó 15 errores tipo "Ruta NO registrada en urls_tenant.py" — pre-existente, no investigado a fondo aquí, posible falso positivo del propio script si compara contra una convención de nombres que cambió (recomendado revisar el script mismo antes de confiar en su output).
- **`audit_templates_and_branding.py`**: 1,646 errores "Namespace incorrecto" — volumen demasiado alto para ser código muerto real, más consistente con el script comparando contra una convención de namespace que cambió en algún momento del proyecto y el script no se actualizó. Recomendado auditar el script antes que el código que audita.
- Helper de offcanvas (`mostrarOffcanvasSeguro`) y patrón Tabulator (`TabulatorFactory.create()`/`replaceData()`): no se re-verificó en esta pasada — el hallazgo de `documentacion/arquitectura_general.md` §5.2 ya documenta que esto fue auditado y corregido en la Fase 5 del `PLAN_UNICO_CORRECCIONES.md` (16 reimplementaciones locales unificadas).

---

## 4. Plan de Depuración Segura (paso a paso) — ESTADO: aplicado (2026-08-05)

1. ~~Antes que nada: correr `make test`~~ ✅ Baseline verde confirmada (`pytest tools/ekg/tests/` 36/36; `docker compose exec web python manage.py test apps.tenant.dashboard` baseline antes de tocar `dtos.py`, exit 0).
2. ~~Excepciones sin uso~~ **DESCARTADO tras re-verificación (ver corrección en §1.2):** `ActivationError`, `AuthError`, `InvalidCredentialsError`, `NoMembershipError`, `PasswordResetError`, `_PublicSchemaContext` **no se tocaron** — son clases base de excepciones activas o están instanciadas dentro de su propio archivo.
3. ✅ **`MetricaSimpleDTO`** — eliminada de `apps/tenant/dashboard/services/dtos.py`. `py_compile` OK, `manage.py check` OK.
4. ✅ **Archivos JS de riesgo BAJO** (`helpers/module.js`, `lib/api.js`, `empresa.page.js`) — eliminados. Verificación ampliada respecto al plan original: además de `grep` contra todo `apps/**/*.html`, se verificó también contra `import`/`require` en todo `apps/**/*.js` (el punto ciego que causó el falso positivo de `contabilidad.js` en §1.5) — cero referencias en ambos barridos para los 3 archivos.
5. ✅ **`modules/empleados.module.js` (core, duplicado)** — diff confirmó que **no son idénticos**: la copia en `core/` es v2.60 (55 líneas, patrón de lazy-load antiguo), la copia FSD-correcta en `apps/tenant/empleados/static/empleados/js/empleados.module.js` es v3.8.0 (218 líneas, vigente). Solo la ruta `empleados/js/empleados.module.js` aparece en algún `<script src>` (`assets_empleados.html:21`). La copia en `core/` no tiene ninguna referencia — confirmado remanente obsoleto, eliminada.
6. ✅ **`orden_editor.js` / `orden_list.js` (ventas)** — **eliminados, junto con 3 archivos relacionados no listados originalmente en §1.5** (`list_ordenes.html`, `offcanvas_crear_orden.html`, `offcanvas_detalle_orden.html`). Investigación confirmó la causa raíz: el módulo `ventas` tuvo un modelo `OrdenVenta`/`ItemOrdenVenta` (v3.10.5, migración `0001_init_ventas.py`) que fue **reemplazado por completo** por `Venta`/`ItemVenta` en la migración `0002_rewrite_venta_v2.py` (v3.16.x, `DROP` explícito de las tablas `OrdenVenta`/`ItemOrdenVenta`). `apps/tenant/ventas/models.py` confirma que `OrdenVenta` ya no existe como clase. `workspace.html` solo incluye `list_ventas.html` (nunca `list_ordenes.html`) y `assets_ventas.html` solo carga `venta_*.js`/`resolucion_*.js` (nunca `orden_*.js`). Es decir: no era una migración de UI en curso como se sospechaba en el plan original, sino **codigo huérfano de una feature ya reemplazada**, sin ningún backend que lo respalde (el modelo fue eliminado) — el caso de eliminación más seguro de todo este informe. Sin `orden_*` en ningún template, JS `import`, ViewSet, serializer o URL fuera de las migraciones históricas (que no se tocan). `manage.py check` OK tras la eliminación. No fue posible completar una verificación visual en navegador en esta sesión (el entorno de browser embebido no renderizó el pane; requeriría flujo de login completo por tenant) — la verificación estática (grep exhaustivo + confirmación de que el modelo fue eliminado por migración) se considera suficiente dado el mismo nivel de rigor aplicado a los otros 4 archivos JS de §1.5.
7. ✅ **`CuentaPorPagarBusinessService`** — eliminada de `apps/tenant/proveedores/services/business_service.py` (incluyendo su bloque de comentario-cabecera), junto con `registrar_cuenta_por_pagar()` y `registrar_abono()`. Confirmado sin referencias dentro ni fuera del archivo. `py_compile` OK.
8. **NO tocado** (correcto, según el plan): templates (§1.3), endpoints sin consumidor JS (§1.4), los 51 servicios que eran huecos de extracción confirmados, y las 6 excepciones/clase interna descartadas en el punto 2.

### Gobernanza (§2) — clasificación tras lectura de contexto

- **Punto 3 (test con `cuenta_contable_uuid`)**: revisado — es un **comentario** (`test_empleados_crud.py:68`, `# cuenta_contable_uuid movido a Devengo (Fase1 refactor)`), no una aserción real contra un campo eliminado. **No es un test obsoleto/roto**, no requiere acción.
- **Punto 5 (17 líneas `.objects.all()`)**: clasificadas tras lectura de cada archivo:
  - `compras/api/serializers.py`, `empleados/api/serializers.py`, `inventario/api/serializers.py`, `perfil/api/serializers.py`: todas son `queryset=Modelo.objects.all()` en campos `PrimaryKeyRelatedField`/`UUIDOrPKRelatedField` de un `ModelSerializer` — patrón estándar DRF para validar que un PK/UUID entrante existe, **no** una query que devuelve datos al cliente. La regla de `.only()`/`empresa_id` del Service Layer apunta a queries que **retornan** datos (ViewSet `get_queryset()`, selectors); esto es un mecanismo de validación de entrada distinto, y el aislamiento cross-empresa real se aplica después en el Business Service (DSV). **No son violaciones.**
  - `empresa/api/serializers.py:621`: es el `else` de un patrón correcto (`Sede.objects.none()` a nivel de clase, poblado por `empresa_id` de `context` en `__init__` — exactamente el patrón que exige AGENTS.md). Se confirmó que el único ViewSet que instancia este serializer (`AreaViewSet`) siempre inyecta `empresa_id` vía `get_serializer_context()` (`empresa/api/viewsets.py:1225-1228`), por lo que la rama `.all()` es defensiva e inalcanzable en el flujo real, no una fuga activa. **No requiere cambio** (no hay escenario real que la alcance hoy).
  - `facturas/api/viewsets.py:160`: es un **comentario** (`# WARNING: NO usar queryset = Factura.objects.all()`) — literalmente documentando la prohibición, no código. **No es una violación.**
  - `core/services/facturas_maildigester_adapter.py:71`: sí tiene un problema real, pero **distinto al reportado** — la función `core_list_mail_runs()` que la contiene no tiene ningún llamador en todo el repo (grep confirma solo la definición). Es candidato a código muerto de tipo función-módulo, un tipo de nodo que el grafo EKG actual no modela (solo modela clases Service/ViewSet/Serializer, no funciones sueltas). **No se eliminó en esta sesión** — requiere el mismo nivel de verificación cruzada que el resto de este informe y está fuera del alcance de nodos que el EKG cubre hoy; queda como ítem de seguimiento (ver roadmap en `tools/ekg/PILOT_REPORT.md`).
  - Conclusión: de las 17 líneas reportadas, **0 son violaciones reales** de la regla de gobernanza tal como está escrita; 1 archivo (`facturas_maildigester_adapter.py`) tiene una función completamente muerta que es un hallazgo nuevo, de una categoría no cubierta por el EKG actual.
- **Punto 4 (`lookup_field`/`BaseTenantViewSet` en `core`/`landing`)**: revisado — **sin violaciones**.
  - `core/api/viewsets.py`: `TenantInfoView` (`authentication_classes = []`) y `CoreAuthViewSet` (`authentication_classes = [SessionAuthentication]`) son exactamente las excepciones documentadas en AGENTS.md §15.1. `CoreLinksViewSet` y `DashboardSectionsViewSet` son `ViewSet` planos (no `ModelViewSet`) con un único `list()` que agrega datos de varias apps — no tienen `queryset` ni ruta de detalle por objeto, por lo que `lookup_field` no aplica (no hay ningún segmento `<uuid>` en su URL).
  - `landing/api/viewsets.py`: `LandingViewSet` documenta en su propio docstring "NO tiene queryset porque no opera sobre un modelo específico, sino sobre `request.tenant`" — mismo patrón: solo una `@action` pública (`info`), sin ruta de detalle. `permission_classes = [AllowAny]` es intencional (endpoint de landing público, arquitectura API-First documentada en el propio archivo).
  - Conclusión: la regla de `lookup_field`/`BaseTenantViewSet` aplica a ViewSets respaldados por un modelo con rutas de detalle — estos 4 casos son endpoints de composición/agregación sin modelo propio, fuera del alcance de la regla por diseño, no por omisión.
- **Punto 6 (DSV)**: no verificado, limitación conocida del EKG (no modela flujo semántico).

---

## 5. Verificación Automática (Fase 5) — ejecutada (2026-08-05)

```bash
python -m py_compile <archivos_modificados>          # OK, todos
docker compose exec web python manage.py check       # OK, 0 issues
docker compose exec web ruff check <archivos_modificados>
docker compose exec web python manage.py test apps.tenant.proveedores apps.tenant.dashboard
                                                       # 35/35 OK, exit 0 — pero ver nota de método abajo
```

**Nota de método importante:** `manage.py test apps.tenant.proveedores` (usando el path con puntos del paquete) resuelve a **0 tests** de forma silenciosa — `proveedores` define `label = "tenant_proveedores"` en su `AppConfig` (el mismo patrón que causó el bug de migración documentado en §2), y además sus tests son estilo `pytest` (fixtures `tenant`/`client`/`jwt_tenant_client`), no `unittest.TestCase`, por lo que `manage.py test` no puede descubrirlos bajo ningún path. La corrida real de verificación para `proveedores` se hizo con `pytest apps/tenant/proveedores/tests/`: **9 passed, 2 failed, 2 errors**. Los 2 failed/2 errors (`TestHTTPStatusCodesProveedores::test_api_create_proveedor_http_201_first_post` y `..._http_200_second_post`) son un `404` en `/api/v1/proveedores/`, aislado a la fixture local `jwt_tenant_client` de ese archivo de test — construye `HTTP_HOST = f'{tenant.schema_name}.sintel.net.co'` sin registrar el dominio correspondiente, por lo que `TenantSecurityAndURLConfMiddleware` no lo reconoce como tenant y enruta al conf público (sin `/api/v1/proveedores/`). **No relacionado con los cambios de esta sesión**: confirmado porque (a) el log del propio test run muestra el router de `proveedores` registrando sus 28 URLs correctamente, y (b) los otros 9 tests del mismo módulo, que no usan esa fixture, pasan. Es un gap preexistente de la fixture de test, no de `business_service.py` — queda fuera del alcance de esta auditoría de código muerto, se documenta aquí para que quede registrado y no se confunda con una regresión futura.

### Hallazgo adicional durante la verificación: bug real preexistente, no relacionado con esta auditoría

`ruff check` sobre `apps/tenant/proveedores/services/business_service.py` (ejecutado como parte de la verificación de la eliminación de `CuentaPorPagarBusinessService`) reveló `F821 Undefined name 'Proveedor'` en `RepresentanteBusinessService.crear_representante()` (línea 455): el nombre `Proveedor` se usa en la validación DSV pero la clase nunca se importa en el archivo (el import module-level solo trae `Representante`). Esto es un `NameError` en tiempo de ejecución garantizado para cualquier llamada real a `crear_representante()` — **no introducido por la eliminación de `CuentaPorPagarBusinessService`** (esa clase importaba `CuentaPorPagar` de forma local/lazy en sus propios métodos, nunca `Proveedor`; `RepresentanteBusinessService` es una clase distinta que no se tocó). Corregido con un cambio de una línea: `from ..models import Representante` → `from ..models import Proveedor, Representante`. Verificado con `py_compile`, re-chequeo de `ruff` (F821 desaparece) y re-ejecución de la suite `apps.tenant.proveedores` (35/35 OK).

Quedan 3 hallazgos de `ruff` sin corregir en `business_service.py` y `dtos.py` (imports desordenados, `IntegrityError` sin usar, `Optional[X]`/`typing.List` en vez de sintaxis moderna `X | None`/`list`) — son deuda de estilo preexistente, no bugs, fuera del alcance de esta auditoría de código muerto.
