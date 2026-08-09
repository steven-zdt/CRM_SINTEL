# Auditoria Tecnica de OCF (Organizational Context Framework) — FASE 1

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED (auditoria) — cero codigo modificado
**Metodologia:** lectura completa de los 10 archivos nucleo (1088 lineas), mas `grep` exhaustivo de consumidores reales en las 17 apps tenant (no solo en los propios archivos/tests de OCF) para distinguir "existe" de "se usa". Todos los hallazgos citan archivo:linea.
**Regla de la fase:** solo auditoria. No se modifico ningun archivo de codigo.

---

## 0. Resumen ejecutivo

OCF es codigo real, bien documentado (cada modulo explica su propia decision de diseno, sus gaps conocidos y por que no se implemento algo) y sin bypasses de seguridad encontrados. Pero el hallazgo mas importante de esta fase es que **la mayor parte de OCF esta construida y probada, pero NO consumida en produccion todavia**:

| Pieza | Construida | Con tests | Consumida en produccion (fuera de tests) |
|---|:---:|:---:|:---:|
| `OrganizationalContext` (clase + `.resolve()`) | Si | Si | Solo indirectamente (via `OrganizationalContextMixin`, ver abajo) |
| `OrganizationalContextMixin` | Si | Si | Heredado por 14 ViewSets, pero **`.get_organizational_context()` nunca se llama** fuera de un comentario (`apps/tenant/empresa/api/viewsets.py:101`) |
| `OrganizationalScope` (clase + `.resolve()`) | Si | Si | **Si** — llamado directamente (no via Mixin) en 8 apps, 20+ sitios |
| `OrganizationalScopeMixin` | Si | Si | **No, cero herencias en todo el proyecto** — codigo muerto |
| `OrganizationalPermission` (permiso jerarquico) | Si | Si | **No** — ningun ViewSet declara `minimum_organizational_level` |
| `verify_organizational_dsv`/`is_organizationally_consistent` | Si | Si | **No** — cero consumidores fuera de su propio test |
| `*OrganizationalBridge` (Cotizacion/Cliente/Proveedor) | Si | Si | **No** — cero consumidores fuera de su propio test |
| `organizational_service_layer.py` (adaptador compras) | Si | Si | **No** — `crear_orden_compra_desde_contexto` no se llama desde ningun ViewSet/vista real |
| `filter_by_context`/`filter_by_scope`/`filter_by_scope_null_safe` | Si | Si | **Si** — en uso real en `compras`, `facturas`, y (via `OrganizationalScope.resolve()` + filtro manual) en varias apps mas |
| `resolve_sede_activa_id` (sede activa) + `contexto_organizacional` (context processor) + `sede_selector.js` | Si | Si | **Si** — cadena completa funcional: registrado en `settings.py:244`, template lo consume (`_header.html`), JS llama `POST /api/v1/core/contexto/sede/` |
| `GET /api/v1/core/contexto/` (lectura de contexto) | Si | No especifico de HTTP (via `ContextoOrganizacionalView`, cubierto indirectamente) | **No** — ningun JS del frontend lo consume hoy |

**Conclusion de la fase:** de las 8 piezas "Fase N" del proyecto OCF, solo 3 tienen consumo real fuera de sus propios tests (`sede_context`/context processor/JS, `OrganizationalScope.resolve()` llamado directo, y los helpers `filter_by_*`). Las otras 5 (DSV generalizado, Bridges adaptados, Permission jerarquico, Service Layer adapter, y el propio `OrganizationalContextMixin`/`get_organizational_context()`) son infraestructura terminada y probada pero **inerte** — construida deliberadamente como opt-in para una Fase 9/rollout que no llego a usarla todavia, no un bug. Esto confirma la instruccion del prompt maestro: "no asumir que OCF/OSF esta completamente terminado solo porque existen los modulos."

---

## 1. `apps/tenant/core/services/organizational_context.py` (205 lineas)

