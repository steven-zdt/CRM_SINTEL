# 📋 Documentación Técnica: Onboarding de Tenants Privados

**Versión:** 1.0  
**Fecha:** 2024-12-19  
**Alcance:** Proceso completo de creación de tenants privados desde el esquema público  
**Referencia:** `apps/public/FLUJO_APLICACION_PUBLIC_v3.3.md`

---

## 1. Visión General de la Arquitectura Pública

El esquema público (`schema='public'`) es el núcleo del sistema multi-tenant SINTEL. Contiene las aplicaciones compartidas que gestionan la infraestructura del SaaS y proporcionan servicios centralizados a todos los tenants privados.

### 1.1 Aplicaciones del Esquema Público

#### `apps/public/core/`
**Propósito:** Funcionalidades core del esquema público (middleware, vistas, landing page).

**Componentes clave:**
- **`PublicIndexView`**: Landing page profesional con redirección inteligente según estado del usuario
- **Middleware**: `ForceNoPortMiddleware`, `HTTPSRedirectMiddleware`, `CSRFTrustedOriginMiddleware`, `RequestContextMiddleware`
- **Templates**: Landing page (`public/core/index.html`) con Bootstrap 5

**Responsabilidades:**
- Renderizar landing page para usuarios anónimos
- Redirigir usuarios autenticados según permisos (staff → `/console/`, normal → `/admin/login/`)
- Normalizar hosts y manejar seguridad de dominios

#### `apps/public/accounts/`
**Propósito:** Gestión de usuarios globales que pueden pertenecer a múltiples tenants.

**Componentes clave:**
- **Modelo `User`**: Usuarios globales en esquema `public` (AUTH_USER_MODEL)
- **Service Layer**: `create_user_service()`, `update_user_service()` en `api/services/user_service.py`
- **API Endpoints**: CRUD completo de usuarios (`/api/admin/v1/accounts/users/`)

**Responsabilidades:**
- Crear y gestionar usuarios globales con hashing seguro de contraseñas
- Generar usernames únicos desde emails
- Normalizar emails a minúsculas
- Proporcionar usuarios administradores para nuevos tenants

#### `apps/public/tenants/`
**Propósito:** Gestión de tenants (Client), dominios y membresías de usuarios a tenants.

**Componentes clave:**
- **Modelo `Client`**: Representa un tenant (empresa/cliente) con `auto_create_schema=True`
- **Modelo `Domain`**: Dominios asociados a tenants (FQDN sin puerto)
- **Modelo `TenantMembership`**: Relación muchos-a-muchos entre usuarios y tenants
- **Service Layer**: `crear_tenant_con_owner()` en `apps/services/onboarding/empresa_service.py`
- **API Endpoints**: CRUD completo de tenants (`/api/public/v1/tenants/`) y endpoint de onboarding (`/api/public/v1/tenants/onboard/`)

**Responsabilidades:**
- Crear esquemas PostgreSQL para nuevos tenants
- Ejecutar migraciones de TENANT_APPS automáticamente
- Registrar dominios FQDN normalizados
- Asignar usuarios propietarios (primary admin) a tenants
- Generar tokens de invitación y enviar emails de activación

#### `apps/public/console/`
**Propósito:** Interfaz de administración web para gestión de tenants, usuarios y catálogos DIAN.

**Componentes clave:**
- **Vistas TemplateView**: `TenantsListView`, `TenantsNewView`, `TenantsStatusView`, `UsersListView`
- **Mixins**: `StaffRequiredMixin`, `PublicSchemaMixin`, `ConsoleTemplateView`
- **Templates**: Formularios HTML con JavaScript para consumo de APIs REST
- **API Endpoints DataTables**: `/api/admin/v1/console/dt/tenants/`, `/api/admin/v1/console/dt/users/`

**Responsabilidades:**
- Renderizar formularios de creación de tenants
- Consumir APIs REST para operaciones CRUD
- Mostrar listas de tenants y usuarios con DataTables
- Gestionar estado de creación de tenants (polling HTMX)

### 1.2 Principios Arquitectónicos

