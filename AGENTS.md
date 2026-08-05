# AGENTS.md

---
name: reglas
description: Reglas Core de Arquitectura y Desarrollo - Proyecto SINTEL v3.5.0
---

# [CORE] SINTEL v3.9.1 — Reglas de Arquitectura y Estructura de Proyecto

Estas reglas son **ESTRICTAS, INMUTABLES Y OBLIGATORIAS** para cualquier modificación, refactorización o creación de código en este proyecto. Este archivo debe ser procesado y asimilado antes de implementar cualquier prompt o sugerencia de código.

Este documento refleja el **ADN real** del codebase: patrones, convenciones y estructuras que están siendo implementadas y refinadas **EN DESARROLLO**.

## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.

- **RAZÓN**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACIÓN**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.

> Ver tambien **§29 [ZERO-HARDCODING]** — Norma de Abstraccion que prohíbe nombres propios de tenants en codigo. Aplica a todo el proyecto con la misma prioridad que esta regla.

## [TECH] 1. Tecnologías Implementadas y Stack Base

### Patrones Implementados (Generales por App)

**Frontend (`static/<app_name>/js`):**

- Vanilla JavaScript ES6+ modular, bajo el namespace `window.Sintel.<App_Name>`.
- Orquestador central: `<app_name>.main.js` (controlador raíz, delega a submódulos).
- Submódulos especializados:
   - `<app_name>.api.js`: Única fuente de verdad para URLs y consumo de endpoints directos (Gateway Directo, sin Facade).
   - `<app_name>.table.js`: Inicialización y configuración de Tabulator, definición de columnas y eventos.
   - `<app_name>.ui.js`: Manejo de DOM, ciclo de vida de Offcanvas Bootstrap, integración con HTMX, recolección de formularios y DOM Shield.
   - `<app_name>.utils.js`: Funciones puras de formateo, validación y helpers (sin efectos secundarios).
   - `<app_name>.sync.js` (si aplica): Orquestación de sincronización o tareas en segundo plano, emisión de eventos y feedback UI.
- Integración nativa con HTMX para acciones asíncronas y feedback reactivo.
- Estricto aislamiento por módulo: ningún JS cruza lógica entre modelos.

**Templates (`templates/tenant/<app_name>`):**
- Estructura Feature-Sliced: cada template corresponde a una acción o vista específica (listado, offcanvas crear/editar/detalle).
- Partials dedicados en `partials/` para componentes reutilizables y tablas.
- Prohibido el uso de templates monolíticos o modals compartidos entre modelos.
- Integración directa con endpoints Gateway Directo vía HTMX (`hx-get`).

**Backend Service Layer (`services/`):**
- Modularización estricta por responsabilidad (paquete `services/`):
   - `__init__.py`: Punto de entrada del paquete. **Re-exports EXPLÍCITOS y declarativos** de todos los símbolos públicos. **[PROHIBIDO]** `from .modulo import *` (wildcard imports). Cada símbolo debe estar listado explícitamente: `from .selectors import ClaseA, ClaseB, funcion_c`. Esto garantiza rastreabilidad y previene la exposición accidental de símbolos privados.
   - `crud_service.py`: Acceso a datos puro y persistencia transaccional (`@transaction.atomic`). Sin lógica de negocio.
   - `business_service.py`: Orquestación y lógica de negocio (idempotencia, validaciones semánticas, cálculos, persistencia desde DTO). Sin acceso directo a ViewSets.
   - `selectors.py`: Consultas `GET` optimizadas (read-only). Define tuplas `LIST_FIELDS`, `DETAIL_FIELDS` como SSoT de campos, y clases `<Modelo>Selector` con `@staticmethod` que retornan QuerySets filtrados por `empresa_id` con `.only()`.
   - `services.py`: Fachada estable que reexporta desde `business_service.py` para compatibilidad de imports existentes.
   - se crearara un servicio por modelo item de modelo existente 
   - `api_mixins.py`: `<Modelo>ServiceMixin` que inyecta acceso estandarizado a Selectors, CRUDService y BusinessService desde el ViewSet. Metodos: `get_qs_list()`, `get_qs_detail()`, `service_crear_*()`.
- Todos los métodos son `@staticmethod` o `@classmethod` y stateless.
- El ViewSet hereda de `BaseTenantViewSet` (`apps.tenant.api.base`) y opcionalmente de un `<Modelo>ServiceMixin`.
- Mixins centrales en `apps/tenant/api/mixins.py`: `SintelDSVMixin` (Double Semantic Verification con `get_empresa_id()`) y `SintelServiceMixin` (inyección de `service_class`).
- Prohibido invocar lógica de negocio desde templates, serializers o signals.
- Validación estricta de `empresa_id` y anti-IDOR en toda mutación.
- Documentación y docstrings obligatorios por archivo y función.

El proyecto se rige estrictamente por este stack; queda prohibido sugerir tecnologías o librerías alternativas sin autorización:

1. **Backend & Base de Datos:**
   - **Python & Django:** Framework principal.
   - **Django REST Framework (DRF):** Construcción de APIs (JSON y endpoints HTMX).
   - **django-tenants:** Manejo de esquemas PostgreSQL para aislamiento Multi-Tenant.
   - **PostgreSQL:** Base de datos relacional.
   - **Celery:** Procesamiento asíncrono y tareas en segundo plano.
2. **Frontend & UI:**
   - **HTMX:** Carga dinámica del DOM y peticiones asíncronas desde HTML.
   - **Vanilla JavaScript (ES6+):** Código modular basado en namespaces.
   - **Bootstrap 5:** Sistema de diseño UI (`Offcanvas` para modales e interfaces secundarias).
   - **Tabulator:** Renderizado reactivo de grillas y tablas de datos.

## [ARCH] 2. Principios Generales de Arquitectura (Bounded Contexts & Zero-Trust)

1. **Comunicación Directa y Contextos Delimitados (Bounded Contexts / Gateway Directo):**
   - Toda aplicación debe operar como un dominio aislado.
   - El frontend y los integradores externos deben consumir exclusivamente los endpoints directos de cada app (ej. `/api/v1/<app_name>/` → `apps/tenant/<app_name>/api/`).
   - El patrón Facade monolítico esta ELIMINADO para consumo frontend. Las rutas directas en `config/api_urls.py` son la SSoT. Los facades legacy en `core/api/v1/` estan en proceso de desmontaje y NO deben usarse para nuevas integraciones.
2. **Aislamiento de la Capa de Presentación (`core`) y Bridge al Esquema Publico:**
   - La app `apps/tenant/core` actua como *UI Shell* (contenedor de interfaz) y como **unico puente autorizado** entre las apps tenant y el esquema publico (`apps/public/`).
   - **Prohibido para `core`:** Implementar logica de negocio de dominio, actuar como proxy de datos, orquestar APIs de dominios adyacentes, reescribir rutas de assets o persistir datos de otras apps.
   - **Permitido para `core`:** Alojar helpers globales de infraestructura (ej. `UIManager`, `TabulatorFactory`, manejadores de sesion) en `apps/tenant/core/static/core/js/`.
   - **Permitido para `core`:** Contener el modulo bridge `apps/tenant/core/services/membership.py` que encapsula TODA interaccion con `apps.public` (ver Seccion 17).
3. **Aislamiento de Datos SSoT (Tenant-Isolation):** Todo modelo de base de datos que pertenezca a un inquilino DEBE heredar de una clase base abstracta (`SintelTenantBaseModel`) que inyecte y valide la clave de partición (`empresa_id`) a nivel de ORM.
4. **Idempotencia por Diseño:** Toda operación de mutación (creación/actualización) o ingesta de datos DEBE ser idempotente. La base de datos debe respaldar esto mediante constraints únicos a nivel de BD; los servicios deben manejar los conflictos de forma transparente (permitiendo un *Silent Success* o *Upsert*).
5. **Centralización del Aprovisionamiento (Core SSoT):** Todo el flujo de inicio de sesión de nuevos tenants privados, validación OTT y su interfaz de bienvenida (Onboarding) pertenecen EXCLUSIVAMENTE a la app `core` (`apps/tenant/core`). La app `landing` está despojada de responsabilidades de aprovisionamiento o seguridad, quedando solo como presentación estática.

## [INFO] 3. Única Fuente de Verdad Documental (SSoT)

1. **PASO INICIAL OBLIGATORIO:** Antes de ejecutar CUALQUIER cambio en una app, se DEBE consultar SIEMPRE de forma inicial el documento de flujo de la misma. Todas las aplicaciones tienen este documento en su directorio `.agent/`. (Ejemplo: `apps/tenant/clientes/.agent/AUDITORIA_FLUJO_CLIENTES.md`).
2. **Documentación Global:** `documentacion/arquitectura_general.md` es la referencia suprema para infraestructura.
3. **Flujo por Aplicación (Modularizado):** Cada `apps/<app_name>/` DEBE contener una carpeta `.agent/` con el archivo de auditoría principal.
4. **Estructura de Documentación Modular:**
   - Portal SSoT: `apps/<app_name>/.agent/AUDITORIA_FLUJO_*.md`
   - Documentos de Soporte: `apps/<app_name>/.agent/docs/` (Flow Maps, Business Logic, Microtasks).
   - Habilidades y Scripts: `apps/<app_name>/.agent/skills/` (Automatizaciones locales).
5. **Gestión de Documentos:** Los archivos `.md` globales residen en `documentacion/`. Los específicos de app residen en su propia carpeta `.agent/docs/`.

## [BACKEND] 4. Capa de Datos y Optimización Backend (Zero Waste)

1. **Cero Creación de Archivos `.py` no Autorizados:** Queda PROHIBIDO crear nuevos archivos `.py` fuera de la estructura de Service Layer establecida (`services/selectors.py`, `services/crud_service.py`, `services/business_service.py`, `services/api_mixins.py`, `services/__init__.py`). Para la app `contabilidad`, la extensión autorizada adicional es `integracion/extractores/` (ver §18). Cualquier otro archivo nuevo requiere autorización explícita.
2. **Restricción de Ambientes (`apps/public/`):** Estrictamente PROHIBIDO modificar, refactorizar o crear archivos dentro de `apps/public/` sin la aprobación explícita (requiere RFC/Issue y etiqueta `needs-admin-approval`). Toda lógica nueva debe acoplarse a la estructura existente.
3. **Prohibición de `views.py` Tradicionales:** No usar el archivo `views.py` legacy para lógica de negocio.
4. **Multi-Tenant Estricto (Zero-Trust SaaS):** Prohibido realizar consultas a modelos sin filtrar por la empresa del tenant (`empresa` o `empresa_id`) en las `TENANT_APPS`.
5. **Optimización Estricta de Consultas (Zero Waste):**
   - **ESTRICTAMENTE PROHIBIDO** el uso de `.all()`, o `.filter()` sin encadenar un `.only()` o `.defer()`.
   - Toda consulta DEBE especificar explícitamente los campos necesarios para minimizar la saturación de memoria y cuellos de botella en la red.
   - **Patrón DRF obligatorio:** `queryset = Model.objects.none()` a nivel de clase + override en `get_queryset()` con `.only()`/`.defer()` según la acción.
   - **Joins obligatorios:** Toda consulta que acceda a campos de modelos relacionados DEBE encadenar `select_related('campo')` (FK / OneToOne) o `prefetch_related('campo')` (M2M / FK inversa) para evitar el problema N+1. Prohibido acceder a `obj.fk.campo` sin `select_related` previo.
6. **Desacoplamiento Operativo:** Las relaciones (`ForeignKey`) que referencien operadores del tenant DEBEN apuntar al modelo del perfil operativo (`'perfil.TenantProfile'`), NUNCA a `settings.AUTH_USER_MODEL`. Esto aísla la autenticación global de la lógica del negocio del tenant.
7. **Cero Efectos Secundarios Ocultos (Cero Signals):** Se prohíbe el uso de *Signals* nativas de Django para ejecutar lógica de negocio. Toda mutación dependiente debe ser orquestada explícitamente en la Capa de Servicios.

## [CRUD-E2E] 5. Ciclo de Vida CRUD End-to-End (Service Layer Arquitecture)

Para garantizar un CRUD completo y seguro, el flujo de procesamiento de datos debe ser estrictamente unidireccional y desacoplado:

1. **Captura y Protección UI (Frontend):**
   - El payload se recopila a través de scripts especializados (`<app>_form.js`).
   - Obligatorio aplicar el "DOM Shield": remover temporalmente atributos `name` de selectores visibles y capturar únicamente valores crudos/ForeignKeys desde inputs ocultos (`<input type="hidden">`).
2. **Recepción y Enrutamiento (View/ViewSet):**
   - Responsable ÚNICAMENTE de la ingesta HTTP. Actúa **SOLO** como enrutador.
   - Delega la validación inicial sintáctica y de tipos a los Serializers/DTOs.
   - Las consultas ORM deben canalizarse a través de `ServiceMixin.get_qs_list()`/`get_qs_detail()` o Selectors. Minimizar imports directos de modelos en ViewSets.
3. **Servicio de Negocio (Business Service):**
   - El ViewSet invoca métodos del `<Modelo>ServiceMixin` que apuntan a `business_service.py`.
   - Recibe datos validados y el contexto de seguridad inyectado (`empresa_id`).
   - Aplica **Doble Verificación Semántica (Double Semantic Verification)**: Valida que todas las entidades/ForeignKeys referenciadas en el payload pertenezcan al tenant actual (Prevención IDOR).
   - Ejecuta reglas de dominio, cálculos matemáticos y validación de idempotencia.
4. **Servicio de Persistencia Transaccional (CRUD/Data Service):**
   - Única capa con permisos para interactuar con la base de datos a nivel de escritura (`crud_service.py`).
   - Toda creación/mutación jerárquica (operaciones compuestas o Maestro-Detalle) DEBE estar obligatoriamente envuelta en bloques transaccionales atómicos (`@transaction.atomic`).
5. **Interfaz Reactiva y UI Feedback:**
   - Tras la persistencia, el backend retorna estados limpios 200/201 (JSON o HTMX OOB Swap).
   - El frontend intercepta la respuesta, muta el DOM o actualiza reactivamente las grillas en memoria (`table.replaceData()` en Tabulator), emite notificaciones (`UIManager.notifySuccess`) y libera recursos, evitando recargas completas.

## [UI] 6. Interfaz de Usuario y Frontend (UI SSoT)

Regla crítica de ubicación de assets: TODOS los archivos `.html` y `.js` deben residir dentro del núcleo (nucleus) de la aplicación a la que pertenecen.

- **Ruta obligatoria para apps tenant:**
   - Templates: `apps/tenant/<app_name>/templates/tenant/<app_name>/` (prefijo `tenant/` en la ruta de templates).
   - JS estático: `apps/tenant/<app_name>/static/<app_name>/js/`
   - Carga de assets: Cada app define un template `assets_<app_name>.html` que centraliza la inclusión de sus scripts y estilos.
- **Ruta obligatoria para apps public (SHARED_APPS):**
   - Templates: `apps/public/<app_name>/templates/<app_name>/`
   - JS estático: `apps/public/<app_name>/static/<app_name>/js/`
- **Excepciones controladas:** Helpers globales de infraestructura en `apps/tenant/core/static/core/js/common/` (ej. `ui-manager.js`, `tabulator.factory.js`, `notyf.init.js`).
- **HTMX y Server-Driven UI:** Las mutaciones HTMX deben originarse desde templates y endpoints ligados al mismo app. Al mover un módulo, actualizar siempre los `include` y referencias `static`.

