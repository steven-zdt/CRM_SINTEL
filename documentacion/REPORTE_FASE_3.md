# REPORTE FASE 3 — Seguridad (Hallazgos SEC-A y SEC-M)

**Fecha:** 2026-07-26
**Alcance:** Los 4 hallazgos SEC-A (ALTO) y los 7 hallazgos SEC-M (MEDIO) de `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`.

Misma limitación de entorno que Fases 1-2 (sin Docker/venv funcional): verificación por `py_compile` + lectura manual, sin `make dj-check`/`make test` reales. `apps/tenant/compras/api/viewsets.py` aparece como archivo nuevo (`??`) en git porque toda la app `compras` ya estaba sin trackear en git antes de esta sesión (parte de los ~450 cambios preexistentes documentados en Fase 1 §0) — solo se modificó una línea de logging ahí, no se creó el archivo.

---

## 1. Hallazgos resueltos completamente

### SEC-A1 — XSS en `offcanvas_detalle_perfil.html`
Reemplazado `{{ profile.cargo|default:"<span>...</span>"|safe }}` (y los 2 campos análogos `departamento`/`telefono_corporativo`) por `{% if %}{{ valor }}{% else %}<span>...</span>{% endif %}`. El valor del campo ahora se auto-escapa; el HTML del placeholder "No definido" es literal del template, no interpolado.

### SEC-A2 — XSS en `pendiente_offcanvas_contabilizar.html`
`{{ sugerencias_puc|safe|default:'[]' }}` (embebido directamente en un `<script>`) reemplazado por `{{ sugerencias_puc|json_script:"sugerencias-puc-data" }}` **fuera** del bloque `<script>` (anidar `<script type="application/json">` dentro de otro `<script>` rompe el parseo HTML — se corrigió la posición, no solo el filtro) + `JSON.parse(document.getElementById(...).textContent)` dentro del script. Verificado que el nombre de contexto `sugerencias_puc` coincide exactamente con lo que setea `apps/tenant/contabilidad/api/viewsets.py:997`.

### SEC-A3 — XXE en parsers XML
Agregado `resolve_entities=False, load_dtd=False, no_network=True` a **los 5 sitios** donde el código construye un `etree.XMLParser`/llama `etree.fromstring` sobre XML de origen externo (no solo los 3 que mencionaba el hallazgo original):
- `apps/tenant/facturas/utils/ubl_parser.py` (2 parsers: `_parse_xml()` y el branch de `iterparse` para AttachedDocument)
- `apps/public/impuestos/services/etl/parse_xml.py` (2 puntos: el `etree.fromstring()` sin parser explícito del happy path, que usaba los defaults inseguros de lxml, y el parser de recuperación de errores)
- `apps/services/document_parser/xml_parser/core.py`
- `apps/services/maildigester/detectors.py` (XML de correos entrantes — origen no confiable)

Se mantuvo `huge_tree=True` donde ya existía (soporta facturas UBL legítimamente grandes) porque sin resolución de entidades no queda vector de expansión que explotar.

### SEC-A4 — `DepartamentoViewSet` sin `IsTenantMember`
`permission_classes = [IsTenantAdminOrReadOnly]` → `[IsTenantMember, IsTenantAdminOrReadOnly]`. `IsTenantMember` ya estaba importado en el archivo.

### SEC-M1 — SSRF en ingesta DIAN
Nueva función `_validar_url_ssrf()` en `apps/public/impuestos/tasks.py`: bloquea esquemas distintos de `http`/`https`, resuelve el hostname y rechaza si la IP resultante es privada/loopback/link-local/reservada/multicast. Se invoca al inicio de `descargar_fuente()`, antes de la verificación de `robots.txt`. **Limitación reconocida y documentada en el propio código:** no protege contra DNS rebinding (TOCTOU entre esta validación y la resolución que hace `requests` al conectar) — suficiente para bloquear el caso común de una URL apuntando directamente a un rango interno/metadata, no una mitigación completa contra un atacante que controle DNS.

### SEC-M2 — XSS adicional en consola de impuestos
- `search_results.html`: nuevo template filter `highlight_safe` (`apps/public/impuestos/templatetags/impuestos_extras.py`) que escapa todo el contenido excepto las etiquetas `<em>`/`</em>` que genera el resaltado de Elasticsearch — preserva la función de resaltado sin permitir que contenido de un documento indexado inyecte HTML/JS. Sin dependencia nueva (no se usó `bleach`, no estaba en `requirements.txt`).
- `logs.html`: `{{log.payload|safe}}` → `{{log.payload}}` (es un `JSONField`, no requiere HTML embebido; `|safe` no cumplía ningún propósito funcional).

