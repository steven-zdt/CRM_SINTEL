# 📋 Flujo Completo y Estructura Funcional - apps/public v3.3

**Fecha:** 2024-12-19  
**Alcance:** `apps/public/` - Aplicaciones del esquema público (SHARED_APPS)  
**Referencia:** `.cursor/rules/reglas.mdc` y `documentacion/arquitectura_general.md`

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
Gestión de tenants (Client), dominios y membresías de usuarios a tenants.

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
Funcionalidades core del esquema público (middleware, vistas, utilidades).

#### Componentes

**Middleware (`middleware.py`):**
- Middleware para manejo de esquemas y routing

**Vistas (`views.py`):**
- `PublicIndexView` - Redirección inteligente desde dominio público
  - Usuario staff → Consola
  - Usuario normal → Login
  - Anónimo → Login

**API (`api/views.py`):**
- `LoggedTokenVerifyView` - Verificación de token JWT con logging
- Registra errores 401 para diagnóstico

#### Templates (`static/public/core/landing/`):
- `index.html` - Landing page pública
- `login.html` - Login
- `activate.html` - Activación de cuenta
- `reset-request.html` - Solicitud reset password
- `reset-confirm.html` - Confirmación reset password

#### JavaScript (`static/core/js/`):
- `landing.ui.js` - UI landing page
- `login.ui.js` - UI login
- `activate.ui.js` - UI activación
- `reset-request.ui.js` - UI reset request
- `reset-confirm.ui.js` - UI reset confirm
- `_csrf.js` - Helpers CSRF

---

## 🔄 Flujos Principales

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

## 📊 Estructura de Archivos

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
│   ├── api/
│   │   ├── serializers.py     # Serializers DRF
│   │   └── viewsets.py        # ClientViewSet, onboard action
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
    ├── views.py               # PublicIndexView
    ├── middleware.py          # Core middleware
    ├── api/
    │   └── views.py           # LoggedTokenVerifyView
    └── static/
        ├── public/core/landing/ # Templates landing
        └── core/js/            # JavaScript landing
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

## 🔐 Validación de Tokens de Acceso Público (v3.3)

### Servicio de Validación (`apps/public/services.py`)

**`generar_hash_acceso()`**
- Genera hash HMAC-SHA256 seguro para acceso público
- Incluye: tipo_documento, documento_id, tenant_schema, expiración
- Hash determinístico pero no reversible

**`validar_hash_acceso()`**
- Valida hash y verifica integridad
- Verifica expiración
- Comparación timing-safe (previene timing attacks)

**`validar_token_documento()`**
- Método principal para validación desde API
- Retorna dict con estado de validación

**`obtener_datos_documento_publico()`**
- Obtiene datos públicos del documento (sin información sensible)
- Requiere acceso al schema del tenant

### Endpoints API Públicos

**`POST /api/public/v1/core/validate-token/`**
- Valida token de acceso público
- Body: `{token, tipo_documento, documento_id, tenant_schema}`
- Returns: `{valido: bool, error?: string, expiracion?: int}`

**`GET /api/public/v1/core/documento-publico/`**
- Obtiene datos públicos de documento validado
- Query params: `token, tipo, id, tenant`
- Returns: `{valido: bool, documento: {...}}`

### Flujo de Acceso Público

```
1. Usuario genera hash de acceso (desde tenant):
   hash = generar_hash_acceso('cotizacion', 123, 'empresa_x', 30)
   
2. Usuario comparte URL pública:
   /public/view/cotizacion/123/?token={hash}&tenant=empresa_x
   
3. Frontend público valida token:
   POST /api/public/v1/core/validate-token/
   {token, tipo_documento: 'cotizacion', documento_id: 123, tenant_schema: 'empresa_x'}
   
4. Si válido, obtiene datos:
   GET /api/public/v1/core/documento-publico/?token={hash}&tipo=cotizacion&id=123&tenant=empresa_x
   
5. Frontend muestra documento con TabulatorFactory (solo lectura)
```

---

## ✅ Migración v3.3 Completada

### Cambios Realizados

1. **Service Layer Pattern:**
   - ✅ Creado `apps/public/services.py` con validación de tokens
   - ✅ Funciones: `generar_hash_acceso()`, `validar_hash_acceso()`, `validar_token_documento()`

2. **Vanilla JS (IIFE):**
   - ✅ Refactorizado `login.ui.js` - Eliminado `import`, agregado IIFE completo
   - ✅ Refactorizado `reset-request.ui.js` - Eliminado `import`, agregado IIFE completo
   - ✅ Refactorizado `reset-confirm.ui.js` - Eliminado `import`, agregado IIFE completo
   - ✅ Refactorizado `activate.ui.js` - Eliminado `import`, agregado IIFE completo
   - ✅ `landing.ui.js` ya estaba en IIFE (sin cambios)

3. **API-First:**
   - ✅ Creado `apps/public/core/api/public_views.py` con endpoints públicos
   - ✅ Endpoints: `validar_token_acceso()`, `obtener_documento_publico()`

4. **Rutas Validadas:**
   - ✅ JavaScript en `apps/public/core/static/core/js/` (correcto)
   - ✅ Templates en `apps/public/core/static/public/core/landing/` (correcto)

### Pendientes

1. **URLs API:** Crear `apps/public/core/api/urls.py` y registrar endpoints
2. **TabulatorFactory:** Implementar en vistas públicas de cotizaciones/proyectos (cuando existan)
3. **Integración Tenant:** Completar `obtener_datos_documento_publico()` con acceso real a modelos del tenant

---

**Última actualización:** 2024-12-19  
**Versión:** 3.3