## [ARCHITECTURE] 7. Arquitectura Feature-Sliced Design (FSD)

**PRINCIPIO FUNDAMENTAL:** Cada modelo de base de datos debe tener su propio ecosistema completo e independiente.

### 7.1. Estructura por Modelo (Ecosistema Completo)
1. **Templates HTML:**
   - `offcanvas_crear_{modelo}.html`, `offcanvas_editar_{modelo}.html`, `offcanvas_detalle_{modelo}.html`, `list_{modelo}.html`.
   - Partials reutilizables en subcarpeta `partials/` (ej. `partials/table.html`, `partials/assets_{app}.html`).
   - **PROHIBIDO:** Archivos monolíticos como `modals.html`.
2. **Scripts JavaScript (Patrón `features/`):**
   - `<app_name>.api.js` (SSoT de URLs y endpoints a nivel raíz del JS de la app).
   - Subcarpeta `features/` con archivos por modelo:
     - `{modelo}_list.js` (Listado y tabla Tabulator).
     - `{modelo}_editor.js` (Formularios crear/editar vía Offcanvas).
   - Variante alternativa por app: `{app_name}.module.js` (orquestador central), `{app_name}.list.js`, `{app_name}.editor.js`, `{app_name}.utils.js`.
   - **PROHIBIDO:** Scripts compartidos entre modelos no relacionados.
3. **API Endpoints (HTMX Actions):**
   - Los Offcanvas DEBEN usar `hx-get` apuntando a `render-offcanvas/crear/`, `editar/` o `detalle/`.
   - Feedback de error inyectado localmente en el contenedor.

## [WIZARD] 8. Patrón Wizard y Flujo de Estado

1. **Asistente en Memoria:** La fase inicial de recolección de configuraciones complejas NO guarda en BD.
2. **Traspaso por SessionStorage:** El JS empaqueta el payload JSON en `sessionStorage`, lanza por HTMX el Editor principal, el cual lee el storage para autollenar antes de permitir el guardado definitivo.

## [SHIELD] 9. Principio Zero Trust (Validación y Cálculos UI)

1. **Validación Explícita:** Nunca confiar en inputs de usuario. Normalizar numéricamente (`parseFloat(value) || 0`) para evitar propagar `NaN`.
2. **SSoT en Cálculos:** Las validaciones matemáticas en el JS deben coincidir con la tolerancia del backend.
3. **Serialización JSON Dura:** Los formularios Maestro-Detalle deben enviar JSON puro. Evitar que el navegador envíe el literal `'[object Object]'`.

## [ALERT] 10. Manejo de Errores y Logging

1. **Logging Obligatorio:** Todo error debe incluir contexto: `[modulo:accion]`.
2. **Aislamiento de Errores UI:** Las fallas de la API (DRF) deben delegarse EXCLUSIVAMENTE a `UIManager.handleError`, mapeando el array de `missing_fields` del backend.

## [ASYNC] 11. Procesamiento Asíncrono, DLQ y Alto Rendimiento

1. **Desacoplamiento de Carga Pesada:** Las tareas masivas, cálculos sobre datos históricos, integraciones de terceros o envíos masivos DEBEN despacharse obligatoriamente a *workers* asíncronos en Celery vía `.delay()`.
2. **Eficiencia en Workers:** Las tareas asíncronas deben diseñarse para consumir la menor cantidad de memoria posible. Deben operar en lotes (*batching*) cuando interactúen con la base de datos y evitar cargar estructuras de datos masivas en RAM.
3. **Tolerancia a Fallos y DLQ (Dead Letter Queues):**
   - Toda tarea encolada en Celery debe definir políticas de reintentos (`max_retries`).
   - Al agotar los reintentos y fallar definitivamente, el *worker* debe capturar el error y el payload original, insertándolo en un registro de base de datos (`FailedTenantTask`). Esto permite observabilidad y reenfilado manual/automatizado sin congelar ni bloquear los workers principales.

## [HTMX-ADVANCED] 12. Server-Driven UI y Out of Band Swaps (OOB)

1. **Reactividad:** Tabulator y otras interfaces deben suscribirse nativamente a respuestas HTMX (`HX-Trigger`).
2. **Transacciones OOB:** Cuando un modal HTMX realiza un POST exitoso que afecta elementos externos, priorizar entregar una mutación DOM fuera de banda (`hx-swap-oob="true"` o `HX-Trigger`).

## [SaaS-DEFENSE] 13. Ciberseguridad Defensiva y Prevención IDOR

1. **Verificación Continua en DML:** Nunca confiar en identificadores (IDs) proporcionados por el cliente. Todo endpoint de mutación (POST/PUT/PATCH/DELETE) debe validar que las entidades referenciadas pertenezcan al tenant autenticado (`empresa=request.user.perfil.empresa`).
2. **Implementación via DSV:** La Doble Verificación Semántica (definida en Sección 5.3) es el mecanismo obligatorio. Se ejecuta en `business_service.py` antes de persistir.
3. **Protección Horizontal:** Estrictamente prohibido confiar ciegamente en IDs provistos en requests HTTP sin validarlos contra el tenant.

## [CORE-DB] 14. Herencia Obligatoria de Modelos SSoT

1. **SintelTenantBaseModel:** Todos los modelos del esquema tenant DEBEN heredar estrictamente de `SintelTenantBaseModel` importado desde `apps.tenant.core.models`.
2. **Prohibición de Herencia Nativa:** Queda prohibido heredar de `models.Model` directamente.
3. **Campos inyectados automáticamente por `SintelTenantBaseModel`:**
   - `empresa`: `ForeignKey('empresa.Empresa', on_delete=PROTECT, null=False, blank=False, db_index=True)`.
   - `created_at`: `DateTimeField(auto_now_add=True, db_index=True)` - Timestamp de creación.
   - `updated_at`: `DateTimeField(auto_now=True, db_index=True)` - Timestamp de última modificación.
4. **Índices obligatorios heredados:** `[empresa]` y `[empresa, -created_at]`. Los modelos hijos PUEDEN añadir índices adicionales en su `Meta.indexes`.
5. **Protección en `save()`:** El modelo base sobrescribe `save()` para lanzar `ValueError` si `empresa_id` es `None`, evitando registros huérfanos.
6. **UUID como Lookup Field:** `BaseTenantViewSet` (`apps/tenant/api/base.py`) define `lookup_field="uuid"` y `lookup_url_kwarg="uuid"`. Todos los ViewSets tenant heredan de esta clase para evitar exposición de PKs internos en URLs públicas.

## [SECURITY] 15. Seguridad, Autenticacion JWT y Roles (Dual-Auth Pattern)

### 15.1. Dual-Auth Centralizado (JWT + Session)

1. **SSoT de Autenticacion:** `BaseTenantViewSet` (`apps/tenant/api/base.py`) define `authentication_classes = [JWTAuthentication, SessionAuthentication]` como unica fuente de verdad. Todos los ViewSets tenant heredan Dual-Auth automaticamente.
   - **[PROHIBIDO]** sobrescribir `authentication_classes` en ViewSets hijos. La autenticacion se hereda de `BaseTenantViewSet` o del DRF global default (`config/settings.py` `DEFAULT_AUTHENTICATION_CLASSES`).
   - **Excepciones explicitas:** `CoreAuthViewSet` (login/logout/from-session) usa `[SessionAuthentication]` exclusivamente. `TenantInfoView` usa `authentication_classes = []` (endpoint publico).
2. **Orden de Prioridad:** DRF evalua `JWTAuthentication` primero (header `Authorization: Bearer`). Si no hay token o es invalido, usa `SessionAuthentication` (cookies). Esto permite que el mismo endpoint sirva tanto a clientes API/moviles como al workspace navegador.
3. **Bridge Session-to-JWT:** El endpoint `GET /api/v1/core/auth/from-session/` genera tokens JWT validos a partir de la sesion activa, sin requerir re-autenticacion por credenciales.

### 15.2. Configuracion JWT (`djangorestframework-simplejwt`)

1. **Libreria:** `djangorestframework-simplejwt[blacklist]>=5.3`.
2. **Parametros SIMPLE_JWT** (`config/settings.py`):
   - `ACCESS_TOKEN_LIFETIME`: 15 minutos.
   - `REFRESH_TOKEN_LIFETIME`: 7 dias.
   - `ROTATE_REFRESH_TOKENS`: `True` (nuevo refresh en cada renovacion).
   - `BLACKLIST_AFTER_ROTATION`: `True` (invalida refresh anterior).
   - `ALGORITHM`: `HS256` con clave de 32+ bytes (`JWT_SECRET_KEY` env var).
   - `AUTH_HEADER_TYPES`: `('Bearer',)`.
3. **Endpoints de Token** (registrados en `config/api_urls.py` y `config/urls_tenant.py`):
   - `POST /api/token/` - Obtener par access/refresh.
   - `POST /api/token/refresh/` - Renovar access token.
   - `POST /api/token/verify/` - Verificar validez de token.

### 15.3. Frontend JWT (`window.jwtAuth`)

1. **Helper Global:** El objeto `window.jwtAuth` (definido en `apps/public/console/static/js/jwt-auth.js`) gestiona tokens en `localStorage`.
2. **Metodo correcto para inyectar Bearer en headers:**
   ```javascript
   const token = window.jwtAuth?.getAccessToken?.();
   if (token) {
       headers['Authorization'] = `Bearer ${token}`;
   }
   ```
   - **[PROHIBIDO]** usar `window.jwtAuth.token` o `window.jwtAuth?.token` (la propiedad `.token` NO existe).
   - **Metodo asincrono (con auto-refresh):** `await window.jwtAuth.getValidAccessToken()` verifica, refresca y retorna el token. Usar cuando el caller ya es `async`.
3. **Inyeccion Automatica:** `TabulatorFactory` inyecta automaticamente `Authorization: Bearer` via `window.jwtAuth`. Los modulos `<app>.api.js` usan `getHeaders()` con `getAccessToken()`.

### 15.4. Jerarquia de Roles (`TenantProfile.rol` = SSoT)

1. **SSoT de Roles:** `TenantProfile.rol` (`apps/tenant/perfil/models.py`) es la UNICA fuente de verdad para permisos basados en rol dentro del tenant. `TenantMembership.rol` (esquema publico) se usa SOLO para verificar membresia cross-schema via el Bridge.
2. **Roles definidos:**
   - `ADMIN` - Acceso total: CRUD completo, asignar roles, configuraciones de empresa.
   - `OPERADOR` - Lectura + escritura limitada (segun app/modelo).
   - `VISOR` - Solo lectura.
3. **Auto-Creacion:** Al hacer login (`CoreAuthViewSet.login()`), si el usuario no tiene `TenantProfile` en el tenant actual, se crea automaticamente con rol `VISOR`.

### 15.5. Permisos Materializados (`apps/tenant/api/permissions.py`)

Todas las apps tenant DEBEN importar permisos desde este modulo centralizado.

1. **Membresia Cross-Schema:**
   - `IsTenantMember`: Verifica membresia activa (`TenantMembership`) en el tenant actual via Core Membership Bridge (Seccion 17). **OBLIGATORIO** en todo ViewSet que herede de `BaseTenantViewSet`.
2. **Basados en TenantProfile.rol (DSV):**
   - `HasTenantRole`: Permiso generico. El ViewSet define `required_roles = ['ADMIN', 'OPERADOR']` y el permiso valida que `perfil.rol` este en la lista. Aplica Double Semantic Verification (perfil.empresa_id == empresa activa).
   - `IsTenantProfileAdmin` / `IsTenantAdmin`: Requiere rol `ADMIN` con DSV completo.
   - `IsTenantProfileOperadorOrAdmin`: Requiere rol `ADMIN` o `OPERADOR` con DSV completo.
   - `IsTenantAdminOrReadOnly`: Lectura para todo autenticado; escritura solo para `ADMIN`. Compatible con ViewSets que usan `_check_enforced_mode`.
3. **Patron de uso en ViewSets:**
   ```python
   permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
   ```
   - **[PROHIBIDO]** importar permisos desde `apps/tenant/empresa/permissions.py` (wrapper legacy deprecado).
   - **[PROHIBIDO]** usar `TenantMembership.rol` para decisiones de permisos dentro del tenant.

### 15.6. Autenticacion en Desarrollo

1. `UnsafeSessionAuthentication` (`apps/tenant/api/authentication.py`): Omite validacion CSRF solo cuando `DEBUG=True`. En produccion se usa `SessionAuthentication` estandar.
2. **[PROHIBIDO]** sobrescribir `get_authenticators()` en ViewSets hijos para inyectar `UnsafeSessionAuthentication` directamente. Esto es deuda tecnica (DEUDA-01). La autenticacion es responsabilidad de `BaseTenantViewSet` via `DEFAULT_AUTHENTICATION_CLASSES`. Si se detecta un override de `get_authenticators()` en un ViewSet hijo, eliminarlo.

## [GOVERNANCE] 16. Reglas de Gobernanza por Aplicación

1. **Módulo Privados (`apps/tenant/nombre_app`):**
   - **Autorización Obligatoria**: Antes de realizar cualquier modificación, refactorización o creación de código en este módulo, se DEBE solicitar autorización y aprobación explícita al USUARIO.
   - **Lectura Previa SSoT**: Es OBLIGATORIO leer el documento de auditoría `.agent/` de la app (el nombre exacto varía por app — ver la tabla en `documentacion/arquitectura_general.md` §10.2, DOC-M1) antes de proponer cambios. Toda modificación debe estar alineada con la arquitectura allí documentada.

## [BRIDGE] 17. Aislamiento de Esquema Publico via Core Membership Bridge

**REGLA FUNDAMENTAL DE AISLAMIENTO CROSS-SCHEMA:**

1. **SSoT del Bridge:** El modulo `apps/tenant/core/services/membership.py` es la UNICA interfaz autorizada para que las apps tenant consulten datos del esquema publico (`apps.public`). Este modulo encapsula el cambio de esquema PostgreSQL de forma segura mediante un context manager (`_PublicSchemaContext`).
2. **Prohibicion de Imports Directos:**
   - **ESTRICTAMENTE PROHIBIDO** que cualquier app tenant distinta de `core` importe directamente desde `apps.public`. Esto incluye `apps.public.tenants.models`, `apps.public.tenants.utils`, o cualquier otro submodulo de `apps/public/`.
   - Ejemplo PROHIBIDO: `from apps.public.tenants.models import TenantMembership` en `apps/tenant/gastos/`.
   - Ejemplo CORRECTO: `from apps.tenant.core.services.membership import check_membership` en `apps/tenant/gastos/`.
3. **Operaciones Expuestas por el Bridge (API Surface):**
   - `check_membership(user, empresa)` - Verifica membresia activa. Retorna `TenantMembership` o `None`.
   - `check_membership_exists(user, empresa)` - Retorna `bool` para verificacion rapida.
   - `check_admin_membership(user, empresa)` - Verifica membresia con rol ADMIN.
   - `check_primary_admin(empresa)` - Retorna el `TenantMembership` del administrador primario.
   - `get_user_role(user, empresa)` - Retorna el string del rol (`ADMIN`, `STAFF`, `OPERADOR`) o `None`.
   - `get_primary_domain(empresa)` - Retorna el dominio primario del tenant.
   - `verify_invitation(token)` - Valida un token de invitacion y retorna la invitacion activa o `None`.