- **SSoT (Single Source of Truth)**: Los modelos en `apps/public/` son la única fuente de verdad para datos compartidos
- **Unidireccionalidad**: Los modelos de tenant pueden referenciar modelos públicos, pero NO al revés
- **API-First**: Toda la lógica de negocio expuesta vía DRF REST API
- **Service Layer Pattern**: Lógica de negocio en `services.py`, views y serializers anémicos
- **Atomicidad**: Procesos de onboarding transaccionales (`@transaction.atomic`)
- **Idempotencia**: Operaciones seguras frente a recargas/autoreloads

---

## 2. Mapa de Enrutamiento (Endpoints)

### 2.1 URLs Públicas (Esquema `public`)

| Ruta | Vista/ViewSet | App | Método | Permisos | Descripción |
|------|---------------|-----|--------|----------|-------------|
| `/` | `PublicIndexView` | `public.core` | GET | Anónimo | Landing page o redirección según autenticación |
| `/admin/` | `admin.site.urls` | Django Admin | GET | Staff | Admin de Django (gestión global) |
| `/console/` | `DashboardView` | `public.console` | GET | Staff | Dashboard principal de la consola |
| `/console/tenants/` | `TenantsListView` | `public.console` | GET | Staff | Lista de tenants (DataTables) |
| `/console/tenants/new/` | `TenantsNewView` | `public.console` | GET | Staff | Formulario de creación de tenant |
| `/console/tenants/status/` | `tenants_status_page` | `public.console` | GET | Staff | Página de estado de creación (polling HTMX) |
| `/console/users/` | `UsersListView` | `public.console` | GET | Staff | Lista de usuarios globales (DataTables) |

### 2.2 API Endpoints REST

| Ruta | ViewSet/Action | App | Método | Permisos | Descripción |
|------|----------------|-----|--------|----------|-------------|
| `/api/public/v1/tenants/` | `ClientViewSet.list()` | `public.tenants` | GET | IsAdminUser | Lista todos los tenants |
| `/api/public/v1/tenants/` | `ClientViewSet.create()` | `public.tenants` | POST | IsAdminUser | Crear tenant (CRUD estándar) |
| `/api/public/v1/tenants/onboard/` | `ClientViewSet.onboard()` | `public.tenants` | POST | IsAdminUser | **Onboarding completo de tenant con propietario** |
| `/api/public/v1/tenants/{id}/` | `ClientViewSet.retrieve()` | `public.tenants` | GET | IsAdminUser | Detalle de tenant |
| `/api/public/v1/tenants/{id}/` | `ClientViewSet.update()` | `public.tenants` | PATCH/PUT | IsAdminUser | Actualizar tenant |
| `/api/public/v1/tenants/{id}/` | `ClientViewSet.destroy()` | `public.tenants` | DELETE | IsAdminUser | Eliminar tenant (hard delete) |
| `/api/public/v1/tenants/{id}/toggle-active/` | `ClientViewSet.toggle_active()` | `public.tenants` | POST | IsAdminUser | Activar/desactivar tenant |
| `/api/admin/v1/accounts/users/` | `UserViewSet` | `public.accounts` | GET/POST/PATCH/DELETE | IsAdminUser | CRUD de usuarios globales |
| `/api/admin/v1/console/dt/tenants/` | `TenantsDataTablesView` | `public.console` | POST | IsAdminUser | Datos para DataTables de tenants |
| `/api/admin/v1/console/dt/users/` | `UsersDataTablesView` | `public.console` | POST | IsAdminUser | Datos para DataTables de usuarios |

### 2.3 Configuración de URLs

**Archivo principal:** `config/urls_public.py`

```python
urlpatterns = [
    path('', PublicIndexView.as_view(), name='public_index'),
    path('admin/', admin.site.urls),
    path('console/', include('apps.public.console.urls')),
    path('api/public/v1/', include('config.public_api_urls')),
    path('api/admin/v1/console/', include('apps.public.console.api.urls')),
    path('api/admin/v1/accounts/', include('apps.public.accounts.api.urls')),
]
```

**Archivo de consola:** `apps/public/console/urls.py`

```python
urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('tenants/', TenantsListView.as_view(), name='tenants-list'),
    path('tenants/new/', TenantsNewView.as_view(), name='tenants-new'),
    path('tenants/status/', tenants_status_page, name='tenants-status'),
    path('users/', UsersListView.as_view(), name='users-list'),
]
```

---

