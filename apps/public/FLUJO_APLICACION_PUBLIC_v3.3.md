# 📋 Flujo Completo y Estructura Funcional - apps/public v2.61.4

**Fecha:** 2026-03-23  
**Alcance:** `apps/public/` - Aplicaciones del esquema público (SHARED_APPS)  
**Referencia:** `AGENTS.md` y arquitectura multi-tenant actualizada

---

## 🏗️ Arquitectura General

### Contexto Multi-Tenant

`apps/public/` contiene las aplicaciones que residen en el **esquema PostgreSQL 'public'** (SHARED_APPS). Estas aplicaciones son compartidas entre todos los tenants y proporcionan:

1. **Gestión de Usuarios Globales** (`accounts/`)
2. **Gestión de Tenants** (`tenants/`)
3. **Catálogo Tributario DIAN** (`impuestos/`)
4. **Consola de Administración** (`console/`)
5. **Core Público** (`core/`)

### Principios Arquitectónicos

- **SSoT (Single Source of Truth):** Los modelos en `apps/public/` son la única fuente de verdad para datos compartidos
- **Unidireccionalidad:** Los modelos de tenant pueden referenciar modelos públicos, pero NO al revés
- **API-First:** Toda la lógica de negocio expuesta vía DRF REST API
- **Service Layer Pattern:** Lógica de negocio en `services.py`, views y serializers anémicos

---

## 📦 Estructura de Módulos

### 1. `apps/public/accounts/` - Usuarios Globales

#### Propósito
Gestión de usuarios globales que pueden pertenecer a múltiples tenants.

#### Modelos Principales

**`User` (AbstractUser)**
- Usuarios globales en esquema `public`
- Campos: `email` (único), `username` (auto-generado), `telefono`, `first_name`, `last_name`
- **Regla de Oro:** NO puede tener ForeignKey hacia modelos de tenant
- Relación unidireccional: `TenantProfile` → `User` (NO al revés)

#### Servicios (`api/services/user_service.py`)

**`create_user_service()`**
- Crea usuario global con hashing seguro (`set_password()`)
- Genera username único desde email si no se proporciona
- Transaccional: `@transaction.atomic`
- Normaliza email a minúsculas

**`update_user_service()`**
- Actualización parcial de usuario
- Hashing seguro de contraseña si se proporciona
- Solo actualiza campos proporcionados

#### API Endpoints
- `GET /api/admin/v1/accounts/users/` - Lista usuarios (solo admin)
- `POST /api/admin/v1/accounts/users/` - Crear usuario
- `GET /api/admin/v1/accounts/users/{id}/` - Detalle usuario
- `PATCH /api/admin/v1/accounts/users/{id}/` - Actualizar usuario
- `DELETE /api/admin/v1/accounts/users/{id}/` - Eliminar usuario

#### Flujo de Creación de Usuario
```
1. Validar email y password
2. Normalizar email a minúsculas
3. Generar username único desde email
4. Crear User con set_password() (hashing seguro)
5. Retornar usuario creado
```

---

### 2. `apps/public/tenants/` - Gestión de Tenants

#### Propósito
Gestión de tenants (Client), dominios, membresías y landing page principal.

#### URLs (`urls.py`) ⭐ NUEVO
- `path('', LandingPageView.as_view())` - Landing page principal
- `path('select/', TenantSelectView.as_view())` - Selección de tenant

#### Vistas (`views.py`) ⭐ NUEVO
- `LandingPageView` (TemplateView) - Landing page profesional SINTEL
  - **Template:** `public/landing.html`
  - **Características:**
    - Hero section con icono y título SINTEL
    - Descripción del sistema integral
    - Botones dinámicos según estado de autenticación
    - Footer con versión del sistema
    - Diseño responsive con Bootstrap 5
- `TenantSelectView` (LoginRequiredMixin) - Selección de tenants disponibles
  - **Template:** `public/tenant_select.html`
  - Lista tenants donde el usuario tiene membresía activa
  - Links directos a dominios de cada tenant