4. **Regla de Extension:** Si una app tenant necesita una nueva consulta al esquema publico, se DEBE agregar una nueva operacion al bridge (`membership.py`). Queda PROHIBIDO crear imports directos como alternativa.
5. **Validacion Automatizada:** El tool `audit_bridge_isolation` del MCP server (`sintel_agent_unified.py`) escanea imports en todas las apps tenant para detectar violaciones a esta regla. Toda PR debe pasar esta auditoria con cero violaciones.
6. **Excepciones:** Solo `apps/tenant/core/` y `apps/tenant/api/` (permisos centrales) pueden importar desde `apps.public`. Ninguna otra app tenant tiene esta autorizacion.

## [CONTAB] 18. Capa de Integración Contable Centralizada (v3.5 — Modelo Pull / Extractores)

**PRINCIPIO:** Todo asiento contable es generado EXCLUSIVAMENTE por el `Contabilizador`. Ninguna app puede crear `AsientoContable` ni `MovimientoContable` directamente. Las apps fuente NO conocen ni dependen de `contabilidad` — la extracción es activa (Pull), no pasiva (Push).

### 18.1. Paquete de Integración (`apps/tenant/contabilidad/integracion/`)

| Módulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador único — valida, resuelve cuentas, construye y persiste asientos atómicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) a código PUC vía `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, período abierto, documento origen existe |
| `excepciones.py` | Jerarquía `ContabilidadError` y subclases |
| `extractores/base.py` | `AbstractExtractor` — interfaz común (ver §18.3) |
| `extractores/gastos.py` | `ExtractorGastos` — extrae `DocumentoSoporte` pendientes |
| `extractores/inventario.py` | `ExtractorInventario` — extrae `MovimientoInventario` pendientes |
| `extractores/facturas.py` | `ExtractorFacturas` — extrae `Factura` ACEPTADA pendientes |
| `extractores/nomina.py` | `ExtractorNomina` — extrae `Devengo` aprobados pendientes |

### 18.2. DTOs — Contrato Inmutable

```python
TransaccionEconomica(
    tipo=TipoTransaccion.COMPRA_GASTO,
    fecha=date(2026, 5, 3),
    tercero=TerceroSnapshot(...),          # Snapshot, sin FK
    lineas=[LineaTransaccion(...)],
    documento_origen=DocumentoOrigen(...)  # Para idempotencia
)
LineaTransaccion(concepto='GASTO_OPERATIVO', monto=..., lado='DEBE')   # default='DEBE'
ImpuestoLinea(tipo='RETEFUENTE', valor=..., lado='HABER')              # default='HABER'
```

- **`lado`**: controla columna del asiento (`'DEBE'` o `'HABER'`). OBLIGATORIO para cuadratura.
- **Idempotencia**: `documento_origen` mapea a `AsientoContable.documento_origen_*`. Constraint UNIQUE en BD.
- **`empresa_id`**: PROHIBIDO pasarlo dentro del DTO — lo inyecta el `Contabilizador` desde su contexto.

### 18.3. Patrón de Integración — Modelo Pull (Extractores)

**Arquitectura:** `contabilidad` extrae activamente de apps fuente. Las apps fuente no conocen ni importan de `contabilidad`.

```python
# En apps/tenant/contabilidad/integracion/extractores/base.py
class AbstractExtractor(ABC):
    def __init__(self, empresa_id: int):
        self.empresa_id = empresa_id
        self.contabilizador = Contabilizador(empresa_id)

    @abstractmethod
    def extraer_pendientes(self) -> list[TransaccionEconomica]: ...

    def contabilizar_pendientes(self) -> dict:
        resultados = {'contabilizados': 0, 'errores': [], 'omitidos': 0}
        for dto in self.extraer_pendientes():
            try:
                self.contabilizador.contabilizar(dto)
                resultados['contabilizados'] += 1
            except Exception as e:
                resultados['errores'].append({'origen': str(dto.documento_origen), 'error': str(e)})
        return resultados
```

**Activación:** Extractores se invocan desde management commands (`manage.py backfill_asientos_gastos`) o tareas Celery periódicas. Nunca desde ViewSets ni Signals.

**Detección de pendientes:** Cada extractor usa `Contabilizador.existe_asiento_para(app_label, modelo, id)` para filtrar documentos ya contabilizados. La idempotencia queda delegada al `Contabilizador` — el extractor no la gestiona.

### 18.4. Cuadratura Obligatoria (Ejemplo COMPRA_GASTO)

```
DEBE 51xxxx Gasto              [subtotal]
HABER 236540 Retefuente        [retefuente]  (si > 0)
HABER 236801 ReteICA           [reteica]     (si > 0)
HABER 233595 CXP Proveedor     [total neto]
TOTAL DEBE == TOTAL HABER == subtotal
```

### 18.5. Numero de Asiento — Formato Canonico

- Normal: `ASI-{YYYYMMDD}-{UUID8}` — generado por `Contabilizador._construir_asiento()`.
- Reversal: `RVER-{YYYYMMDD}-{UUID8}`.
- PROHIBIDO que el caller externo provea el número.

### 18.6. Prohibiciones

- PROHIBIDO crear `AsientoContable`/`MovimientoContable` directamente desde ViewSets, Signals o apps fuente.
- PROHIBIDO que apps fuente (`gastos`, `facturas`, `inventario`, `empleados`) importen desde `apps.tenant.contabilidad`.
- PROHIBIDO hardcodear códigos PUC en apps fuente — usar `cuenta_hint` o `ReglaContable`.
- PROHIBIDO usar `lado='DEBE'` para impuestos/retenciones (su natural es `'HABER'`).
- PROHIBIDO el patrón Push (app fuente llama función de contabilidad) — solo Pull (extractor de contabilidad lee app fuente).

### 18.7. [CRITICAL] APP_ORIGEN_PREFIJOS — Single Source of Truth (SSoT) para Códigos PUC

**REGLA MANDATORIA:** Todos los códigos PUC (Plan de Cuentas) de vinculación contable para **TODAS las apps de negocio** (facturas, clientes, gastos, empleados, inventario, proveedores) DEBEN **ÚNICAMENTE** obtenerse desde:

```
apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS
```

#### 18.7.1. Estructura Centralizada

```python
# SSoT — Single Source of Truth
APP_ORIGEN_PREFIJOS: dict = {
    'facturas': ['130505', '130510', '1305', '135515', ..., '4175', '418', ...],
    'clientes': ['1305', '130505', '4135', '413505', '413510', '1375'],
    'gastos': ['233505', '233550', ..., '51', '6'],
    'empleados': ['5105', '5110', ..., '51', '25', '2370', ...],
    'inventario': ['143505', '143510', '1435', '613505', '6135', '4135', '51', '15'],
    'proveedores': ['2205', '220501', '2335', '233505', '2365', '236505-540', '2805', '280505'],
}

def filtrar_cuentas_por_app_origen(qs, app_origen: str):
    """Aplica filtro de seguridad por app — permite solo prefijos autorizados."""
    prefijos = APP_ORIGEN_PREFIJOS.get(app_origen, [])
    # ...
```

#### 18.7.2. Cómo Acceder a los Prefijos (Patrones Autorizados)

**PATRÓN 1: ViewSet — Búsqueda de Cuentas (Frontend → API)**

```python
# En contabilidad/api/viewsets.py:CuentaContableViewSet

def get_queryset(self):
    qs = CuentaContableSelector.get_qs_list()
    
    # Frontend envía: ?app_origen=inventario&codigo_prefix=51
    app_origen = self.request.query_params.get('app_origen', '').strip()
    if app_origen:
        qs = filtrar_cuentas_por_app_origen(qs, app_origen)  # ← Usa SSoT
    
    codigo_prefix = self.request.query_params.get('codigo_prefix', '').strip()
    if codigo_prefix:
        qs = qs.filter(codigo__startswith=codigo_prefix)
    
    return qs
```

**PATRÓN 2: Frontend JavaScript — Búsqueda Autocomplete**

```javascript
// En inventario.api.js
searchCuentas: async (query, options = {}) => {
  const params = {
    search: query,
    app_origen: 'inventario',  // ← Declara su app_origen
    activa: 'true'
  };
  if (options.codigoPrefix) {
    params.codigo_prefix = options.codigoPrefix;
  }
  return w.http('GET', '/api/v1/contabilidad/cuentas-contables/', params);
}
```

El backend resuelve automáticamente qué prefijos son válidos (`APP_ORIGEN_PREFIJOS['inventario']`).

**PATRÓN 3: Backend Service — Extracción de Cuentas**

```python
# En gastos/services/business_service.py o integracion/extractores/gastos.py

from apps.tenant.contabilidad.services.selectors import (
    APP_ORIGEN_PREFIJOS,
    filtrar_cuentas_por_app_origen,
    CuentaContableSelector
)

# Obtener cuentas permitidas para gastos
prefijos_gastos = APP_ORIGEN_PREFIJOS['gastos']  # ← Lee desde SSoT
qs = CuentaContableSelector.get_qs_list()
qs = filtrar_cuentas_por_app_origen(qs, 'gastos')

# Ahora qs contiene SOLO cuentas con prefijos autorizados para gastos
for cuenta in qs:
    print(f"{cuenta.codigo} - {cuenta.nombre}")
```

#### 18.7.3. Prohibiciones Estrictas

**❌ PROHIBIDO — Hardcoding de Prefijos:**

```python
# ❌ INCORRECTO — Hardcoded prefixes scattered in code
GASTOS_PREFIJOS = ['51', '52', '53']  # En gastos/models.py
FACTURAS_PREFIJOS = ['4135', '4175']   # En facturas/api/viewsets.py

def buscar_cuentas(app):
    if app == 'gastos':
        return CuentaContable.objects.filter(codigo__in=GASTOS_PREFIJOS)
```

**✅ CORRECTO — Centralizado en APP_ORIGEN_PREFIJOS:**

```python
# ✅ CORRECTO — Single source of truth
from apps.tenant.contabilidad.services.selectors import (
    APP_ORIGEN_PREFIJOS,
    filtrar_cuentas_por_app_origen
)

def buscar_cuentas(app_origen):
    qs = CuentaContable.objects.all()
    return filtrar_cuentas_por_app_origen(qs, app_origen)
```

**❌ PROHIBIDO — Hardcodear en Fixtures o Data Seeds:**

```python
# ❌ INCORRECTO — Seeds con prefijos hardcoded
factories.CuentaFactory(codigo='5100', nombre='Gastos')
factories.CuentaFactory(codigo='5105', nombre='Sueldos')
```

**✅ CORRECTO — Validar contra SSoT:**

```python
# ✅ CORRECTO — Código validado contra APP_ORIGEN_PREFIJOS
prefijos_permitidos = APP_ORIGEN_PREFIJOS['empleados']
assert any(codigo.startswith(p) for p in prefijos_permitidos), \
    f"Código {codigo} no está permitido para empleados"
```

#### 18.7.4. Actualización de Prefijos (Proceso Obligatorio)

Cuando se agreguen nuevos códigos PUC para una app:

1. **Identificar:** ¿Qué app de negocio necesita el nuevo código? (ej: inventario necesita depreciación → '51')
2. **Centralizar:** Agregar el código ÚNICAMENTE a `APP_ORIGEN_PREFIJOS[<app>]` en `selectors.py`
3. **Documentar:** Describir en comentario inline por qué ese app necesita ese código
4. **Validar:** Verificar que el nuevo prefijo no conflictúe con otra app
5. **Testear:** Probar búsqueda desde frontend para verificar que aparecen resultados

**NO hacer:**
- ❌ Crear tabla `AppPrefixes` nueva
- ❌ Agregar campo en modelo `CuentaContable` para prefijos por app
- ❌ Distribuir prefijos en múltiples archivos

#### 18.7.5. Auditoría Periódica

**Verificación automática:** Ejecutar anualmente (o al agregar apps nuevas):

```bash
# Script: tools/audit_app_origen_prefijos.py
# Verifica que NO haya hardcoded prefijos en otras apps
grep -r "PREFIJOS\|codigo__in\|codigo__startswith" \
  --include="*.py" \
  apps/tenant/{facturas,clientes,gastos,empleados,inventario,proveedores} \
  | grep -v "contabilidad/services/selectors.py"
```

Si encuentra matches → error, requiere migración a `APP_ORIGEN_PREFIJOS`.

#### 18.7.6. Suma

- **Donde viven:** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`
- **Cómo se accede:** `from apps.tenant.contabilidad.services.selectors import APP_ORIGEN_PREFIJOS, filtrar_cuentas_por_app_origen`
- **No se duplican:** Prohibido hardcoding en otras apps
- **Se validan:** Mediante `filtrar_cuentas_por_app_origen()` en backend
- **Mejoras futuras:** Migrar a Django admin si se requiere UI de gestión sin código

### 18.8. [COMPLETED] Eliminación de Campos Contables en Apps Origen (v3.10.2)

**Estado:** ✅ **COMPLETADO** — 2026-05-28

Todas las apps de negocio han sido **completamente desacopladas** de responsabilidad contable. Se eliminaron campos `cuenta_contable_uuid`, propiedades de resolución de labels y funciones de búsqueda de cuentas de:

#### 18.8.1. Apps Refactorizadas

| App | Modelo | Campo Eliminado | Archivos | Migración |
|---|---|---|---|---|
| **proveedores** | Proveedor | `codigo_contable`, `cuenta_contable_uuid` | 4 | 0007 |
| **clientes** | Cliente | `cuenta_contable_uuid` | 5 | 0007 |
| **inventario** | 4 modelos | `cuenta_inventario_uuid`, `cuenta_costo_uuid`, `cuenta_ingreso_uuid`, `cuenta_activo_uuid`, `cuenta_depreciacion_uuid` | 6 | 0009 |
| **facturas** | Factura | `cuenta_contable_uuid` | 4 | 0026 |
| **gastos** | DocumentoSoporte | `cuenta_gasto_uuid` | 6 | 0020 |
| **empleados** | Devengo | `cuenta_contable_uuid` | 5 | 0010 |

**Total:** 6 apps, 10 modelos, 15 campos eliminados, 30 archivos modificados, 6 migraciones aplicadas.

#### 18.8.2. Cambios Estructurales

Cada app fue limpiada sistemáticamente en las siguientes capas:

1. **ORM (`models.py`):** Eliminar campo UUIDField o CHAR para soft reference contable
2. **Selectores (`services/selectors.py`):** Quitar de tuplas `LIST_FIELDS`, `DETAIL_FIELDS`
3. **Serializers (`api/serializers.py`):** Quitar de `Meta.fields`, eliminar `get_<campo>()`, `validate_<campo>()`
4. **Lógica de Negocio (`services/business_service.py`):** Quitar validaciones contables e imports
5. **Templates:** Quitar secciones "Integración Contable" y campos de búsqueda
6. **JavaScript (`static/*/js/features/`):** Quitar funciones `initCuentaSearch()`, `getCuentaByUuid()`, data collection

#### 18.8.3. Garantía de Pureza (Pull Model)

✅ **Post-refactorización:**
- ✅ Ningún import de `apps.tenant.contabilidad` desde apps origen
- ✅ Ningún campo de tipo `UUIDField` para mapeo contable
- ✅ Ningún input HTML para búsqueda de cuentas
- ✅ 0 referencias a `cuenta_contable_*` en código vivo (excepto migraciones)
- ✅ Django system check: 0 errores

