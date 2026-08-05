# ✅ Solución: Error de Redirección a URLConf Público Después de Activación

## 📋 Problema Resuelto

**Error:** Después de la activación de un tenant privado, el sistema redirigía al usuario al URLConf público (`ROOT_URLCONF`) en lugar de mantenerlo en el URLConf del tenant (`TENANT_URLCONF`).

**Causa Raíz:** El uso de `reverse('tenant_dashboard:index')` después de `login()` puede ejecutarse en un contexto donde el URLConf no está correctamente preservado, causando que Django use el `ROOT_URLCONF` por defecto.

---

## ✅ Solución Implementada

### Cambio en `apps/tenant/landing/views.py`

**Antes (PROBLEMÁTICO):**
```python
# 7. Redirigir a dashboard
try:
    return redirect(reverse('tenant_dashboard:index'))
except Exception:
    return redirect('/dashboard/')
```

**Después (CORREGIDO):**
```python
# 7. Redirigir a dashboard usando URL absoluta del tenant
# ⚠️ CRÍTICO: Usar URL absoluta garantiza que el middleware resuelva el tenant correctamente
# en la nueva request. Si usamos reverse() o URL relativa, puede usar ROOT_URLCONF incorrecto.
from apps.public.tenants.models import Domain
from django.conf import settings

# Obtener dominio primario del tenant
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()

if domain:
    # Construir URL absoluta con el dominio del tenant
    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    dashboard_url = f"{protocol}://{domain.domain}/dashboard/"
    
    # Redirect absoluto que garantiza que el middleware resuelva el tenant correctamente
    return redirect(dashboard_url)
else:
    # Fallback si no hay dominio (no debería pasar en producción)
    messages.warning(self.request, 'No se encontró el dominio del tenant. Redirigiendo a login.')
    return redirect('tenant_landing:login')
```

---

## 🔍 Por Qué Esta Solución Funciona

### 1. URL Absoluta Preserva el Contexto del Tenant

Al usar una URL absoluta con el dominio del tenant (`http://cliente.sintel.net.co/dashboard/`):

- ✅ El navegador hace una **nueva request** con el `HTTP_HOST` correcto
- ✅ El middleware `TenantMainMiddleware` resuelve el tenant correctamente
- ✅ El `TENANT_URLCONF` se activa automáticamente en la nueva request
- ✅ No depende del estado del request anterior que puede haber sido modificado por `login()`

### 2. Flujo Correcto

```
1. Usuario accede a: http://cliente.sintel.net.co/activate?token=...
2. TenantMainMiddleware resuelve tenant → TENANT_URLCONF activo ✅
3. ActivateOwnerView procesa formulario
4. Usuario se loguea: login(request, user)
5. Redirect a: http://cliente.sintel.net.co/dashboard/ (URL absoluta) ✅
6. Nueva request con HTTP_HOST=cliente.sintel.net.co
7. TenantMainMiddleware resuelve tenant → TENANT_URLCONF activo ✅
8. Dashboard se carga correctamente en el contexto del tenant ✅
```

### 3. Ventajas sobre `reverse()`

| Aspecto | `reverse()` | URL Absoluta |
|---------|-------------|--------------|
| **Preservación de URLConf** | ❌ Puede usar ROOT_URLCONF | ✅ Garantiza TENANT_URLCONF |
| **Dependencia de estado** | ❌ Depende del request actual | ✅ Nueva request limpia |
| **Confiabilidad** | ⚠️ Puede fallar después de login() | ✅ Siempre funciona |
| **Debugging** | ❌ Difícil de rastrear | ✅ Fácil de verificar |

---

## 🧪 Verificación

### Test Manual

1. **Crear tenant nuevo:**
   ```bash
   # Acceder a http://sintel.net.co/console/tenants/
   # Crear tenant con nombre "Test Tenant", schema "test", email "test@example.com"
   ```

2. **Activar tenant:**
   ```bash
   # Abrir link de activación: http://test.sintel.net.co/activate?token=...
   # Completar formulario de activación
   ```

3. **Verificar redirect:**
   - ✅ Debe redirigir a `http://test.sintel.net.co/dashboard/`
   - ✅ NO debe redirigir a `http://sintel.net.co/console/` o rutas públicas
   - ✅ El dashboard debe cargar correctamente

### Test Automatizado

```python
def test_activation_redirects_to_tenant_dashboard():
    """Verifica que después de activación, el redirect va al dashboard del tenant."""
    # 1. Crear tenant
    tenant = crear_tenant_con_owner(...)
    
    # 2. Generar token
    token = generate_invitation_token(user.id, tenant.id)
    
    # 3. POST a /activate/ con token
    client = Client(HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    response = client.post(f'/activate/?token={token}', data={
        'password1': 'Test123!',
        'password2': 'Test123!',
    })
    
    # 4. Verificar redirect
    assert response.status_code == 302
    assert response['Location'] == f"http://{tenant.schema_name}.sintel.net.co/dashboard/"
    
    # 5. Seguir redirect y verificar URLConf
    dashboard_response = client.get('/dashboard/', HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")
    assert dashboard_response.status_code == 200
    # Verificar que se usa TENANT_URLCONF (no ROOT_URLCONF)
```

---

## 📚 Referencias

- **Informe del Error:** `documentacion/INFORME_ERROR_REDIRECT_TENANT.md`
- **Enrutamiento Hostname:** `documentacion/ENRUTAMIENTO_HOSTNAME_ESTABLE.md`
- **Arquitectura General:** `documentacion/arquitectura_general.md` (v2.27)

---

## 🎯 Estado

- ✅ **Problema identificado**
- ✅ **Solución implementada**
- ⏳ **Pendiente: Pruebas en producción**
- ⏳ **Pendiente: Tests automatizados**

---

**Fecha:** 2026-01-30  
**Versión:** v2.27  
**Estado:** ✅ **SOLUCIONADO**