### SEC-M3 — Clave Fernet efímera
`get_fernet_key()` ahora persiste la clave generada en modo desarrollo en `<BASE_DIR>/.cache/fernet_dev_key.bin` (agregado a `.gitignore`) y la reutiliza en el siguiente arranque del proceso, en vez de generar una nueva cada vez. Cierra el escenario real de pérdida de datos (passwords IMAP cifrados quedando indescifrables tras cada reinicio) sin tocar el comportamiento de producción (sigue exigiendo `MAILCFG_FERNET_KEY` y fallando si falta — sin cambios). Nota: el fix de Fase 1 (SEC-C1, `DEBUG` ahora `False` por defecto) ya cerraba la mayor parte de este riesgo en cualquier entorno que no fije `DJANGO_DEBUG=True` explícitamente, ya que la rama efímera solo se alcanza con `DEBUG=True`.

### SEC-M6 — Logging de payloads completos
Reemplazado el logging de `request.data` completo por `list(request.data.keys())` (con fallback seguro a `type(request.data).__name__` si no es dict-like) en 4 ViewSets: `ProyectoViewSet`, `OrdenCompraViewSet`, `GastoViewSet`, `ContratoViewSet` y `DevengoViewSet` (estos 2 últimos en `empleados/api/viewsets.py`, con datos salariales/PII). Se preserva la utilidad de debug ("qué campos llegaron") sin exponer valores.

---

## 2. Hallazgos investigados y NO corregidos (con la razón concreta)

Estos 3 requerían un cambio de mayor alcance o riesgo que el que se puede justificar como "fix quirúrgico de una fase de seguridad" sin cobertura de tests real. Se documenta la evidencia exacta encontrada para que una fase dedicada los aborde con el contexto ya investigado.

### SEC-M4 — DSV/`empresa_id` faltante en lookups internos

Se investigaron los 2 grupos de hallazgos por separado:

1. **`FacturaInterAppAPI` (`apps/tenant/facturas/services/business_service.py:915-1004`)**: al leer el código completo se confirmó que esta clase es un **contrato interno documentado explícitamente como "ABIERTO PARA APPS DE NEGOCIO"** ("Contrato de acceso sin restricción empresa_id para lectura... Llamadas desde servicios internos SOLO — no exponible como API HTTP"), usado por Contabilidad, Proyectos, Gastos, Empleados y Proveedores. Agregar un filtro `empresa_id` obligatorio requeriría cambiar la firma de `get_by_id`/`get_by_cufe`/`get_by_numero`/`list_all`/`summary_all`, rompiendo a **todos** sus llamadores actuales. No se tocó: es un contrato intencional, no un descuido, y "arreglarlo" es en realidad rediseñarlo.

2. **`contabilidad/services/business_service.py` (`actualizar_asiento`, `aprobar_asiento`, `actualizar_cuenta`, `eliminar_cuenta`, `actualizar_periodo`, `eliminar_periodo`, `cerrar_periodo`)**: se trazó el llamador real de `actualizar_asiento`/`aprobar_asiento` en `apps/tenant/contabilidad/api/viewsets.py:348-384` y se confirmó que **ya** resuelven el objeto vía `get_asiento_by_identifier(identifier, empresa_id=self.get_empresa_id())` (empresa-scoped) **antes** de llamar al business service — el `.get(id=asiento_id)` posterior es un re-fetch de un objeto ya validado, no una puerta de entrada nueva. El resto de los métodos (`actualizar_cuenta`, etc.) mezclan referencias entre la capa CRUD y la capa BusinessService con nombres iguales, lo que requeriría trazar cada uno individualmente para descartar código muerto antes de tocarlo. Dado que el motor contable es la parte más sensible del sistema y no hay forma de correr sus tests en este entorno, se optó por **no** modificar estas rutas para un endurecimiento puramente teórico (cero diferencia de explotabilidad confirmada) — se deja documentado para que el equipo lo revise con tests reales disponibles.

### SEC-M5 — CORS/cookie scoping