#### 18.8.4. Implicancia: Contabilidad es Ahora Pure Pull

Con esta refactorización:

1. **Extractores** en `apps/tenant/contabilidad/integracion/extractores/` son los ÚNICOS lectores de apps origen
2. **Apps origen** NO saben que existen — zero coupling
3. **Nuevo usuario/flujo:** Usuario contabiliza documento manual en offcanvas de Contabilidad (not en app origen)
4. **Documentación:** el checklist de esta refactorización se aplicó ad-hoc en su momento y no quedó formalizado en un documento aparte (referencia previa a `REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md` retirada en Fase 9 del plan de correcciones — el archivo nunca existió en el repositorio, ver DOC-A4)

#### 18.8.5. Validación

```bash
# Verificar que NO hay referencias contables pendientes
grep -r "cuenta_gasto\|cuenta_contable_uuid\|cuenta_.*_uuid" \
  apps/tenant/{proveedores,clientes,inventario,facturas,gastos,empleados} \
  --include="*.py" --include="*.html" --include="*.js" \
  | grep -v migrations
# Output: (vacío — cero matches)

# Django check
python manage.py check
# Output: System check identified no issues (0 silenced).
```

#### 18.8.6. Próximos Pasos

- **Contabilidad:** Validar que extractores leen correctamente sin campos contables en origen
- **Testing:** Smoke tests en cada app para crear/editar documentos sin error
- **Fallback Manual:** Documentar flujo de contabilización manual en offcanvas Contabilidad

## [AI-AGENTS] 20. Arquitectura de Agentes IA Especializados (Asistente Contable)

### 20.1. Principio de Diseño

El asistente IA es un **método de entrada rápida** para las líneas del asiento contable en el flujo Manual On-Demand. Actúa como autocompletado inteligente: el contador revisa y confirma antes de generar. La validación local (cuadratura, nivel 6, `TipoComprobante`) siempre es la fuente de verdad final.

**Contrato inmutable:**
- Input: JSON estructurado del documento origen (montos, retenciones, tercero, app_label)
- Output: array de `LineaManual` validadas contra el PUC del tenant, con `|ΣDebe - ΣHaber| = 0`
- El asiento no se persiste hasta que el usuario presiona "Generar Asiento"

### 20.2. Agentes Especializados por Dominio

| Agent ID | App Label | Conocimiento NIIF | Modelo de IA |
|----------|-----------|-------------------|--------------|
| `FacturacionAgent` | `facturas` | Causación Factura de Venta: CxC (1305), IVA generado (240805), Retefuente (2365xx), ReteICA (2368xx), Ingresos (4135xx) | claude-haiku-4-5-20251001 |
| `GastosAgent` | `gastos` | Causación Compra/Gasto: CxP Proveedor (2335xx), IVA descontable (240810), Retefuente (2365xx), Gastos operativos (51xx) | claude-haiku-4-5-20251001 |
| `NominaAgent` | `empleados` | Causación Nómina: Salarios (5105xx), Aportes seguridad social (2370xx), Obligaciones laborales (25xx) | claude-haiku-4-5-20251001 |
| `InventarioAgent` | `inventario` | Sincronización Kardex: Inventario (1435xx), CMV (6135xx), Ingresos (4135xx) | claude-haiku-4-5-20251001 |

El enrutamiento es automático: el orquestador lee `app_label` del request y filtra las cuentas PUC disponibles via `APP_ORIGEN_PREFIJOS[app_label]` antes de construir el prompt.

### 20.3. Flujo de Enrutamiento (Orquestador)

```
POST /api/v1/contabilidad/pendientes/asistente-ia/
    │
    ├─ AsistenteIAInputSerializer.validate()
    │       ← app_label, modelo, documento_id, subtotal, impuestos, total, tercero
    │
    ├─ DocumentosPendientesViewSet.asistente_ia()
    │       ← IsTenantMember + IsTenantAdminOrReadOnly
    │
    ├─ ContabilidadBusinessService.sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)
    │       ├─ filtrar_cuentas_por_app_origen(qs, app_label)  → cuentas nivel-6 del tenant
    │       ├─ anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(...)
    │       │       model = 'claude-haiku-4-5-20251001'
    │       │       prompt = [tipo_label + cuentas disponibles + montos del documento]
    │       ├─ json.loads(response)
    │       ├─ Validar cada cuenta_codigo: CuentaContable.nivel==6, activa==True, empresa_id
    │       └─ Validar cuadratura: |ΣDebe - ΣHaber| < 0.01
    │
    └─ Response({'lineas': [{cuenta_codigo, cuenta_nombre, debe, haber, descripcion}, ...]})
```

### 20.4. Prompt Engineering — Estructura Canónica

El prompt enviado al modelo Claude tiene la siguiente estructura fija:

```
Eres un contador experto en NIIF PYMES Colombia con amplio conocimiento del PUC.

Documento a contabilizar:
- Tipo: {tipo_label}           ← FacturacionAgent / GastosAgent / etc.
- Numero: {numero}
- Tercero: {tercero_nombre} (NIT: {tercero_nit})
- Subtotal: $ {subtotal}
- Impuestos/Retenciones: $ {impuestos}
- Total a pagar/cobrar: $ {total}

Cuentas PUC nivel 6 disponibles para {tipo_label}:
- 130505: Clientes nacionales (ACTIVO)
- 510506: Salarios (GASTO)
- ...  ← máx 50 cuentas filtradas por APP_ORIGEN_PREFIJOS[app_label]

Genera las lineas del asiento contable en partida doble garantizando que
la suma del Debe sea exactamente igual a la suma del Haber.
Responde UNICAMENTE con un JSON valido (sin markdown, sin texto adicional):
{"lineas": [{"cuenta_codigo": "string", "debe": 0.00, "haber": 0.00, "descripcion": "string"}, ...]}
```

### 20.5. Seguridad y Validaciones Post-IA

Toda cuenta sugerida por la IA es validada antes de ser retornada al frontend:
1. **Existencia**: `CuentaContable.objects.filter(empresa_id=empresa_id, codigo=codigo)` — IDOR prevention
2. **Nivel auxiliar**: `nivel == 6` — cumple NIIF PYMES y `_validar_cuentas_auxiliares()`
3. **Activa**: `activa == True` — no se pueden usar cuentas desactivadas
4. **Cuadratura**: `|ΣDebe - ΣHaber| < 0.01` — partida doble garantizada antes de enviar al frontend

Si alguna validación falla, el endpoint devuelve `HTTP 400` con clave `ia` explicando el error.

### 20.6. Configuración

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | API key del tenant Anthropic | Sí |

El paquete `anthropic>=0.40.0,<1.0` está declarado en `requirements.txt`.
Si la clave no está configurada, el endpoint devuelve `HTTP 400` con mensaje descriptivo — no hace fallback silencioso.

### 20.7. Reglas de Compliance para Agentes IA en SINTEL

1. **[PROHIBIDO]** Persistir asientos desde el asistente IA sin confirmación explícita del usuario
2. **[PROHIBIDO]** Retornar cuentas no validadas contra el DB del tenant — toda cuenta pasa por DSV
3. **[OBLIGATORIO]** El botón "Generar Asiento" sigue requiriendo cuadratura local < 0.01 — independiente de la IA
4. **[OBLIGATORIO]** El asistente IA solo opera en el contexto del ViewSet autenticado — `IsTenantMember` siempre activo
5. **[OBLIGATORIO]** Las líneas sugeridas son editables — el contador es la autoridad final
6. **[PROHIBIDO]** Los agentes IA no pueden importar directamente de apps fuente — solo operan sobre el contexto de `contabilidad`

## [MEMORY] 19. Memory Bank y Estado a Largo Plazo (MEMORY.md)

**REGLA OBLIGATORIA PARA TODOS LOS AGENTES Y EDITORES DE CÓDIGO (Claude Code, Cursor, Copilot, Antigravity, etc.)**

1. **Lectura Inicial Obligatoria:** Al iniciar cualquier sesión, tarea o contexto nuevo, el agente/editor DEBE leer el archivo `MEMORY.md` ubicado en la raíz del proyecto.
2. **Propósito del Memory Bank:** `MEMORY.md` es la fuente canónica del estado actual del proyecto, decisiones arquitectónicas recientes (ADRs) y el progreso activo. Su objetivo es evitar refactorizaciones cíclicas y la pérdida de contexto en tareas extensas.
3. **Mantenimiento Continuo:** Al finalizar hitos importantes, implementar cambios estructurales o resolver bugs complejos, el agente DEBE actualizar proactivamente `MEMORY.md` para reflejar el nuevo estado, garantizando que futuras sesiones hereden este conocimiento.
4. **Inmutabilidad de ADRs:** Las decisiones listadas bajo la sección de ADRs en `MEMORY.md` no pueden ser alteradas ni refactorizadas sin autorización explícita del usuario principal.

---

## [HTMX-OFFCANVAS] 26. Patron Anti-Backdrop: Offcanvas + HTMX (Bootstrap 5)

**PROBLEMA:** Combinar `hx-swap="innerHTML"` con `bootstrap.Offcanvas.getOrCreateInstance(el).show()` produce **pantalla negra en el segundo intento** de apertura. El swap elimina el elemento DOM pero no el `.offcanvas-backdrop` que Bootstrap dejó en `<body>`. Al volver a mostrar, se acumula un segundo backdrop → opacidad doble → pantalla completamente negra.

### 26.1. Patron Obligatorio — `mostrarOffcanvasSeguro(el)`

**[PROHIBIDO]** en cualquier handler que abra un offcanvas post-HTMX swap:
```javascript
// ❌ INCORRECTO — acumula backdrops
bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
```

**[OBLIGATORIO]** usar el helper de limpieza antes de mostrar:
```javascript
// ✅ CORRECTO — limpia backdrops huerfanos, crea instancia fresca
function mostrarOffcanvasSeguro(el) {
    if (!el || !w.bootstrap?.Offcanvas) return;
    d.querySelectorAll('.offcanvas-backdrop').forEach(b => b.remove());
    d.body.classList.remove('overflow-hidden', 'modal-open');
    var prev = bootstrap.Offcanvas.getInstance(el);
    if (prev) prev.dispose();
    new bootstrap.Offcanvas(el).show();
}
mostrarOffcanvasSeguro(offcanvasEl);
```

En templates con `hx-on::after-request`, usar el helper global registrado en el template padre del modulo:
```html
hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvas('offcanvas-id'); }"
```

`sintelAbrirOffcanvas` encapsula identicamente la misma logica de limpieza.

> **CRITICO — Regla de scope `hx-on::` (incidente 2026-06-01):**
> `hx-on::` en un botón/form SOLO captura eventos que se disparan en ESE elemento.
> En HTMX 1.9.x:
> - `htmx:afterRequest` → dispara en el **elemento iniciador** → `hx-on::after-request` funciona en botones
> - `htmx:afterSettle` → dispara en el **elemento target** (el div receptor del swap) → `hx-on::after-settle` NO funciona en botones
>
> **Usar `hx-on::after-request` en botones** para abrir offcanvas post-HTMX (el swap inline ocurre de forma sícrona ANTES de que se dispare `afterRequest`).
> **Usar `document.addEventListener('htmx:afterSettle', ...)` en JS** para inicializar formularios en los módulos editor.

### 26.2. Contenedores HTMX — SSoT en Template Padre

**[PROHIBIDO]** declarar el mismo `id` de contenedor HTMX en dos templates distintos del mismo modulo.

**Regla:** el template que incluye los sub-templates (`list_inventario.html`, etc.) es la SSoT de los contenedores HTMX:
```html
<!-- ✅ CORRECTO: definidos UNA SOLA VEZ en el template padre -->
<div id="offcanvas-container-inventario"></div>
<div id="offcanvas-container-activos"></div>
<div id="offcanvas-container-servicios"></div>
```

Los sub-templates incluidos (`list_productos.html`, `list_activos.html`, etc.) **NO deben** repetir estos contenedores. Duplicar un `id` en el DOM hace que HTMX apunte al primer match (dentro de un pane oculto) en vez del contenedor correcto.

### 26.3. Inicializacion del Helper Global

En el template padre del modulo agregar el script de definicion:
```html
<script>
(function() {
    window.sintelAbrirOffcanvas = function(id) {
        document.querySelectorAll('.offcanvas-backdrop').forEach(function(b) { b.remove(); });
        document.body.classList.remove('overflow-hidden', 'modal-open');
        var el = document.getElementById(id);
        if (el && window.bootstrap && window.bootstrap.Offcanvas) {
            var prev = bootstrap.Offcanvas.getInstance(el);
            if (prev) prev.dispose();
            new bootstrap.Offcanvas(el).show();
        }
    };
})();
</script>
```

### 26.4. Diagnostico Rapido

```bash
# Detecta todos los getOrCreateInstance que pueden acumular backdrops
grep -rn "getOrCreateInstance" apps/tenant/*/static/*/js/ --include="*.js"
# Cada match debe ser evaluado: si viene despues de htmx.ajax o hx-swap → migrar a mostrarOffcanvasSeguro
```

---

## [UUID-FORMS] 27. UUID-Safe Form Submissions — PROHIBIDO parseInt en Selects de API

**PROBLEMA:** Los selects (`<select>`) cuyos options se cargan dinamicamente desde la API reciben `option.value = item.id` donde `item.id` es un **UUID string** (porque `CategoriaItemListSerializer` declara `id = serializers.UUIDField(source='uuid')`). Aplicar `parseInt()` sobre ese value extrae solo el prefijo numerico del UUID, generando un PK entero incorrecto.

**Ejemplo del fallo:**
```
UUID del item seleccionado:  "9abc1234-xxxx-..."
parseInt("9abc1234...", 10) = 9              ← extrae solo el '9' inicial
Payload enviado: { categoria: 9 }           ← entero incorrecto
Backend: CategoriaItem.objects.get(pk=9) → DoesNotExist
Error: "Clave primaria '9' invalida — objeto no existe"
```

### 27.1. Patron Obligatorio en Editores JS

**[PROHIBIDO]** convertir a entero cualquier campo de FK que puede ser UUID:
```javascript
// ❌ INCORRECTO — corrompe UUID en entero parcial
categoria: formData.get('categoria') ? parseInt(formData.get('categoria'), 10) : null,
categoria: parseInteger(formData.get('categoria')),
```

**[OBLIGATORIO]** enviar el valor crudo (string):
```javascript
// ✅ CORRECTO — UUIDOrPKRelatedField maneja tanto UUIDs como enteros
categoria: formData.get('categoria') || null,
```

`UUIDOrPKRelatedField.to_internal_value(data)` ya discrimina internamente:
- Si `data.isdigit()` → lookup por PK entero
- Si no → lookup por UUID: `queryset.get(uuid=data_str)`

No se necesita ninguna conversion en el frontend.

### 27.2. Patron Obligatorio en Utils de Carga de Selects

Cuando se compara `selectedId` con `option.value` para preseleccionar, usar comparacion de strings (no enteros):
```javascript
// ❌ INCORRECTO — parseInt(UUID) da NaN o entero parcial
var selId = selectedId ? parseInt(selectedId, 10) : null;
if (selId && cat.id === selId) { option.selected = true; }

// ✅ CORRECTO — comparacion UUID-safe
var selId = selectedId ? String(selectedId) : null;
if (selId && String(cat.id) === selId) { option.selected = true; }
```

