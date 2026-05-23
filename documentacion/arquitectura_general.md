# Arquitectura General — SINTEL ERP

**Version:** 3.9.3  
**Ultima actualizacion:** 2026-05-23  
**Fuente canonica:** `documentacion/arquitectura_general.md`  
**Reglas de desarrollo:** `AGENTS.md` (raiz del proyecto)  
**Estado actual del proyecto:** `MEMORY.md` (raiz del proyecto)  
**Modo de Proyecto:** EN DESARROLLO (Development Mode)

> Antes de modificar cualquier app, leer `AGENTS.md` completo y el documento `.agent/AUDITORIA_FLUJO_*.md` de esa app. Este documento describe la infraestructura global, no la logica interna de cada app.

---

## 1. Vision y Core Tecnologico del Proyecto

SINTEL es un ERP SaaS multi-tenant para gestion contable y facturacion electronica en Colombia. Cada empresa (tenant) opera en un esquema PostgreSQL aislado, compartiendo la misma infraestructura de servidores. El sistema implementa Feature-Sliced Design (FSD) con Service Layer estricto, autenticacion Dual-Auth (JWT + Session) y frontend sin build step.

**Dominio de negocio principal:** facturacion electronica DIAN (XML, envio, estados), contabilidad NIIF PYMES, nomina colombiana, inventario con Kardex, gastos operativos, cotizaciones comerciales, proyectos y CRM basico.

### 1.1. Stack Backend

| Tecnologia | Version | Rol |
|---|---|---|
| Python | 3.12 | Lenguaje principal |
| Django | 4.x | Framework web |
| Django REST Framework | 3.x | APIs JSON (ViewSets, Serializers, Routers) |
| django-tenants | 3.x | Aislamiento multi-tenant por esquemas PostgreSQL |
| PostgreSQL | 15+ | Base de datos relacional |
| Celery | 5.x | Tareas asincronas y procesamiento en segundo plano |
| Redis | 7.x | Broker de Celery y cache |
| WhiteNoise | 6.x | Servicio de archivos estaticos en produccion |
| djangorestframework-simplejwt | 5.3+ | Tokens JWT (access 15 min, refresh 7 dias, HS256) |
| anthropic | 0.40+ | SDK para agentes IA especializados (Asistente Contable) |

### 1.2. Stack Frontend

| Tecnologia | Version | Rol |
|---|---|---|
| HTMX | 1.9.10 | Server-driven UI, carga dinamica de fragmentos HTML |
| Bootstrap | 5.3.2 | Sistema de diseno UI, Offcanvas para modales laterales |
| Tabulator | 6.2.5 | Grillas de datos reactivas con paginacion remota |
| Vanilla JS ES6+ | — | Modulos por namespace `window.Sintel.<App>` |
| Bootstrap Icons + Font Awesome | — | Iconografia |

**No hay build step.** Todas las librerias se cargan via CDN. No existe Webpack, Vite ni compilacion de frontend. Alpine.js esta disponible via CDN pero no es parte del estandar aprobado.

### 1.3. Infraestructura

| Componente | Tecnologia |
|---|---|
| Contenedores | Docker + Docker Compose |
| Servidor WSGI | Gunicorn |
| Proxy inverso | Nginx (produccion) |
| Autenticacion asimetrica | HS256 JWT via variable de entorno `JWT_SECRET_KEY` |

### 1.4. Directorio `config/` — Nucleo de Configuracion

El directorio `config/` es el nucleo de configuracion del proyecto. Toda la orquestacion de URLs, settings y tareas asincronas pasa por aqui.

| Archivo | Responsabilidad |
|---|---|
| `settings.py` | SSoT de toda la configuracion Django (SHARED_APPS, TENANT_APPS, JWT, Celery, etc.) |
| `urls_public.py` | ROOT_URLCONF — dominio admin mapea al esquema public |
| `urls_tenant.py` | TENANT_URLCONF — subdominios mapean al esquema tenant |
| `api_urls.py` | SSoT de TODAS las rutas API REST (`/api/v1/...`). Ningun ViewSet se registra fuera de este archivo |
| `celery.py` | Configuracion Celery + autodiscovery de tasks |
| `public_api_urls.py` | Rutas API del esquema publico |
| `well_known.py` | Endpoints `.well-known` (DIAN, OAuth) |

