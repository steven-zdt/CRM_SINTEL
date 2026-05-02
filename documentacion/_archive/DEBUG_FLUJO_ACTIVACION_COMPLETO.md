# 🔍 Debug: Flujo Completo de Activación de Tenant (Paso a Paso)

## 📋 Objetivo

Documentar el flujo completo desde la creación del tenant hasta la activación, identificando cada punto donde el enrutamiento puede fallar.

---

## 🔄 Flujo Completo (Paso a Paso)

### PASO 1: Creación del Tenant en Consola Pública

**URL:** `http://sintel.com/console/tenants/`

**Proceso:**
1. Usuario staff accede a la consola pública
2. Completa formulario de creación de tenant:
   - `nombre`: Nombre de la empresa
   - `schema_name`: Código del tenant (ej: "cliente")
   - `dominio_fqdn`: Opcional (se autogenera como `<schema>.sintel.com`)
   - `owner_email`: Email del owner
3. Sistema ejecuta `crear_tenant_con_owner()`:
   - Crea `User` con `set_unusable_password()`
   - Crea `Client` (dispara `auto_create_schema=True`)
   - Crea `Domain` con FQDN normalizado
   - Crea `TenantMembership` (ADMIN, `is_primary_admin=True`)
   - Genera token de invitación
   - Envía email con link de activación

**Verificación:**
```python
# Verificar tenant creado
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import schema_context

with schema_context('public'):
    tenant = Client.objects.get(schema_name='cliente')
    domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
    print(f"Tenant: {tenant.nombre}, Dominio: {domain.domain}")
```

---

### PASO 2: Email de Invitación

**Contenido del Email:**
- Link de activación: `https://cliente.sintel.com/activate?token=...`
- Token firmado con TTL (24 horas)
- Instrucciones para activar cuenta

**Verificación:**
```python
# Verificar token
from apps.public.tenants.services.invitations import verify_invitation_token

token = "eyJ1c2VyX2lkIjozLCJ0ZW5hbnRfaWQiOjQ1LCJleHBpcmVzX2F0IjoiMjAyNi0wMS0zMVQxNToyNTo1My45MTQ2NDMifQ:1vlv3x:EuyjYmyb9-y3QUqbB4Eur_t4N7DSLlfZ7PVq00r5Otg"
payload = verify_invitation_token(token)
print(f"Token válido: {payload is not None}")
```

---

### PASO 3: Acceso al Link de Activación

**URL:** `http://cliente.sintel.com/activate?token=...`

**Proceso:**
1. Navegador hace request con `HTTP_HOST=cliente.sintel.com`
2. `ForceNoPortMiddleware` normaliza `HTTP_HOST` (elimina puerto si existe)
3. `TenantMainMiddleware`:
   - Busca `Domain.objects.filter(domain='cliente.sintel.com')`
   - Encuentra tenant: `Client(schema_name='cliente')`
   - Activa schema: `connection.set_schema_to('cliente')`
   - Establece `request.urlconf = settings.TENANT_URLCONF`
   - Inyecta `request.tenant = tenant`
4. Django resuelve `/activate/` en `TENANT_URLCONF`:
   - `config/urls_tenant.py` → `apps.tenant.landing.urls` → `path('activate/', ...)`
5. `ActivateOwnerView.dispatch()` valida token
6. `ActivateOwnerView.get()` renderiza formulario de activación

**Verificación:**
```python
# Simular request
from django.test import Client

client = Client(HTTP_HOST='cliente.sintel.com')
response = client.get('/activate/?token=...')
print(f"Status: {response.status_code}")
print(f"Template: {response.template_name if hasattr(response, 'template_name') else 'N/A'}")
```

**✅ Punto de Verificación 1:** El request debe usar `TENANT_URLCONF`, no `ROOT_URLCONF`.

---

### PASO 4: Envío del Formulario de Activación

**Request:** `POST http://cliente.sintel.com/activate/?token=...`

**Datos:**
- `password1`: Nueva contraseña
- `password2`: Confirmación de contraseña
- `csrfmiddlewaretoken`: Token CSRF

**Proceso:**
1. `ActivateOwnerView.form_valid()`:
   - Verifica token (ya validado en `dispatch()`)
   - Obtiene usuario: `User.objects.get(pk=payload['user_id'])`
   - Valida tenant: `request.tenant.id == payload['tenant_id']`
   - Valida membresía: `TenantMembership.objects.filter(...)`
   - Establece password: `user.set_password(password)`
   - **Loguea usuario:** `login(request, user)` ⚠️ **PUNTO CRÍTICO**
   - **Redirige:** `redirect(dashboard_url)` ⚠️ **PUNTO CRÍTICO**