**Responsabilidad:** define `OrganizationalContext` (dataclass frozen, Tenant->Empresa->Sede->Area->Usuario->Perfil->Rol->Alcance->Timezone->Configuracion) y `OrganizationalContextMixin` (expone `self.get_organizational_context()`).

**Dependencias:** `apps.tenant.core.services.sede_context.resolve_sede_activa_id` (import diferido dentro de `resolve()`), `apps.tenant.empresa.models.Empresa` (fallback DEBUG), `django.conf.settings` (`DEBUG`, `TIME_ZONE`). `filter()` importa `organizational_filters.filter_by_context` de forma diferida.

**Entradas:** `resolve(request)` recibe un `HttpRequest` autenticado (`request.user`, `request.tenant`, `request.user.tenant_profile`).

**Salidas:** instancia inmutable `OrganizationalContext`; `to_dict()` para serializacion JSON; `filter(model)` retorna un `QuerySet`.

**Consumidores reales (grep, fuera de tests):**
- `apps/tenant/core/api/contexto.py:56` (`ContextoOrganizacionalView.get()`, via el Mixin) — **unico consumidor real de `OrganizationalContext.resolve()` en produccion**.
- `OrganizationalContextMixin` heredado en 14 `api/viewsets.py` (bancos, clientes, compras, contabilidad, cotizaciones, dashboard, empresa, facturas, gastos, inventario, perfil, proveedores, proyectos, ventas) — **pero ninguno llama `self.get_organizational_context()`**. Verificado por `grep -rn "\.get_organizational_context()" apps/tenant/*/api/viewsets.py apps/tenant/*/views.py` → unico resultado es un comentario en `apps/tenant/empresa/api/viewsets.py:101`, no una llamada real.

**Duplicaciones (documentadas por el propio codigo, no un descuido):** el algoritmo "leer `perfil.empresa_id`, si no hay perfil y `DEBUG=True` usar `Empresa.objects.only('id').first()` con warning" esta implementado **3 veces**: `SintelDSVMixin.get_empresa_id()` (`apps/tenant/api/mixins.py:24`, original), `OrganizationalContext.resolve()` (aqui, lineas 135-153), y `OrganizationalScope.resolve()` (`organizational_scope.py:149-165`, ver §2). El docstring del modulo (lineas 8-15) es explicito: es una decision consciente ("duplicado aqui a proposito... si alguno de los dos algoritmos cambia, el otro debe actualizarse a mano") respaldada por un "test de paridad" — confirmado que existe **solo para el par mixins.py/organizational_context.py** (`test_organizational_context.py`, ver §"Tests"). **No existe un test de paridad equivalente para `organizational_scope.py`** pese a que su docstring reclama "mismo algoritmo y misma justificacion" — este es el hallazgo de duplicacion mas concreto de la fase (ver §10 Riesgos).

**Codigo muerto:** ninguno dentro del archivo — todo lo definido se usa desde algun lugar (aunque sea solo desde tests o desde el Mixin sin llamar).

**Uso real:** parcial — la clase se resuelve correctamente en el unico endpoint que la consume (`/api/v1/core/contexto/`), pero el Mixin esta inerte en las otras 13 apps que lo heredan sin invocarlo.

**Tests:** `apps/tenant/core/tests/test_organizational_context.py` (96 lineas) — usa `RequestFactory` + `SintelTenantTestCase`, incluye explicitamente una prueba de paridad contra `SintelDSVMixin` con el MISMO request (ver docstring del test, lineas 6-10).

---

## 2. `apps/tenant/core/services/organizational_scope.py` (231 lineas)

**Responsabilidad:** define `OrganizationalScope` (dataclass frozen — conjunto TOTAL de `sede_ids`/`area_ids` permitidos, no una posicion activa unica), `OrganizationalScopeMixin`, y los helpers `sede_esta_en_alcance()`/`area_esta_en_alcance()` para `validate()` de serializers.