## 3. Flujo Paso a Paso de Creación de un Tenant

### 3.1 Fase 1: Acceso a la Consola

**Paso 1.1:** Usuario administrador accede a `http://sintel.com/console/tenants/new/`

**Proceso:**
1. **Middleware Chain:**
   - `ForceNoPortMiddleware`: Normaliza `HTTP_HOST` eliminando puerto
   - `TenantMainMiddleware`: Resuelve tenant desde dominio → `schema='public'`
   - `TenantSecurityAndURLConfMiddleware`: Valida acceso público y establece `request.urlconf = 'config.urls_public'`

2. **Resolución de URL:**
   - Django resuelve `/console/tenants/new/` → `apps/public/console/urls.py` → `TenantsNewView`

3. **Vista `TenantsNewView`:**
   - Verifica permisos: `StaffRequiredMixin` (requiere `is_staff=True`)
   - Verifica esquema: `PublicSchemaMixin` (requiere `schema='public'`)
   - Renderiza template: `console/pages/tenants/new.html`
   - Contexto incluye: `api_onboard_url='/api/public/v1/tenants/onboard/'`, `api_users_url`, `tenant_domain_base`

### 3.2 Fase 2: Formulario de Creación

**Paso 2.1:** Usuario completa el formulario en `console/pages/tenants/new.html`

**Campos del formulario:**
- **`nombre`** (requerido): Nombre de la empresa/tenant (ej: "Acme SAS")
- **`schema_name`** (requerido): Código único del tenant en PostgreSQL (ej: "acme")
  - Validaciones frontend: Solo letras minúsculas, números y guiones bajos (`[a-z0-9_]+`)
  - Máximo 63 caracteres (límite de PostgreSQL)
  - No puede ser `"public"` (reservado)
  - No puede contener puntos
- **`dominio_fqdn`** (opcional): Dominio FQDN personalizado (si no se proporciona, se autogenera como `<schema>.<TENANT_DOMAIN_BASE>`)
- **`owner_email`** (requerido si no se proporciona `admin_user_id`): Email del propietario
- **`admin_user_id`** (opcional): ID del usuario administrador existente (alternativa a `owner_email`)
- **`paid_until`** (opcional): Fecha de pago hasta
- **`on_trial`** (opcional, default: `true`): Si está en período de prueba

**Paso 2.2:** JavaScript del formulario valida campos y realiza `POST /api/public/v1/tenants/onboard/`

**Payload enviado:**
```json
{
    "nombre": "Acme SAS",
    "schema_name": "acme",
    "dominio_fqdn": "acme.sintel.com",
    "owner_email": "admin@acme.com",
    "paid_until": null,
    "on_trial": true
}
```

### 3.3 Fase 3: Procesamiento en el Backend

**Paso 3.1:** `ClientViewSet.onboard()` recibe la petición

**Ubicación:** `apps/public/tenants/api/viewsets.py` (líneas 58-176)

**Proceso:**
1. **Validación de permisos:** `IsAdminUser` (requiere `is_staff=True`)
2. **Validación de datos:** `OnboardTenantWithOwnerSerializer` valida payload
3. **Llamada al servicio:** `crear_tenant_con_owner(**serializer.validated_data)`
4. **Manejo de errores:**
   - `ValidationError` → 400 Bad Request
   - `ValueError` → 400 Bad Request
   - `Exception` → 500 Internal Server Error
5. **Respuesta exitosa:** 201 Created con dict `{"client_id", "domain", "membership_id", "login_url"}`

### 3.4 Fase 4: Servicio de Onboarding

**Paso 4.1:** `crear_tenant_con_owner()` ejecuta el proceso atómico

**Ubicación:** `apps/services/onboarding/empresa_service.py` (líneas 196-520)

**Decorador:** `@transaction.atomic` (garantiza atomicidad: todo o nada)

**Orden de ejecución:**

#### 4.1.1 Resolver Usuario Administrador

**Lógica:**
- Si `admin_user_id` está presente: Obtener usuario existente por ID
- Si `owner_email` está presente: Crear/obtener usuario por email (idempotente)
  - Si usuario existe: Usar existente
  - Si usuario no existe: Crear nuevo con `set_unusable_password()` (se activará en subdominio)
  - Generar username único desde email si el modelo tiene campo `username`