### 27.3. Alcance de la Regla

Aplica a TODOS los campos de FK en formularios de inventario y cualquier app que use `Utils.loadCategoriasSelect` o cualquier funcion que cargue options desde la API:
- `categoria` en Producto, Servicio, Activo Fijo
- Cualquier campo FK con `UUIDOrPKRelatedField` en el serializer
- Cualquier `<select>` cuyas opciones vengan de `GET /api/v1/*/`

### 27.4. Diagnostico

```bash
# Detecta todos los parseInt sobre campos de formulario FK en editores JS
grep -rn "parseInt.*formData\|parseInteger.*formData" apps/tenant/*/static/*/js/features/
# Cada match sobre campos de FK (categoria, producto, servicio, etc.) debe ser migrado
```

---

## Apendice A. Comandos de Operacion

### Docker / Make (Desarrollo)
- **Levantar servicios:** `make up` (web:8000, db:5432, redis:6379, celery)
- **Detener:** `make down` | **Logs:** `make logs` | **Shell:** `make shell`
- **Directo:** `docker compose up --build`
- **REGLA CRITICA — Healthcheck PostgreSQL:** El healthcheck del servicio `db` DEBE usar `psql -c 'SELECT 1'`, NUNCA `pg_isready`. `pg_isready` solo verifica TCP y produce falso-positivo durante la inicialización del DB. Ver `skills/workflow/docker-services.md`.
- **REGLA CRITICA — Superusuario del sistema:** El usuario administrador del dominio público (`sintel.net.co/admin/`) se crea SIEMPRE y SOLO de forma manual con `python manage.py createsuperuser [--tenant <schema>]`. NUNCA se crea automáticamente al arrancar el servidor. `ensure_admin` SOLO verifica existencia — no crea usuarios. PROHIBIDO usar `ensure_admin` para crear administradores. Para la primera instalación ejecutar `createsuperuser` manualmente.

### Serializers — Obtener empresa_id (REGLA CRITICA)
- **PROHIBIDO en serializers:** `self.context.get('request').user.perfil.empresa_id` — lanza `AttributeError: 'User' object has no attribute 'perfil'` cuando el user no tiene `TenantProfile` asociado. Afecta GET list/detail porque el serializer se ejecuta antes de cualquier guard de perfil.
- **Patrón correcto:** Agregar `_get_empresa_id()` a `NormalizationMixin` con dos niveles: (1) `self.context.get('empresa_id')` si el ViewSet lo inyecta, (2) fallback `Empresa.objects.only('id').first()`. Ver `serializers.py` de inventario como referencia.
- **Patrón en ViewSet:** Inyectar `empresa_id` en `get_serializer_context()` para que el serializer no necesite acceder al `request.user` directamente.

### Onboarding de Tenants Privados (Contraseñas y Activación)
- **REGLA ABSOLUTA — Contraseñas:** Las contraseñas de owners de tenants privados se crean SIEMPRE y SOLO por el propio usuario a través del email de activación. NUNCA de forma automática.
- **REGLA ABSOLUTA — Flujo de activación canónico (v3.15.1):** Todo email de activación de tenant privado DEBE enviarse exclusivamente via `EmailService.send_tenant_activation_email(user, tenant)`. Esta función es el SSoT — genera el código Redis (8 chars, TTL 48h) internamente. PROHIBIDO llamar a `generate_invitation_token`, `build_activation_url`, `send_invitation_email` directamente en flujos de onboarding.
- **Flujo único autorizado:** `crear_tenant_con_owner()` → `set_unusable_password()` → `EmailService.send_tenant_activation_email()` → email con código 8 chars → `{schema}.sintel.net.co/static/tenant/core/auth/activate.html` → `POST /api/v1/core/auth/activate-with-code/` → `user.set_password()`.
- **Prohibido en onboarding:** `set_password(...)`, `make_random_password()`, `create_user_service(password=...)`. Solo `set_unusable_password()`.
- **`ensure_admin`** SOLO verifica si existe un superusuario activo — NO crea usuarios. Si no existe ninguno, muestra alerta y ordena ejecutar `createsuperuser`. Nunca se llama automáticamente al arrancar el servidor.

### Nomenclatura y Abstracción de Configuraciones (v3.16.0 — INMUTABLE) → Ver §29 para reglas detalladas
- **REGLA CRITICA — Sin nombres propios de tenants en código:** Cualquier script, management command, configuración de infraestructura o docstring en `apps/public/` DEBE usar placeholders abstractos (`{schema_name}`, `{schema}.sintel.net.co`, `<schema_name>`) en lugar de nombres propios de tenants específicos (`cliente`, `home`, `putito`, `tupapi`, etc.).
- **REGLA CRITICA — Datos dinámicos via ORM:** Los scripts de aprovisionamiento (DNS, extra_hosts, health checks) deben obtener la lista de tenants activos consultando `Client.objects.exclude(schema_name="public").filter(is_active=True)`, nunca una lista hardcodeada.
- **EXCEPCIÓN DOCUMENTADA — Dominio público:** `schema_name="public"` y `sintel.net.co` son la excepción explícita y documentada. Su DNS se gestiona independientemente y nunca debe ser modificado por comandos de aprovisionamiento de tenants privados. La excepción está marcada con comentario en `ensure_tenant_dns.py`.
- **REGLA CRITICA — Filtro console/users/:** El endpoint `UsersDataTableView` SOLO muestra `Q(is_staff=True, is_superuser=True) OR Q(TenantMembership.is_primary_admin=True)`. PROHIBIDO cambiar este filtro sin aprobación manual — exponer empleados de tenants en el panel admin es una brecha de privacidad.
- **REGLA CRITICA — is_staff para owners:** Los owners de tenants privados tienen `is_staff=False, is_superuser=False`. PROHIBIDO asignar `is_staff=True` a un owner de tenant en ningún flujo de onboarding o management command. Solo los admins del sistema tienen `is_staff=True + is_superuser=True`.

### Migraciones Multi-Tenant
- **Tenants:** `make migrate-tenants` / `docker compose exec web python manage.py migrate_schemas`
- **Shared (público):** `make migrate-shared` / `docker compose exec web python manage.py migrate_schemas --shared`
- **Crear migraciones:** `make makemigrations` | **Verificar pendientes:** `make check-migrations`

### Tests
- **Todos:** `make test` | **Archivo:** `make test-file FILE="path/to/test.py"` | **Smoke:** `make smoke`
- **Directo:** `python manage.py test apps.tenant.<app_name>`

### Calidad de Código (target py3.12, line-length 100)
- **Auditoría completa:** `make audit` (ruff + bandit + django check + static check)
- **Lint + autofix:** `make ruff` / `ruff check . --fix`
- **Seguridad:** `make bandit` | **Django check:** `make dj-check`
- **Compilación Python (pre-PR):** `python -m py_compile archivo.py`

### Contabilidad
- **Seed reglas contables:** `python manage.py seed_reglas_contables`
- **Seed catálogo NIIF:** `python manage.py poblar_catalogo_niif`
- **Backfill asientos gastos:** `python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]`

### One-off
- **Crear empresa:** `make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"`
- **Superusuario:** `docker compose exec web python manage.py createsuperuser`

## [KARPATHY] 21. Karpathy Coding Principles (Caution over Speed)

**PRINCIPIO FUNDAMENTAL:** Reducir errores comunes de LLMs mediante cautela, simplicidad y cambios quirúrgicos.

1.  **Pensar antes de Codificar**: No asumir. Si hay incertidumbre, preguntar. Explicitar suposiciones. Si hay múltiples interpretaciones, presentarlas antes de elegir una.
2.  **Simplicidad Primero**: Código mínimo necesario. Prohibido crear abstracciones para código de un solo uso o añadir "flexibilidad" no solicitada. Si se puede hacer en 50 líneas en vez de 200, reescribir.
3.  **Cambios Quirúrgicos**: Tocar SOLO lo estrictamente necesario. No "mejorar" código adyacente ni refactorizar lo que no está roto. Empatar el estilo existente. Si se detecta código muerto no relacionado, reportarlo pero NO borrarlo sin permiso.
4.  **Ejecución Basada en Objetivos**: Transformar tareas en metas verificables. Para tareas de múltiples pasos, definir un plan: `1. [Paso] → verificar: [check]`.

## [CSS-ISOLATION] 22. Aislamiento de Estilos CSS por Aplicacion

**PRINCIPIO FUNDAMENTAL:** Los estilos visuales (CSS) de cada aplicacion son propiedad exclusiva de esa app. Ninguna app puede modificar, inyectar ni sobreescribir la apariencia visual de otra app desde el exterior. Los estilos solo pueden originarse y aplicarse desde dentro de la misma app.

### 22.1. SSoT de Assets CSS por App

- Todo estilo visual que afecte los templates de una app DEBE provenir EXCLUSIVAMENTE del directorio estatico de esa misma app.
- **Ruta obligatoria (apps tenant):** `apps/tenant/<app_name>/static/<app_name>/css/`
- **Ruta obligatoria (apps public):** `apps/public/<app_name>/static/<app_name>/css/`
- Cada app centraliza la inclusion de sus hojas de estilo en el partial `partials/assets_<app_name>.html`. Esa es la UNICA puerta de entrada autorizada para CSS de la app.

### 22.2. Prohibiciones Estrictas (Cross-App CSS)

1. **[PROHIBIDO] `<link>` cross-app:** Un template de `clientes` NO puede cargar un CSS ubicado en `facturas/static/facturas/css/` ni en ninguna app distinta de `clientes`.
2. **[PROHIBIDO] Reglas CSS cross-app:** Un archivo `gastos.css` NO puede definir reglas que apunten a selectores o clases visuales de `proveedores`, `clientes` u otra app.
3. **[PROHIBIDO] Bloques `<style>` cross-app:** Prohibido agregar `<style>` en templates de una app con reglas que modifiquen componentes de otra app.
4. **[PROHIBIDO] Atributos `style=""` cross-app:** Prohibido usar `style=""` inline en templates de una app para sobreescribir estilos definidos por otra app.

**Ejemplo PROHIBIDO:**
```html
<!-- En apps/tenant/clientes/templates/tenant/clientes/list_cliente.html -->
<link href="{% static 'facturas/css/tabla.css' %}" rel="stylesheet">
<style>.proveedor-card { color: red; }</style>
```

**Ejemplo CORRECTO:**
```html
<!-- En apps/tenant/clientes/templates/tenant/clientes/list_cliente.html -->
{% include "tenant/clientes/partials/assets_clientes.html" %}
```

### 22.3. Excepciones Controladas (CSS Global Autorizado)

| Fuente | Razon |
|---|---|
| Bootstrap 5 via CDN | Sistema de diseno UI compartido — infraestructura global |
| `apps/tenant/core/static/core/css/` | Shell UI estructural: navbar, sidebar, layout base. NUNCA reglas de apps de dominio |
| Variables CSS `--sintel-*` del shell `core` | Tokens de diseno globales permitidos como custom properties |

### 22.4. Auditoria y Cumplimiento

- Toda PR que modifique archivos `.css` o templates DEBE verificar que no hay referencias cross-app en `<link href>`, `{% static %}` ni bloques `<style>`.
- Un agente que detecte una violacion DEBE reportarla al usuario antes de continuar, sin propagarla.

## [JS-ISOLATION] 23. Aislamiento de JavaScript por Aplicacion

**PRINCIPIO FUNDAMENTAL:** El codigo JavaScript de cada aplicacion es propiedad exclusiva de esa app. Ninguna app puede importar, invocar ni extender la logica JS de otra app de dominio directamente. Los scripts solo pueden originarse y ejecutarse desde dentro de la misma app.

### 23.1. SSoT de Assets JS por App

- Todo script que controle la logica o UI de una app DEBE residir EXCLUSIVAMENTE en el directorio estatico de esa misma app.
- **Ruta obligatoria (apps tenant):** `apps/tenant/<app_name>/static/<app_name>/js/`
- **Ruta obligatoria (apps public):** `apps/public/<app_name>/static/<app_name>/js/`
- Cada app carga sus propios scripts via el partial `partials/assets_<app_name>.html`. Esa es la UNICA puerta de entrada autorizada para JS de la app.
- Namespace obligatorio: `window.Sintel.<AppName>` — cada app opera bajo su propio namespace global sin colisionar con otros.

### 23.2. Prohibiciones Estrictas (Cross-App JS)

1. **[PROHIBIDO] `<script src>` cross-app:** Un template de `clientes` NO puede cargar un `.js` ubicado en `facturas/static/facturas/js/` ni en ninguna app distinta de `clientes`.
2. **[PROHIBIDO] Llamadas cross-namespace:** Un modulo de `gastos` NO puede invocar directamente funciones de `window.Sintel.Clientes`, `window.Sintel.Facturas` u otro namespace de app de dominio.
3. **[PROHIBIDO] Importar modulos JS de otra app:** Prohibido referenciar funciones, clases o utilidades definidas en los archivos `.js` de otra app de dominio (ej. usar `clientes.api.js` desde `proveedores`).
4. **[PROHIBIDO] Modificar el namespace de otra app:** Prohibido extender, sobreescribir o monkey-patchear el objeto `window.Sintel.<OtraApp>` desde fuera de esa app.
5. **[PROHIBIDO] Eventos cross-app con acoplamiento directo:** Prohibido que una app escuche eventos HTMX o DOM disparados por otra app para ejecutar logica de negocio propia, salvo via eventos estandarizados del shell `core` (ej. `sintel:tenant-ready`).

**Ejemplo PROHIBIDO:**
```html
<!-- En apps/tenant/clientes/templates/tenant/clientes/list_cliente.html -->
<script src="{% static 'facturas/js/facturas.api.js' %}"></script>
<script>
  // Llamada directa al namespace de otra app
  window.Sintel.Proveedores.table.reload();
</script>
```

**Ejemplo CORRECTO:**
```html
<!-- En apps/tenant/clientes/templates/tenant/clientes/list_cliente.html -->
{% include "tenant/clientes/partials/assets_clientes.html" %}
<script>
  // Solo invoca el namespace propio
  window.Sintel.Clientes.init();
</script>
```

### 23.3. Excepciones Controladas (JS Global Autorizado)

| Fuente | Razon |
|---|---|
| CDN: Bootstrap 5, HTMX, Tabulator, Font Awesome | Infraestructura UI compartida — permitida globalmente |
| `apps/tenant/core/static/core/js/common/` | Helpers globales de infraestructura: `ui-manager.js`, `tabulator.factory.js`, `notyf.init.js`, `http.js` |
| `apps/public/console/static/js/jwt-auth.js` | Helper global de autenticacion JWT — `window.jwtAuth` |
| Eventos del shell `core` (`sintel:*`) | Canal de comunicacion inter-app autorizado via Custom Events estandarizados |

### 23.4. Canal de Comunicacion Inter-App Autorizado (Custom Events)

Cuando una app necesita notificar a otra de un cambio de estado (ej. un cliente nuevo creado que debe reflejarse en facturas), el mecanismo autorizado es:

```javascript
// App emisora (clientes): dispara evento estandarizado
document.dispatchEvent(new CustomEvent('sintel:cliente:created', { detail: { uuid } }));

// App receptora (facturas): escucha el evento estandarizado
document.addEventListener('sintel:cliente:created', (e) => {
    window.Sintel.Facturas.ClienteSelector.refresh(e.detail.uuid);
});
```

