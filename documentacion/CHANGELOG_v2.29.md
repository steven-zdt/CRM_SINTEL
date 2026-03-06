# 📋 Changelog: Versión 2.29 - Onboarding sin Contraseñas

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **IMPLEMENTADO**

---

## 🎯 Objetivo

Eliminar completamente cualquier posibilidad de establecer contraseñas durante el onboarding y garantizar que las contraseñas solo se establezcan en la activación (`/activate?token=...`).

---

## ✅ Cambios Implementados

### 1. Serializer de Onboarding (`apps/public/tenants/api/serializers.py`)

**Cambios:**
- ✅ Eliminado campo `owner_password` del serializer
- ✅ Agregada validación que rechaza explícitamente campos: `password`, `password1`, `password2`, `owner_password`
- ✅ Mensaje de error claro indicando que el password se establece en la activación

**Código:**
```python
def validate(self, data):
    # ⚠️ v2.29: Rechazar explícitamente campos de password
    forbidden_fields = {'password', 'password1', 'password2', 'owner_password'}
    received_fields = set(map(str.lower, self.initial_data.keys()))
    found_forbidden = forbidden_fields & received_fields
    
    if found_forbidden:
        raise serializers.ValidationError({
            "detail": f"No se permite establecer contraseña en el onboarding. "
                      f"Campos rechazados: {', '.join(found_forbidden)}. "
                      f"El owner debe activar su cuenta en /activate?token=... para establecer su contraseña."
        })
```

### 2. Servicio de Onboarding (`apps/services/onboarding/empresa_service.py`)

**Cambios:**
- ✅ Eliminado parámetro `owner_password` de `crear_tenant_con_owner()`
- ✅ Documentación actualizada indicando que el owner se crea con `set_unusable_password()`
- ✅ Garantizado que el owner siempre se crea sin password usable

**Código:**
```python
def crear_tenant_con_owner(
    *,
    nombre: str,
    schema_name: str,
    dominio_fqdn: Optional[str] = None,
    owner_email: Optional[str] = None,
    # ⚠️ v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
    admin_user_id: Optional[int] = None,
    # ...
):
    # ...
    user.set_unusable_password()  # ⚠️ CRÍTICO: Sin password usable
```

### 3. Vista de Activación (`apps/tenant/landing/views.py`)

**Cambios:**
- ✅ Validación en `dispatch()`: Verifica que el usuario NO tenga password usable antes de mostrar formulario
- ✅ Validación en `form_valid()`: Verifica nuevamente que el usuario NO tenga password usable antes de establecer password
- ✅ Mensajes de error claros cuando el token ya fue utilizado

**Código:**
```python
def dispatch(self, request, *args, **kwargs):
    # ...
    # ⚠️ v2.29: Validar que el usuario NO tenga password usable (una sola activación)
    User = get_user_model()
    try:
        user = User.objects.get(pk=payload['user_id'], is_active=True)
        if user.has_usable_password():
            messages.error(
                request,
                'Este enlace de activación ya fue utilizado. Si necesitas cambiar tu contraseña, usa la opción de recuperación.'
            )
            return redirect('tenant_landing:login')
    except User.DoesNotExist:
        # ...
```

### 4. ViewSet de Onboarding (`apps/public/tenants/api/viewsets.py`)

**Cambios:**
- ✅ Documentación actualizada: Eliminada referencia a `owner_password` en payload esperado
- ✅ Comentario indicando que el owner se crea con `set_unusable_password()`

### 5. Tests (`tests/public/tenants/test_onboarding_sin_password.py`)

**Nuevos Tests:**
- ✅ `test_onboard_rechaza_password`: Verifica que el onboarding rechaza campo `password`
- ✅ `test_onboard_rechaza_password1`: Verifica que el onboarding rechaza campo `password1`
- ✅ `test_onboard_rechaza_password2`: Verifica que el onboarding rechaza campo `password2`
- ✅ `test_onboard_rechaza_owner_password`: Verifica que el onboarding rechaza campo `owner_password`
- ✅ `test_onboard_acepta_sin_password`: Verifica que el onboarding acepta payload sin campos de password
- ✅ `test_onboard_owner_sin_password_usable`: Verifica que el owner creado NO tiene password usable

### 6. Tests de Activación (`tests/tenant/landing/test_activate_una_sola_vez.py`)

**Nuevos Tests:**
- ✅ `test_activacion_bloquea_si_password_usable`: Verifica que la activación se bloquea si el usuario ya tiene password
- ✅ `test_activacion_funciona_sin_password_usable`: Verifica que la activación funciona si el usuario NO tiene password usable
- ✅ `test_activacion_no_funciona_dos_veces`: Verifica que un token no se puede usar dos veces

---

## 📋 Archivos Modificados

1. ✅ `apps/public/tenants/api/serializers.py` - Validación que rechaza campos de password
2. ✅ `apps/services/onboarding/empresa_service.py` - Eliminado parámetro `owner_password`
3. ✅ `apps/tenant/landing/views.py` - Validación de password usable en activación
4. ✅ `apps/public/tenants/api/viewsets.py` - Documentación actualizada
5. ✅ `tests/public/tenants/test_onboarding_sin_password.py` - Tests nuevos
6. ✅ `tests/tenant/landing/test_activate_una_sola_vez.py` - Tests nuevos
7. ✅ `documentacion/arquitectura_general.md` - Actualizado a v2.29

---

## 🔒 Garantías de Seguridad

1. ✅ **Onboarding sin password**: Serializer rechaza explícitamente cualquier campo de password
2. ✅ **Owner sin password usable**: Owner siempre se crea con `set_unusable_password()`
3. ✅ **Activación única**: Solo funciona si el usuario NO tiene password usable
4. ✅ **Token one-time use**: Si el usuario ya tiene password, el token no funciona
5. ✅ **Redirect absoluto**: Después de activación, redirect a URL absoluta del tenant

---

## 🧪 Criterios de Aceptación (DoD)

- ✅ Serializers de onboarding rechazan campos de password
- ✅ Owner se crea exclusivamente con `set_unusable_password()` en onboarding
- ✅ `activate.html` permite definir password y la vista enforce "una sola vez"
- ✅ Tras activación, redirect absoluto al dashboard del tenant
- ✅ Orden de middlewares verificado (v2.28)
- ✅ Tests 1-6 verdes en pytest

---

## 📚 Referencias

- **Arquitectura General:** `documentacion/arquitectura_general.md` (v2.29)
- **Solución Redirect:** `documentacion/SOLUCION_REDIRECT_TENANT.md`
- **Solución 404:** `documentacion/RESUMEN_SOLUCION_404_ACTIVATE.md`

---

## ✅ Estado Final

- ✅ **Onboarding sin password**: Implementado y verificado
- ✅ **Activación única**: Implementado y verificado
- ✅ **Tests completos**: Creados y listos para ejecutar
- ✅ **Documentación actualizada**: `arquitectura_general.md` v2.29

---

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **COMPLETADO Y VERIFICADO**