#### Templates ⭐ NUEVO
- `templates/public/landing.html` - Landing page principal
- `templates/public/tenant_select.html` - Selección de tenant

#### Management Commands ⭐ NUEVO
- `create_public_tenant.py` - Crea tenant público obligatorio
  - Configura `Client(schema_name='public')` y `Domain(domain='localhost')`
  - Comando: `python manage.py create_public_tenant`

#### Modelos Principales

**`Client` (TenantMixin)**
- Representa un tenant (empresa/cliente)
- Campos: `nombre`, `schema_name` (único), `paid_until`, `on_trial`, `is_active`
- `auto_create_schema = True` - Crea esquema PostgreSQL automáticamente
- `auto_drop_schema = True` - Elimina esquema al borrar tenant
- **Candado de Seguridad:** Imposible borrar tenant 'public'

**`Domain` (DomainMixin)**
- Dominios asociados a tenants
- Constraint: Un solo dominio principal (`is_primary=True`) por tenant
- Dominio esperado: `{schema_name}.{TENANT_DOMAIN_BASE}`

**`TenantMembership`**
- Relación muchos-a-muchos entre usuarios y tenants
- Campos: `client`, `user`, `rol` (ADMIN/STAFF/USER), `is_primary_admin`, `is_active`
- Constraint: Solo un `is_primary_admin=True` por tenant

#### Servicios (`services.py`)

**`generar_schema_name(nombre: str) -> str`**
- Genera schema_name válido desde nombre de empresa
- Normaliza: minúsculas, sin espacios, sin caracteres especiales
- Evita 'public' y garantiza unicidad
- Longitud máxima: 63 caracteres

**`crear_tenant_con_owner()`**
- Crea tenant completo con propietario
- Flujo:
  1. Genera/valida `schema_name`
  2. Verifica usuario admin existe y está activo
  3. Crea `Client` → señal post_save crea `Domain` principal
  4. Ejecuta `migrate_schemas` para el schema
  5. Crea `TenantMembership` con rol ADMIN + `is_primary_admin=True`
  6. Verifica integridad final (schema existe, dominio único)
  7. Construye `login_url` estándar
- **Transaccional:** `@transaction.atomic` - Todo o nada

#### API Endpoints
- `GET /api/public/v1/tenants/` - Lista tenants (solo admin)
- `POST /api/public/v1/tenants/` - Crear tenant
- `POST /api/public/v1/tenants/onboard/` - Onboarding completo (tenant + owner)
- `GET /api/public/v1/tenants/{id}/` - Detalle tenant
- `PATCH /api/public/v1/tenants/{id}/` - Actualizar tenant
- `DELETE /api/public/v1/tenants/{id}/` - Eliminar tenant (soft delete)

#### Flujo de Onboarding de Tenant
```
1. Validar payload (nombre, schema_name, owner_email o admin_user_id)
2. Crear/obtener usuario global (idempotente por email)
3. Generar schema_name si no se proporciona
4. Crear Client (auto_create_schema=True crea esquema)
5. Domain principal creado por señal post_save
6. Ejecutar migrate_schemas para el schema
7. Crear TenantMembership (rol=ADMIN, is_primary_admin=True)
8. (Opcional) Seed de perfil si tabla existe
9. Retornar {client_id, domain, membership_id, login_url}
```

---

### 3. `apps/public/impuestos/` - Catálogo Tributario DIAN

#### Propósito
Catálogo legal tributario de la DIAN (Colombia) disponible para todos los tenants.

#### Modelos Principales

**Catálogos Base:**
- `TipoImpuesto` - Tipos de impuestos (IVA, Retención, etc.)
- `TarifaIVA` - Tarifas de IVA según normativa DIAN
- `ConceptoRetencion` - Conceptos de retención (ICA, IVA, Renta, etc.)
- `CodigoTributario` - Códigos tributarios (Responsabilidades, Regímenes)
- `ActividadEconomica` - Actividades económicas según CIIU