### 1.5. Resolucion de Tenant por Hostname

```
request → TenantMiddleware → hostname match → set schema PostgreSQL

admin.sintel.co    →  public schema    →  urls_public.py
empresa.sintel.co  →  tenant schema    →  urls_tenant.py
```

---

## 2. Capa de Datos e Infraestructura Multi-Tenant (Zero-Trust)

### 2.1. Division de Esquemas PostgreSQL

| Esquema | Apps | Contenido |
|---|---|---|
| `public` | `SHARED_APPS` | Usuarios globales (`accounts.User`), registro de tenants (`tenants.Client`), catalogo DIAN (`impuestos`), consola admin (`console`) |
| Tenant (uno por empresa) | `TENANT_APPS` | Todos los datos de negocio del tenant: facturas, contabilidad, empleados, inventario, etc. |

Los esquemas tenant estan completamente aislados a nivel de base de datos. Una consulta en el esquema de "Empresa A" nunca puede acceder a los datos de "Empresa B" por disenio del ORM.

### 2.2. Modelo Base Obligatorio — `SintelTenantBaseModel`

**SSoT:** `apps/tenant/core/models.py`

Todos los modelos del esquema tenant heredan de `SintelTenantBaseModel`, nunca de `models.Model`. Este modelo base inyecta automaticamente:

| Campo | Tipo | Detalle |
|---|---|---|
| `empresa` | `ForeignKey('empresa.Empresa', PROTECT)` | Clave de particion — filtra al tenant actual |
| `created_at` | `DateTimeField(auto_now_add=True)` | Timestamp de creacion, indexado |
| `updated_at` | `DateTimeField(auto_now=True)` | Timestamp de ultima modificacion, indexado |

**Indices heredados automaticamente:** `[empresa]` y `[empresa, -created_at]`.

**Proteccion en `save()`:** el modelo base lanza `ValueError` si `empresa_id` es `None`, evitando registros huerfanos por error de programacion.

### 2.3. Regla Zero-Trust de Consultas

Toda consulta ORM en apps tenant debe filtrar por `empresa_id`. Las siguientes practicas estan prohibidas:

- Usar `.all()` sin filtro de empresa
- Usar `.filter()` sin encadenar `.only()` o `.defer()`
- Acceder a `obj.fk.campo` sin `select_related()` previo (problema N+1)

**Patron obligatorio en ViewSets:**

```
queryset = Model.objects.none()   # nivel de clase
get_queryset() → .filter(empresa_id=...).only(campos).select_related(...)
```

### 2.4. UUID como Lookup Field

`BaseTenantViewSet` (`apps/tenant/api/base.py`) define `lookup_field = "uuid"`. Todos los ViewSets tenant heredan este valor. Las PKs enteras nunca se exponen en URLs publicas de la API.

### 2.5. Seguridad y Autenticacion (Dual-Auth)

**SSoT de autenticacion:** `BaseTenantViewSet` en `apps/tenant/api/base.py`.

`authentication_classes = [JWTAuthentication, SessionAuthentication]` — heredado por todos los ViewSets. Prohibido sobrescribir en ViewSets hijos.

DRF evalua JWT primero (header `Authorization: Bearer`). Si falla, usa Session (cookie). Esto permite que el mismo endpoint sirva a clientes API y al workspace del navegador.

**Bridge Session → JWT:** `GET /api/v1/core/auth/from-session/`

**Endpoints de token:**

| Endpoint | Metodo | Accion |
|---|---|---|
| `/api/token/` | POST | Obtener par access/refresh |
| `/api/token/refresh/` | POST | Renovar access token |
| `/api/token/verify/` | POST | Verificar validez de token |

**Parametros JWT (`config/settings.py`):** access 15 min, refresh 7 dias, ROTATE=True, BLACKLIST=True, algoritmo HS256.

### 2.6. Roles y Permisos

**SSoT de roles:** `TenantProfile.rol` en `apps/tenant/perfil/models.py`