**Ubicación:** Líneas 263-326

**Resultado:** Objeto `User` en esquema `public`

#### 4.1.2 Validar Schema Name

**Lógica:**
- Normalizar `schema_name` a minúsculas y sin espacios
- Validar formato: `validate_schema_name(raw_schema)`
- Verificar que no contenga puntos
- Verificar que no sea `"public"` (reservado)
- Verificar unicidad: `Client.objects.filter(schema_name=raw_schema).exists()`

**Ubicación:** Líneas 328-331

**Resultado:** `schema_name` validado y normalizado

#### 4.1.3 Crear Client (Tenant)

**Lógica:**
- Crear instancia `Client` con:
  - `schema_name=raw_schema`
  - `nombre=nombre.strip()`
  - `paid_until=paid_until`
  - `on_trial=on_trial`
  - `is_active=True`
- **CRÍTICO:** `client.save()` con `auto_create_schema=True`
  - django-tenants ejecuta automáticamente:
    1. `CREATE SCHEMA {schema_name}` en PostgreSQL
    2. `migrate_schemas --schema {schema_name}` (aplica migraciones de TENANT_APPS)

**Ubicación:** Líneas 333-343

**Resultado:** 
- Registro en tabla `public.tenants_client`
- Esquema PostgreSQL `{schema_name}` creado
- Tablas de TENANT_APPS migradas en el esquema

#### 4.1.4 Crear Domain (Dominio Principal)

**Lógica:**
- Construir dominio FQDN: `_build_primary_domain(schema_name, dominio_fqdn)`
  - Si `dominio_fqdn` está vacío o inválido: Autogenerar como `<schema>.<TENANT_DOMAIN_BASE>`
  - Normalizar dominio: Eliminar protocolo, www, puerto, rutas
  - Validar FQDN: `validate_fqdn(fqdn)`
- Crear `Domain` con:
  - `domain=primary_fqdn` (sin puerto, sin www)
  - `tenant=client`
  - `is_primary=True`
- Manejar condiciones de carrera: `get_or_create()` con read-back en caso de `IntegrityError`

**Ubicación:** Líneas 345-367

**Resultado:** Registro en tabla `public.tenants_domain`

#### 4.1.5 Crear TenantMembership (Propietario)

**Lógica:**
- Crear `TenantMembership` con:
  - `client=client`
  - `user=user` (usuario administrador)
  - `rol="ADMIN"`
  - `is_primary_admin=True`
  - `is_active=True`
- Idempotente: `get_or_create()` para evitar duplicados

**Ubicación:** Líneas 369-379

**Resultado:** Registro en tabla `public.tenants_tenantmembership`

#### 4.1.6 Seed Opcional de Perfil

**Lógica:**
- Verificar que tabla `perfil_tenantprofile` existe en el schema del tenant
- Si no existe: Forzar migraciones con `_ensure_schema_ready(client, required_tables)`
- Si existe: Crear `TenantProfile` dentro de `schema_context(client.schema_name)`:
  - `user=user`
  - `cargo="Administrador Principal"`
  - `departamento="Gerencia"`
  - `configuracion={"theme": "light", "notifications": True}`
- **CRÍTICO:** Si el seed falla, NO abortar el onboarding (es opcional)

**Ubicación:** Líneas 381-424

**Resultado:** Perfil creado en el schema del tenant (si la tabla existe)

#### 4.1.7 Generar Token de Invitación y Enviar Email

**Lógica:**
- Solo si `owner_email` fue proporcionado (no si se usó `admin_user_id`)
- Generar token de invitación con TTL de 24 horas: `generate_invitation_token(user_id, tenant_id, ttl_hours=24)`
- Construir URL de activación: `build_activation_url(domain.domain, token)`
- Enviar email de invitación: `send_invitation_email(user, client, activation_url)`
- **CRÍTICO:** Si el envío de email falla, NO abortar el onboarding

**Ubicación:** Líneas 426-497

**Resultado:** Token generado y email enviado (o URL construida en modo desarrollo)

#### 4.1.8 Construir Login URL