- El nombre del evento DEBE seguir el patron `sintel:<app>:<accion>`.
- El `detail` solo expone datos minimos necesarios (UUID, estado). NUNCA objetos internos del modulo emisor.
- La app receptora es responsable de manejar el evento con su propia logica encapsulada.

### 23.5. Auditoria y Cumplimiento

- Toda PR que modifique archivos `.js` o templates DEBE verificar que no hay `<script src>` cross-app ni llamadas a `window.Sintel.<OtraApp>` desde fuera de esa app.
- Un agente que detecte una violacion DEBE reportarla al usuario antes de continuar, sin propagarla.

## [TESTING] 24. Patrones Obligatorios para Tests Multi-Tenant

**Post-mortem: Bug 2026-05-15** — Tests de permisos CRUD fallaban con `AssertionError: 405 != 201/200` para el usuario `admin_user` incluso en DEBUG. Causa: usuarios creados en esquema incorrecto, rol `STAFF` inexistente, sin `TenantProfile` en el tenant.

### 24.1. Regla de Tres Esquemas

| Modelo | Esquema | Como crearlo en tests |
|--------|---------|----------------------|
| `User` (AUTH_USER_MODEL) | **public** | `with schema_context(get_public_schema_name()): User.objects.create_user(...)` |
| `TenantMembership` | **public** | `with schema_context(get_public_schema_name()): TenantMembership.objects.create(...)` |
| `TenantProfile` | **tenant activo** | `TenantProfile.objects.create(...)` (sin schema_context, ya estamos en tenant) |
| `Empresa`, `CategoriaItem`, etc. | **tenant activo** | `Empresa.objects.create(...)` directamente |

**[PROHIBIDO]** Crear `User` o `TenantMembership` sin el `schema_context` del esquema public en tests de tenant. Esto causa que `request.user.is_authenticated == False` en runtime, bloqueando `_check_enforced_mode` con un falso `405`.

### 24.2. SSoT de Roles (solo estos 3 existen)

```
ADMIN     → TenantProfile.rol='ADMIN'     → Lectura + Escritura + Admin
OPERADOR  → TenantProfile.rol='OPERADOR'  → Lectura + Escritura limitada
VISOR     → TenantProfile.rol='VISOR'     → Solo lectura
```

**[PROHIBIDO]** Usar `rol='STAFF'`, `rol='USER'` o cualquier otro rol en `TenantMembership` o `TenantProfile`. No existen en `RolTenant` (`apps/tenant/perfil/models.py`) y causan fallos silenciosos de permisos.

### 24.3. setUp Canónico para Tests de Permisos

```python
from django_tenants.utils import get_public_schema_name, schema_context
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

class TestMiModeloCRUD(SintelTenantTestCase):

    def setUp(self):
        super().setUp()

        # 1. Empresa singleton (requerida por get_empresa_singleton() y _get_empresa_id())
        self.empresa = Empresa.objects.create(
            razon_social="Test", nit="900000001", singleton_key=1
        )

        # 2. Usuarios en esquema PUBLIC
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            self.admin_user = User.objects.create_user(
                username="admin@test.com", email="admin@test.com", is_active=True
            )
            self.visor_user = User.objects.create_user(
                username="visor@test.com", email="visor@test.com", is_active=True
            )

        # 3. TenantProfile en esquema TENANT (conexion ya activa desde super().setUp())
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.create(user=self.admin_user, empresa=self.empresa, rol='ADMIN')
        TenantProfile.objects.create(user=self.visor_user, empresa=self.empresa, rol='VISOR')

        # 4. TenantMembership en esquema PUBLIC
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant, user=self.admin_user, rol='ADMIN', is_active=True
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.visor_user, rol='VISOR', is_active=True
            )

        # 5. Clientes API — UNO POR ROL (no reutilizar self.api_client)
        domain = self.domain.domain
        self.admin_client = APIClient(HTTP_HOST=domain)
        self.admin_client.force_authenticate(user=self.admin_user)
        self.visor_client = APIClient(HTTP_HOST=domain)
        self.visor_client.force_authenticate(user=self.visor_user)
```

### 24.4. Arquitectura de _check_enforced_mode

`BaseViewSet._check_enforced_mode(request)` implementa la siguiente logica en inventario:

```
¿request.user autenticado?  → No  → 405 (fallo silencioso si usuario mal creado)
¿metodo SAFE (GET)?         → Si  → Permitido para todos
¿IsTenantAdmin OK?          → Si  → Permitido (en DEBUG siempre True)
                            → No  → 405 "Solo ADMIN puede crear/editar/eliminar"
```

**Referencia completa:** `apps/tenant/inventario/.agent/docs/TESTING_MULTI_TENANT_PATTERNS.md`

---

### 24.5. Estandar de Aislamiento Multi-Tenant — Los 3 Niveles Obligatorios

**REGLA FUNDAMENTAL:** Todo test de app tenant que implique lectura, acceso directo o creacion/mutacion de datos DEBE verificar los 3 niveles de aislamiento. El patron canonico es `apps/tenant/gastos/tests/test_multitenant_isolation.py`.

#### Los 3 Niveles (no negociables)

| Nivel | Que valida | Assertion minima |
|---|---|---|
| **1 — Listado** | `GET /api/v1/{app}/` desde `tenant1` solo devuelve datos de `tenant1` | `assert objeto_t2.descripcion not in [item['campo'] for item in results]` |
| **2 — IDOR directo** | `GET /api/v1/{app}/{uuid_de_tenant2}/` desde `tenant1` devuelve 404 | `assert resp.status_code == 404` |
| **3 — IDOR en FKs** | `POST` con FK de `tenant2` desde `tenant1` devuelve 400/403/404 | `assert resp.status_code in (400, 403, 404)` |

#### Template Canonico (copiar y adaptar por app)

```python
# apps/tenant/{app}/tests/test_multitenant_isolation.py
import pytest
from django_tenants.utils import schema_context
from rest_framework import status
from apps.public.tenants.models import TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_multitenant_isolation_{app}(client, tenant1, tenant2):
    """
    Verifica los 3 niveles de aislamiento multi-tenant para {App}.
    Patron: apps/tenant/gastos/tests/test_multitenant_isolation.py
    """
    # --- NIVEL 1 & 2 setup: crear datos en cada tenant ---
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="user1_t1", email="u1@t1.local", password="pass")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")
        obj1 = {Model}.objects.create(empresa=emp1, ...)  # objeto de tenant1

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user2_t2", email="u2@t2.local", password="pass")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")
        obj2 = {Model}.objects.create(empresa=emp2, ...)  # objeto de tenant2

    # --- NIVEL 1: Aislamiento en listado ---
    client.force_login(user1)
    resp = client.get("/api/v1/{app}/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    ids_visibles = [item['{campo_identificador}'] for item in resp.json().get('results', [])]
    assert '{valor_obj1}' in ids_visibles      # propio tenant: VISIBLE
    assert '{valor_obj2}' not in ids_visibles  # otro tenant: INVISIBLE

    # --- NIVEL 2: Prevencion de IDOR (acceso directo por UUID) ---
    resp = client.get(
        f"/api/v1/{app}/{obj2.uuid}/",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND  # UUID de otro tenant: 404

    # --- NIVEL 3: Prevencion de IDOR en FKs (FK de otro tenant en payload) ---
    payload = {
        "{campo_fk}": obj2.id,  # FK que pertenece a tenant2 — debe ser rechazado
        # ... resto del payload valido para tenant1
    }
    resp = client.post(
        "/api/v1/{app}/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
    )
    assert resp.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )  # FK de otro tenant: rechazado por DSV
```

#### Fixtures `conftest.py` estandar para tests de aislamiento

```python
# apps/tenant/{app}/tests/conftest.py
import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa


def _make_test_tenant(schema: str, nombre: str, nit: str):
    """Crea (o reutiliza) un tenant de prueba con schema y empresa."""
    tenant_obj = Client.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = Client.objects.create(schema_name=schema, nombre=nombre)
            Domain.objects.create(
                tenant=tenant_obj,
                domain=f'{schema}.sintel.net.co',  # dominio de test
                is_primary=True,
            )
    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)
    with schema_context(schema):
        if not Empresa.objects.exists():
            Empresa.objects.create(nit=nit, razon_social=f"Empresa {nombre} SAS", direccion="Calle Test")
    return tenant_obj


@pytest.fixture
def tenant1(db):
    return _make_test_tenant('tenant1', 'Tenant 1', '111111111')


@pytest.fixture
def tenant2(db):
    return _make_test_tenant('tenant2', 'Tenant 2', '222222222')
```

#### Reglas de naming para fixtures de aislamiento

| Elemento | Patron | Ejemplo |
|---|---|---|
| schema del tenant de test | `tenant1`, `tenant2` | No usar `home`, `cliente`, etc. |
| dominio del tenant de test | `{schema}.sintel.net.co` | `tenant1.sintel.net.co` |
| email del usuario de test | `u{n}@t{n}.local` | `u1@t1.local` |
| username | `user{n}_t{n}` | `user1_t1` |

**[OBLIGATORIO]** Cada app tenant con modelos propios DEBE tener un archivo `test_multitenant_isolation.py` con los 3 niveles verificados.

**[PROHIBIDO]** Tests de CRUD de tenant que solo verifiquen el happy path sin incluir los niveles 2 (IDOR directo) y 3 (IDOR en FKs).

## [UUID-MIGRATION] 25. Migracion Obligatoria de Lookup Field: PK Entero → UUID

**PRINCIPIO:** Ningún ViewSet tenant debe exponer PKs enteros en URLs públicas. §14.6 establece `lookup_field="uuid"` como el estándar heredado de `BaseTenantViewSet`. Esta sección define el diagnóstico, patrón y verificación para cualquier ViewSet que use `lookup_field='id'`.

### 25.1. Regla Mandatoria

**[PROHIBIDO]** Declarar `lookup_field = 'id'` o `lookup_url_kwarg = 'id'` en ViewSets que hereden de `BaseTenantViewSet`. El `lookup_field = 'uuid'` se hereda automáticamente — no redeclarar.

**[OBLIGATORIO]** Todo modelo que exponga un ViewSet con lookup DEBE tener un campo `uuid`:
```python
# Patron canonico (AGENTS.md §25) — igual en todos los modelos conformes
uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
```

### 25.2. Diagnostico

```bash
# Detecta ViewSets que sobreescriben lookup_field con 'id'
grep -rn "lookup_field\s*=\s*['\"]id['\"]" apps/tenant/ --include="*.py"
grep -rn "lookup_url_kwarg\s*=\s*['\"]id['\"]" apps/tenant/ --include="*.py"

# Detecta modelos sin campo uuid
grep -rL "uuid = models.UUIDField" apps/tenant/*/models.py
```

### 25.3. Patron de Migracion (4 Pasos Coordinados)

**Paso 1 — Modelo:** Agregar campo `uuid`.
```python
import uuid as uuid_module
# En la clase del modelo (despues de SintelTenantBaseModel):
uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
```

**Paso 2 — Migracion de BD** (patron seguro, 3 fases):
```python
# 0. Agregar nullable
migrations.AddField(model_name='mimodelo', name='uuid',
    field=models.UUIDField(db_index=True, null=True, blank=True, editable=False))
# 1. Poblar registros existentes via SQL
migrations.RunPython(lambda apps, schema: schema.execute(
    "UPDATE <tabla> SET uuid = gen_random_uuid() WHERE uuid IS NULL;"))
# 2. Hacer unique y requerido
migrations.AlterField(model_name='mimodelo', name='uuid',
    field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True))
```

**Paso 3 — Backend: Serializer + Selector + ViewSet:**
- Serializer: agregar `'uuid'` a `Meta.fields` y `read_only_fields`.
- Selector `get_detail()`: cambiar `pk=valor` → `uuid=valor`.
- Selector `LIST_FIELDS` y `DETAIL_FIELDS`: agregar `'uuid'`.
- ViewSet: eliminar `lookup_field = 'id'` y `lookup_url_kwarg = 'id'`.
- Acciones `render-offcanvas/`: cambiar `Model.objects.get(id=val)` → `Model.objects.get(uuid=val)`.

**Paso 4 — Frontend (coordinar en el mismo PR):**
- `<app>.api.js`: Las funciones que construyen URLs de detalle reciben UUID desde el serializer.
- `<modelo>_list.js`: Cambiar `data.id` → `data.uuid` al leer el identificador de Tabulator rows.
- Templates: Cambiar `data-instance-id="{{ instance.id }}"` → `data-uuid="{{ instance.uuid }}"`.
- Para edicion via formulario: `form.dataset.uuid` en lugar de `form.querySelector('[name="id"]')`.

### 25.4. Verificacion Post-Migracion

```bash
# No deben existir
grep -rn "lookup_field.*=.*['\"]id['\"]" apps/tenant/ --include="viewsets.py"
grep -rn "data.id\b" apps/tenant/*/static/*/js/features/*.js
grep -rn "data-instance-id" apps/tenant/ --include="*.html"

# Smoke test manual
curl -s http://tenant.local/api/v1/<app>/{UUID}/ | python3 -m json.tool  # debe dar 200
curl -s http://tenant.local/api/v1/<app>/1/  # debe dar 404 (integer bloqueado)
```

### 25.5. Registro de Estado por App

| App | ViewSet | Estado | Notas |
|-----|---------|--------|-------|
| gastos | GastoViewSet | **MIGRADO** (v3.7.6) | lookup uuid, serializer uuid, JS uuid |
| gastos | ResolucionDIANViewSet | **MIGRADO** (v3.7.6) | lookup uuid, serializer uuid, JS uuid |
| Demás ViewSets tenant | — | CONFORMES | Heredan uuid de BaseTenantViewSet |

**Actualizar esta tabla** al migrar nuevas apps o confirmar conformidad.

### 25.6. Prohibiciones

- **[PROHIBIDO]** Puente permanente `get_object()` que soporte PK entero. Es transitorio (max 1 sprint) y debe eliminarse una vez el frontend migra.
- **[PROHIBIDO]** Hardcodear `/api/v1/<app>/{integer}/` en frontend JS o templates.

---

## [EDIT-FORM] 28. Marco de Diagnostico: Formularios de Edicion (Edit Form Fields Reset)

**Contexto:** Aplica a cualquier app del proyecto cuando al abrir un offcanvas de edicion los campos aparecen en blanco o sin los valores almacenados en base de datos.

### 28.1. Las Tres Fuentes de Datos en un Formulario de Edicion

Un formulario de edicion tiene siempre estas 3 fuentes que deben coordinarse:

```
1. Template Django       → pre-renderiza con {% if instance %}...selected{% endif %}
2. JS async catalogos    → cargarServicios(), cargarProveedores(), cargarXxx()
3. JS async API detail   → cargarDetalles(uuid) → GET /api/v1/{app}/{uuid}/
```

Cuando los campos aparecen vacios, **una fuente esta sobreescribiendo a otra** — generalmente (3) destruye (1), o existe un bloque de limpieza que no distingue "crear" de "editar".

---

### 28.2. Inventario de Campos por Tipo

Antes de diagnosticar, clasificar cada campo roto:

