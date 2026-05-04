# AGENTS.md

---
name: reglas
description: Reglas Core de Arquitectura y Desarrollo - Proyecto SINTEL v2.62.0
---

# [CORE] SINTEL v2.62.0 - Reglas de Arquitectura y Estructura de Proyecto

Estas reglas son **ESTRICTAS, INMUTABLES Y OBLIGATORIAS** para cualquier modificación, refactorización o creación de código en este proyecto. Este archivo debe ser procesado y asimilado antes de implementar cualquier prompt o sugerencia de código.

Este documento refleja el **ADN real** del codebase: patrones, convenciones y estructuras que ya están materializados en producción.

## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.
- **RAZÓN**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACIÓN**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.

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
   - `__init__.py`: Punto de entrada del paquete. Exporta las clases principales para imports limpios.
   - `crud_service.py`: Acceso a datos puro y persistencia transaccional (`@transaction.atomic`). Sin lógica de negocio.
   - `business_service.py`: Orquestación y lógica de negocio (idempotencia, validaciones semánticas, cálculos, persistencia desde DTO). Sin acceso directo a ViewSets.
   - `selectors.py`: Consultas `GET` optimizadas (read-only). Define tuplas `LIST_FIELDS`, `DETAIL_FIELDS` como SSoT de campos, y clases `<Modelo>Selector` con `@staticmethod` que retornan QuerySets filtrados por `empresa_id` con `.only()`.
   - `services.py`: Fachada estable que reexporta desde `business_service.py` para compatibilidad de imports existentes.
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

1. **PASO INICIAL OBLIGATORIO:** Antes de ejecutar CUALQUIER cambio en una app, se DEBE consultar SIEMPRE de forma inicial el documento de flujo de la misma. Todas las aplicaciones tienen este documento en su raíz. (Ejemplo: `apps/tenant/clientes/AUDITORIA_FLUJO_CLIENTES.md` o `apps/<app_name>/flujo_app.md`).
2. **Documentación Global:** `documentacion/arquitectura_general.md` es la referencia suprema.
3. **Flujo por Aplicación:** Cada `apps/<app_name>/` DEBE contener y mantener un archivo de auditoría/flujo que describa su lógica secuencial específica.
4. **Gestión de Documentos:** Todos los demás archivos `.md` de soporte deben residir exclusivamente en `documentacion/`.

## [BACKEND] 4. Capa de Datos y Optimización Backend (Zero Waste)

1. **Cero Creación de Archivos `.py` no Autorizados:** Queda PROHIBIDO crear nuevos archivos `.py` fuera de la estructura de Service Layer establecida (`services/selectors.py`, `services/crud_service.py`, `services/business_service.py`, `services/api_mixins.py`, `services/__init__.py`). Cualquier otro archivo nuevo requiere autorización explícita.
2. **Restricción de Ambientes (`apps/public/`):** Estrictamente PROHIBIDO modificar, refactorizar o crear archivos dentro de `apps/public/` sin la aprobación explícita (requiere RFC/Issue y etiqueta `needs-admin-approval`). Toda lógica nueva debe acoplarse a la estructura existente.
3. **Prohibición de `views.py` Tradicionales:** No usar el archivo `views.py` legacy para lógica de negocio.
4. **Multi-Tenant Estricto (Zero-Trust SaaS):** Prohibido realizar consultas a modelos sin filtrar por la empresa del tenant (`empresa` o `empresa_id`) en las `TENANT_APPS`.
5. **Optimización Estricta de Consultas (Zero Waste):**
   - **ESTRICTAMENTE PROHIBIDO** el uso de `.all()`, o `.filter()` sin encadenar un `.only()` o `.defer()`.
   - Toda consulta DEBE especificar explícitamente los campos necesarios para minimizar la saturación de memoria y cuellos de botella en la red.
   - **Patrón DRF obligatorio:** `queryset = Model.objects.none()` a nivel de clase + override en `get_queryset()` con `.only()`/`.defer()` según la acción.
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

## [GOVERNANCE] 16. Reglas de Gobernanza por Aplicación

1. **Módulo Privados (`apps/tenant/nombre_app`):**
   - **Autorización Obligatoria**: Antes de realizar cualquier modificación, refactorización o creación de código en este módulo, se DEBE solicitar autorización y aprobación explícita al USUARIO.
   - **Lectura Previa SSoT**: Es OBLIGATORIO leer el archivo `AUDITORIA_FLUJO_COMPLETO.md` (o `AUDITORIA_INVENTARIO.md` si existe) antes de proponer cambios. Toda modificación debe estar alineada con la arquitectura allí documentada.

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

## [CONTAB] 18. Capa de Integración Contable Centralizada (v3.0 — Fase 1)

**PRINCIPIO:** Todo asiento contable es generado EXCLUSIVAMENTE por el `Contabilizador`. Ninguna app puede crear `AsientoContable` ni `MovimientoContable` directamente.

### 18.1. Paquete de Integración (`apps/tenant/contabilidad/integracion/`)

| Módulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador único — valida, resuelve cuentas, construye y persiste asientos atómicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) → código PUC vía `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, período abierto, documento origen existe |
| `excepciones.py` | Jerarquía de errores (`ContabilidadError` y subclases) |

### 18.2. DTOs — Contrato Inmutable

```python
# DTO principal — frozen dataclass (inmutable por diseño)
TransaccionEconomica(
    tipo=TipoTransaccion.COMPRA_GASTO,    # Enum
    fecha=date(2026, 5, 3),
    descripcion="...",
    tercero=TerceroSnapshot(...),          # Snapshot, sin FK
    lineas=[LineaTransaccion(...)],        # Lista de partidas
    documento_origen=DocumentoOrigen(...) # Trazabilidad para idempotencia
)