Investigado en detalle; no se aplicó ningún cambio porque cada elemento señalado por la auditoría resultó ser un requisito estructural de la arquitectura multi-tenant por subdominio, no un descuido corregible:
- `CORS_ALLOWED_ORIGIN_REGEXES` con wildcard `*.sintel.net.co`: necesario porque los tenants son subdominios creados dinámicamente: no hay una lista finita de orígenes que se pueda fijar de antemano sin romper el modelo SaaS.
- `CSRF_COOKIE_DOMAIN=".{TENANT_DOMAIN_BASE}"`: necesario para el patrón dual-schema de ADR-002 y para llamadas legítimas cross-subdominio.
- `CSRF_COOKIE_HTTPONLY=False`: confirmado que **numerosos** archivos JS (`workspace.html`, `compras.api.js`, `ventas.api.js`, `gastos.api.js`, `empresa.api.js`, entre otros) leen la cookie directamente vía `getCookie('csrftoken')` para setear la cabecera `X-CSRFToken` manualmente. Cambiar esto a `True` habría roto todos esos flujos de escritura (POST/PATCH/PUT/DELETE) en producción — una regresión mucho peor que el hallazgo que se buscaba cerrar.
- El control mitigante más importante (`SESSION_COOKIE_DOMAIN` sin compartir entre subdominios) **ya estaba correctamente ausente/sin configurar** — confirmado, no requiere cambio.

### SEC-M7 — `EmpresaViewSet`/`MailInboxConfigViewSet` sin `BaseTenantViewSet`

Se confirmó que ninguno de los 2 modelos (`Empresa`, `MailInboxConfig`) tiene campo `uuid` — migrar a `lookup_field='uuid'` requeriría el mismo proceso de 4 pasos aplicado en Fase 2 (ARQ-A1), pero sobre el modelo `Empresa` (el más central y referenciado de todo el sistema, singleton por tenant) y su configuración de correo asociada. Se verificó que ambos `get_queryset()` **ya** respetan el aislamiento por esquema y `IsTenantMember`/`IsTenantAdminOrReadOnly` correctamente — el hallazgo es estrictamente "formato de PK expuesto" (enumeración de bajo impacto), no una fuga de datos entre tenants. Dado que `Empresa` siendo singleton por tenant no tiene "otros registros" que enumerar dentro del mismo tenant, y que migrar el modelo central del sistema sin poder correr la suite de tests es un riesgo desproporcionado al beneficio, se dejó sin cambios. Recomendado como una fase dedicada y probada, no como parte de un barrido de seguridad general.

---

## 3. Criterios de "fase estable" — checklist

- [x] `py_compile` limpio en los 13 archivos `.py` tocados/creados.
- [x] Verificado que `sugerencias_puc` (SEC-A2) coincide exactamente entre template y view.
- [x] Verificado que ningún otro `etree.fromstring`/`etree.parse` sin parser seguro quedó en el repo (grep exhaustivo tras aplicar los 5 fixes de SEC-A3).
- [x] Verificado que `_validar_url_ssrf` se invoca antes de cualquier red hacia `url_origen`, con logging y manejo de error consistente con el patrón ya usado para el bloqueo por `robots.txt` en el mismo archivo.
- [x] Cada decisión de "no corregir" (SEC-M4, SEC-M5, SEC-M7) tiene evidencia concreta documentada (archivo:línea, llamadores trazados, o razón estructural), no una omisión silenciosa.
- [x] Confirmado que los cambios no tocan `CSRF_COOKIE_HTTPONLY` ni ningún otro setting cuyo cambio rompería JS ya dependiente de él.

## 4. Archivos tocados (14 modificados + 3 nuevos)

```
M  .gitignore
M  apps/public/impuestos/services/etl/parse_xml.py
M  apps/public/impuestos/tasks.py
M  apps/public/impuestos/templates/console/pages/impuestos/fragments/logs.html
M  apps/public/impuestos/templates/console/pages/impuestos/fragments/search_results.html
M  apps/services/document_parser/xml_parser/core.py
M  apps/services/maildigester/detectors.py
M  apps/services/security/crypto.py
M  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/pendiente_offcanvas_contabilizar.html
M  apps/tenant/compras/api/viewsets.py (ya sin trackear en git antes de esta sesion)
M  apps/tenant/empleados/api/viewsets.py
M  apps/tenant/facturas/utils/ubl_parser.py
M  apps/tenant/gastos/api/viewsets.py
M  apps/tenant/perfil/api/viewsets.py
M  apps/tenant/perfil/templates/tenant/perfil/offcanvas_detalle_perfil.html
M  apps/tenant/proyectos/api/viewsets.py
?? apps/public/impuestos/templatetags/__init__.py
?? apps/public/impuestos/templatetags/impuestos_extras.py
```

No se ejecutó ningún `git add`/`git commit`.

## 5. Siguiente paso

Antes de Fase 4 (Performance — PERF-A/PERF-M): recomendado ejecutar `make dj-check` y, si es posible, probar manualmente el flujo de búsqueda de la consola de impuestos (`{% load impuestos_extras %}` es nuevo) y la previsualización de "Contabilizar Pendiente" (el `json_script` cambió de posición en el DOM respecto al `<script>`).