**Lógica:**
- Construir URL de login: `_build_login_url(domain.domain)`
  - Protocolo: `https` si `SECURE_SSL_REDIRECT=True` y no DEBUG, sino `http`
  - Puerto: Incluir `:APP_PORT` en desarrollo si está configurado
  - Formato: `{protocol}://{domain_with_port}/`

**Ubicación:** Líneas 499-500

**Resultado:** URL completa de acceso al tenant (ej: `http://acme.sintel.com:8000/`)

#### 4.1.9 Retornar Resultado

**Lógica:**
- Construir dict de respuesta:
  ```python
  {
      "client_id": client.id,
      "domain": domain.domain,
      "membership_id": membership.id,
      "login_url": login_url,
      "activation_url": activation_url  # Si se generó
  }
  ```
- Logging de éxito
- Retornar dict

**Ubicación:** Líneas 502-520

**Resultado:** Dict con información completa del tenant creado

### 3.5 Fase 5: Respuesta al Frontend

**Paso 5.1:** JavaScript recibe respuesta 201 Created

**Payload recibido:**
```json
{
    "client_id": 42,
    "domain": "acme.sintel.com",
    "membership_id": 15,
    "login_url": "http://acme.sintel.com:8000/",
    "activation_url": "http://acme.sintel.com:8000/activate/?token=abc123..."
}
```

**Paso 5.2:** Frontend muestra mensaje de éxito y URL de acceso

**Acciones del frontend:**
- Mostrar mensaje: "Tenant creado exitosamente"
- Mostrar `login_url` como enlace clickeable
- Mostrar `activation_url` si está presente (para invitación por email)
- Opcionalmente redirigir a página de estado: `/console/tenants/status/?client_id=42`

---

## 4. Diagrama de Flujo

```mermaid
graph TB
    Start([Usuario Admin accede a /console/tenants/new/]) --> Middleware[Middleware Chain:<br/>ForceNoPortMiddleware<br/>TenantMainMiddleware<br/>TenantSecurityAndURLConfMiddleware]
    Middleware --> ResolveURL[Resolución de URL:<br/>config/urls_public.py<br/>apps/public/console/urls.py]
    ResolveURL --> TenantsNewView[TenantsNewView.render]
    TenantsNewView --> RenderForm[Renderizar template:<br/>console/pages/tenants/new.html]
    RenderForm --> UserFills[Usuario completa formulario:<br/>nombre, schema_name, owner_email]
    UserFills --> JSValidate[Validación JavaScript<br/>en el frontend]
    JSValidate --> POSTOnboard[POST /api/public/v1/tenants/onboard/]
    POSTOnboard --> ClientViewSet[ClientViewSet.onboard]
    ClientViewSet --> ValidatePerms{¿Usuario es staff?}
    ValidatePerms -->|No| Error403[403 Forbidden]
    ValidatePerms -->|Sí| ValidateSerializer[OnboardTenantWithOwnerSerializer.is_valid]
    ValidateSerializer -->|Inválido| Error400[400 Bad Request<br/>Errores de validación]
    ValidateSerializer -->|Válido| CallService[crear_tenant_con_owner<br/>@transaction.atomic]
    
    CallService --> ResolveUser{¿admin_user_id<br/>o owner_email?}
    ResolveUser -->|admin_user_id| GetUser[User.objects.get<br/>pk=admin_user_id]
    ResolveUser -->|owner_email| CreateUser[User.objects.filter<br/>email=owner_email<br/>o create con<br/>set_unusable_password]
    
    GetUser --> ValidateSchema[Validar schema_name:<br/>validate_schema_name<br/>Verificar unicidad]
    CreateUser --> ValidateSchema
    ValidateSchema -->|Inválido| Rollback[ROLLBACK Transaction]
    ValidateSchema -->|Válido| CreateClient[Client.save<br/>auto_create_schema=True]
    
    CreateClient --> DjangoTenants[django-tenants ejecuta:<br/>CREATE SCHEMA {schema}<br/>migrate_schemas --schema {schema}]
    DjangoTenants --> CreateDomain[Domain.objects.get_or_create<br/>domain=primary_fqdn<br/>is_primary=True]
    CreateDomain --> CreateMembership[TenantMembership.objects.get_or_create<br/>rol=ADMIN<br/>is_primary_admin=True]
    CreateMembership --> SeedProfile{¿Tabla<br/>perfil_tenantprofile<br/>existe?}
    
    SeedProfile -->|Sí| CreateProfile[TenantProfile.objects.get_or_create<br/>dentro de schema_context]
    SeedProfile -->|No| SkipProfile[Omitir seed<br/>continuar onboarding]
    CreateProfile --> GenerateToken{¿owner_email<br/>proporcionado?}
    SkipProfile --> GenerateToken
    
    GenerateToken -->|Sí| Invitation[generate_invitation_token<br/>send_invitation_email]
    GenerateToken -->|No| BuildLoginURL
    Invitation --> BuildLoginURL[build_login_url<br/>domain.domain]
    
    BuildLoginURL --> ReturnResult[Retornar dict:<br/>client_id, domain,<br/>membership_id, login_url]
    ReturnResult --> Response201[201 Created<br/>Response con dict]
    Response201 --> FrontendSuccess[Frontend muestra:<br/>Mensaje de éxito<br/>URL de acceso<br/>activation_url si existe]
    
    Rollback --> Error400
    Error403 --> End([Fin])
    Error400 --> End
    FrontendSuccess --> End
    
    style Start fill:#e1f5ff
    style End fill:#ffe1f5
    style CallService fill:#fff4e1
    style DjangoTenants fill:#e1ffe1
    style Response201 fill:#e1ffe1
    style Error400 fill:#ffe1e1
    style Error403 fill:#ffe1e1
    style Rollback fill:#ffe1e1
```

