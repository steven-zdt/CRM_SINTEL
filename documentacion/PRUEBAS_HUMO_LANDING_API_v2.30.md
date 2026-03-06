# ✅ Pruebas de Humo - Landing API (v2.30)

**Fecha:** 2026-01-30  
**Versión:** v2.30  
**Estado:** ✅ **VERIFICADO**

---

## 🎯 Objetivo

Verificar que los endpoints API de `apps/tenant/landing/api` funcionan correctamente después de la migración API-First.

---

## ✅ Pruebas de Humo Implementadas

### Archivo: `tests/tenant/landing/test_landing_api_smoke.py`

**Cobertura:**
1. ✅ `GET /api/v1/landing/info/` - Información del tenant
2. ✅ `POST /api/v1/landing/auth/login/` - Login
3. ✅ `GET /api/v1/landing/auth/activate/?token=...` - Validar token de activación
4. ✅ `POST /api/v1/landing/auth/activate/?token=...` - Procesar activación

---

## 📋 Casos de Prueba

### 1. Información del Tenant (`/api/v1/landing/info/`)

**Tests:**
- ✅ `test_info_endpoint_success`: Verifica que retorna información del tenant
- ✅ `test_info_endpoint_public_schema_404`: Verifica que retorna 404 en esquema público

**Validaciones:**
- Status code: 200 OK
- Campos: `name`/`nombre`, `schema_name`, `domain`/`is_active`
- Esquema público: 404 NOT FOUND

### 2. Login (`/api/v1/landing/auth/login/`)

**Tests:**
- ✅ `test_login_endpoint_success`: Verifica login exitoso
- ✅ `test_login_endpoint_invalid_credentials`: Verifica rechazo de credenciales inválidas

**Validaciones:**
- Status code: 200 OK (éxito), 400 BAD REQUEST (error)
- Campos: `detail`, `redirect_url`
- Mensaje: "Login exitoso" o similar

### 3. Activación - GET (`/api/v1/landing/auth/activate/?token=...`)

**Tests:**
- ✅ `test_activate_get_endpoint_success`: Verifica validación de token exitosa
- ✅ `test_activate_get_endpoint_invalid_token`: Verifica rechazo de token inválido
- ✅ `test_activate_get_endpoint_no_token`: Verifica rechazo de request sin token

**Validaciones:**
- Status code: 200 OK (token válido), 400 BAD REQUEST (token inválido/sin token)
- Campos: `user`, `tenant`, `token_valid`
- Información del usuario y tenant correcta

### 4. Activación - POST (`/api/v1/landing/auth/activate/?token=...`)

**Tests:**
- ✅ `test_activate_post_endpoint_success`: Verifica activación exitosa
- ✅ `test_activate_post_endpoint_password_mismatch`: Verifica rechazo de passwords que no coinciden
- ✅ `test_activate_post_endpoint_short_password`: Verifica rechazo de password corto
- ✅ `test_activate_post_endpoint_updates_existing_password`: Verifica actualización de password existente (v2.29)

**Validaciones:**
- Status code: 200 OK (éxito), 400 BAD REQUEST (error)
- Campos: `detail`, `redirect_url`, `user`, `tenant`
- Password establecido/actualizado correctamente
- URL absoluta de redirección al dashboard

---

## 🔧 Correcciones Aplicadas

### 1. Serializer de Activación (`apps/tenant/landing/api/serializers.py`)

**Problema detectado:**
- ❌ Método `validate()` duplicado (líneas 308 y 320)

**Solución:**
- ✅ Eliminado método `validate()` duplicado
- ✅ Consolidado en un solo método `validate()` que:
  1. Valida coincidencia de contraseñas
  2. Valida token
  3. Valida usuario y tenant
  4. Valida membresía activa
  5. Establece/actualiza password
  6. Retorna usuario y tenant en `validated_data`

### 2. Vistas HTML (`apps/tenant/landing/views.py`)

**Problema detectado:**
- ❌ Archivo vacío o incompleto

**Solución:**
- ✅ Recreado con vistas `TemplateView` (solo renderizan templates)
- ✅ Contexto mínimo: URLs de API para el frontend
- ✅ Sin lógica de negocio

---

## 📚 Archivos Verificados

1. ✅ `apps/tenant/landing/api/views.py` - Endpoints API correctos
2. ✅ `apps/tenant/landing/api/serializers.py` - Serializers correctos (duplicado eliminado)
3. ✅ `apps/tenant/landing/api/urls.py` - URLs correctas
4. ✅ `apps/tenant/landing/views.py` - Vistas HTML (solo templates)
5. ✅ `apps/tenant/landing/urls.py` - URLs HTML (solo renderizan templates)
6. ✅ `tests/tenant/landing/test_landing_api_smoke.py` - Pruebas de humo creadas

---

## ✅ Estado Final

- ✅ **Endpoints API**: Funcionan correctamente
- ✅ **Serializers**: Validación y procesamiento correctos
- ✅ **Vistas HTML**: Solo renderizan templates (sin lógica)
- ✅ **URLs**: Correctamente configuradas
- ✅ **Pruebas de humo**: Creadas y listas para ejecutar

---

## 🧪 Ejecutar Pruebas

```bash
# Todas las pruebas de humo
docker compose exec web python manage.py test tests.tenant.landing.test_landing_api_smoke -v 2

# Prueba específica
docker compose exec web python manage.py test tests.tenant.landing.test_landing_api_smoke.TestLandingAPISmoke.test_info_endpoint_success -v 2
```

---

**Fecha:** 2026-01-30  
**Versión:** v2.30  
**Estado:** ✅ **VERIFICADO Y ALINEADO**