# Campo critico en LineaTransaccion e ImpuestoLinea:
LineaTransaccion(concepto='GASTO_OPERATIVO', monto=..., lado='DEBE')   # default='DEBE'
ImpuestoLinea(tipo='RETEFUENTE', valor=..., lado='HABER')              # default='HABER'
```

- **`lado`**: controla qué columna del asiento recibe el monto (`'DEBE'` o `'HABER'`). Campo OBLIGATORIO para cuadratura correcta.
- **Idempotencia**: `documento_origen` (app_label + modelo + id) mapea a `AsientoContable.documento_origen_*`. La restricción `UNIQUE` en BD garantiza un solo asiento por documento fuente.

### 18.3. Servicio de Materialización por App Fuente

Cada app fuente expone su propia función en `apps/tenant/contabilidad/services/asientos_service.py`:

```python
# PATRON OBLIGATORIO para toda app fuente
from apps.tenant.contabilidad.services.asientos_service import materializar_asiento_desde_gasto

asiento = materializar_asiento_desde_gasto(gasto)  # Acepta objeto, no ID
```

**Reglas del patrón:**
- La función construye el DTO completo y llama a `Contabilizador(empresa_id).contabilizar(dto)`
- El hook en el service de la app fuente debe estar dentro de `try/except Exception` (no bloquear el negocio)
- Errores de contabilización se loguean como `WARNING`, no como `ERROR` crítico

### 18.4. Cuadratura Obligatoria (DEBE = HABER)

Todo asiento DEBE cuadrar. Fórmula para `COMPRA_GASTO`:

```
DEBE 51xxxx Gasto              [subtotal]
HABER 236540 Retefuente        [retefuente]  (si > 0)
HABER 236801 ReteICA           [reteica]     (si > 0)
HABER 233595 CXP Proveedor     [total = subtotal - retenciones]
─────────────────────────────────────────────
TOTAL DEBE == TOTAL HABER == subtotal
```

### 18.5. ReglaContable — Mapeo PUC por Tenant

- Modelo: `ReglaContable(empresa, tipo_transaccion, concepto, cuenta_codigo, activo)`
- Seed inicial: `python manage.py seed_reglas_contables`
- `ResolverCuentas.resolver_cuenta(concepto, tipo_transaccion, cuenta_hint=None)` → `str PUC`
- `cuenta_hint` sobreescribe el lookup del catálogo (para gastos con `Gasto.codigo_contable` configurado)

### 18.6. Numero de Asiento — Formato Canónico

- Asiento nuevo: `ASI-{YYYYMMDD}-{UUID8}` (ej. `ASI-20260503-A1B2C3D4`)
- Reversal: `RVER-{YYYYMMDD}-{UUID8}`
- Generado por `Contabilizador._construir_asiento()` — **nunca por el caller externo**

### 18.7. Prohibiciones Absolutas

- **PROHIBIDO** crear `AsientoContable` o `MovimientoContable` directamente desde ViewSets, Services de otras apps o Signals
- **PROHIBIDO** pasar `empresa_id` dentro del DTO (`TransaccionEconomica.empresa_id` queda `None` — lo inyecta el Contabilizador)
- **PROHIBIDO** usar `lado='DEBE'` para impuestos/retenciones (su natural es `'HABER'`)
- **PROHIBIDO** hardcodear códigos PUC en apps fuente — siempre usar `cuenta_hint` o `ReglaContable`

## [MEMORY] 19. Memory Bank y Estado a Largo Plazo (MEMORY.md)

**REGLA OBLIGATORIA PARA TODOS LOS AGENTES Y EDITORES DE CÓDIGO (Claude Code, Cursor, Copilot, Antigravity, etc.)**

1. **Lectura Inicial Obligatoria:** Al iniciar cualquier sesión, tarea o contexto nuevo, el agente/editor DEBE leer el archivo `MEMORY.md` ubicado en la raíz del proyecto.
2. **Propósito del Memory Bank:** `MEMORY.md` es la fuente canónica del estado actual del proyecto, decisiones arquitectónicas recientes (ADRs) y el progreso activo. Su objetivo es evitar refactorizaciones cíclicas y la pérdida de contexto en tareas extensas.
3. **Mantenimiento Continuo:** Al finalizar hitos importantes, implementar cambios estructurales o resolver bugs complejos, el agente DEBE actualizar proactivamente `MEMORY.md` para reflejar el nuevo estado, garantizando que futuras sesiones hereden este conocimiento.
4. **Inmutabilidad de ADRs:** Las decisiones listadas bajo la sección de ADRs en `MEMORY.md` no pueden ser alteradas ni refactorizadas sin autorización explícita del usuario principal.

---

## Apendice A. Comandos de Operacion
- **Instalación:** `pip install -r requirements.txt`
- **Docker (Desarrollo):** `docker compose up --build`
- **Migraciones Multi-Tenant:** `docker compose exec web python manage.py migrate_schemas`
- **Migraciones Shared:** `docker compose exec web python manage.py migrate_schemas --shared`
- **Linter (Ruff):** `ruff check .`
- **Formateador (Ruff):** `ruff format .`
- **Testing:** `python manage.py test` / `python manage.py test apps.tenant.<app_name>`
- **Compilación Python:** `python -m py_compile archivo.py` (validación pre-PR)