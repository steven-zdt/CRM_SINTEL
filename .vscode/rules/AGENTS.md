---
name: reglas-vscode
description: Copia localizada de AGENTS.md para reglas de editor/CI
---

# AGENTS.md

---
name: reglas
description: Reglas Core de Arquitectura y Desarrollo - Proyecto SINTEL v2.61.4
---

# [CORE] SINTEL v2.61.4 - Reglas de Arquitectura y Estructura de Proyecto

Estas reglas son **ESTRICTAS, INMUTABLES Y OBLIGATORIAS** para cualquier modificación, refactorización o creación de código en este proyecto. Este archivo debe ser procesado y asimilado antes de implementar cualquier prompt o sugerencia de código.

## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.
- **RAZÓN**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACIÓN**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.

## [TECH] 1. Tecnologías Implementadas y Stack Base

### Ejemplo: Tecnologías y Patrones Implementados (Generales por App)

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
- Modularización estricta por responsabilidad:
   - `crud_service.py`: Acceso a datos puro (QuerySets optimizados, sin lógica de negocio ni validaciones).
   - `business_service.py`: Orquestación y lógica de negocio (idempotencia, naturaleza, validaciones, persistencia desde DTO, etc.).
   - `services.py`: SSoT de funciones de dominio, persistencia, utilidades y contratos de integración.
- Todos los métodos son `@staticmethod` o `@classmethod` y stateless.
- El ViewSet hereda de un Mixin de servicio (`<Modelo>ServiceMixin`) que expone los métodos del Service Layer.
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

## [ARCH] 2. Reglas Generales de Arquitectura
1. **Gateway Directo:** El frontend y los integradores deben consumir exclusivamente los endpoints directos de cada app (ej. `apps/tenant/<app_name>/api/`). Queda ELIMINADO el patrón Facade.
1.1 **Deshabilitación de la Fachada (Facade):**
- **Fachada deshabilitada:** No debe existir ninguna capa intermediaria que orqueste o reencamine llamadas frontend a múltiples apps desde una API centralizada.
- **`apps/tenant/core` como interfaz de presentación:** Actuará exclusivamente como shell/contendor de interfaz (UI shell). Su responsabilidad es ensamblar y presentar los assets de cada app, sin contener lógica de negocio ni actuar como fuente de datos.
- **Responsabilidades prohibidas para `core`:** Prohibido implementar lógica de negocio, orquestación de APIs, reescritura de rutas de assets o persistencia de datos.
- **Excepciones permitidas:** Únicamente helpers infraestructurales globales (p. ej. `UIManager`, `TabulatorFactory`) pueden permanecer en `apps/tenant/core/static/core/js/`.
2. **Idempotencia Obligatoria:** Las operaciones de creación o ingesta de datos DEBEN ser idempotentes. Se deben utilizar claves únicas o constraints a nivel de BD para prevenir duplicados (permitiendo "Silent Success").
3. **Aislamiento SSoT:** Todo modelo de tenant DEBE heredar de `SintelTenantBaseModel`, el cual inyecta automáticamente la relación de `empresa`, asegurando el aislamiento de datos.

## [INFO] 3. Única Fuente de Verdad Documental (SSoT)
1. **Documentación Global:** `documentacion/arquitectura_general.md` es la referencia suprema.
2. **Flujo por Aplicación:** Cada `apps/<app_name>/` DEBE contener un archivo `AUDITORIA_FLUJO_COMPLETO.md` o `flujo_app.md` que describa su lógica secuencial específica.
3. **Gestión de Documentos:** Todos los demás archivos `.md` de soporte deben residir exclusivamente en `documentacion/`.