**Catálogos Avanzados (SSoT):**
- `ContribuyenteTipo` - Tipos de contribuyente (PN/PJ) con segmentos DIAN
- `RegimenRenta` - Regímenes de renta (Ordinario, RTE, SIMPLE)
- `ResponsabilidadRUT` - Responsabilidades RUT (códigos DIAN)
- `PerfilTributario` - Combinaciones recomendadas de características tributarias

**Ingesta de Documentos:**
- `DocumentoFuente` - Documentos fuente para ingesta (PDF, HTML, XML, XLS, CSV)
- `IngestaLog` - Logs de procesamiento de documentos
- `NormaTributaria` - Normas tokenizadas y normalizadas extraídas de documentos

#### Servicios

**ETL Pipeline (`services/etl/`):**
- `pipeline.py` - Pipeline principal de ingesta
- `parse_pdf.py`, `parse_html.py`, `parse_xml.py`, `parse_excel.py`, `parse_csv.py` - Parsers por tipo
- `normalizer.py` - Normalización de texto
- `tokenizer.py` - Tokenización de normas
- `validators.py` - Validación de datos
- `upserts.py` - Upsert de catálogos
- `detectors.py` - Detección de tipo de documento

**Provider (`services/provider.py`):**
- Servicio provider para acceso a catálogos desde tenant apps
- Métodos para obtener tipos de contribuyente, regímenes, responsabilidades

#### API Endpoints
- `GET /api/public/v1/impuestos/tipos/` - Lista tipos de impuesto
- `GET /api/public/v1/impuestos/tarifas-iva/` - Lista tarifas IVA
- `GET /api/public/v1/impuestos/conceptos-retencion/` - Lista conceptos retención
- `GET /api/public/v1/impuestos/contribuyentes-tipos/` - Lista tipos contribuyente
- `GET /api/public/v1/impuestos/regimenes-renta/` - Lista regímenes renta
- `GET /api/public/v1/impuestos/responsabilidades-rut/` - Lista responsabilidades RUT
- `GET /api/public/v1/impuestos/perfiles-tributarios/` - Lista perfiles tributarios
- `POST /api/public/v1/impuestos/ingesta/` - Crear proceso de ingesta
- `GET /api/public/v1/impuestos/ingesta/{id}/` - Detalle ingesta
- `GET /api/public/v1/impuestos/search/` - Búsqueda en normas tributarias

#### Flujo de Ingesta de Documentos
```
1. Crear DocumentoFuente (archivo o URL)
2. Detectar tipo de documento (PDF, HTML, XML, etc.)
3. Parsear documento según tipo
4. Normalizar texto extraído
5. Tokenizar normas (artículos, temas, impuestos)
6. Validar datos extraídos
7. Upsert catálogos (tipos, tarifas, conceptos)
8. Crear NormaTributaria tokenizada
9. Indexar en OpenSearch para búsqueda
10. Registrar logs de cada etapa
```

---

### 4. `apps/public/console/` - Consola de Administración

#### Propósito
Interfaz de administración para gestión de tenants, usuarios y catálogos DIAN.

#### Modelos

**`ConsoleActionLog`**
- Registro de auditoría de acciones en consola
- Acciones: `TENANT_CREATE`, `TENANT_UPDATE`, `TENANT_DELETE`, `USER_CREATE`, `USER_UPDATE`, `USER_DELETE`
- Campos: `action`, `actor`, `tenant`, `target_user`, `metadata`, `created_at`

#### Vistas (`views.py`)

**Vistas de Renderizado (TemplateView):**
- `DashboardView` - Dashboard principal
- `TenantsListView` - Lista de tenants (DataTables)
- `TenantsNewView` - Formulario crear tenant
- `TenantsStatusView` - Estado de creación (polling HTMX)
- `UsersListView` - Lista usuarios (DataTables)
- `ImpuestosCatalogoView` - Catálogo DIAN
- `ImpuestosIngestaListView` - Lista procesos ingesta
- `ImpuestosIngestaCreateView` - Crear ingesta
- `ImpuestosIngestaDetailView` - Detalle ingesta

**Mixins:**
- `StaffRequiredMixin` - Requiere usuario staff
- `PublicSchemaMixin` - Verifica esquema 'public'
- `ConsoleTemplateView` - Vista base para consola