| Rol | Capacidades |
|---|---|
| `ADMIN` | CRUD completo, asignar roles, configuracion de empresa |
| `OPERADOR` | Lectura + escritura segun app |
| `VISOR` | Solo lectura |

**SSoT de permisos:** `apps/tenant/api/permissions.py` — unica fuente para importar permisos en todo el proyecto.

| Permiso | Descripcion |
|---|---|
| `IsTenantMember` | Verifica membresia activa en el tenant. Obligatorio en todo ViewSet |
| `IsTenantAdminOrReadOnly` | Lectura para autenticados; escritura solo para ADMIN |
| `IsTenantProfileOperadorOrAdmin` | Requiere ADMIN u OPERADOR |
| `HasTenantRole` | Generico — el ViewSet declara `required_roles` |

**Auto-creacion de perfil:** al hacer login, si el usuario no tiene `TenantProfile` en el tenant actual, se crea automaticamente con rol `VISOR`.

**Frontend JWT:**

```javascript
// CORRECTO:
const token = window.jwtAuth?.getAccessToken?.();

// PROHIBIDO — la propiedad .token no existe:
window.jwtAuth.token
```

---

## 3. Patron de Arquitectura del Backend (Service Layer Unificada)

### 3.1. Feature-Sliced Design (FSD) — Un Ecosistema por Modelo

Cada app tenant implementa un ecosistema completo e independiente por modelo de dominio.

```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          — Re-exporta clases principales (imports explicitos, sin wildcards)
    crud_service.py      — SOLO persistencia DB (@transaction.atomic)
    business_service.py  — Reglas de negocio + Double Semantic Verification (IDOR)
    selectors.py         — QuerySets read-only con .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py        — <Modelo>ServiceMixin inyectado en ViewSet
    services.py          — Facade estable (re-exporta desde business_service)
  api/
    viewsets.py          — Hereda BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/
    offcanvas_crear_<modelo>.html
    offcanvas_editar_<modelo>.html
    offcanvas_detalle_<modelo>.html
    list_<modelo>.html
    partials/
  static/<app>/js/
    <app>.api.js                   — SSoT de todas las URLs de endpoint
    features/
      <modelo>_list.js             — Grilla Tabulator
      <modelo>_editor.js           — Formularios Offcanvas
  .agent/
    AUDITORIA_FLUJO_*.md           — Flujo especifico de la app (leer antes de modificar)
    docs/
    skills/
```

### 3.2. Flujo Unidireccional (Obligatorio)

```
ViewSet → ServiceMixin → BusinessService (DSV + reglas) → CRUDService (DB) → Response JSON / HTMX OOB
```

El ViewSet es un enrutador HTTP puro. Toda logica de negocio vive en el Service Layer. Los modelos no contienen logica de negocio. Los Serializers solo realizan validacion sintactica y de tipos.

### 3.3. Responsabilidades por Capa

| Capa | Archivo | Responsabilidad |
|---|---|---|
| ViewSet | `api/viewsets.py` | Ingesta HTTP, delegacion a ServiceMixin, respuesta |
| Serializer | `api/serializers.py` | Validacion sintactica y de tipos, serializacion de salida |
| ServiceMixin | `services/api_mixins.py` | Inyecta `get_qs_list()`, `get_qs_detail()`, `service_crear_*()` |
| BusinessService | `services/business_service.py` | DSV, reglas de dominio, calculos, idempotencia |
| CRUDService | `services/crud_service.py` | Persistencia DB unica (`@transaction.atomic`) |
| Selector | `services/selectors.py` | QuerySets de lectura con `.only()`, `LIST_FIELDS`, `DETAIL_FIELDS` |

### 3.4. Double Semantic Verification (DSV)

Toda mutacion en `business_service.py` valida que los FKs del payload pertenezcan al tenant actual (`empresa_id`). Esta verificacion es la defensa principal contra ataques IDOR (Insecure Direct Object Reference) a nivel de aplicacion.

La DSV verifica:
1. Que el recurso objetivo exista en el tenant
2. Que todos los FKs referenciados en el payload pertenezcan al mismo tenant
3. Que el usuario autenticado tenga membresia activa

### 3.5. Frontend — Patron de Modulos JS

**Namespace por app:** `window.Sintel.<App>`

