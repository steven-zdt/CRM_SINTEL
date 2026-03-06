# Flujo End-to-End Simulado: Onboarding → Workspace

## ⚠️ POLÍTICA v2.30: Arquitectura API-First

Este documento simula paso a paso el flujo completo desde la creación del tenant hasta la visualización en workspace, validando que todos los componentes funcionan correctamente según la arquitectura API-First v2.30.

---

## PASO 1: Alta del Tenant desde la Consola Pública

### 1.1 Acceso a la Consola
- **URL**: `http://sintel.com/console/tenants/`
- **Dominio**: Público (ROOT_URLCONF)
- **Autenticación**: Usuario staff/superuser

### 1.2 Formulario "Nuevo Tenant"
- **Endpoint**: `POST /api/public/v1/tenants/onboard/`
- **Datos mínimos**:
  ```json
  {
    "nombre": "Empresa Test",
    "email_admin": "owner@test.com",
    "schema_name": "test-empresa"
  }
  ```
- **Servicio**: `apps.services.onboarding.empresa_service.crear_empresa()`
- **Acciones del servicio**:
  1. Crea `Client` con `auto_create_schema=True`
  2. Crea `Domain` primario (FQDN sin puerto en producción)
  3. Crea `User` owner (sin password usable)
  4. Crea `TenantMembership` activa
  5. Genera token de activación
  6. Retorna `login_url` al dominio del tenant

### 1.3 Dominio Resultante
- **Ejemplo**: `home.sintel.com`
- **Resolución**: Por hostname (no por subcarpeta)
- **Middleware**: `TenantMainMiddleware` detecta el dominio y cambia al esquema del tenant

### 1.4 Correo de Invitación
- **URL de activación**: `https://home.sintel.com/static/tenant/landing/activate.html?token=...`
- **Shell estático**: Consume API, no HTML dinámico del backend

---

## PASO 2: Activación del Owner en el Dominio del Tenant

### 2.1 El Owner Abre el Enlace
- **URL**: `https://home.sintel.com/static/tenant/landing/activate.html?token=...`
- **Shell**: Estático en `apps/tenant/landing/static/tenant/landing/activate.html`
- **URLCONF**: Ahora bajo TENANT_URLCONF (privado)

### 2.2 Validación del Token (GET)
- **Endpoint**: `GET /api/v1/core/landing/auth/activate/?token=...`
- **Respuestas posibles**:
  - **200 OK**: Token válido, usuario sin password usable → mostrar formulario
  - **409 CONFLICT**: Cuenta ya activada → mostrar mensaje y redirigir a Login
  - **400 BAD REQUEST**: Token inválido/expirado → ofrecer solicitar nuevo

### 2.3 Activación (POST)
- **Endpoint**: `POST /api/v1/core/landing/auth/activate/?token=...`
- **Payload**:
  ```json
  {
    "password1": "nuevapass123",
    "password2": "nuevapass123"
  }
  ```
- **Respuesta**: `200 OK` con:
  ```json
  {
    "detail": "Cuenta activada exitosamente.",
    "redirect_url": "https://home.sintel.com/workspace/",
    "user": {...},
    "tenant": {...}
  }
  ```
- **Acción del shell**: Redirige con `window.location.href = data.redirect_url`

---

## PASO 3: Iniciar Sesión (UI Única Orquestada por Core)

### 3.1 Landing del Tenant
- **URL**: `GET http://home.sintel.com/`
- **Redirección**: `/static/tenant/landing/index.html` (shell estático)
- **Botón "Iniciar Sesión"**: Apunta a `/static/tenant/landing/login.html`

### 3.2 Login desde el Shell
- **Shell**: `apps/tenant/landing/static/tenant/landing/login.html`
- **Endpoint**: `POST /api/v1/core/auth/login/`
- **Payload**:
  ```json
  {
    "email": "owner@test.com",
    "password": "nuevapass123"
  }
  ```
- **Respuesta exitosa** (`200 OK`):
  ```json
  {
    "detail": "Login exitoso.",
    "redirect_url": "https://home.sintel.com/workspace/",
    "user": {...},
    "tenant": {...}
  }
  ```
- **Sin membresía**: Error controlado (401/403), no se permite acceso

### 3.3 Logout
- **Endpoint**: `POST /api/v1/core/auth/logout/`
- **Respuesta**: `200 OK` con `redirect_url="/"`
- **Acción**: Frontend redirige a landing

**⚠️ CLAVE v2.30**: Login/logout/reset van exclusivamente por Core (`/api/v1/core/auth/*`). Landing API solo conserva `info` y `activate`. La UI (shells) siempre consume Core para auth.

---

## PASO 4: Reset de Contraseña (desde la UI Única)

### 4.1 Solicitud de Reset
- **Endpoint**: `POST /api/v1/core/auth/password-reset/request/`
- **Payload**:
  ```json
  {
    "email": "owner@test.com"
  }
  ```