#### API Endpoints (DataTables)
- `POST /api/admin/v1/console/dt/tenants/` - Datos para tabla tenants
- `POST /api/admin/v1/console/dt/users/` - Datos para tabla usuarios

#### Flujo de Consola
```
1. Usuario staff accede a consola (esquema public)
2. Vista renderiza template HTML
3. JavaScript consume API JSON (DataTables, CRUD)
4. Acciones registradas en ConsoleActionLog
5. Redirecciones según resultado
```

---

### 5. `apps/public/core/` - Core Público

#### Propósito
Funcionalidades core del esquema público (middleware, vistas, utilidades, URLs básicas).

#### Componentes

**URLs (`urls.py`):** ⭐ NUEVO
- `path('', PublicIndexView.as_view())` - Página principal
- `path('workspace/', workspace_redirect)` - Redirección a consola
- `path('favicon.ico', favicon_view)` - Favicon placeholder (204 No Content)
- `path('console/tenants/', RedirectView)` - Redirección a gestión de tenants

**Vistas (`views.py`):**
- `PublicIndexView` (TemplateView) - Redirige a landing page de tenants
  - **Lógica de redirección:**
    - Usuario staff/superuser → `/console/` (Consola de administración)
    - Usuario anónimo → Renderiza vista básica

**Management Commands:** ⭐ NUEVO
- `setup_default_tenant.py` - Crea tenant público obligatorio para localhost
  - Configura `Client(schema_name='public', domain='localhost')`
  - Ejecuta migraciones en esquema del tenant
  - Crea perfil de tenant para usuario admin
  - Comando: `python manage.py setup_default_tenant`

**API (`api/views.py`):**
- `LoggedTokenVerifyView` - Verificación de token JWT con logging
- Registra errores 401 para diagnóstico

#### Templates (`templates/public/core/`):
- `index.html` - Landing page profesional (Bootstrap 5)
  - Hero section con título y descripción
  - Features: Multi-Tenant, Escalabilidad, Módulos, API-First, Seguridad, Contabilidad Invisible
  - CTA: Botón "Acceso Administrador Plataforma" → `/admin/`
  - Footer con información del proyecto

#### Scripts de Inicialización (`scripts/setup_public_domain.py`):
- **Propósito:** Crear el tenant público y asociar dominios necesarios
- **Funcionalidad:**
  - Crea tenant `public` si no existe (campo `nombre='SINTEL Public'`)
  - Crea/verifica dominios: `sintel.com` (primario), `localhost`, `127.0.0.1`, `0.0.0.0`
  - Establece dominio primario si no existe
  - Idempotente: puede ejecutarse múltiples veces sin problemas
- **Uso:**
  ```bash
  docker exec -it crm_sintel-web-1 python scripts/setup_public_domain.py
  ```
- **Configuración PYTHONPATH:**
  - Calcula BASE_DIR correctamente (dos niveles arriba desde `scripts/`)
  - Inyecta BASE_DIR en `sys.path` antes de importar Django
  - Configura `DJANGO_SETTINGS_MODULE = 'config.settings'`
  - Inicializa Django con `django.setup()`

#### JavaScript (`static/core/js/`):
- `landing.ui.js` - UI landing page
- `login.ui.js` - UI login
- `activate.ui.js` - UI activación
- `reset-request.ui.js` - UI reset request
- `reset-confirm.ui.js` - UI reset confirm
- `_csrf.js` - Helpers CSRF

---

## 🔄 Flujos Principales

### Flujo 0: Acceso al Dominio Público (Landing Page) ⭐ ACTUALIZADO

**Escenario:** Usuario accede a `http://localhost/`