Archivos por rol:

| Archivo | Responsabilidad |
|---|---|
| `<app>.api.js` | SSoT de todas las URLs y consumo de endpoints. Sin logica de UI |
| `features/<modelo>_list.js` | Inicializacion de Tabulator, columnas, eventos de busqueda |
| `features/<modelo>_editor.js` | Ciclo de vida del Offcanvas (crear/editar/detalle), listeners de formulario |

**Tabulator (grillas):** Todas las grillas usan `TabulatorFactory.create()` definido en `apps/tenant/core/static/core/js/common/tabulator.factory.js`. Inyecta JWT automaticamente y espera respuesta DRF paginada: `{ count, next, previous, results: [] }`.

**HTMX (Offcanvas):** Los Offcanvas se cargan via `hx-get` apuntando a `render-offcanvas/crear/`. El backend retorna HTML parcial. Regla critica: usar siempre `mostrarOffcanvasSeguro(el)` definido en cada editor, que limpia backdrops acumulados antes de llamar `show()`. Ver AGENTS.md §26 para el patron completo.

**Helpers globales de infraestructura:** `apps/tenant/core/static/core/js/common/` — disponibles en todo el tenant.

| Helper | Archivo |
|---|---|
| `UIManager` | `ui-manager.js` — notificaciones, manejo de errores 400, offcanvas |
| `TabulatorFactory` | `tabulator.factory.js` — creacion de grillas con JWT auto-inyectado |

### 3.6. Procesamiento Asincrono

Las tareas masivas, calculos sobre datos historicos e integraciones de terceros se despachan a workers Celery via `.delay()`. Toda tarea define politicas de reintentos (`max_retries`). Al agotar reintentos, el payload se inserta en un registro `FailedTenantTask` para observabilidad y reencola manual.

---

## 4. Aislamiento Cross-Schema y Gobernanza de Datos

### 4.1. Core Membership Bridge

**SSoT del bridge:** `apps/tenant/core/services/membership.py`

Las apps tenant **no pueden** importar directamente desde `apps.public.*`. El bridge es la unica interfaz autorizada para consultar datos del esquema publico.

| Operacion del Bridge | Descripcion |
|---|---|
| `check_membership(user, empresa)` | Verifica membresia activa. Retorna `TenantMembership` o `None` |
| `check_membership_exists(user, empresa)` | Retorna `bool` para verificacion rapida |
| `check_admin_membership(user, empresa)` | Verifica membresia con rol ADMIN |
| `check_primary_admin(empresa)` | Retorna el `TenantMembership` del administrador primario |
| `get_user_role(user, empresa)` | Retorna el string del rol o `None` |
| `get_primary_domain(empresa)` | Retorna el dominio primario del tenant |
| `verify_invitation(token)` | Valida token de invitacion |

**Excepcion:** Solo `apps/tenant/core/` y `apps/tenant/api/` (permisos centrales) pueden importar desde `apps.public`. Ninguna otra app tenant tiene esta autorizacion.

**Extension del bridge:** si una app necesita una nueva consulta al esquema publico, se agrega la operacion a `membership.py`. Prohibido crear imports directos como alternativa.

### 4.2. Reglas de Aislamiento de Assets (CSS/JS)

Todos los archivos `.html` y `.js` deben residir dentro del nucleo de la app a la que pertenecen.

| Tipo | Ruta obligatoria |
|---|---|
| Templates tenant | `apps/tenant/<app>/templates/tenant/<app>/` |
| JS estatic tenant | `apps/tenant/<app>/static/<app>/js/` |
| Templates public | `apps/public/<app>/templates/<app>/` |
| JS estatico public | `apps/public/<app>/static/<app>/js/` |
| Helpers globales (excepcion controlada) | `apps/tenant/core/static/core/js/common/` |

Cada app define un template `assets_<app>.html` que centraliza la inclusion de sus scripts y estilos. Prohibidos: scripts compartidos entre modelos no relacionados, templates monoliticos, referencias cruzadas de assets entre apps.

### 4.3. Prohibiciones de Gobernanza

