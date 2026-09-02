# AI_MCP_POLICY — Fases 2, 3, 31-33

## AI-07 = BLOQUEADO POR DEFECTO DE TERCEROS (investigado 2026-09-01)

Se intentó la primera exposición real (`@mcp_viewset(actions=["list",
"retrieve"])` en `ClienteViewSet`) y se **revirtió** tras encontrar un
defecto real y reproducible en `django-rest-framework-mcp==0.1.0a4`
(paquete alfa, `requirements.txt:17` ya lo señala como tal):
**`execute_tool()` (`djangorestframework_mcp/views.py`) nunca asigna
`HttpRequest.method`** al construir la petición interna que ejecuta la
acción del ViewSet (verificado leyendo el código completo del método:
`grep -n "request.method\|\.method ="` sobre el archivo instalado →
cero resultados). Esto rompe cualquier `permission_class` que dependa
de `request.method in SAFE_METHODS` -- exactamente el patrón que usa
`IsTenantAdminOrReadOnly` (`apps/tenant/api/permissions.py`), la clase
de permiso más común en este proyecto (usada en la enorme mayoría de
ViewSets, incluido `ClienteViewSet`).

**Evidencia real, no teórica**: con `ClienteViewSet` decorado, un
usuario con `TenantProfile(rol="OPERADOR")` (explícitamente NO admin)
autenticado con JWT real (`RefreshToken.for_user()`) invocando
`list_clientes` (una acción de LECTURA) vía MCP recibía:
```
{'content': [{'text': 'Forbidden: Solo usuarios ADMIN del tenant
pueden crear/editar/eliminar.', 'type': 'text'}], 'isError': True}
```
Es decir: MCP bloqueaba una lectura legítima tratándola como si fuera
una escritura, porque `IsTenantAdminOrReadOnly.has_permission()` nunca
llega a su primer `if request.method in SAFE_METHODS: return True` --
`request.method` nunca es `"GET"` en la petición fabricada por el
paquete, así que siempre cae al chequeo de rol ADMIN.

**Por qué se revierte en vez de trabajar alrededor del defecto**: el
alcance de AI-07 (Fase 32, "MCP READ FIRST") es exponer LECTURA seria
y confiable, no una lectura que falla espuriamente para cualquier
usuario no-ADMIN -- eso es peor que no exponer nada, porque un cliente
MCP legítimo (ej. un agente actuando en nombre de un `OPERADOR` real)
sería rechazado incorrectamente. Ningún workaround propio (parchear el
paquete de terceros, o reescribir `IsTenantAdminOrReadOnly` para no
depender de `request.method`) es apropiado sin que el usuario lo
autorice explícitamente -- ambos tocan código fuera del alcance de
"decorar un ViewSet existente".

**Estado real de MCP** (sin cambios respecto al estado antes de esta
investigación -- el revert dejó el código exactamente como estaba):
`django-rest-framework-mcp` está instalado y montado (`/mcp/` en
schema público y de tenant, `config/urls_tenant.py:166`,
`config/urls_public.py:117`) con `BYPASS_VIEWSET_AUTHENTICATION=False`
y `BYPASS_VIEWSET_PERMISSIONS=False` (`config/settings.py:677-692`) --
preserva auth/permisos de cada ViewSet por diseño del propio paquete
(cuando esos permisos no dependen de `request.method`). **Cero
ViewSets decorados con `@mcp_viewset`/`@mcp_tool`** -- el servidor MCP
no expone ninguna herramienta hoy.

**Camino real hacia adelante** (ninguno ejecutado, requiere decisión
del usuario):
1. Actualizar `django-rest-framework-mcp` a una versión que corrija
   esto (sin acceso a red en este entorno para verificar si ya existe
   una version mas reciente que 0.1.0a4 -- pendiente de chequeo
   manual).
2. O decorar solo ViewSets cuyo `permission_classes` NO dependa de
   `request.method` (ej. `IsTenantMember` sola, como
   `ReportingViewSet`) -- evita el bug sin arreglarlo, valido para un
   primer piloto acotado si el usuario prefiere avanzar así.
3. O reportar/parchear el paquete (`vendor`/fork local) -- cambio de
   mayor alcance, requiere autorización explícita.

## Fase 32 — MCP READ FIRST (diseño)

Cuando se decida exponer MCP, la primera etapa debe ser
**estrictamente de solo lectura**: decorar únicamente los ViewSets/
acciones cuyo `http_method_names` sea `['get', 'head', 'options']` (o
un subconjunto de acciones GET dentro de un ViewSet más amplio) --
nunca `DELETE`/`PUT`/`PATCH`/`POST` en esta primera etapa, sin
excepción, hasta validar aislamiento y permisos en producción real.

## Fase 33 — MCP WRITE (diseño, condicionado)

Solo tras la etapa READ validada, y solo para ViewSets cuyo dominio ya
tenga:
1. Un flujo de aprobación de tool WRITE ya implementado y probado en
   `apps/services/ai/` (hoy no existe -- ver `AI_RELEASE_GATE.md`).
2. Idempotencia real en el endpoint (no solo documentada).
3. Auditoría real de la operación (quién, cuándo, qué se escribió).

## Fase 3 — Clasificación de riesgo por herramienta MCP (diseño, tabla vacía hoy)

Sin ViewSets decorados, no hay nada que clasificar todavía. Cuando se
decoren los primeros, cada uno debe pasar por la misma matriz
`ToolRisk` ya definida en `apps/services/ai/tools/base.py`
(`SAFE_READ`/`SENSITIVE_READ`/`SAFE_WRITE`/`SENSITIVE_WRITE`/
`HIGH_RISK`) -- reutilizar la clasificación existente, no crear una
segunda taxonomía paralela solo para MCP.

## Filtrado por dominio/permiso/riesgo (Fase 31)

Diseño: la lista de ViewSets decorados que efectivamente aparecen en
`/mcp/` debe poder filtrarse server-side por el mismo `ToolRisk` y
permisos DRF ya existentes -- nunca "todos los ViewSets del proyecto
expuestos indiscriminadamente" (regla explícita de la Fase 31). No
implementado -- documentado como criterio de diseño para cuando se
retome.