```
1. Request HTTP → localhost/
   
2. django-tenants TenantMainMiddleware:
   - Busca dominio en BD: Domain.objects.filter(domain='localhost').first()
   - Encuentra: Domain(domain='localhost', tenant=Client(schema_name='public'))
   - Activa schema: connection.set_schema_to('public')
   - Establece request.tenant = Client(schema_name='public')
   
3. Django resuelve URL en config/urls.py:
   - path('', include('apps.public.tenants.urls')) → LandingPageView
   
4. LandingPageView.dispatch():
   - Si usuario autenticado y staff → redirect('/console/')
   - Si usuario anónimo → Renderiza 'public/landing.html'
   - Muestra landing page SINTEL con:
     - Hero section: "SINTEL - Sistema Integral de Gestión Empresarial"
     - Botones dinámicos: "Iniciar Sesión" o "Ir al Workspace"
     - Footer con versión v2.61.4
   
5. Response 200 OK con HTML de landing page
```

**URLs Adicionales Configuradas:**
- `/workspace/` → Redirige a `/console/`
- `/favicon.ico` → 204 No Content
- `/robots.txt` → Respuesta estándar
- `/sitemap.xml` → XML vacío

**Archivos Involucrados:**
- `apps/public/tenants/views.py` - LandingPageView, TenantSelectView
- `apps/public/tenants/templates/public/landing.html` - Template landing page
- `apps/public/core/urls.py` - URLs básicas (workspace/, favicon.ico)
- `config/urls.py` - Configuración maestro de URLs

**Inicialización Requerida:**
- Ejecutar `python manage.py create_public_tenant` para crear tenant público
- Verificar que exista:
  - Client(schema_name='public', nombre='Sitio Público SINTEL')
  - Domain(domain='localhost', tenant=public, is_primary=True)

### Flujo 1: Creación de Tenant (Onboarding)

```
1. Admin accede a consola (/console/tenants/new/)
2. Completa formulario (nombre, email owner, etc.)
3. JavaScript POST /api/public/v1/tenants/onboard/
4. Backend:
   a. Valida payload
   b. Crea/obtiene usuario global (idempotente)
   c. Genera schema_name
   d. Crea Client (auto_create_schema=True)
   e. Domain creado por señal

---

## ✅ Implementado y funcional (actualizado 2026-03-27)

Se han aplicado y verificado las siguientes correcciones y mejoras en `apps/public` durante la iteración de marzo 2026:

- **Onboarding estable y idempotente:** Corrección de error de `Empresa` nulo durante bootstrap; `crear_tenant_con_owner()` ahora garantiza creación completa y retorno estable de `login_url`.
- **Fix migraciones DateTimeField:** Corregido error en migraciones que originaba TypeError al aplicar defaults en `DateTimeField`.
- **Eliminación robusta de usuarios/tenants:** Implementado `delete_user_service` y `DeletionAudit` en `apps/public/accounts/models.py`; auditoría y limpieza por esquema comprobadas.
- **Restauración API pública `/api/public/v1/users/`:** Añadidos fallback determinísticos en `config/public_api_urls.py` y `config/urls_public.py`, y serializer que expone `username` en la respuesta de creación.
- **Protecciones y logging:** Middleware y logging reforzados en `apps/public/tenants/middleware_*` para trazar resolución de tenant y bloquear rutas públicas en contextos tenant.
- **Corrección tenants list (console):** `TenantsDataTableView` ahora excluye explícitamente `schema_name='public'` y `schema_name='test'` en listados administrativos para evitar artefactos de tests; logging temporal añadido para diagnóstico.

Validación rápida realizada en entorno de CI local (Docker):

- Reconstrucción de imágenes y levantamiento de contenedores: `docker compose up -d --build`
- Ejecución de prueba focalizada que fallaba anteriormente:
   - `pytest -q apps/public/console/tests.py::ConsoleAPIConsumptionTests::test_tenants_api_returns_paginated_results -q -s -o log_cli=true -o log_cli_level=DEBUG`
   - Resultado: `1 passed` (el test de paginación de tenants ahora pasa).

Notas de alcance:
- Se evitaron cambios invasivos en la estructura de templates y JS (manteniendo FSD/SSoT). 
- Se introdujeron logs temporales para depuración en `TenantsDataTableView` y `ClientViewSet` — pueden eliminarse tras estabilizar la suite completa.

Próximo paso recomendado:
- Ejecutar la suite completa `pytest apps/public` en CI para validar otras pruebas afectadas, y preparar commit/PR con cambios y notas de migración.

   f. Ejecuta migrate_schemas
   g. Crea TenantMembership (ADMIN, primary)
   h. (Opcional) Seed perfil
5. Retorna {client_id, domain, membership_id, login_url}
6. Frontend muestra login_url y estado
```