| Regla | Detalle |
|---|---|
| Sin emojis en `.py` | Causan `SyntaxError` → Django 500 |
| `SintelTenantBaseModel` obligatorio | Todos los modelos tenant lo heredan; nunca `models.Model` directamente |
| `empresa_id` en toda query | Sin `.all()` ni `.filter()` sin empresa |
| `.only()` obligatorio | Toda queryset especifica campos |
| Sin Signals para logica de negocio | Todo en Service Layer |
| Sin `.py` nuevos fuera del Service Layer | Requiere autorizacion explicita del usuario |
| `apps/public/` bloqueado | Requiere RFC + etiqueta `needs-admin-approval` |
| UUID como lookup field | `BaseTenantViewSet` expone UUID; nunca PKs enteras en URLs |
| FK a `perfil.TenantProfile` | Nunca FK a `settings.AUTH_USER_MODEL` desde modelos tenant |
| `py_compile` hook | PostToolUse hook valida toda edicion `.py`. Corregir antes de continuar |

### 4.4. Principios de Idempotencia

Toda operacion de mutacion (creacion/actualizacion) o ingesta de datos debe ser idempotente. La base de datos respalda esto mediante constraints unicos. Los servicios manejan conflictos via Silent Success o Upsert. Prohibido generar errores 500 por duplicados cuando el sistema puede detectarlos semanticamente.

---

## 5. Capa de Integracion Contable Centralizada (Modelo Pull)

### 5.1. Principio Fundamental

Ningun asiento contable se crea directamente desde apps fuente. El `Contabilizador` de `contabilidad` extrae activamente los documentos pendientes. Las apps fuente (`facturas`, `gastos`, `empleados`, `inventario`) no conocen ni importan desde `contabilidad`.

**Patron Push (PROHIBIDO):** app fuente llama funcion de contabilidad.  
**Patron Pull (OBLIGATORIO):** extractor de contabilidad lee app fuente.

### 5.2. Paquete de Integracion

**Ruta:** `apps/tenant/contabilidad/integracion/`

| Modulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador unico — valida, resuelve cuentas, construye y persiste asientos atomicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) a codigo PUC via `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, periodo abierto, documento origen existe |
| `excepciones.py` | Jerarquia `ContabilidadError` y subclases |
| `extractores/base.py` | `AbstractExtractor` — interfaz comun |
| `extractores/gastos.py` | `ExtractorGastos` — extrae `DocumentoSoporte` pendientes |
| `extractores/inventario.py` | `ExtractorInventario` — extrae `MovimientoInventario` pendientes |
| `extractores/facturas.py` | `ExtractorFacturas` — extrae `Factura` ACEPTADA pendientes |
| `extractores/nomina.py` | `ExtractorNomina` — extrae `Devengo` aprobados pendientes |

### 5.3. DTOs — Contrato Inmutable

Los DTOs son frozen dataclasses que encapsulan el contexto economico del documento origen:

- `TransaccionEconomica` — envelope principal con tipo, fecha, tercero (snapshot), lineas y documento origen
- `LineaTransaccion` — concepto, monto y lado del asiento (`'DEBE'` o `'HABER'`)
- `ImpuestoLinea` — tipo, valor y lado (impuestos van siempre a `'HABER'`)
- `TerceroSnapshot` — snapshot del tercero sin FK (inmutable en el tiempo)
- `DocumentoOrigen` — app_label, modelo, id para idempotencia

El campo `empresa_id` no va dentro del DTO — lo inyecta el `Contabilizador` desde su contexto. La idempotencia se garantiza via constraint UNIQUE sobre `documento_origen` en `AsientoContable`.

### 5.4. Numero de Asiento — Formato Canonico

| Tipo | Formato |
|---|---|
| Normal | `ASI-{YYYYMMDD}-{UUID8}` |
| Reversal | `RVER-{YYYYMMDD}-{UUID8}` |

El numero lo genera exclusivamente el `Contabilizador._construir_asiento()`. Prohibido que el caller externo lo provea.

### 5.5. APP_ORIGEN_PREFIJOS — SSoT de Codigos PUC

**SSoT:** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`

Todos los codigos PUC de vinculacion contable para todas las apps de negocio (facturas, clientes, gastos, empleados, inventario, proveedores) se obtienen exclusivamente desde este diccionario. Prohibido hardcodear prefijos en apps fuente.