**✅ Punto de Verificación 2:** Después de `login()`, el `request.urlconf` debe seguir siendo `TENANT_URLCONF`.

**❌ PROBLEMA IDENTIFICADO:** Después de `login()`, el `reverse('tenant_dashboard:index')` puede usar `ROOT_URLCONF` incorrecto.

---

### PASO 5: Redirect Después de Activación

**Antes (PROBLEMÁTICO):**
```python
return redirect(reverse('tenant_dashboard:index'))
```

**Problema:**
- `reverse()` puede ejecutarse en un contexto donde `request.urlconf` no está preservado
- Django puede usar `ROOT_URLCONF` por defecto
- El redirect puede apuntar a una ruta pública

**Después (SOLUCIONADO):**
```python
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
protocol = 'https' if settings.SECURE_SSL_REDIRECT else 'http'
dashboard_url = f"{protocol}://{domain.domain}/dashboard/"
return redirect(dashboard_url)
```

**Solución:**
- URL absoluta garantiza que el navegador haga una nueva request con `HTTP_HOST` correcto
- El middleware `TenantMainMiddleware` resuelve el tenant correctamente
- El `TENANT_URLCONF` se activa automáticamente

**✅ Punto de Verificación 3:** El redirect debe ser a `http://cliente.sintel.com/dashboard/`, NO a `http://sintel.com/console/`.

---

### PASO 6: Nueva Request al Dashboard

**URL:** `http://cliente.sintel.com/dashboard/`

**Proceso:**
1. Navegador hace nueva request con `HTTP_HOST=cliente.sintel.com`
2. `ForceNoPortMiddleware` normaliza `HTTP_HOST`
3. `TenantMainMiddleware`:
   - Busca `Domain.objects.filter(domain='cliente.sintel.com')`
   - Encuentra tenant: `Client(schema_name='cliente')`
   - Activa schema: `connection.set_schema_to('cliente')`
   - Establece `request.urlconf = settings.TENANT_URLCONF`
4. Django resuelve `/dashboard/` en `TENANT_URLCONF`:
   - `config/urls_tenant.py` → `apps.tenant.dashboard.urls` → `DashboardIndexView`
5. Vista renderiza dashboard del tenant

**✅ Punto de Verificación 4:** El dashboard debe cargar correctamente en el contexto del tenant.

---

## 🔍 Puntos de Falla Identificados

### 1. ❌ Redirect Después de `login()`

**Ubicación:** `apps/tenant/landing/views.py` (línea 307)

**Problema:** `reverse('tenant_dashboard:index')` puede usar `ROOT_URLCONF` incorrecto.

**Solución:** ✅ **IMPLEMENTADA** - Usar URL absoluta con dominio del tenant.

### 2. ⚠️ Preservación de URLConf

**Ubicación:** Después de `login()` en `ActivateOwnerView.form_valid()`

**Problema:** El `request.urlconf` puede no estar preservado después de `login()`.

**Solución:** ✅ **IMPLEMENTADA** - URL absoluta no depende del estado del request anterior.

### 3. ⚠️ Validación de Tenant

**Ubicación:** `apps/tenant/landing/views.py` (línea 278)

**Verificación:** ✅ **CORRECTO** - Se valida que `request.tenant.id == payload['tenant_id']`.

---

## 🧪 Script de Verificación

**Archivo:** `scripts/debug_tenant_routing_activation.py`

**Uso:**
```bash
docker compose exec web python scripts/debug_tenant_routing_activation.py
```

**Verifica:**
1. Creación de tenant
2. Generación de token
3. Resolución de URL `/activate/`
4. Procesamiento de formulario
5. Redirect después de activación
6. Acceso a dashboard

---

## 📊 Tabla de Verificación

| Paso | Verificación | Estado | Notas |
|------|--------------|--------|-------|
| 1. Creación tenant | Tenant y dominio creados | ✅ | Verificado |
| 2. Email invitación | Token generado y válido | ✅ | Verificado |
| 3. Acceso /activate/ | URLConf = TENANT_URLCONF | ✅ | Verificado |
| 4. Procesamiento POST | Token y membresía válidos | ✅ | Verificado |
| 5. Redirect después login | URL absoluta del tenant | ✅ | **CORREGIDO** |
| 6. Acceso /dashboard/ | URLConf = TENANT_URLCONF | ✅ | Verificado |

---

## 🎯 Conclusión

**Problema Principal:** El redirect después de la activación usaba `reverse()` que podía fallar o usar el URLConf incorrecto.

**Solución:** Usar URL absoluta con el dominio del tenant garantiza que el middleware resuelva correctamente el tenant en la nueva request.

**Estado:** ✅ **SOLUCIONADO**

---

**Fecha:** 2026-01-30  
**Versión:** v2.27