### Flujo 2: Gestión de Usuarios Globales

```
1. Admin accede a consola (/console/users/)
2. DataTables carga usuarios desde /api/admin/v1/console/dt/users/
3. Crear usuario:
   a. Modal con formulario
   b. POST /api/admin/v1/accounts/users/
   c. create_user_service() crea usuario
   d. Retorna usuario creado
4. Editar usuario:
   a. Modal con datos existentes
   b. PATCH /api/admin/v1/accounts/users/{id}/
   c. update_user_service() actualiza
5. Eliminar usuario:
   a. Confirmación
   b. DELETE /api/admin/v1/accounts/users/{id}/
```

### Flujo 3: Ingesta de Catálogo DIAN

```
1. Admin accede a consola (/console/impuestos/ingesta/create/)
2. Sube documento o proporciona URL
3. POST /api/public/v1/impuestos/ingesta/
4. Backend:
   a. Crea DocumentoFuente
   b. Detecta tipo (PDF, HTML, XML, etc.)
   c. Ejecuta pipeline ETL:
      - Parsear documento
      - Normalizar texto
      - Tokenizar normas
      - Validar datos
      - Upsert catálogos
   d. Crea NormaTributaria
   e. Indexa en OpenSearch
   f. Registra logs
5. Retorna proceso de ingesta con estado
6. Frontend muestra progreso y resultados
```

---

## 🔐 Seguridad y Permisos

### Autenticación
- **SessionAuthentication:** Para UI (cookies de sesión)
- **JWT:** Para API programática (opcional)

### Permisos
- **IsAdminUser:** Requerido para gestión de tenants y usuarios
- **IsAuthenticated:** Requerido para acceso a consola
- **PublicSchemaMixin:** Verifica esquema 'public' para consola

### Validaciones
- **Schema Name:** Sin puntos, único, no 'public'
- **Email:** Único, normalizado a minúsculas
- **Domain:** Un solo dominio principal por tenant
- **Primary Admin:** Solo un `is_primary_admin=True` por tenant

---

## 📊 Estructura de Archivos ⭐ ACTUALIZADA

```
apps/public/
├── accounts/
│   ├── models.py              # User (AbstractUser)
│   ├── managers.py            # UserManager (genera username)
│   ├── api/
│   │   ├── serializers.py     # Serializers DRF
│   │   ├── viewsets.py        # ViewSets CRUD
│   │   └── services/
│   │       └── user_service.py # create_user_service, update_user_service
│   └── migrations/
│
├── tenants/
│   ├── models.py              # Client, Domain, TenantMembership
│   ├── services.py            # crear_tenant_con_owner, generar_schema_name
│   ├── views.py               # ⭐ NUEVO: LandingPageView, TenantSelectView
│   ├── urls.py                # ⭐ NUEVO: URLs landing page y selección
│   ├── templates/             # ⭐ NUEVO: Templates públicos
│   │   └── public/
│   │       ├── landing.html   # Landing page principal
│   │       └── tenant_select.html # Selección de tenant
│   ├── api/
│   │   ├── serializers.py     # Serializers DRF
│   │   └── viewsets.py        # ClientViewSet, onboard action
│   ├── management/
│   │   └── commands/
│   │       └── create_public_tenant.py # ⭐ NUEVO: Crear tenant público
│   ├── middleware.py           # Tenant middleware
│   └── migrations/
│
├── impuestos/
│   ├── models.py              # Catálogos DIAN, DocumentoFuente, NormaTributaria
│   ├── services/
│   │   ├── provider.py        # Provider para tenant apps
│   │   └── etl/               # Pipeline ETL
│   ├── api/
│   │   ├── serializers.py     # Serializers DRF
│   │   ├── viewsets.py        # ViewSets catálogos
│   │   └── ingesta/           # API ingesta documentos
│   └── migrations/
│
├── console/
│   ├── models.py              # ConsoleActionLog
│   ├── views.py               # TemplateViews consola
│   ├── api/
│   │   └── views.py           # Endpoints DataTables
│   ├── templates/             # Templates HTML consola
│   └── static/js/             # JavaScript consola
│
└── core/
    ├── views.py               # PublicIndexView (redirección básica)
    ├── urls.py                # ⭐ NUEVO: URLs básicas (workspace/, favicon.ico)
    ├── management/
    │   └── commands/
    │       └── setup_default_tenant.py # ⭐ NUEVO: Setup tenant por defecto
    ├── middleware.py          # Core middleware
    ├── api/
    │   └── views.py           # LoggedTokenVerifyView
    └── static/
        └── core/js/           # JavaScript core
```