| App | Ejemplos de prefijos autorizados |
|---|---|
| `facturas` | `1305`, `4135`, `4175`, `2365`, `2368`, `240805` |
| `clientes` | `1305`, `1375`, `4135`, `413505`, `413510` |
| `gastos` | `233505`, `51`, `6`, `2365`, `240810` |
| `empleados` | `5105`, `5110`, `2370`, `25`, `51` |
| `inventario` | `143505`, `1435`, `6135`, `4135`, `51`, `15` |
| `proveedores` | `2205`, `2335`, `2365`, `2805`, `280505` |

### 5.6. Retenciones — ADR-001 Pull Model

**SSoT:** `docs/ADR-001-retention-pull-model.md`

El modelo `Retencion` vive en `contabilidad`. Las apps fuente nunca almacenan montos de retencion directamente. Para crear o consultar retenciones se usa `RetencionesService` de `apps/tenant/contabilidad/services/retenciones_service.py`.

**Endpoints de retenciones:**

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/contabilidad/retenciones/obtener-por-tercero/` | GET | Configuracion de retencion para un NIT dado |
| `/api/v1/contabilidad/retenciones/obtener-por-documento/` | GET | Retenciones de un documento origen |
| `/api/v1/contabilidad/retenciones/` | GET / POST | Listado y creacion |

### 5.7. Activacion de Extractores

Los extractores se invocan exclusivamente desde management commands o tareas Celery periodicas. Nunca desde ViewSets ni Signals.

```bash
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
```

---

## 6. Ecosistema de Agentes de Inteligencia Artificial

### 6.1. Principio de Diseno

El asistente IA es un metodo de entrada rapida para lineas de asiento contable en el flujo Manual On-Demand. Actua como autocompletado inteligente: el contador revisa y confirma antes de generar. La validacion local (cuadratura, nivel 6, `TipoComprobante`) es siempre la fuente de verdad final. La IA nunca persiste datos sin confirmacion explicitica del usuario.

### 6.2. Agentes Especializados por Dominio

| Agent ID | App Label | Conocimiento NIIF Colombia | Modelo |
|---|---|---|---|
| `FacturacionAgent` | `facturas` | CxC (1305), IVA generado (240805), Retefuente (2365xx), ReteICA (2368xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |
| `GastosAgent` | `gastos` | CxP Proveedor (2335xx), IVA descontable (240810), Retefuente (2365xx), Gastos operativos (51xx) | `claude-haiku-4-5-20251001` |
| `NominaAgent` | `empleados` | Salarios (5105xx), Aportes seguridad social (2370xx), Obligaciones laborales (25xx) | `claude-haiku-4-5-20251001` |
| `InventarioAgent` | `inventario` | Inventario (1435xx), CMV (6135xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |

El enrutamiento es automatico: el orquestador lee `app_label` del request y filtra las cuentas PUC disponibles via `APP_ORIGEN_PREFIJOS[app_label]` antes de construir el prompt.

### 6.3. Flujo del Orquestador

```
POST /api/v1/contabilidad/pendientes/asistente-ia/
    |
    +-- AsistenteIAInputSerializer.validate()
    |       <- app_label, modelo, documento_id, subtotal, impuestos, total, tercero
    |
    +-- DocumentosPendientesViewSet.asistente_ia()
    |       <- IsTenantMember + IsTenantAdminOrReadOnly
    |
    +-- ContabilidadBusinessService.sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)
    |       +-- filtrar_cuentas_por_app_origen(qs, app_label) → cuentas nivel-6 del tenant
    |       +-- anthropic.messages.create(model='claude-haiku-4-5-20251001', ...)
    |       +-- Validar cada cuenta: nivel==6, activa==True, empresa_id (DSV)
    |       +-- Validar cuadratura: |Sum(Debe) - Sum(Haber)| < 0.01
    |
    +-- Response({ lineas: [{cuenta_codigo, cuenta_nombre, debe, haber, descripcion}, ...] })