## [BACKEND] 4. Restricciones de Backend (Django & DRF)
1. **Cero Creación de Archivos `.py` no Autorizados:** Queda estrictamente PROHIBIDO sugerir o crear nuevos archivos de Python en aplicaciones existentes. Toda refactorización debe usar la estructura existente.
1.1 **Prohibición de modificaciones en `apps/public`:** PROHIBIDO modificar, refactorizar, o crear archivos dentro de `apps/public/` sin la aprobación explícita (requiere RFC/Issue y etiqueta `needs-admin-approval`).
2. **Prohibición de `views.py` Tradicionales:** No usar el archivo `views.py` legacy para lógica de negocio.
3. **Multi-Tenant Estricto (Zero-Trust SaaS):** Prohibido realizar consultas a modelos sin filtrar por la empresa del tenant (`empresa` o `empresa_id`) en las `TENANT_APPS`. 
   - **Prevención IDOR:** Toda mutación o asignación de ForeignKeys DEBE validar estructuralmente que el ID referenciado pertenece al tenant de `request.user.perfil.empresa`.
4. **Optimización de Queries y BdD (Zero Waste):** ESTRICTAMENTE PROHIBIDO usar `.all()`, o `.filter()` sin encadenar un `.only()` o `.defer()`. Toda consulta DEBE especificar explícitamente los campos necesarios.
5. **Referencias a Operadores del Tenant:** Las relaciones (`ForeignKey`) a usuarios operativos DEBEN apuntar a `'perfil.TenantProfile'`, NUNCA a `settings.AUTH_USER_MODEL`.
6. **Cero Signals:** Evitar el uso de señales de Django para prevenir efectos secundarios ocultos.

## [CRUD-E2E] 5. Ciclo de Vida CRUD End-to-End (Service Layer Modularizado)
Para garantizar un CRUD completo y seguro, toda operación debe seguir estrictamente este flujo unidireccional:

1. **Captura y Protección UI (Frontend):**
   - El payload se recopila a través de scripts especializados (`<app>_form.js`).
   - Obligatorio aplicar el "DOM Shield": remover temporalmente atributos `name` de selectores visibles y capturar únicamente valores crudos/ForeignKeys desde inputs ocultos (`input type="hidden"`).
2. **Recepción y Enrutamiento (ViewSet):**
   - El ViewSet actúa **SOLO** como enrutador HTTP. Prohibido importar modelos directamente aquí.
   - Delega la validación inicial de tipos al Serializer.
3. **Validación de Negocio (Business Service):**
   - El ViewSet invoca métodos del `<Modelo>ServiceMixin` que apuntan a `business_service.py`.
   - Se inyecta el `empresa_id`.
   - **Double Semantic Verification:** Se valida que todas las ForeignKeys del payload pertenezcan al tenant actual.
   - Se aplican las reglas de negocio, cálculos de dominio y validación de idempotencia.
4. **Persistencia Transaccional (CRUD Service):**
   - Delegación a `crud_service.py` para la ejecución real en base de datos.
   - Toda creación/mutación jerárquica (Maestro-Detalle) debe estar obligatoriamente envuelta en `@transaction.atomic`.
5. **Respuesta y UI Feedback (HTMX/Tabulator):**
   - El backend retorna 200/201 (JSON o HTMX OOB Swap).
   - El frontend intercepta la respuesta, actualiza el UI reactivamente (`table.replaceData()` en Tabulator) y emite notificaciones (`UIManager.notifySuccess`).

## [UI] 6. Interfaz de Usuario y Frontend (UI SSoT)
Regla crítica de ubicación de assets: TODOS los archivos `.html` y `.js` deben residir dentro del núcleo (nucleus) de la aplicación a la que pertenecen.

- **Ruta obligatoria para apps tenant:**
   - Templates: `apps/tenant/<app_name>/templates/<app_name>/`
   - JS estático: `apps/tenant/<app_name>/static/<app_name>/js/`
- **Ruta obligatoria para apps public (SHARED_APPS):**
   - Templates: `apps/public/<app_name>/templates/<app_name>/`
   - JS estático: `apps/public/<app_name>/static/<app_name>/js/`
- **Excepciones controladas:** Recursos verdaderamente compartidos y helpers de infra (p. ej. `UIManager`) en `apps/tenant/core/static/core/js/`.
- **HTMX y Server-Driven UI:** Las mutaciones HTMX deben originarse desde templates y endpoints ligados al mismo app. Al mover un módulo, actualizar siempre los `include` y referencias `static`.