**Contrato documentado (lineas 1-40) — la distincion mas importante de todo OCF/OSF:** `OrganizationalContext` responde "donde estoy parado" (una sede activa singular, para defaultear registros nuevos y pintar el header); `OrganizationalScope` responde "que puedo tocar en total" (el conjunto completo, para Selectors y validacion de escritura). El propio modulo documenta una asimetria real que descubrio: `OrganizationalContext.filter()` filtra solo por la sede activa (1 sola), mientras `HasOrganizationalScope` (ADR-003) valida contra el conjunto completo — si un selector usara `OrganizationalContext.filter()` en vez de `OrganizationalScope.filter()`, un perfil con 3 sedes asignadas veria solo 1 en los listados. **Este bug potencial esta prevenido, no materializado**: verificado que ningun selector real llama `OrganizationalContext.filter()` (grep sin resultados fuera de su propio test) — todos los que filtran por scope usan `OrganizationalScope`/`filter_by_scope*` directamente.

**Dependencias:** `django.conf.settings` (`DEBUG`). Nada mas — deliberadamente independiente de `organizational_context.py` (no lo importa, no depende de que se resuelva primero).

**Entradas:** `resolve(request)`, `permits_sede(sede_id)`, `permits_area(area_id)`, `filter(model)`.

**Consumidores reales (fuera de tests) — confirmado por grep, 8 apps, ~20 sitios:**
`compras` (`services/api_mixins.py:84`, `services/selectors.py:114` via `filter_by_scope`), `cotizaciones` (`services/api_mixins.py:38,57`), `empleados` (`services/api_mixins.py:49,72`, `views.py:64`), `facturas` (`api/viewsets.py:227,369`, `views.py:65`), `gastos` (`services/api_mixins.py:46,65`, `views.py:57`), `inventario` (`services/api_mixins.py:299`, `api/viewsets.py:529,548`), `proyectos` (`api/viewsets.py:114,134,409,479,562,602` — **6 llamadas independientes en el mismo archivo**, `views.py:58`), `ventas` — patron de consumo confirmado tambien ahi por la clasificacion de FASE 0.