---

## 5. Dependencias y Llamados entre Apps

### 5.1 Flujo de Dependencias

```
┌─────────────────────────────────────────────────────────────────┐
│                    apps/public/console/                          │
│  (Interfaz de Usuario - TemplateViews y JavaScript)             │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              │ HTTP POST
                              │ /api/public/v1/tenants/onboard/
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              apps/public/tenants/api/viewsets.py               │
│              ClientViewSet.onboard()                             │
│  - Validación de permisos (IsAdminUser)                         │
│  - Validación de datos (OnboardTenantWithOwnerSerializer)      │
│  - Manejo de errores (400, 403, 500)                           │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              │ Llamada directa
                              │ crear_tenant_con_owner()
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│      apps/services/onboarding/empresa_service.py               │
│      crear_tenant_con_owner()                                    │
│  - @transaction.atomic (atomicidad)                             │
│  - Resolución de usuario (create_user_service)                  │
│  - Creación de Client (auto_create_schema=True)                  │
│  - Creación de Domain                                            │
│  - Creación de TenantMembership                                  │
│  - Seed opcional de TenantProfile                               │
│  - Generación de token de invitación                            │
└────────────────────────────┬────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ apps/public/ │   │  django-tenants  │   │ apps/public/     │
│ accounts/api/│   │  (auto_create_   │   │ tenants/services/│
│ services/    │   │  schema=True)    │   │ invitations.py   │
│ user_service │   │                  │   │                  │
│ .py          │   │  - CREATE SCHEMA │   │  - generate_     │
│              │   │  - migrate_      │   │    invitation_    │
│ create_user_ │   │    schemas       │   │    token()        │
│ service()    │   │                  │   │  - send_         │
│              │   │                  │   │    invitation_    │
│              │   │                  │   │    email()        │
└───────────────┘   └──────────────────┘   └──────────────────┘
```

### 5.2 Inyección de Dependencias

#### 5.2.1 Service Layer Pattern

**Principio:** La lógica de negocio se centraliza en funciones de servicio, no en views o serializers.

**Ejemplo:**
```python
# ❌ INCORRECTO: Lógica en el ViewSet
class ClientViewSet(viewsets.ModelViewSet):
    def onboard(self, request):
        # Lógica de negocio aquí (INCORRECTO)
        user = User.objects.create(...)
        client = Client.objects.create(...)
        # ...

# ✅ CORRECTO: Lógica en el servicio
class ClientViewSet(viewsets.ModelViewSet):
    def onboard(self, request):
        # ViewSet solo valida y delega
        serializer = OnboardTenantWithOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = crear_tenant_con_owner(**serializer.validated_data)
        return Response(result, status=201)
```

#### 5.2.2 Uso de Servicios entre Apps

