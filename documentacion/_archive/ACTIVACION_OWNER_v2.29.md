# ✅ Activación de Owner Mejorada (v2.29)

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**

---

## 🎯 Objetivo

Mejorar el flujo de activación del owner para que:
1. **Siempre muestre el formulario** cuando el token sea válido, incluso si el usuario ya tiene contraseña usable
2. **Permita actualizar la contraseña** del owner mediante el formulario de activación
3. **Redirija con URL absoluta** al dashboard después de activación exitosa

---

## ✅ Cambios Implementados

### 1. Vista de Activación (`apps/tenant/landing/views.py`)

**Cambios en `ActivationForm`:**
- ✅ Renombrado `password` → `password1`
- ✅ Renombrado `password_confirm` → `password2`
- ✅ Mantiene validación de coincidencia

**Cambios en `ActivateOwnerView.dispatch()`:**
- ✅ **ANTES (v2.28)**: Redirigía a `/login/` si el usuario ya tenía password usable
- ✅ **AHORA (v2.29)**: Siempre muestra el formulario si el token es válido, sin importar si tiene password usable
- ✅ Eliminada validación `if user.has_usable_password(): return redirect(...)`

**Cambios en `ActivateOwnerView.form_valid()`:**
- ✅ Permite establecer/actualizar contraseña incluso si ya tiene una usable
- ✅ Mensaje de éxito diferenciado: "activada" vs "actualizada"
- ✅ Redirect absoluto al dashboard (v2.27)

**Código Clave:**
```python
def dispatch(self, request, *args, **kwargs):
    # ⚠️ v2.29: SIEMPRE muestra el formulario si el token es válido
    # NO validamos has_usable_password() aquí - permitimos actualizar contraseña
    token = request.GET.get('token')
    payload = verify_invitation_token(token)
    if not payload:
        return redirect('tenant_landing:login')
    
    # Almacenar payload y token para usar en get/post
    request._activation_payload = payload
    request._activation_token = token
    request._activation_user = user
    
    return super().dispatch(request, *args, **kwargs)

def form_valid(self, form):
    # 4. Establecer/actualizar password (v2.29: permite actualizar incluso si ya tiene una)
    password = form.cleaned_data['password1']
    user.set_password(password)
    user.save(update_fields=['password'])
    
    # 5. Loguear usuario
    login(self.request, user)
    
    # 7. Redirect absoluto al dashboard (v2.27)
    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    dashboard_url = f"{protocol}://{domain.domain}/dashboard/"
    return redirect(dashboard_url)
```

### 2. URLs (`apps/tenant/landing/urls.py`)

**Cambios:**
- ✅ Agregada ruta `activate` sin slash (evita 404 por trailing slash)
- ✅ Mantiene ruta `activate/` con slash

**Código:**
```python
urlpatterns = [
    # ⚠️ v2.29: Ambas variantes para evitar 404 por trailing slash
    path('activate', views.ActivateOwnerView.as_view(), name='activate_no_slash'),
    path('activate/', views.ActivateOwnerView.as_view(), name='activate'),
]
```

### 3. Template (`apps/tenant/landing/templates/tenant/landing/activate.html`)

**Cambios:**
- ✅ Renombrado `name="password"` → `name="password1"`
- ✅ Renombrado `name="password_confirm"` → `name="password2"`
- ✅ Actualizados IDs: `id_password` → `id_password1`, `id_password_confirm` → `id_password2`
- ✅ Actualizadas referencias a errores del formulario

### 4. Middleware Order (`config/settings.py`)

**Verificado:**
- ✅ Orden correcto: `TenantMainMiddleware` → `TenantSecurityAndURLConfMiddleware` (v2.29) → `TenantSecurityMiddleware`
- ✅ Garantiza que `/activate/` se resuelva en `TENANT_URLCONF`

### 5. Tests