```
TIPO                              MECANISMO ESPERADO EN TEMPLATE
─────────────────────────────     ─────────────────────────────────────────────
<input type="text/number/date">   value="{{ instance.campo }}"
<textarea>                        {{ instance.campo }} entre los tags
<select> opciones estaticas       {% if instance.campo == val %}selected{% endif %}
<select> opciones dinamicas       data-selected="{{ instance.campo_uuid }}" + JS
<input type="hidden"> (sync)      value="{{ instance.campo_id }}"
```

---

### 28.3. Checklist de Bugs mas Comunes

#### A) Limpieza incondicional en wizard/step navigation (CRITICO)

```javascript
// BUG — borra siempre, incluyendo modo edicion
if (stepIdx === 0) {
    select.value = '';
    hiddenInput.value = '';
}

// FIX — solo limpiar si es proyecto/instancia NUEVA
if (stepIdx === 0 && !currentInstance) {
    select.value = '';
    hiddenInput.value = '';
}
```

**Por que es seguro:** Cuando `irAStep()` se llama desde `cargarDetalles()`, `currentInstance` ya fue asignado (API respondio). Cuando se llama desde `init()` para una instancia nueva, `currentInstance === null`.

**Buscar en el codigo:** cualquier `select.value = ''` o `input.value = ''` dentro de funciones de navegacion de pasos/tabs.

---

#### B) Mismatch PK entero vs UUID en selects dinamicos

```javascript
// BUG — API devuelve PK integer, select tiene valores UUID
const val = currentInstance.campo_id;   // → 42  (integer)
select.value = val;                     // falla, no existe <option value="42">

// FIX — exponer UUID desde serializer y usarlo en JS
// serializers.py:
campo_uuid = serializers.CharField(source='campo.uuid', read_only=True, allow_null=True)

// editor.js:
const val = currentInstance.campo_uuid;  // → "abc-123-..."
select.value = val;                      // coincide con option.value del select dinamico
```

**Regla:** Si un `<select>` se carga dinamicamente con opciones que tienen `value = UUID`, el campo del serializer que lo pre-selecciona DEBE devolver un UUID, no un PK entero.

---

#### C) Campo `write_only` en serializer — no llega al GET

```python
# BUG — el JS intenta leer este campo pero no viene en la respuesta GET
extra_kwargs = { 'responsable_id': {'write_only': True} }
```
```javascript
syncSelect('responsable-select', data.responsable_id);  // → undefined, no-op
```

**Fix A:** Si el template ya pre-renderiza el select con `selected`, no hay que sincronizarlo en JS. Solo asegurar que ningun cleanup lo borre (ver §28.3.A).

**Fix B:** Si no viene pre-renderizado, agregar campo read-only separado:
```python
responsable_uuid = serializers.CharField(source='responsable.uuid', read_only=True, allow_null=True)
```

---

#### D) Race condition entre carga de catalogo y asignacion de valor

```
Escenario A: cargarDetalles() termina ANTES que cargarCatalogo()
  → asigna data-selected en el <select>
  → select.value = uuid falla (no hay opciones aun)
  → cuando cargarCatalogo() termina, lee data-selected → selecciona ✓

Escenario B: cargarCatalogo() termina ANTES que cargarDetalles()
  → opciones existen pero data-selected no esta
  → ninguna opcion seleccionada
  → cuando cargarDetalles() termina, select.value = uuid funciona ✓ (opciones ya existen)
```

**Bug real:** Solo si `cargarCatalogo()` NO lee `data-selected` al terminar de poblar opciones. Solucion robusta:

```javascript
// En cargarCatalogo(), al final del loop de opciones:
const preSelected = select.getAttribute('data-selected');
if (preSelected) {
    const opt = [...select.options].find(o => o.value === preSelected);
    if (opt) opt.selected = true;
}
```

---

#### E) Guard `editorEventsInitialized` bloquea recarga de catalogos

```javascript
// BUG — segunda apertura del offcanvas no recarga catalogos
function initEditorEvents() {
    if (editorEventsInitialized) return;   // sale antes de cargarCatalogo()
    editorEventsInitialized = true;
    cargarCatalogo();
}
```

**Fix:** El flag se debe resetear en el evento `hidden.bs.offcanvas` para que la siguiente apertura recargue correctamente:
```javascript
offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
    editorEventsInitialized = false;
});
```

---

### 28.4. Flujo de Diagnostico Rapido (5 Pasos)

```
1. Abrir offcanvas edicion en browser + DevTools abierto
2. Identificar los IDs de los campos en blanco (#campo-id)
3. Buscar en {app}_editor.js:
     a. ¿Hay cleanup que limpie esos IDs sin condicion? → §28.3.A
     b. ¿Hay select.value = data.campo_id con campo_id undefined? → §28.3.B o §28.3.C
4. Ejecutar GET /api/v1/{app}/{uuid}/ y verificar:
     a. ¿El campo existe en la respuesta JSON?
     b. ¿Es UUID o PK entero?
     c. ¿Esta marcado write_only (ausente en GET)?
5. Aplicar el fix correspondiente del checklist §28.3
```

---

### 28.5. Tabla de Fix por Tipo de Campo

| Tipo de campo | Fix en serializer | Fix en template | Fix en JS |
|---------------|------------------|-----------------|-----------|
| Select estatico vacio | — | Agregar `{% if instance.campo == val %}selected{% endif %}` | — |
| Select dinamico (UUID) | Agregar `campo_uuid = CharField(source='campo.uuid', read_only=True)` | `data-selected="{{ instance.campo.uuid\|default:'' }}"` | Leer `data.campo_uuid` |
| Input text/number/date vacio | — | Agregar `value="{{ instance.campo\|default:'' }}"` | — |
| Campo borrado por cleanup | — | Ya pre-renderizado ✓ | Proteger cleanup: `&& !currentInstance` |
| Campo write_only ausente en GET | Quitar `write_only` o agregar campo `_uuid` read-only | — | Actualizar clave leida |

---

### 28.6. Reglas Obligatorias

- **[OBLIGATORIO]** Todo `<select>` cargado dinamicamente con opciones UUID DEBE tener su valor de pre-seleccion expuesto en el serializer como UUID (no PK entero).
- **[OBLIGATORIO]** Todo bloque de limpieza de campos en funciones de navegacion wizard/step DEBE verificar `!currentInstance` antes de borrar valores.
- **[PROHIBIDO]** Limpiar campos de formulario en funciones de navegacion sin discriminar modo creacion vs modo edicion.
- **[OBLIGATORIO]** Al agregar un campo `_uuid` read-only en un serializer con `exclude`, no se requiere actualizar `Meta.fields` — se incluye automaticamente.
- **[PROHIBIDO]** Usar `pk=valor_uuid` en selectors cuando `valor_uuid` es un UUID string (type mismatch en PostgreSQL para columnas integer PK).

---

## [ZERO-HARDCODING] 29. Norma de Abstraccion Zero-Hardcoding (Escalabilidad a 1000+ Tenants)

**REGLA FUNDAMENTAL — Aplica a TODO el proyecto: `apps/public/`, `apps/tenant/`, `tests/`, `scripts/`, `scratch/`**

La plataforma SINTEL debe poder aprovisionar y gestionar cualquier numero de tenants sin requerir la modificacion de una sola linea de codigo estatico. Esta norma define los patrones OBLIGATORIOS y los antipatrones PROHIBIDOS.

---

### 29.1. Antipatron A — Listas Estaticas de Tenants [PROHIBIDO]

**[PROHIBIDO]** — Cualquier iteracion manual o lista hardcodeada de schemas o dominios:

```python
# PROHIBIDO
for schema in ['home', 'cliente', 'putito', 'empresa1']:
    ...
tenants = ["public", "empresa_a", "empresa_b"]
```

**[OBLIGATORIO]** — Sustituir SIEMPRE por consultas dinamicas al ORM del modelo `Client`:

```python
# CORRECTO
from apps.public.tenants.models import Client
for tenant in Client.objects.exclude(schema_name='public').filter(is_active=True):
    with tenant_context(tenant):
        ...
```

**Variante con filtro opcional `--schema`:**
```python
tenants = Client.objects.exclude(schema_name='public').filter(is_active=True)
if schema_filter:  # argumento CLI opcional
    tenants = tenants.filter(schema_name=schema_filter)
```

---

### 29.2. Antipatron B — Nombres Propios y Dominios Fijos [PROHIBIDO]

**[PROHIBIDO]** — Cadenas literales apuntando a tenants especificos de produccion:

```python
# PROHIBIDO
tenant = Client.objects.get(schema_name='home')
domain = Domain.objects.get(domain='cliente.sintel.net.co')
host = "home.sintel.net.co"
url = "http://tupapi.sintel.net.co/api/"
```

**[OBLIGATORIO]** — Resolver dinamicamente desde el ORM o variables de entorno:

```python
# CORRECTO
tenant = Client.objects.exclude(schema_name='public').filter(is_active=True).first()
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
host = domain.domain  # resuelto en runtime
url = f"{protocol}://{domain.domain}/api/"
```

**[EXCEPCION DOCUMENTADA]** — `schema_name='public'` y el dominio raiz `sintel.net.co` son la unica excepcion permitida. Son el dominio de la plataforma, no un tenant privado. Su DNS se gestiona independientemente. Esta excepcion DEBE estar marcada con comentario explicito en el codigo.

---

### 29.3. Antipatron C — Ejemplos Hardcodeados en Logs y Help Text [PROHIBIDO]

**[PROHIBIDO]** — Ejemplos en `help=`, `print()`, docstrings que usen nombres reales de tenants:

```python
# PROHIBIDO
help = "Ejecuta el proceso. Ej: --schema cliente"
print("Accede via: http://home.sintel.net.co/")
print("client = Client.objects.get(schema_name='putito')")
```

**[OBLIGATORIO]** — Usar marcadores genericos abstractos:

```python
# CORRECTO
help = "Ejecuta el proceso. Ej: --schema {schema_name}"
print("Accede via: http://{schema}.sintel.net.co/")
print("client = Client.objects.get(schema_name='<schema_name>')")
```

---

### 29.4. Antipatron D — Fixtures de Tests con Nombres de Produccion [PROHIBIDO]

**[PROHIBIDO]** — Fixtures que referencian tenants de produccion o asumen estado de la BD real:

```python
# PROHIBIDO
tenant = Client.objects.filter(schema_name='home').first()
tenant = Client(schema_name='home', nombre='Home Test Tenant', ...)
domain = 'home.sintel.net.co'
client.defaults["HTTP_HOST"] = "cliente.sintel.net.co"
```

**[OBLIGATORIO]** — Nombres claramente transaccionales que no colisionen con produccion:

```python
# CORRECTO — schema con prefijo "test_", nombres genericos, dominios ".sintel.local"
schema_name = "test_schema_01"
tenant = Client(schema_name=schema_name, nombre='Test Tenant Isolation', ...)
domain = f"{schema_name}.sintel.local"
client.defaults["HTTP_HOST"] = domain  # o f"{self.tenant.schema_name}.sintel.local"
```

**Convencion de nombres para fixtures de tests:**
| Elemento | Patron correcto | Patron incorrecto |
|---|---|---|
| schema_name | `test_{app}_{descripcion}_01` | `home`, `cliente`, `empresa` |
| domain | `test-{desc}-01.sintel.local` | `home.sintel.net.co`, `cliente.sintel.net.co` |
| HTTP_HOST | `f"{self.tenant.schema_name}.sintel.local"` | `"home.sintel.net.co"` |
| nombre Tenant | `"Test {App} Tenant"` | `"Home Test Tenant"` |

---

### 29.5. Alcance y Enforcement

**Alcance total — aplica a:**
- `apps/public/` — management commands, tasks, services, tests
- `apps/tenant/` — tests, scripts de utilidad
- `tests/` — todos los fixtures y factories
- `scripts/` — scripts de diagnostico y utilidad
- `scratch/` — scripts de desarrollo/debug
- `config/` — settings y configuraciones

**Enforcement — validacion obligatoria antes de merge:**
```bash
# Buscar violaciones de tipo B (strings literales de tenants conocidos)
grep -rn "'home'\|'cliente'\|'putito'\|'tupapi'\|home\.sintel\.com\|cliente\.sintel\.com" \
    apps/ tests/ scripts/ scratch/ --include="*.py" \
    | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema" \
    | grep -v "schema_name='public'\|# EXCEPCION"
# Resultado esperado: 0 lineas
```

**Patron de argumentos CLI para scripts:**
Todo script o management command que opere sobre tenants DEBE:
1. Aceptar `--schema <schema_name>` como argumento opcional
2. Sin `--schema`: iterar `Client.objects.exclude(schema_name='public').filter(is_active=True)`
3. Con `--schema`: filtrar `tenants.filter(schema_name=schema_filter)`

**Ejemplo patron completo:**
```python
# Patron canonico para scripts/management commands
schema_filter = None
args = sys.argv[1:]
for i, arg in enumerate(args):
    if arg == "--schema" and i + 1 < len(args):
        schema_filter = args[i + 1]

tenants = Client.objects.exclude(schema_name="public").filter(is_active=True)
if schema_filter:
    tenants = tenants.filter(schema_name=schema_filter)

for tenant in tenants:
    with tenant_context(tenant):  # o schema_context(tenant.schema_name)
        # logica de negocio...
        pass
```

---

### 29.6. Tabla de Decision Rapida

| Situacion | Antipatron | Patron correcto |
|---|---|---|
| Iterar tenants | `for s in ['home','cliente']` | `Client.objects.exclude(schema_name='public')` |
| Obtener un tenant | `Client.objects.get(schema_name='home')` | `Client.objects.filter(...).first()` con arg CLI |
| URL de tenant | `"http://home.sintel.net.co"` | `f"http://{domain.domain}"` donde `domain` viene del ORM |
| HTTP_HOST en test | `"home.sintel.net.co"` | `f"{self.tenant.schema_name}.sintel.local"` |
| Schema en fixture | `schema_name='cliente'` | `schema_name='test_feature_01'` |
| Ejemplo en help | `ej: --schema putito` | `ej: --schema {schema_name}` |
| DNS management command | lista `['home','cliente']` | `Client.objects.exclude(schema_name='public')` |

---

## [ORM-SELECTORS] 30. Marco de Referencia: Constantes de Selector y Serializer (Zero-Collision Pattern)

**Aplica a:** todas las apps bajo `apps/tenant/` y `apps/public/` sin excepcion.

---

### 30.1. Raiz del problema — dos contextos, una sola constante

Las constantes `LIST_FIELDS` / `DETAIL_FIELDS` en `services/selectors.py` son el SSoT de campos por app.
Se usan en **dos contextos con reglas incompatibles**:

| Contexto | Uso tipico | Acepta `rel__campo` |
|---|---|---|
| **Queryset ORM** `.only()` | `Model.objects.only(*DETAIL_FIELDS)` | SI — traversal ORM valida |
| **Serializer** `Meta.fields` | `fields = tuple(DETAIL_FIELDS) + (...)` | NO — DRF lanza `ImproperlyConfigured` |

Cuando una sola constante alimenta ambos contextos, **cualquier string con `__` (doble guion bajo) la hace explotar** en tiempo de request (no de arranque — `django check` no lo detecta).

> **Incidente de referencia (2026-06-01):**
> `django.core.exceptions.ImproperlyConfigured: Field name sede__nombre is not valid
>  for model Factura in FacturaDetailSerializer`