## [ARCHITECTURE] 7. Arquitectura Feature-Sliced Design (FSD)
**PRINCIPIO FUNDAMENTAL:** Cada modelo de base de datos debe tener su propio ecosistema completo e independiente.

### 7.1. Estructura por Modelo (Ecosistema Completo)
1. **Templates HTML:**
   - `offcanvas_crear_{modelo}.html`, `offcanvas_editar_{modelo}.html`, `offcanvas_detalle_{modelo}.html`, `list_{modelo}.html`.
   - **PROHIBIDO:** Archivos monolíticos como `modals.html`.
2. **Scripts JavaScript:**
   - `{modelo}_main.js` (Orquestador).
   - `{modelo}_form.js` (Manejo de formularios).
   - **PROHIBIDO:** Scripts compartidos entre modelos no relacionados.
3. **API Endpoints (HTMX Actions):**
   - Los Offcanvas DEBEN usar `hx-get` apuntando a `render-offcanvas/crear/`, `editar/` o `detalle/`.
   - Feedback de error inyectado localmente en el contenedor.

## [WIZARD] 8. Patrón Wizard y Flujo de Estado
1. **Asistente en Memoria:** La fase inicial de recolección de configuraciones complejas NO guarda en BD.
2. **Traspaso por SessionStorage:** El JS empaqueta el payload JSON en `sessionStorage`, lanza por HTMX el Editor principal, el cual lee el storage para autollenar antes de permitir el guardado definitivo.
# AGENTS.md

---
name: reglas
description: Reglas Core de Arquitectura y Desarrollo - Proyecto SINTEL v2.61.4
---

# [CORE] SINTEL v2.61.4 - Reglas de Arquitectura y Estructura de Proyecto

Estas reglas son **ESTRICTAS, INMUTABLES Y OBLIGATORIAS** para cualquier modificación, refactorización o creación de código en este proyecto. Este archivo debe ser procesado y asimilado antes de implementar cualquier prompt o sugerencia de código.

## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.
- **RAZÓN**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACIÓN**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.

## [TECH] 1. Tecnologías Implementadas y Stack Base

### Ejemplo: Tecnologías y Patrones Implementados (Generales por App)

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
- Modularización estricta por responsabilidad:
   - `crud_service.py`: Acceso a datos puro (QuerySets optimizados, sin lógica de negocio ni validaciones).
   - `business_service.py`: Orquestación y lógica de negocio (idempotencia, naturaleza, validaciones, persistencia desde DTO, etc.).
   - `services.py`: SSoT de funciones de dominio, persistencia, utilidades y contratos de integración.
- Todos los métodos son `@staticmethod` o `@classmethod` y stateless.
- El ViewSet hereda de un Mixin de servicio (`<Modelo>ServiceMixin`) que expone los métodos del Service Layer.
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

## [ARCH] 2. Reglas Generales de Arquitectura
1. **Gateway Directo:** El frontend y los integradores deben consumir exclusivamente los endpoints directos de cada app (ej. `apps/tenant/<app_name>/api/`). Queda ELIMINADO el patrón Facade.
1.1 **Deshabilitación de la Fachada (Facade):**
- **Fachada deshabilitada:** No debe existir ninguna capa intermediaria que orqueste o reencamine llamadas frontend a múltiples apps desde una API centralizada.
- **`apps/tenant/core` como interfaz de presentación:** Actuará exclusivamente como shell/contendor de interfaz (UI shell). Su responsabilidad es ensamblar y presentar los assets de cada app, sin contener lógica de negocio ni actuar como fuente de datos.
- **Responsabilidades prohibidas para `core`:** Prohibido implementar lógica de negocio, orquestación de APIs, reescritura de rutas de assets o persistencia de datos.
- **Excepciones permitidas:** Únicamente helpers infraestructurales globales (p. ej. `UIManager`, `TabulatorFactory`) pueden permanecer en `apps/tenant/core/static/core/js/`.
2. **Idempotencia Obligatoria:** Las operaciones de creación o ingesta de datos DEBEN ser idempotentes. Se deben utilizar claves únicas o constraints a nivel de BD para prevenir duplicados (permitiendo "Silent Success").
3. **Aislamiento SSoT:** Todo modelo de tenant DEBE heredar de `SintelTenantBaseModel`, el cual inyecta automáticamente la relación de `empresa`, asegurando el aislamiento de datos.

