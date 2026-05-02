# Core Auth Implementation - v2.61

**Fecha:** 2024-12-19  
**Estado:** ✅ Implementado  
**Versión:** 2.61

---

## 📋 Resumen

Implementación del `CoreAuthViewSet` en Core API para centralizar la autenticación de usuarios en tenants privados.

### Problema Resuelto

- **Error anterior:** `POST /api/v1/core/auth/login/` retornaba 404 (endpoint no existía)
- **Solución:** Implementación completa de `CoreAuthViewSet` con acciones `login` y `logout`
- **Resultado:** Endpoint funcional que retorna JSON válido en lugar de HTML 404

---

## 🏗️ Arquitectura

### Ubicación

- **ViewSet:** `apps/tenant/core/api/viewsets.py` - `CoreAuthViewSet`
- **URLs:** `apps/tenant/core/api/urls.py` - Registrado en router
- **Endpoint base:** `/api/v1/core/auth/`

### Endpoints Implementados

| Endpoint | Método | Acción | Estado |
|----------|--------|--------|--------|
| `/api/v1/core/auth/login/` | POST | `CoreAuthViewSet.login` | ✅ Implementado |
| `/api/v1/core/auth/logout/` | POST | `CoreAuthViewSet.logout` | ✅ Implementado |

---

## 📝 Especificación de Endpoints

### POST /api/v1/core/auth/login/

**Descripción:** Autentica un usuario en el tenant actual.

**Autenticación:** No requerida (AllowAny)

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña"
}
```

**Response 200 OK:**
```json
{
  "success": true,
  "redirect_url": "/dashboard/",
  "user": {
    "id": 1,
    "email": "usuario@ejemplo.com",
    "first_name": "Nombre",
    "last_name": "Apellido"
  }
}
```

**Response 400 Bad Request:**
```json
{
  "detail": "Email y contraseña son requeridos."
}
```

**Response 401 Unauthorized:**
```json
{
  "detail": "Credenciales inválidas."
}
```

**Response 403 Forbidden:**
```json
{
  "detail": "No tienes acceso a este tenant. Por favor, contacta al administrador."
}
```

**Validaciones:**
1. ✅ Email y contraseña requeridos
2. ✅ Autenticación con email o username
3. ✅ Usuario activo (`is_active=True`)
4. ✅ TenantMembership activa en el tenant actual
5. ✅ Login de sesión (SessionAuthentication)

**Logging:**
- ✅ Logs de éxito (info)
- ✅ Logs de credenciales inválidas (warning)
- ✅ Logs de usuarios inactivos (warning)
- ✅ Logs de membresía faltante (warning)
- ✅ Logs de errores inesperados (error)

---

### POST /api/v1/core/auth/logout/

**Descripción:** Cierra la sesión del usuario actual.

**Autenticación:** No requerida (AllowAny)

**Request Body:** Vacío

**Response 200 OK:**
```json
{
  "success": true,
  "message": "Sesión cerrada correctamente."
}
```

**Response 500 Internal Server Error:**
```json
{
  "detail": "Error interno al procesar el logout."
}
```

**Validaciones:**
- ✅ Cierre de sesión seguro con `logout(request)`
- ✅ Manejo de errores robusto

**Logging:**
- ✅ Logs de éxito (info)
- ✅ Logs de errores inesperados (error)

---

## 🔧 Implementación Técnica

### Manejo de Esquemas

El ViewSet maneja correctamente el cambio entre esquemas:

```python
# Autenticación busca en esquema public
current_schema = connection.schema_name
try:
    connection.set_schema_to_public()
    # Buscar usuario o membresía
finally:
    connection.set_schema(current_schema)
```

### Validación de TenantMembership

```python
# Verificar membresía activa en tenant actual
membership = TenantMembership.objects.filter(
    client=tenant,
    user=user,
    is_active=True,
).first()
```

### Autenticación Flexible

Soporta autenticación con:
- Email directo (si `USERNAME_FIELD = 'email'`)
- Username (buscando usuario por email primero)

---

## 🔄 Compatibilidad

### Frontend

El frontend puede usar Core API directamente:

```javascript
const response = await fetch('/api/v1/core/auth/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrftoken,
  },
  credentials: 'same-origin',
  body: JSON.stringify({ email, password })
});
```

### Landing API (Alternativa)

Landing API sigue disponible como alternativa:
- `/api/v1/landing/auth/login/` - Funciona (compatibilidad)
- `/api/v1/core/auth/login/` - Recomendado (centralizado)

---

## 📊 Comparación con Landing API

| Característica | Landing API | Core API |
|----------------|-------------|----------|
| Endpoint | `/api/v1/landing/auth/login/` | `/api/v1/core/auth/login/` |
| ViewSet | `LandingViewSet` (no implementado) | `CoreAuthViewSet` ✅ |
| Serializer | `TenantLoginSerializer` | Lógica en ViewSet |
| Validación | ✅ | ✅ |
| TenantMembership | ✅ | ✅ |
| SessionAuth | ✅ | ✅ |
| Logging | ⚠️ Básico | ✅ Completo |
| Estado | ⚠️ Alternativa | ✅ Centralizado |

---

## ✅ Checklist de Validación

- [x] ViewSet implementado en `apps/tenant/core/api/viewsets.py`
- [x] ViewSet registrado en `apps/tenant/core/api/urls.py`
- [x] Endpoint `/api/v1/core/auth/login/` funcional
- [x] Endpoint `/api/v1/core/auth/logout/` funcional
- [x] Validación de credenciales
- [x] Validación de TenantMembership
- [x] Manejo de esquemas (public/tenant)
- [x] Logging completo
- [x] Manejo de errores robusto
- [x] Respuestas JSON estructuradas
- [ ] Tests unitarios (pendiente)
- [ ] Tests de integración (pendiente)

---

## 🎯 Próximos Pasos

1. **Tests:** Agregar tests unitarios y de integración
2. **Password Reset:** Implementar endpoints de password-reset si se requiere
3. **Documentación API:** Actualizar Swagger/OpenAPI schema
4. **Migración Frontend:** Actualizar frontend para usar Core API (opcional)

---

## 📚 Referencias

- `documentacion/PLAN_URLS_TENANTS_PRIVADOS.md` - Plan de implementación
- `documentacion/urls_mapping.md` - Mapeo de URLs
- `apps/tenant/core/api/viewsets.py` - Implementación
- `apps/tenant/core/api/urls.py` - Registro de URLs
- `apps/tenant/landing/api/serializers.py` - Lógica de referencia

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.0