---

### 30.2. Taxonomia de strings validos por contexto

| Tipo de string | Ejemplo | `.only()` ORM | `Meta.fields` serializer |
|---|---|---|---|
| Campo de modelo directo | `"nombre"`, `"empresa_id"`, `"sede_id"` | SI | SI |
| FK id autogenerado | `"cliente_id"`, `"sede_id"` | SI | SI |
| Traversal de relacion | `"sede__nombre"`, `"cliente__uuid"` | SI | NO |
| Campo de serializer declarado | `"sede_nombre"`, `"tipo_display"` | NO | SI |

**Regla de oro:** si el string tiene `__` (doble guion bajo), no puede estar en `LIST_FIELDS` ni `DETAIL_FIELDS` si esas constantes se usan en `Meta.fields`.

---

### 30.3. Patron de riesgo — detectarlo

En `api/serializers.py` de cualquier app, buscar:

```python
# PATRON DE RIESGO — la constante se pasa directo a Meta.fields
fields = tuple(DETAIL_FIELDS) + ("campo_extra",)
fields = DETAIL_FIELDS + ("campo_extra",)
fields = tuple(LIST_FIELDS)
```

Si existe alguno de estos patrones, la constante referenciada **NUNCA puede contener strings con `__`**.

---

### 30.4. Arquitectura correcta — Zero-Collision Pattern

Separar en tres niveles en `services/selectors.py`:

```python
# ============================================================
# NIVEL 1: Campos de modelo puro — validos en AMBOS contextos
# Regla: solo nombres de atributos directos del modelo Django.
#        Incluye FK ids (campo_id). NUNCA doble guion bajo.
# ============================================================
LIST_FIELDS = (
    "id", "uuid", "empresa_id",
    "nombre", "estado", "fecha_creacion",
    "cliente_id",           # FK id autogenerado — valido en ambos
    "sede_id",              # FK id autogenerado — valido en ambos
)

DETAIL_FIELDS = LIST_FIELDS + (
    "descripcion", "observaciones",
    "created_at", "updated_at",
    # solo atributos directos del modelo — nunca rel__campo
)

# ============================================================
# NIVEL 2: Traversals ORM — SOLO para .only(), nunca en Meta.fields
# Prefijo _ = uso interno del modulo selector.
# Nombrar por relacion: _<RELACION>_TRAVERSALS
# ============================================================
_CLIENTE_TRAVERSALS   = ("cliente__razon_social", "cliente__numero_documento")
_SEDE_TRAVERSALS      = ("sede__nombre", "sede__uuid")
_PROVEEDOR_TRAVERSALS = ("proveedor__razon_social",)
_AREA_TRAVERSALS      = ("area__nombre",)

# ============================================================
# NIVEL 3: Clases Selector — usan NIVEL 1 + NIVEL 2 juntos en .only()
# ============================================================
class MiModeloSelector:
    @staticmethod
    def qs_list(empresa_id: int):
        return MiModelo.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            "cliente", "sede"    # obligatorio para cada relacion en TRAVERSALS
        ).only(
            *LIST_FIELDS,
            *_CLIENTE_TRAVERSALS,   # inline — no contaminan Meta.fields
            *_SEDE_TRAVERSALS,
        )

    @staticmethod
    def qs_detail(empresa_id: int):
        return MiModelo.objects.filter(
            empresa_id=empresa_id
        ).select_related(
            "cliente", "sede", "proveedor"
        ).only(
            *DETAIL_FIELDS,
            *_CLIENTE_TRAVERSALS,
            *_SEDE_TRAVERSALS,
            *_PROVEEDOR_TRAVERSALS,
        )
```

---

### 30.5. Patron correcto — serializer

```python
# api/serializers.py

# CORRECTO: campos de serializer usan notacion con PUNTO (source="rel.campo")
# Nunca doble guion bajo en nombres de campos de serializer.

cliente_nombre    = serializers.CharField(source="cliente.razon_social",   read_only=True, allow_null=True)
sede_nombre       = serializers.CharField(source="sede.nombre",             read_only=True, allow_null=True)
proveedor_nombre  = serializers.CharField(source="proveedor.razon_social",  read_only=True, allow_null=True)

class Meta:
    model = MiModelo
    # DETAIL_FIELDS solo contiene atributos de modelo (Nivel 1) — sin __
    # Los campos de serializer se agregan explicitamente
    fields = tuple(DETAIL_FIELDS) + (
        "cliente_nombre",    # CharField declarado arriba — notacion punto
        "sede_nombre",       # CharField declarado arriba — notacion punto
        "sede",              # UUIDOrPKRelatedField o PrimaryKeyRelatedField
        # NUNCA: "sede__nombre", "cliente__razon_social"
    )
```

---

### 30.6. Tabla de equivalencias — ORM vs Serializer

| Lo que quieres exponer | En `.only()` (selector) | En `Meta.fields` (serializer) |
|---|---|---|
| Nombre del cliente | `"cliente__razon_social"` | `cliente_nombre` via `CharField(source="cliente.razon_social")` |
| Nombre de la sede | `"sede__nombre"` | `sede_nombre` via `CharField(source="sede.nombre")` |
| UUID de la sede | `"sede__uuid"` | `sede_uuid` via `UUIDField(source="sede.uuid")` o `SerializerMethodField` |
| ID de FK (entero) | `"sede_id"` | `"sede_id"` — directo, valido en ambos |
| Objeto FK completo | no aplica en `.only()` | `sede` via `PrimaryKeyRelatedField` / `UUIDOrPKRelatedField` |

---

### 30.7. Anti-patrones catalogados — PROHIBIDOS

```python
# ❌ ANTIPATRON A — traversal en constante compartida con Meta.fields
LIST_FIELDS = (
    "id", "uuid",
    "sede__nombre",          # PROHIBIDO si LIST_FIELDS va a Meta.fields
    "cliente__razon_social", # PROHIBIDO
)

# ❌ ANTIPATRON B — traversal directa en Meta.fields del serializer
class Meta:
    fields = ("id", "uuid", "sede__nombre")  # PROHIBIDO — DRF explota

# ❌ ANTIPATRON C — source con doble guion bajo en serializer
sede_nombre = serializers.CharField(source="sede__nombre")  # PROHIBIDO
# Correcto: source="sede.nombre" (punto, no doble guion bajo)

# ❌ ANTIPATRON D — omitir select_related al usar traversal en .only()
Model.objects.only("sede__nombre")  # Falla silenciosamente sin select_related
# Correcto: .select_related("sede").only("sede__nombre")
```

---

### 30.8. Reglas de select_related obligatorio

Cuando se agrega una traversal `_*_TRAVERSALS` al `.only()`, el `select_related` correspondiente es **obligatorio**:

| Traversal en `.only()` | `select_related` requerido |
|---|---|
| `"sede__nombre"` | `.select_related("sede")` |
| `"cliente__razon_social"` | `.select_related("cliente")` |
| `"proveedor__nit"` | `.select_related("proveedor")` |
| `"area__nombre"` | `.select_related("area")` |
| `"factura_costo__numero"` | `.select_related("factura_costo")` |
| `"sede__area__nombre"` | `.select_related("sede__area")` |

Sin `select_related`, Django hace N+1 queries o retorna `None` silenciosamente.

---

### 30.9. Auditoria de apps — estado actual (2026-06-01)

Apps que usan el patron de riesgo `tuple(FIELDS)` en `Meta.fields`:

| App | Serializer | Patron | Estado |
|---|---|---|---|
| `facturas` | `FacturaDetailSerializer` | `tuple(DETAIL_FIELDS) + (...)` | CORREGIDO — `_SEDE_ONLY_TRAVERSALS` separadas |
| `proveedores` | `ProveedorDetailSerializer` | `DETAIL_FIELDS + (...)` | Sin traversals en la constante — seguro |

Apps que usan listas explicitas en `Meta.fields` (patron seguro — traversals en constantes no afectan):

| App | Patron serializer | Traversals en constantes LIST/DETAIL_FIELDS | Riesgo |
|---|---|---|---|
| `gastos` | Lista explicita | SI — solo para `.only()` | NINGUNO |
| `proyectos` | `exclude = ['empresa']` | SI — `_SEDE_DETAIL_TRAVERSALS` separadas | NINGUNO |
| `cotizaciones` | Lista explicita | SI — `_SEDE_LIST_TRAVERSALS` separadas | NINGUNO |
| `inventario` | Lista explicita | SI — `_SEDE_ONLY_TRAVERSALS` separadas | NINGUNO |
| `empleados` | Lista explicita | SI — solo para `.only()` | NINGUNO |
| `perfil` | Lista explicita | SI (`user__email`, `departamento__nombre`) | NINGUNO — no se usan en Meta.fields |
| `clientes` | Lista explicita | Sin traversals | NINGUNO |

---

### 30.10. Verificacion automatica — ejecutar antes de mergear

```bash
# 1. Detectar traversals ORM dentro de constantes LIST_FIELDS / DETAIL_FIELDS
#    (lineas que esten dentro de esas constantes y tengan doble guion bajo)
docker compose exec web python -c "
import ast, pathlib, sys
errors = []
for f in pathlib.Path('apps/tenant').rglob('selectors.py'):
    src = f.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ('LIST_FIELDS', 'DETAIL_FIELDS'):
                    for elt in ast.walk(node.value):
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and '__' in elt.value:
                            errors.append(f'{f}:{elt.lineno} -> {t.id} contiene traversal: {elt.value!r}')
if errors:
    print('ERRORES:')
    for e in errors: print(' ', e)
    sys.exit(1)
else:
    print('OK: ninguna traversal ORM en LIST_FIELDS/DETAIL_FIELDS')
"

# 2. Detectar serializers que usan tuple(FIELDS) — patron de riesgo
grep -rn "tuple(LIST_FIELDS)\|tuple(DETAIL_FIELDS)\|= LIST_FIELDS +\|= DETAIL_FIELDS +" \
  apps/tenant/*/api/serializers.py apps/public/*/api/serializers.py 2>/dev/null
# Para cada resultado: ejecutar verificacion 1 sobre su selectors.py correspondiente

# 3. Smoke test serializers — instanciar y forzar build de campos
docker compose exec web python -c "
import django; django.setup()
import importlib, pathlib, sys
errors = []
for f in pathlib.Path('apps/tenant').rglob('serializers.py'):
    mod_path = str(f).replace('/', '.').replace('\\\\', '.').replace('.py', '')
    try:
        mod = importlib.import_module(mod_path)
        for name in dir(mod):
            cls = getattr(mod, name)
            if isinstance(cls, type) and hasattr(cls, 'Meta') and hasattr(cls.Meta, 'model'):
                try:
                    _ = cls().fields
                except Exception as e:
                    errors.append(f'{name}: {e}')
    except Exception:
        pass
if errors:
    for e in errors: print('ERROR:', e)
    sys.exit(1)
else:
    print('OK: todos los serializers instancian sin error')
"
```

---

### 30.11. Checklist al agregar cualquier FK a una app existente

- [ ] FK id (`campo_id`) agregado a `LIST_FIELDS` y `DETAIL_FIELDS` (valido en ambos)
- [ ] Traversals (`campo__subcampo`) en constante privada `_<RELACION>_TRAVERSALS`
- [ ] `select_related("<relacion>")` agregado en cada metodo selector que use las traversals
- [ ] `campo_nombre = CharField(source="relacion.campo")` en serializer (punto, no `__`)
- [ ] Si el serializer usa `tuple(FIELDS)` en Meta.fields: auditar que la constante NO tiene `__`
- [ ] Verificacion 30.10 paso 1 pasa en verde
- [ ] `django check` limpio
- [ ] Smoke test serializer: `s = MiSerializer(); _ = s.fields` sin excepcion

---

## [FRONTEND-SSOT] 31. Unica Fuente de Verdad para Frontend — `.agents/skills/frontend/`

**REGLA OBLIGATORIA — Aplica a toda tarea que toque HTML, JS, HTMX, Offcanvas, Tabulator o cualquier componente UI.**

Antes de escribir, modificar o revisar cualquier codigo frontend, el agente DEBE consultar los skills de frontend como unica fuente de verdad:

```
.agents/skills/frontend/
  htmx.md              — Patrones HTMX, hx-on::, eventos, OOB, polling
  ui-management.md     — Offcanvas/Modal lifecycle, UIManager, backdrops
  crud-fsd.md          — Arquitectura CRUD completa (HTMX + Tabulator + Vanilla JS)
  vanilla-js.md        — Namespace, window.http(), UUID sin parseInt, CustomEvents
  tabulator.md         — TabulatorFactory, formatters, cellClick, replaceData
  dom-ids-sync.md      — Sincronizacion IDs HTML ↔ JS, data-attributes
  creacion_item_full.md — Patron completo Add Association end-to-end
```

### 31.1. Protocolo de consulta obligatorio

```
ANTES de cualquier accion frontend:
  1. Identificar categoria: HTMX / Offcanvas / JS / Tabulator / DOM
  2. Abrir el skill correspondiente en .agents/skills/frontend/
  3. Aplicar exactamente el patron documentado
  4. Si el skill no cubre el caso → escalar al usuario, NO improvisar
```

### 31.2. Prohibiciones derivadas de los skills

| Prohibicion | Skill de referencia |
|---|---|
| `bootstrap.Offcanvas.getOrCreateInstance(el).show()` sin dispose | ui-management.md §2, AGENTS.md §26 |
| `hx-on::after-settle` en atributos de botones | htmx.md §12.1 |
| `hx-on::after-swap` en atributos de botones | htmx.md §12.1 (usar `after-request`) |
| `htmx:afterSwap` en `document.addEventListener` | htmx.md §12.2-B (usar `afterSettle`) |
| `setTimeout()` como sustituto de `afterSettle` | htmx.md §12.2-B |
| `parseInt()` sobre campos FK/UUID de API | vanilla-js.md §4, AGENTS.md §27 |
| Traversals `campo__subcampo` en `LIST_FIELDS`/`DETAIL_FIELDS` | creacion_item_full.md, AGENTS.md §30 |
| `new Tabulator()` directamente | tabulator.md §1 (usar TabulatorFactory) |
| Codigo JS global sin namespace `window.Sintel.<App>` | vanilla-js.md §1 |

### 31.3. Patron de apertura de offcanvas — decision tree

```
¿Desde un botón HTML con hx-get?
  └─ hx-on::after-request="...UIManager.handleOffcanvas(el,'show')..."  [htmx.md §12.1]

¿Desde document.addEventListener en un modulo JS?
  └─ htmx:afterSettle → UIManager.handleOffcanvas(el,'show')           [htmx.md §12.2-B]

¿Desde htmx.ajax().then() en un modulo JS?
  └─ UIManager.handleOffcanvas(el,'show') directamente                 [ui-management.md §2]

¿UIManager no disponible? → fallback seguro:
  const prev = bootstrap.Offcanvas.getInstance(el);
  if (prev) prev.dispose();
  document.querySelectorAll('.offcanvas-backdrop').forEach(b=>b.remove());
  new bootstrap.Offcanvas(el).show();
```

### 31.4. Enforcement

Al iniciar cualquier tarea con cambios de UI, el agente debe declarar en su respuesta:
> "Consultado: .agents/skills/frontend/[archivo.md] — patron [seccion]"

Si no puede determinar el patron correcto leyendo los skills, escalar al usuario antes de implementar.