```

### 6.4. Seguridad Post-IA

Toda cuenta sugerida por la IA pasa por cuatro validaciones antes de enviarse al frontend:

1. **Existencia y DSV:** `CuentaContable.objects.filter(empresa_id=empresa_id, codigo=codigo)` — previene IDOR
2. **Nivel auxiliar:** `nivel == 6` — cumple NIIF PYMES
3. **Activa:** `activa == True` — no se usan cuentas desactivadas
4. **Cuadratura:** `|Sum(Debe) - Sum(Haber)| < 0.01` — partida doble garantizada

Si alguna validacion falla, el endpoint devuelve `HTTP 400` con clave `ia` explicando el error. No hay fallback silencioso.

### 6.5. Configuracion y Compliance

| Variable de entorno | Descripcion | Obligatoria |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key del tenant Anthropic | Si |

**Reglas de compliance:**

- Prohibido persistir asientos desde la IA sin confirmacion explicita del usuario
- Prohibido retornar cuentas no validadas contra el DB del tenant
- El boton "Generar Asiento" siempre requiere cuadratura local < 0.01, independiente de la IA
- El asistente IA opera solo en el contexto del ViewSet autenticado (`IsTenantMember` siempre activo)
- Las lineas sugeridas son editables — el contador es la autoridad final
- Los agentes IA no pueden importar directamente de apps fuente — solo operan sobre el contexto de `contabilidad`

### 6.6. Agentes de Codigo (Claude Code)

El archivo `AGENTS.md` es el contexto primario para cualquier agente de codigo (Claude Code, Cursor, Copilot). El archivo `MEMORY.md` en la raiz del proyecto es la fuente canonica del estado actual, decisiones arquitectonicas recientes (ADRs) y progreso activo.

Regla para agentes de codigo: al iniciar cualquier sesion o tarea nueva, leer `MEMORY.md` primero, luego `AGENTS.md`, luego el `.agent/AUDITORIA_FLUJO_*.md` de la app objetivo.

---

## 7. Indice General de Fuentes de Verdad (Mapeo de Apps)

### 7.1. Esquema Public (`SHARED_APPS`)

Documento de referencia: `apps/public/FLUJO_APLICACION_PUBLIC_v3.3.md`

| App | Ruta | Responsabilidad |
|---|---|---|
| `accounts` | `apps/public/accounts/` | Modelo `User` global (AbstractUser), creacion y gestion de usuarios |
| `tenants` | `apps/public/tenants/` | `Client` (django-tenants), `TenantMembership`, invitaciones OTT |
| `impuestos` | `apps/public/impuestos/` | Catalogo DIAN: tarifas IVA, retenciones, RetencionICA |
| `console` | `apps/public/console/` | Consola admin: crear tenants, gestionar membresias, JWT bridge |
| `core` (public) | `apps/public/core/` | Middleware de resolucion de tenant, infraestructura compartida |

### 7.2. Esquema Tenant (`TENANT_APPS`)

> **Regla (AGENTS.md §16):** antes de modificar cualquier app, leer su documento de auditoria. Si no existe, solicitar autorizacion explicita al usuario.

| App | Ruta | Responsabilidad | SSoT (documento de auditoria) |
|---|---|---|---|
| `core` | `apps/tenant/core/` | UI Shell, bridge cross-schema, onboarding, auth JWT | `apps/tenant/core/.agent/AUDITORIA_FLUJO_CORE.md` |
| `empresa` | `apps/tenant/empresa/` | Datos fiscales, logo, configuracion del tenant | `apps/tenant/empresa/.agent/AUDITORIA_EMPRESA.md` |
| `perfil` | `apps/tenant/perfil/` | `TenantProfile` — rol del usuario dentro del tenant | `apps/tenant/perfil/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `facturas` | `apps/tenant/facturas/` | Facturacion electronica DIAN (XML, envio, estados) | `apps/tenant/facturas/.agent/AUDITORIA_FLUJO_COMPLETO_FACTUR.md` |
| `contabilidad` | `apps/tenant/contabilidad/` | PUC NIIF, asientos, movimientos, extractores Pull, agente IA | `apps/tenant/contabilidad/.agent/AUDITORIA_COMPLETA_CONTABILIDAD.md` |
| `gastos` | `apps/tenant/gastos/` | DocumentoSoporte, gastos operativos, retenciones | `apps/tenant/gastos/.agent/AUDITORIA_FLUJO_COMPLETO_GASTOS.md` |
| `inventario` | `apps/tenant/inventario/` | Productos, servicios, activos fijos, Kardex unificado | `apps/tenant/inventario/.agent/AUDITORIA_INVENTARIO.md` |
| `empleados` | `apps/tenant/empleados/` | Nomina colombiana, devengos, contratos, HE y recargos | `apps/tenant/empleados/.agent/AUDITORIA_FLUJO_EMPLEADOS.md` |
| `cotizaciones` | `apps/tenant/cotizaciones/` | Cotizaciones comerciales, items, vinculacion con facturas | `apps/tenant/cotizaciones/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `clientes` | `apps/tenant/clientes/` | CRM basico, terceros clientes, configuracion de retenciones | `apps/tenant/clientes/.agent/AUDITORIA_FLUJO_CLIENTES.md` |
| `proveedores` | `apps/tenant/proveedores/` | Terceros proveedores, documentos soporte | `apps/tenant/proveedores/.agent/AUDITORIA_FLUJO_COMPLETO_PROVE.md` |
| `proyectos` | `apps/tenant/proyectos/` | Gestion de proyectos, tareas diarias con periodo | `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `dashboard` | `apps/tenant/dashboard/` | Vista consolidada y metricas del tenant | — |
| `landing` | `apps/tenant/landing/` | Pagina publica estatica del tenant | `apps/tenant/landing/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `mail` | `apps/tenant/mail/` | Envio de correos transaccionales del tenant | — |
| `mailinbox` | `apps/tenant/mailinbox/` | Bandeja de entrada de mensajes del tenant | — |

### 7.3. Fuentes de Verdad Globales

| SSoT | Ruta | Descripcion |
|---|---|---|
| Arquitectura global | `documentacion/arquitectura_general.md` | Este documento |
| Reglas de desarrollo | `AGENTS.md` | Reglas estrictas e inmutables para todo el proyecto |
| Estado del proyecto | `MEMORY.md` (raiz) | Estado actual, ADRs activos, progreso en curso |
| Rutas API | `config/api_urls.py` | Unica fuente de verdad para endpoints REST |
| Settings | `config/settings.py` | Configuracion Django, JWT, Celery, SHARED/TENANT_APPS |
| Codigos PUC por app | `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS` | Prefijos autorizados por app de negocio |
| Roles de tenant | `apps/tenant/perfil/models.py:TenantProfile.rol` | ADMIN / OPERADOR / VISOR |
| Permisos DRF | `apps/tenant/api/permissions.py` | Unica fuente para importar permisos en ViewSets |
| Autenticacion | `apps/tenant/api/base.py:BaseTenantViewSet` | Dual-Auth centralizado (JWT + Session) |
| Modelo base tenant | `apps/tenant/core/models.py:SintelTenantBaseModel` | Herencia obligatoria para todos los modelos tenant |
| Bridge cross-schema | `apps/tenant/core/services/membership.py` | Unica interfaz autorizada para consultar esquema public |
| ADR Retenciones | `docs/ADR-001-retention-pull-model.md` | Contabilidad owns Retencion, Pull Model |

### 7.4. Comandos Esenciales

```bash
# Docker
make up                  # Levantar servicios (web:8000, db:5432, redis:6379, celery)
make down                # Detener
make logs                # Tail logs del contenedor web
make shell               # Shell en el contenedor web

# Migraciones multi-tenant
make migrate-tenants     # Todos los esquemas tenant
make migrate-shared      # Esquema public
make makemigrations      # Crear migraciones
make check-migrations    # Verificar pendientes

# Calidad de codigo
make audit               # ruff + bandit + django check
make ruff                # Lint + autofix (line-length 100, py3.12)
make bandit              # Escaneo de seguridad

# Tests
make test                # Todos los tests (pytest)
make smoke               # Suite de smoke tests

# Contabilidad
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]

# Tenant
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
docker compose exec web python manage.py createsuperuser

# Validacion pre-PR (obligatorio)
python -m py_compile <archivo.py>
```