## [INFO] 3. Única Fuente de Verdad Documental (SSoT)
1. **Documentación Global:** `documentacion/arquitectura_general.md` es la referencia suprema.
2. **Flujo por Aplicación:** Cada `apps/<app_name>/` DEBE contener un archivo `AUDITORIA_FLUJO_COMPLETO.md` o `flujo_app.md` que describa su lógica secuencial específica.
3. **Gestión de Documentos:** Todos los demás archivos `.md` de soporte deben residir exclusivamente en `documentacion/`.

## [BACKEND] 4. Restricciones de Backend (Django & DRF)
1. **Cero Creación de Archivos `.py` no Autorizados:** Queda estrictamente PROHIBIDO sugerir o crear nuevos archivos de Python en aplicaciones existentes. Toda refactorización debe usar la estructura existente.
1.1 **Prohibición de modificaciones en `apps/public`:** PROHIBIDO modificar, refactorizar, o crear archivos dentro de `apps/public/` sin la aprobación explícita (requiere RFC/Issue y etiqueta `needs-admin-approval`).
2. **Prohibición de `views.py` Tradicionales:** No usar el archivo `views.py` legacy para lógica de negocio.
3. **Multi-Tenant Estricto (Zero-Trust SaaS):** Prohibido realizar consultas a modelos sin filtrar por la empresa del tenant (`empresa` o `empresa_id`) en las `TENANT_APPS`. 
   - **Prevención IDOR:** Toda mutación o asignación de ForeignKeys DEBE validar estructuralmente que el ID referenciado pertenece al tenant de `request.user.perfil.empresa`.
4. **Optimización de Queries y BdD (Zero Waste):** ESTRICTAMENTE PROHIBIDO usar `.all()`, o `.filter()` sin encadenar un `.only()` o `.defer()`. Toda consulta DEBE especificar explícitamente los campos necesarios.
5. **Referencias a Operadores del Tenant:** Las relaciones (`ForeignKey`) a usuarios operativos DEBEN apuntar a `'perfil.TenantProfile'`, NUNCA a `settings.AUTH_USER_MODEL`.
6. **Cero Signals:** Evitar el uso de señales de Django para prevenir efectos secundarios ocultos.

## [CRUD-E2E] 5. Ciclo de Vida CRUD End-to-End (Service Layer Modularizado)
Para garantizar un CRUD completo y seguro, toda operación debe seguir estrictamente este flujo unidireccional:

1. **Captura y Protección UI (Frontend):**
   - El payload se recopila a través de scripts especializados (`<app>_form.js`).
   - Obligatorio aplicar el "DOM Shield": remover temporalmente atributos `name` de selectores visibles y capturar únicamente valores crudos/ForeignKeys desde inputs ocultos (`input type="hidden"`).
2. **Recepción y Enrutamiento (ViewSet):**
   - El ViewSet actúa **SOLO** como enrutador HTTP. Prohibido importar modelos directamente aquí.
   - Delega la validación inicial de tipos al Serializer.
3. **Validación de Negocio (Business Service):**
   - El ViewSet invoca métodos del `<Modelo>ServiceMixin` que apuntan a `business_service.py`.
   - Se inyecta el `empresa_id`.
   - **Double Semantic Verification:** Se valida que todas las ForeignKeys del payload pertenezcan al tenant actual.
   - Se aplican las reglas de negocio, cálculos de dominio y validación de idempotencia.
4. **Persistencia Transaccional (CRUD Service):**
   - Delegación a `crud_service.py` para la ejecución real en base de datos.
   - Toda creación/mutación jerárquica (Maestro-Detalle) debe estar obligatoriamente envuelta en `@transaction.atomic`.