- **Respuesta**: `200 OK` (idempotente, no filtra existencia de usuarios)
- **Shell**: `apps/tenant/landing/static/tenant/landing/reset-request.html`

### 4.2 Validación / Confirmación
- **Validación**: `POST /api/v1/core/auth/password-reset/validate/`
- **Confirmación**: `POST /api/v1/core/auth/password-reset/confirm/`
- **Payload confirmación**:
  ```json
  {
    "uid": "...",
    "token": "...",
    "password1": "newpass123",
    "password2": "newpass123"
  }
  ```
- **Respuesta**: `200 OK` con `redirect_url` (p. ej. `/workspace/#landing`)
- **Shell**: `apps/tenant/landing/static/tenant/landing/reset-confirm.html`

---

## PASO 5: Ver los Datos del Cliente en Workspace (Core Orquesta)

### 5.1 Navegación
- **URL**: `GET http://home.sintel.com/workspace/`
- **Vista**: `apps.tenant.core.views_ui.WorkspaceView`
- **Template**: `apps/tenant/core/templates/tenant/core/workspace.html`
- **Autenticación**: Requerida (cookie/sesión en el dominio del tenant)

### 5.2 Orquestación de Datos (Core)
El workspace consume exclusivamente Core API:

- **Empresa (SSoT)**: `GET /api/v1/core/mi-empresa/`
- **Perfil del usuario**: `GET /api/v1/core/mi-perfil/`
- **Facturas (resumen)**: `GET /api/v1/core/facturas/resumen/`
- **Contabilidad (resumen)**: `GET /api/v1/core/contabilidad/resumen/`
- **Dashboard completo**: `GET /api/v1/core/dashboard/`

**⚠️ POLÍTICA**: Estas rutas de Core delegan en services/providers de las TENANT_APPS (empresa, perfil, facturas, contabilidad) y nunca duplican la lógica.

### 5.3 Workspace Listo
- **Template**: Renderiza layout (navbar, secciones, tarjetas)
- **HTMX**: Carga partials lazy desde `/ui/<app>/partials/<name>/`
- **JavaScript**: Cada partial ejecuta su módulo JS para cargar datos desde Core API
- **Branding**: Si la empresa existe (singleton por tenant), se muestra logo/nombre; si no, placeholders

---

## PASO 6: Pruebas de Humo (Validación Rápida del Circuito)

### 6.1 Routing por Hostname
- **Verificación**: Con `HTTP_HOST='home.sintel.com'`, los requests a `/api/v1/*` usan TENANT_URLCONF (privado)
- **Middleware**: `TenantMainMiddleware` + `TenantURLConfMiddleware` en orden correcto
- **Resultado esperado**: No hay 404/mezclas con ROOT_URLCONF

### 6.2 Activación
- **GET**: `/api/v1/core/landing/auth/activate/?token=...` → 200/409/400 según estado
- **POST**: `/api/v1/core/landing/auth/activate/?token=...` → 200 con `redirect_url` absoluta a `/workspace/`

### 6.3 Login (Core)
- **POST**: `/api/v1/core/auth/login/` → 200 + `redirect_url="/workspace/"` si credenciales correctas y hay membresía
- **Sin membresía**: Error controlado (401/403)

### 6.4 Logout (Core)
- **POST**: `/api/v1/core/auth/logout/` → 200 + `redirect_url="/"`

### 6.5 Resúmenes Core
- **GET**: `/api/v1/core/mi-empresa/` → 200 con estructura mínima
- **GET**: `/api/v1/core/mi-perfil/` → 200 con estructura mínima
- **GET**: `/api/v1/core/facturas/resumen/` → 200 con estructura mínima
- **GET**: `/api/v1/core/contabilidad/resumen/` → 200 con estructura mínima
- **GET**: `/api/v1/core/dashboard/` → 200 con estructura completa
- **Resultado**: `workspace.html` debe verse poblado

---

## Resultado Esperado

✅ **Tenant creado** desde la consola pública y accesible solo por su dominio (`home.sintel.com`)

✅ **Owner activado** vía shell estático que consume la API (sin HTML renderizado por backend)

✅ **Login/Logout/Reset** por Core API y la UI redirige con `redirect_url`

✅ **Workspace de Core visible**, con datos orquestados desde las TENANT_APPS a través de los services y providers definidos, sin duplicación de lógica, siguiendo API‑First

---

## Notas Técnicas Finales

### UI = Shells Estáticos
- Ubicación: `/static/tenant/landing/*.html`
- Consumen: JSON de `/api/v1/core/*` y, para activación, `/api/v1/landing/auth/activate/`
- No hay vistas HTML dinámicas en backend

### Core API = Orquestador Único
- UI privada: Todos los flujos de autenticación están en Core
- Landing API: Reducida a `info` y `activate`
- SSoT: Core es la única fuente de verdad para auth

### Resolución por Hostname
- Garantizada por middlewares y configuración ROOT_URLCONF/TENANT_URLCONF
- Separación público/privado: Dominio público → ROOT_URLCONF, Subdominio tenant → TENANT_URLCONF