**`apps/public/tenants/api/viewsets.py` → `apps/services/onboarding/empresa_service.py`:**
```python
from apps.services.onboarding.empresa_service import crear_tenant_con_owner

# En ClientViewSet.onboard()
result = crear_tenant_con_owner(**serializer.validated_data)
```

**`apps/services/onboarding/empresa_service.py` → `apps/public/accounts/api/services/user_service.py`:**
```python
from apps.public.accounts.api.services.user_service import create_user_service

# En crear_tenant_con_owner() (solo si se necesita crear usuario con password)
user = create_user_service(email=email, password=password, ...)
```

**`apps/services/onboarding/empresa_service.py` → `apps/public/tenants/services/invitations.py`:**
```python
from apps.public.tenants.services.invitations import (
    generate_invitation_token,
    send_invitation_email,
    build_activation_url,
)

# En crear_tenant_con_owner()
token = generate_invitation_token(user_id=user.id, tenant_id=client.id)
activation_url = build_activation_url(domain.domain, token)
send_invitation_email(user, client, activation_url)
```

### 5.3 Redirecciones

**No hay redirecciones directas entre apps durante el onboarding.** El flujo es:

1. **Frontend → API:** JavaScript realiza `POST /api/public/v1/tenants/onboard/`
2. **API → Service:** ViewSet llama a `crear_tenant_con_owner()`
3. **Service → ORM:** Servicio crea modelos usando Django ORM
4. **Service → django-tenants:** `Client.save()` con `auto_create_schema=True` ejecuta migraciones
5. **API → Frontend:** ViewSet retorna `Response` con datos JSON

### 5.4 Signals (Señales de Django)

**No se utilizan signals para el proceso de onboarding.** El flujo es explícito:

- **Domain NO se crea por signal:** Se crea explícitamente en `crear_tenant_con_owner()` (línea 351)
- **TenantMembership NO se crea por signal:** Se crea explícitamente (línea 371)
- **TenantProfile NO se crea por signal:** Se crea explícitamente dentro de `schema_context` (línea 396)

**Razón:** Mayor control, depuración más fácil, y garantía de orden de ejecución.

### 5.5 Transacciones Atómicas

**Decorador:** `@transaction.atomic` en `crear_tenant_con_owner()`

**Garantía:** Si cualquier paso falla, se hace ROLLBACK de toda la transacción:
- Usuario NO creado
- Client NO creado
- Schema PostgreSQL NO creado
- Domain NO creado
- TenantMembership NO creado

**Excepción:** El seed de perfil y el envío de email son opcionales y no abortan el onboarding si fallan.

### 5.6 Context Managers

**`schema_context(schema_name)`:**
- Usado para ejecutar código dentro del schema del tenant
- Ejemplo: Crear `TenantProfile` en el schema del tenant (línea 394)

```python
with schema_context(client.schema_name):
    from apps.tenant.perfil.models import TenantProfile
    TenantProfile.objects.get_or_create(user=user, defaults={...})
```

---

## 6. Consideraciones de Seguridad

### 6.1 Validaciones de Permisos

- **`IsAdminUser`**: Requerido para todas las operaciones de onboarding
- **`StaffRequiredMixin`**: Requerido para acceso a vistas de consola
- **`PublicSchemaMixin`**: Requerido para asegurar que se accede desde esquema `public`

### 6.2 Validaciones de Datos

- **Schema Name**: Validado con `validate_schema_name()` (sin puntos, no "public", único)
- **Email**: Normalizado a minúsculas, validado por Django
- **Domain FQDN**: Normalizado (sin protocolo, www, puerto), validado con `validate_fqdn()`

### 6.3 Protección del Tenant Público

- **Candado en modelo:** `Client.delete()` bloquea eliminación de tenant `public`
- **Candado en API:** `ClientViewSet.destroy()` bloquea eliminación de tenant `public`
- **Logging de seguridad:** Intentos de eliminación registrados en `security.tenants` logger

---

## 7. Referencias

- **Documentación oficial django-tenants:** https://django-tenants.readthedocs.io/
- **Flujo completo de aplicación pública:** `apps/public/FLUJO_APLICACION_PUBLIC_v3.3.md`
- **Reglas de arquitectura:** `.cursor/rules/reglas.mdc`
- **Arquitectura general:** `documentacion/arquitectura_general.md`

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.0