---

## ⚠️ Violaciones de Reglas Detectadas

### 1. Templates fuera de ruta especificada
- **Actual:** `apps/public/console/templates/`, `apps/public/impuestos/templates/`
- **Regla:** Templates deben estar en `apps/tenant/core/templates/tenant/core/`
- **Acción:** Migrar templates a ruta correcta o documentar excepción

### 2. JavaScript fuera de ruta especificada
- **Actual:** `apps/public/console/static/js/`, `apps/public/core/static/core/js/`
- **Regla:** JavaScript debe estar en `apps/tenant/core/static/core/js/`
- **Acción:** Migrar JavaScript a ruta correcta o documentar excepción

### 3. Service Layer Pattern
- **Estado:** ✅ Correcto - Lógica en `services.py`
- **Ejemplos:** `accounts/api/services/user_service.py`, `tenants/services.py`

### 4. Multi-Tenant Estricto
- **Estado:** ✅ Correcto - No aplica (esquema public compartido)
- **Nota:** Los modelos públicos NO filtran por `empresa_id` (correcto)

---

## 📝 Notas de Migración

### Templates
Los templates de `apps/public/console/` y `apps/public/impuestos/` son específicos del esquema público y no deben migrarse a `apps/tenant/core/templates/` porque:
- Son parte de la consola de administración (esquema public)
- No son parte del workspace de tenant
- Tienen su propia estructura y propósito

### JavaScript
El JavaScript de `apps/public/console/static/js/` y `apps/public/core/static/core/js/` es específico del esquema público y puede mantenerse en su ubicación actual, pero debería seguir las reglas:
- Vanilla JS (sin jQuery)
- IIFE para encapsulamiento
- Logging con prefijos

---

## 🎯 Recomendaciones

1. **Documentar excepciones:** Los templates y JavaScript de `apps/public/` son excepciones válidas a las reglas de UI SSoT
2. **Mantener Service Layer:** Continuar usando `services.py` para lógica de negocio
3. **API-First:** Mantener todas las operaciones expuestas vía DRF REST API
4. **Vanilla JS:** Migrar cualquier jQuery restante a Vanilla JS
5. **Logging:** Asegurar prefijos consistentes en todos los módulos

---

---

## � Management Commands Disponibles

### Tenant Público

**`python manage.py create_public_tenant`**
- Crea el tenant público obligatorio para django-tenants
- Configura `Client(schema_name='public')` y `Domain(domain='localhost')`
- Parámetros:
  - `--domain` (default: localhost) - Dominio para el tenant
- Uso: `docker compose exec web python manage.py create_public_tenant`

**`python manage.py setup_default_tenant`**
- Configura tenant por defecto con empresa completa
- Crea esquema de BD y ejecuta migraciones
- Crea perfil de tenant para usuario admin
- Parámetros:
  - `--domain` (default: localhost) - Dominio para el tenant
  - `--empresa-nombre` (default: SINTEL Demo) - Nombre de la empresa
- Uso: `docker compose exec web python manage.py setup_default_tenant`

### Flujo de Inicialización

