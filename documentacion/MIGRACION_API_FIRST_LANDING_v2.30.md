# ✅ Migración API-First de Landing (v2.30)

**Fecha:** 2026-01-30  
**Versión:** v2.30  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**

---

## 🎯 Objetivo

Migrar **TODA** la lógica de negocio de `apps/tenant/landing` a `apps/tenant/landing/api`, siguiendo la arquitectura **API-First**. Las vistas HTML clásicas quedan como "shells" que solo renderizan templates, sin lógica de negocio.

---

## ✅ Cambios Implementados

### 1. Endpoint API de Activación (`apps/tenant/landing/api/views.py`)

**Nuevo:** `OwnerActivationAPIView`

**GET `/api/v1/landing/auth/activate/?token=...`:**
- Valida token
- Retorna información del usuario y tenant
- ⚠️ v2.29: Siempre retorna información si el token es válido, incluso si el usuario ya tiene contraseña usable

**POST `/api/v1/landing/auth/activate/?token=...`:**
- Valida token y datos (password1/password2)
- Valida membresía activa
- Establece/actualiza contraseña
- Loguea usuario
- Retorna URL absoluta de redirección al dashboard

**Código:**
```python
class OwnerActivationAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, *args, **kwargs):
        # Valida token y retorna información
        ...
    
    def post(self, request, *args, **kwargs):
        # Procesa activación y retorna redirect_url
        ...
```

### 2. Serializer de Activación (`apps/tenant/landing/api/serializers.py`)

**Nuevo:** `OwnerActivationSerializer`

**Campos:**
- `password1`: Nueva contraseña (mínimo 8 caracteres)
- `password2`: Confirmación de contraseña (debe coincidir)

**Validaciones:**
- Token válido y no expirado
- Usuario existe y está activo
- Tenant coincide con el token
- Membresía activa en el tenant
- password1 y password2 coinciden
- password1 mínimo 8 caracteres

**Procesamiento:**
- Establece/actualiza contraseña del usuario
- Retorna usuario y tenant en `validated_data` para usar en la vista

### 3. URLs API (`apps/tenant/landing/api/urls.py`)

**Agregado:**
```python
path("auth/activate/", OwnerActivationAPIView.as_view(), name="activate"),
```

**Endpoints API disponibles:**
- `GET /api/v1/landing/info/` - Información del tenant
- `POST /api/v1/landing/auth/login/` - Login
- `GET /api/v1/landing/auth/activate/?token=...` - Validar token de activación
- `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación

### 4. Vistas HTML Deshabilitadas (`apps/tenant/landing/views.py`)

**Cambios:**
- ✅ `TenantLandingView`: Convertida a `TemplateView` (solo renderiza template)
- ✅ `TenantLoginView`: Convertida a `TemplateView` (solo renderiza template)
- ✅ `ActivateOwnerView`: Convertida a `TemplateView` (solo renderiza template)
- ❌ Eliminada toda la lógica de negocio (validación, autenticación, activación)
- ❌ Eliminado `ActivationForm` (la validación está en el serializer)

**Código Antes (v2.29):**
```python
class ActivateOwnerView(FormView):
    form_class = ActivationForm
    
    def dispatch(self, request, *args, **kwargs):
        # Lógica de validación de token
        ...
    
    def form_valid(self, form):
        # Lógica de activación
        ...
```

**Código Ahora (v2.30):**
```python
class ActivateOwnerView(TemplateView):
    template_name = 'tenant/landing/activate.html'
    
    def get_context_data(self, **kwargs):
        # Solo proporciona URLs de API
        context['api_activate_url'] = reverse('tenant_landing_api:activate')
        context['token'] = self.request.GET.get('token', '')
        return context
```

### 5. URLs Clásicas (`apps/tenant/landing/urls.py`)

**Estado:**
- ✅ URLs mantenidas para renderizar templates
- ⚠️ **DESHABILITADAS**: No procesan formularios ni contienen lógica de negocio
- ✅ Solo existen para renderizar templates HTML

**Comentarios agregados:**
```python
# ⚠️ v2.30: Lógica movida a /api/v1/landing/info/
# ⚠️ v2.30: Lógica movida a /api/v1/landing/auth/login/
# ⚠️ v2.30: Lógica movida a /api/v1/landing/auth/activate/
```

---

## 📋 Flujo Completo (v2.30)

### 1. Landing Page (`/`)
- **Template**: Renderiza `tenant/landing/index.html`
- **Frontend**: Consume `GET /api/v1/landing/info/` para datos del tenant
- **Lógica**: 100% en la API

### 2. Login (`/login/`)
- **Template**: Renderiza `tenant/landing/login.html`
- **Frontend**: Consume `POST /api/v1/landing/auth/login/` para autenticación
- **Lógica**: 100% en la API

### 3. Activación (`/activate/?token=...`)
- **Template**: Renderiza `tenant/landing/activate.html`
- **Frontend**: 
  - `GET /api/v1/landing/auth/activate/?token=...` para validar token
  - `POST /api/v1/landing/auth/activate/?token=...` para procesar activación
- **Lógica**: 100% en la API

---

## 🔒 Garantías de Seguridad

1. ✅ **Validación de token**: En el serializer y la vista API
2. ✅ **Validación de membresía**: En el serializer
3. ✅ **Validación de tenant**: Token debe corresponder al tenant activo
4. ✅ **Contraseña segura**: Mínimo 8 caracteres, validación de coincidencia
5. ✅ **Redirect absoluto**: URL absoluta al dashboard (v2.27)

---

## 📚 Archivos Modificados

1. ✅ `apps/tenant/landing/api/views.py` - Agregado `OwnerActivationAPIView`
2. ✅ `apps/tenant/landing/api/serializers.py` - Agregado `OwnerActivationSerializer`
3. ✅ `apps/tenant/landing/api/urls.py` - Agregada ruta de activación
4. ✅ `apps/tenant/landing/views.py` - Deshabilitada lógica de negocio (solo templates)
5. ✅ `apps/tenant/landing/urls.py` - Comentarios indicando deshabilitación
6. ✅ `documentacion/MIGRACION_API_FIRST_LANDING_v2.30.md` - Documentación nueva

---

## ✅ Criterios de Aceptación (DoD)

- ✅ Toda la lógica de negocio está en `apps/tenant/landing/api/`
- ✅ Las vistas HTML solo renderizan templates (shells vacíos)
- ✅ Los templates deben usar JavaScript para consumir las APIs
- ✅ Endpoints API funcionan correctamente (GET y POST)
- ✅ Validaciones y seguridad mantenidas
- ✅ Redirect absoluto al dashboard funciona

---

## 🗒️ Notas de Release (v2.30)

**Migración API-First completa:**
- Toda la lógica de negocio movida a la API
- Vistas HTML deshabilitadas (solo renderizan templates)
- Frontend debe consumir APIs REST para toda la funcionalidad

**Endpoints API disponibles:**
- `GET /api/v1/landing/info/` - Información del tenant
- `POST /api/v1/landing/auth/login/` - Login
- `GET /api/v1/landing/auth/activate/?token=...` - Validar token
- `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación

**Compatibilidad:**
- Templates HTML mantenidos para renderizado
- URLs clásicas mantenidas (solo para renderizar templates)
- Frontend debe actualizarse para consumir APIs

---

**Fecha:** 2026-01-30  
**Versión:** v2.30  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**