**Actualizados:**
- ✅ `test_activate_owner.py`: Actualizado para usar `password1`/`password2`
- ✅ `test_activate_una_sola_vez.py`: Actualizado para reflejar nuevo comportamiento (permite actualizar password)
- ✅ `test_activation_flow_v2_29.py`: Nuevos tests para validar comportamiento v2.29

**Tests Nuevos:**
1. `test_activate_get_with_valid_token_and_usable_password`: Verifica que GET muestra formulario incluso con password usable
2. `test_activate_post_updates_password_even_if_usable`: Verifica que POST actualiza password incluso si ya tiene una
3. `test_activate_post_redirect_absolute_url`: Verifica redirect absoluto al dashboard
4. `test_activate_token_one_time_use`: Verifica comportamiento del token (actualmente reutilizable mientras sea válido)

---

## 📋 Flujo Completo (v2.29)

### 1. Usuario Recibe Email de Invitación
```
Email: https://{tenant}/activate?token=...
```

### 2. GET /activate?token=...
- ✅ Token válido → Muestra formulario (incluso si tiene password usable)
- ❌ Token inválido/expirado → Redirige a `/login/`

### 3. POST /activate?token=...
- ✅ Valida token
- ✅ Valida membresía activa
- ✅ Establece/actualiza contraseña
- ✅ Loguea usuario
- ✅ Redirige con URL absoluta: `http(s)://{domain}/dashboard/`

### 4. Usuario en Dashboard
- ✅ Autenticado
- ✅ Contraseña establecida/actualizada
- ✅ Sesión activa

---

## 🔒 Garantías de Seguridad

1. ✅ **Token válido requerido**: Solo funciona con token firmado y no expirado
2. ✅ **Validación de membresía**: Usuario debe tener membresía activa en el tenant
3. ✅ **Validación de tenant**: Token debe corresponder al tenant activo
4. ✅ **Contraseña segura**: Mínimo 8 caracteres, validación de coincidencia
5. ✅ **Redirect absoluto**: Garantiza resolución correcta del tenant en nueva request

---

## 📚 Archivos Modificados

1. ✅ `apps/tenant/landing/views.py` - Lógica de activación actualizada
2. ✅ `apps/tenant/landing/urls.py` - Ruta `activate` sin slash agregada
3. ✅ `apps/tenant/landing/templates/tenant/landing/activate.html` - Campos renombrados
4. ✅ `tests/tenant/landing/test_activate_owner.py` - Tests actualizados
5. ✅ `tests/tenant/landing/test_activate_una_sola_vez.py` - Tests actualizados
6. ✅ `tests/tenant/landing/test_activation_flow_v2_29.py` - Nuevos tests
7. ✅ `documentacion/ACTIVACION_OWNER_v2.29.md` - Documentación nueva

---

## ✅ Criterios de Aceptación (DoD)

- ✅ GET /activate con token válido y usuario con password usable → 200 & template activate.html
- ✅ POST /activate (password1/password2 válidos) → set_password + login + redirect absoluto al dashboard
- ✅ Token válido permite múltiples usos mientras no expire (actualmente no se invalida después de uso)
- ✅ Orden de middlewares validado: TenantMainMiddleware → TenantSecurityAndURLConfMiddleware → TenantSecurityMiddleware
- ✅ Suite de tests verde

---

## 🗒️ Notas de Release (v2.29)

**Activación de Owner mejorada:**
- `/activate` muestra formulario siempre con token válido
- Ya no desvía a `/login/` en usuarios con contraseña previa
- Permite actualizar contraseña mediante el mismo formulario

**Seguridad & UX:**
- Token válido mientras no expire
- Contraseña establecida/actualizada con confirmación
- Sesión autenticada y redirect absoluto al dashboard

**Compatibilidad multi-tenant:**
- Garantizada por `TenantSecurityAndURLConfMiddleware` (v2.29)
- Redirect absoluto (fix v2.27)

---

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **IMPLEMENTADO Y VERIFICADO**