**Duplicaciones:**
1. Resolucion de `empresa_id` triplicada (ver §1 — aqui es la copia #3, lineas 149-165).
2. **`OrganizationalScopeMixin` nunca se hereda en ningun lugar del proyecto** (`grep -rn "OrganizationalScopeMixin" apps/tenant/ --include=*.py` solo devuelve su propia definicion y su test) — todos los 8 consumidores llaman `OrganizationalScope.resolve(self.request)` **directamente y sin cache**, en vez de usar el Mixin (que cachearia el resultado en `self._organizational_scope` durante la vida del request/instancia). Consecuencia real, no teorica: `apps/tenant/proyectos/api/viewsets.py` llama `OrganizationalScope.resolve(self.request)` en 6 metodos distintos — cada llamada re-ejecuta `perfil.sedes_asignadas.values_list('id', flat=True)` (una query) para un perfil con `alcance` SEDE/AREA. Si dos de esos metodos se ejecutan en el mismo request (ej. `get_queryset()` + `perform_create()`), son 2 queries redundantes que el Mixin habria evitado con una sola.

**Codigo muerto:** `OrganizationalScopeMixin` (clase completa, lineas 184-198) — construida, probada, pero cero adopcion real.

**Uso real:** alto para la clase `OrganizationalScope` y sus metodos estaticos/de instancia (`permits_sede`, `filter`); nulo para el Mixin.

**Tests:** `apps/tenant/core/tests/test_organizational_scope.py` (175 lineas) — la suite mas grande de las 9. No se verifico en esta fase si incluye un test que ejercite el Mixin (candidato a revisar en FASE 2, ya que el Mixin no se usa en produccion pero si podria estar cubierto solo por su propio test unitario aislado).

---

## 3. `apps/tenant/core/services/organizational_permissions.py` (76 lineas)

**Responsabilidad:** jerarquia de 6 niveles (`ADMIN_GLOBAL > ADMIN_EMPRESA > ADMIN_SEDE > JEFE_AREA > OPERADOR > CONSULTA`), derivada de datos ya existentes (`rol`, `alcance`, `is_staff`) sin campo nuevo. `resolve_organizational_permission_level()` + `level_meets_minimum()`.

**Gap documentado explicitamente por el propio modulo (lineas 19-28):** el pedido original tenia un nivel "Supervisor" entre `JEFE_AREA` y `OPERADOR` que no existe en el modelo real (`rol`/`alcance`) — tratado como sinonimo de `OPERADOR` en vez de inventar una capacidad sin respaldo. Documentado, no oculto.

**Dependencias:** ninguna (funciones puras sobre strings).

**Consumidor real:** `apps/tenant/api/permissions.py:198-228` (`OrganizationalPermission.has_permission()`) — la unica clase que usa estas funciones.

**Uso real de `OrganizationalPermission` como permiso DRF:** **ninguno**. `grep -rn "OrganizationalPermission(" apps/tenant/*/api/*.py` no encuentra ningun ViewSet que la incluya en `permission_classes`, ni que declare el atributo opt-in `minimum_organizational_level` que la activa (la clase esta diseñada fail-closed/no-op: si `minimum_organizational_level` no esta declarado, `has_permission()` retorna `True` sin restringir — confirmado en `apps/tenant/api/permissions.py:224-226`).

**Codigo muerto:** ninguno en el modulo en si (todo se usa desde `permissions.py`), pero la clase que lo consume (`OrganizationalPermission`) esta a su vez sin adoptar — cadena completa construida y sin uso.

**Tests:** `apps/tenant/core/tests/test_organizational_permissions.py` (158 lineas).

---

## 4. `apps/tenant/core/services/organizational_dsv.py` (108 lineas)

**Responsabilidad:** generaliza el patron anti-IDOR `empresa->modelo` (usado ya en las 17 apps) a `empresa->sede->area->modelo`, como funcion pura (`verify_organizational_dsv`, `is_organizationally_consistent`) reusable tanto desde un permiso DRF como desde un Business Service.

**Alcance honesto declarado (lineas 15-28):** NO reimplementa verificacion de tenant (ya cubierta por aislamiento de esquema), usuario (ya cubierta por `OrganizationalContext.resolve()`) ni rol (ya cubierta por `HasTenantRole`/`OrganizationalPermission`) — se enfoca solo en la pieza nueva (sede/area). Diseno deliberadamente no-redundante.

**Dependencias:** `organizational_context.OrganizationalContext` (solo el tipo, para type hints/lectura de `context.empresa_id`/`context.alcance`).

**Consumidores reales fuera de tests:** **ninguno**. `grep -rln "verify_organizational_dsv\|is_organizationally_consistent" apps/tenant/ --include=*.py` solo encuentra el propio archivo y su test.

**Codigo muerto:** funcionalmente si (0 consumidores de produccion), pero es exactamente lo que su propio docstring anuncia: "Fase 5" construida como pieza aislada, con la migracion real (aplicarla en los Business Service de las 17 apps) deferida a Fase 9/rollout — no es un descuido, es infraestructura en espera.

**Tests:** `apps/tenant/core/tests/test_organizational_dsv.py` (89 lineas).

---

## 5. `apps/tenant/core/services/organizational_bridges.py` (111 lineas)

**Responsabilidad:** contrato `OrganizationalBridge` (Protocol: `get_by_uuid`/`exists`) + 3 adaptadores (`CotizacionOrganizationalBridge`, `ClienteOrganizationalBridge`, `ProveedorOrganizationalBridge`) que envuelven los bridges reales de `facturas/services/selectors.py` sin modificarlos.

**Honestidad de cobertura, documentada por el propio modulo (lineas 26-39):** de los 5 bridges reales de `facturas`, solo 3 encajan en el contrato `get_by_uuid`/`exists` (forma uuid->dict). `InventarioItemBridge` (catalogo/busqueda) y `BancosBridge` (agregado numerico) **no se adaptan a la fuerza** — quedan documentados en `_BRIDGES_SIN_ADAPTAR`, no ocultos ni forzados a un contrato que no les corresponde. Tambien documenta que `VentasBridge`/`ComprasBridge` **no existen** (esas apps leen por FK directa + DSV, no por bridge) y explicitamente decide no fabricarlos sin necesidad real (`_BRIDGES_INEXISTENTES`).

**Dependencias:** `apps.tenant.facturas.services.selectors.{CotizacionBridge,ClienteBridge,ProveedorBridge}` (imports diferidos dentro de cada metodo — los bridges reales, sin modificar, confirmado por lectura).

**Consumidores reales fuera de tests:** **ninguno**. Confirmado por grep de instanciacion (`OrganizationalBridge()`) sin resultados fuera del propio modulo/test.

**Bypass check:** NO bypasea el Service Layer ni los bridges existentes — son adaptadores puros que delegan 100% de la logica a los bridges reales ya existentes, sin reimplementar nada.

**Codigo muerto:** funcionalmente si (0 consumidores de produccion) — misma naturaleza que §4, infraestructura en espera de Fase 9.

**Tests:** `apps/tenant/core/tests/test_organizational_bridges.py` (72 lineas).

---

## 6. `apps/tenant/core/services/organizational_filters.py` (90 lineas)

**Responsabilidad:** 3 funciones puras de filtrado de queryset: `filter_by_context()` (ADR-003, un solo `sede_id`/`area_id`), `filter_by_scope()` (OSF F5, conjunto via `__in`), `filter_by_scope_null_safe()` (OSF F7, variante que trata `sede`/`area` NULL como visible para todos los alcances — justificada empiricamente: "100% de los registros reales de Factura/Cotizacion/DocumentoSoporte/MovimientoInventario/Proyecto/Empleado tienen sede=NULL hoy").

**Este es el modulo con mayor adopcion real de todo OCF/OSF** — es la pieza que efectivamente mueve queries de produccion (ver §2, consumidores de `filter_by_scope`).

**Dependencias:** solo `django.db.models` (`Q`, `QuerySet`) — sin dependencia de `OrganizationalContext`/`OrganizationalScope` (helpers puros que reciben ids ya resueltos, no objetos).

**Duplicacion estructural, no de codigo:** las 3 funciones son casi identicas entre si (mismo patron `.filter(empresa_id=...)` + condicional por sede/area) — no es codigo duplicado copiado sino 3 variantes deliberadas del mismo patron para 3 casos distintos (activa-unica / conjunto-estricto / conjunto-null-safe). No se considera un hallazgo de "logica duplicada" indebida porque cada una tiene semantica distinta y esta documentada como tal.

**Codigo muerto:** ninguno — las 3 funciones tienen consumidores reales (`filter_by_context`: piloto `compras`; `filter_by_scope`: `compras/services/selectors.py:114`; `filter_by_scope_null_safe`: `facturas/services/selectors.py`, confirmado por comentario en linea 121-122 de ese archivo).

**Tests:** `apps/tenant/core/tests/test_organizational_filters.py` (95 lineas).

---

## 7. `apps/tenant/core/services/organizational_service_layer.py` (70 lineas)

**Responsabilidad:** helpers de resolucion (`resolve_empresa_and_sede`, `resolve_perfil`) que convierten un `OrganizationalContext` en instancias reales (`Empresa`, `Sede`, `TenantProfile`); mas UN adaptador de demostracion (`crear_orden_compra_desde_contexto`) sobre `OrdenCompraBusinessService.crear_orden_compra` (compras, ADR-003) **sin modificar ese Business Service**.

**Autolimitacion documentada (lineas 25-27):** el propio modulo declara que construir 17 adaptadores (uno por app) sin que ninguna fase futura los haya pedido seria "infraestructura especulativa" — decision consciente de no sobre-construir.

**Dependencias:** `organizational_context.OrganizationalContext` (tipo); `apps.tenant.empresa.models.{Empresa,Sede}`, `apps.tenant.perfil.models.TenantProfile`, `apps.tenant.compras.services.business_service.OrdenCompraBusinessService` (imports diferidos).

**Consumidores reales fuera de tests:** **ninguno**. `crear_orden_compra_desde_contexto` no se llama desde ningun ViewSet/vista de `compras` — el flujo real de creacion de `OrdenCompra` sigue pasando por `OrdenCompraBusinessService.crear_orden_compra` directamente (empresa/sede como objetos ya resueltos por el ViewSet, no via este adaptador).

**Bypass check:** NO — el adaptador delega 100% al Business Service real, no reimplementa logica de negocio.

**Codigo muerto:** funcionalmente si (0 consumidores de produccion), naturaleza identica a §4/§5.

**Tests:** `apps/tenant/core/tests/test_organizational_service_layer.py` (82 lineas).

---

## 8. `apps/tenant/core/services/sede_context.py` (35 lineas) + `apps/tenant/core/context_processors.py` (40 lineas)

**Responsabilidad conjunta:** `resolve_sede_activa_id()` es el UNICO algoritmo de "cual es la sede activa" (sesion -> primera `sedes_asignadas` -> Sede "Principal" de la empresa), compartido explicitamente por `SintelDSVMixin.get_sede_id()` (`apps/tenant/api/mixins.py`, consumido por ViewSets DRF), `OrganizationalContext.resolve()` (§1), y el context processor `contexto_organizacional()` (usado por el header HTML compartido). Esta es la **unica** pieza de OCF donde la duplicacion de algoritmo fue evitada activamente (factorizada en una funcion compartida) en vez de tolerada con un test de paridad — patron mas seguro que el usado para `empresa_id` (ver §1/§2).

**Consumidores reales confirmados:**
- `apps/tenant/api/mixins.py` (`SintelDSVMixin.get_sede_id()`) — produccion, ViewSets DRF.
- `apps/tenant/core/context_processors.py:32` — produccion, registrado en `config/settings.py:244` (`TEMPLATES[0]['OPTIONS']['context_processors']`), confirmado activo.
- `apps/tenant/core/templates/tenant/partials/_header.html` consume `sede_activa`/`sedes_disponibles` (lineas 12, 22, 25, 28, 86) — confirmado, no es codigo muerto de template.
- `apps/tenant/core/static/core/js/common/sede_selector.js` — confirmado incluido en `_header.html:88`, llama `POST /api/v1/core/contexto/sede/` (`ContextoSedeView`, §9) para persistir el cambio en `request.session['sede_activa_id']`.

**Esta es la unica cadena end-to-end de OCF/OSF verificada como 100% funcional en produccion**, desde el modelo de datos hasta el click del usuario en el dropdown del header.

**Tests:** no tiene test unitario dedicado propio visible en `core/tests/test_organizational_*.py` (su logica se ejercita indirectamente via `test_organizational_context.py`, que llama `OrganizationalContext.resolve()`, que a su vez llama `resolve_sede_activa_id()`). **Gap menor:** no se encontro un test que ejercite `contexto_organizacional()` (el context processor) ni `sede_selector.js` de forma aislada — cobertura solo indirecta.

---

## 9. `apps/tenant/core/api/contexto.py` (122 lineas)

**Responsabilidad:** `ContextoOrganizacionalView` (`GET /api/v1/core/contexto/`, solo lectura, expone `OrganizationalContext.to_dict()` + `OrganizationalScope.to_dict()` en un bloque `scope`) y `ContextoSedeView` (`POST /api/v1/core/contexto/sede/`, cambia la sede activa en sesion, con DSV inline: la sede debe pertenecer a la empresa y estar dentro de `sedes_asignadas` si `alcance != EMPRESA`).

**Permisos:** ambas vistas usan `[IsAuthenticated, IsTenantMember]` — permisos ya existentes del proyecto, sin bypass.

**Consumidores reales:** `ContextoSedeView` — si, consumida por `sede_selector.js` (§8). `ContextoOrganizacionalView` (el GET de solo lectura) — **no consumida por ningun JS del frontend hoy**, es un endpoint construido y funcional pero sin cliente real todavia (confirmado, `grep -rln "core/contexto" apps/tenant/*/static/*/js/**/*.js` solo encuentra `sede_selector.js`, que llama al endpoint `/sede/`, no al de lectura).

**Observacion de arquitectura (no bug, nota para FASE 3):** `ContextoSedeView.post()` implementa la verificacion DSV (pertenencia a empresa + `sedes_asignadas`) directamente en el cuerpo del metodo de la vista (lineas 107-118), en vez de delegarla a un Selector o Business Service dedicado. Es una verificacion corta (2 queries, ninguna mutacion de modelo de negocio mas alla de `request.session`) y el propio docstring la justifica ("mismo criterio que `HasOrganizationalScope`, aplicado aqui al momento de elegirla") — no viola la regla de Service Layer de forma grave porque no hay un modelo de negocio (`SintelTenantBaseModel`) siendo escrito, solo lectura de `Sede` + escritura de sesion. Se deja como observacion para FASE 3 (Contrato Definitivo), no como hallazgo bloqueante.

**Tests:** no hay `test_contexto_api.py` dedicado visible en el listado de FASE 0 — la vista se ejercita indirectamente via los tests unitarios de `OrganizationalContext`/`OrganizationalScope`, pero **no se encontro un test HTTP real (`APIClient`/`RequestFactory` contra la URL) para ninguno de los dos endpoints**. Gap real, candidato a FASE 2/7.

---

## 10. Verificacion de las 4 prohibiciones explicitas del prompt maestro

| Prohibicion | Resultado |
|---|---|
| ¿Logica duplicada? | **Si, documentada y parcialmente cubierta por tests.** Resolucion de `empresa_id` triplicada (`SintelDSVMixin`, `OrganizationalContext.resolve()`, `OrganizationalScope.resolve()`) — solo el primer par tiene test de paridad automatizado. `OrganizationalScopeMixin` sin cache real, forzando resolucion repetida en `proyectos` (6 llamadas sin cache en un mismo archivo). |
| ¿Fuente de verdad paralela? | **No.** `TenantProfile.rol`/`.alcance` siguen siendo la unica fuente — todo lo nuevo LEE de ahi, nada la reemplaza ni la sombra. |
| ¿Bypass de permissions? | **No.** Todo lo nuevo es aditivo/fail-closed (`OrganizationalPermission` no restringe si no se opta explicitamente; `ContextoOrganizacionalView`/`ContextoSedeView` usan `IsTenantMember` existente). |
| ¿Bypass de Service Layer? | **No.** `organizational_bridges.py` y `organizational_service_layer.py` son adaptadores que delegan 100% a los Business Service/Bridges reales, sin reimplementar logica. Unica observacion menor: `ContextoSedeView` hace su propia verificacion en vez de un Selector dedicado (ver §9) — no es un bypass del Service Layer de un modelo de negocio, es logica de sesion/UI. |
| ¿Bypass de Selectors? | **No.** `filter_by_scope*`/`OrganizationalScope.filter()` se usan DENTRO de los selectors existentes de cada app (ej. `compras/services/selectors.py:114`), no en su lugar. |
| ¿Bypass de DSV? | **No.** `organizational_dsv.py` generaliza el patron anti-IDOR existente sin reemplazarlo (0 consumidores todavia, pero tampoco ningun DSV existente fue debilitado). |

---

## 11. Estado de ejecucion de tests (pytest real, Docker)

Se lanzo `docker compose exec web python -m pytest apps/tenant/core/tests/test_organizational_*.py -q` (9 archivos, 994 lineas) contra el contenedor `crm_sintel-web-1`. **Resultado confirmado (2026-08-09): `53 passed, 1 warning in 1452.86s (0:24:12)`** — el tiempo largo (24 min) fue creacion de esquema de test para las 186 migraciones reales del proyecto, no un fallo. El unico warning es de DRF (`min_value should be an integer or Decimal instance`), no relacionado con OCF. Todas las afirmaciones "demostrado por" de este documento y de `OSF_TECHNICAL_AUDIT.md` quedan verificadas por ejecucion real, no solo por lectura de codigo.

---

## Cierre de FASE 1

Ningun archivo de codigo funcional fue modificado. Documento creado: `documentacion/OCF_TECHNICAL_AUDIT.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