```
1. Crear tenant público (obligatorio):
   python manage.py create_public_tenant
   
2. (Opcional) Configurar tenant con empresa:
   python manage.py setup_default_tenant
   
3. Verificar acceso:
   http://localhost/ → Landing page SINTEL
   http://localhost/console/ → Dashboard admin
```

---

## ✅ Migración v2.61.4 Completada

### Cambios Realizados (2026-03-23)

1. **Tenant Público Multi-tenant:**
   - ✅ Creado `apps/public/tenants/management/commands/create_public_tenant.py`
   - ✅ Configurado tenant público obligatorio: `Client(schema_name='public', domain='localhost')`
   - ✅ Resueltos errores 404 del middleware django-tenants

2. **Landing Page y URLs:**
   - ✅ Creado `apps/public/tenants/views.py` con `LandingPageView` y `TenantSelectView`
   - ✅ Creado `apps/public/tenants/urls.py` para rutas principales
   - ✅ Creado `apps/public/core/urls.py` para URLs básicas (workspace/, favicon.ico)
   - ✅ Templates: `public/landing.html` y `public/tenant_select.html`

3. **Configuración URLs Maestro:**
   - ✅ Actualizado `config/urls.py` con estructura jerárquica:
     - `path('', include('apps.public.tenants.urls'))` - Landing page
     - `path('', include('apps.public.core.urls'))` - URLs básicas
     - `path('console/', include('apps.public.console.urls'))` - Consola admin
   - ✅ Agregadas rutas para robots.txt, sitemap.xml

4. **Corrección Errores 404:**
   - ✅ `/` → Landing page SINTEL
   - ✅ `/workspace/` → Redirige a `/console/`
   - ✅ `/favicon.ico` → 204 No Content
   - ✅ `/console/tenants/` → Gestión de tenants
   - ✅ Rutas adicionales silenciadas

### Estado Actual

**URLs Funcionales:**
- `http://localhost/` → Landing page SINTEL
- `http://localhost/console/` → Dashboard administración
- `http://localhost/admin/` → Django admin
- `http://localhost/api/v1/` → APIs por tenant
- `http://localhost/api/public/v1/` → APIs públicas

**Arquitectura Multi-tenant:**
- ✅ Esquema `public` configurado para `localhost`
- ✅ Middleware django-tenants funcional
- ✅ Redirecciones inteligentes según autenticación
- ✅ Separación clara entre rutas públicas y de tenant

---

---

## 🟢 Actualización v2.61.4 (2026-03-28)

Se han consolidado cambios estructurales orientados a la seguridad y centralización en Core API:

### 1. Centralización de Identidad en Core
- **Auth Shells**: `login.html`, `activate.html` y `password-reset.html` han sido migrados definitivamente a `apps/tenant/core/static/tenant/core/auth/`.
- **API First**: El frontend consume exclusivamente `CoreAuthViewSet` para todas las operaciones de identidad.

### 2. Servicio de Email Centralizado (SSoT)
- **EmailService**: Implementado en `apps/public/core/services/email_service.py`.
- **Templates Unificados**: Ubicados en `apps/public/core/templates/public/core/emails/`.
- **Alcance**: Gestiona invitaciones de owner y restablecimiento de contraseñas con logging avanzado `[EMAIL:SEND]`.

### 3. Resiliencia y Auditoría (DLQ)
- **FailedTenantTask**: Implementado en `apps/public/tenants/models.py` para capturar fallos en tareas de Celery (onboarding).
- **Consola de Auditoría**: Integración de eventos de activación (`USER_ACTIVATE`) en el log de acciones de la consola.

### 4. Segmentación Estricta de UI
- **Hardening de Rutas**: Los dominios privados solo resuelven rutas de `core`. Se prohíbe el acceso a la landing pública desde subdominios de clientes.
- **Dominio SSoT**: Registro obligatorio de dominios en `Domain` (ej. `home.sintel.com`) para evitar fugas de información entre esquemas.

**Última actualización:** 2026-03-28  
**Versión:** 2.61.4 - Estabilización Alpha