5. **Respuesta y UI Feedback (HTMX/Tabulator):**
   - El backend retorna 200/201 (JSON o HTMX OOB Swap).
   - El frontend intercepta la respuesta, actualiza el UI reactivamente (`table.replaceData()` en Tabulator) y emite notificaciones (`UIManager.notifySuccess`).

## [UI] 6. Interfaz de Usuario y Frontend (UI SSoT)
Regla crítica de ubicación de assets: TODOS los archivos `.html` y `.js` deben residir dentro del núcleo (nucleus) de la aplicación a la que pertenecen.

- **Ruta obligatoria para apps tenant:**
   - Templates: `apps/tenant/<app_name>/templates/<app_name>/`
   - JS estático: `apps/tenant/<app_name>/static/<app_name>/js/`
- **Ruta obligatoria para apps public (SHARED_APPS):**
   - Templates: `apps/public/<app_name>/templates/<app_name>/`
   - JS estático: `apps/public/<app_name>/static/<app_name>/js/`
- **Excepciones controladas:** Recursos verdaderamente compartidos y helpers de infra (p. ej. `UIManager`) en `apps/tenant/core/static/core/js/`.
- **HTMX y Server-Driven UI:** Las mutaciones HTMX deben originarse desde templates y endpoints ligados al mismo app. Al mover un módulo, actualizar siempre los `include` y referencias `static`.

## [ARCHITECTURE] 7. Arquitectura Feature-Sliced Design (FSD)
**PRINCIPIO FUNDAMENTAL:** Cada modelo de base de datos debe tener su propio ecosistema completo e independiente.

### 7.1. Estructura por Modelo (Ecosistema Completo)
1. **Templates HTML:**
   - `offcanvas_crear_{modelo}.html`, `offcanvas_editar_{modelo}.html`, `offcanvas_detalle_{modelo}.html`, `list_{modelo}.html`.
   - **PROHIBIDO:** Archivos monolíticos como `modals.html`.
2. **Scripts JavaScript:**
   - `{modelo}_main.js` (Orquestador).
   - `{modelo}_form.js` (Manejo de formularios).
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

## [ASYNC] 11. Procesamiento Asíncrono y Dead Letter Queues (DLQ)
1. **Delegación Estricta:** Tareas masivas o integraciones de terceros DEBEN despacharse a Celery vía `.delay()`.
2. **Dead Letter Queue:** Toda tarea de Celery debe tener `max_retries`. Al fallar definitivamente, insertar en un registro de base de datos (`FailedTenantTask`) para permitir revisión y reenvío manual sin congelar workers.

## [HTMX-ADVANCED] 12. Server-Driven UI y Out of Band Swaps (OOB)
1. **Reactividad:** Tabulator y otras interfaces deben suscribirse nativamente a respuestas HTMX (`HX-Trigger`).
2. **Transacciones OOB:** Cuando un modal HTMX realiza un POST exitoso que afecta elementos externos, priorizar entregar una mutación DOM fuera de banda (`hx-swap-oob="true"` o `HX-Trigger`).

## [SaaS-DEFENSE] 13. Ciberseguridad Defensiva y Prevención IDOR
1. **Double Semantic Verification:** Requerida en todo endpoint DML para verificar inyectivamente `empresa=request.user.perfil.empresa`.
2. **Protección Horizontal:** Prohibido confiar ciegamente en IDs provistos en requests HTTP.

## [CORE-DB] 14. Herencia Obligatoria de Modelos SSoT
1. **SintelTenantBaseModel:** Todos los modelos del esquema tenant DEBEN heredar estrictamente de `SintelTenantBaseModel` importado desde `apps.tenant.core.models`.
2. **Prohibición de Herencia Nativa:** Queda prohibido heredar de `models.Model` directamente.

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

---

## C. Comandos de Operación
- **Instalación:** `pip install -r requirements.txt`
- **Docker (Desarrollo):** `docker-compose up --build`
- **Linter (Ruff):** `ruff check .`
- **Formateador (Ruff):** `ruff format .`
- **Testing:** `pytest` / `pytest path/to/test_file.py::test_function_name`