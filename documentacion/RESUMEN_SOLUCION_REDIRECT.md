# ✅ Resumen: Solución al Error de Redirección a URLConf Público

## 📋 Problema Identificado

**Síntoma:** Después de la activación de un tenant privado mediante `http://cliente.sintel.com/activate?token=...`, el sistema redirigía al usuario al URLConf público (`ROOT_URLCONF`) en lugar de mantenerlo en el URLConf del tenant (`TENANT_URLCONF`).

**Causa Raíz:** El uso de `reverse('tenant_dashboard:index')` después de `login()` puede ejecutarse en un contexto donde el URLConf no está correctamente preservado, causando que Django use el `ROOT_URLCONF` por defecto.

---

## ✅ Solución Implementada

### Código Corregido

**Archivo:** `apps/tenant/landing/views.py` (líneas 307-335)

```python
# 7. Redirigir a dashboard usando URL absoluta del tenant
# ⚠️ CRÍTICO: Usar URL absoluta garantiza que el middleware resuelva el tenant correctamente
# en la nueva request. Si usamos reverse() o URL relativa, puede usar ROOT_URLCONF incorrecto.
# 
# IMPORTANTE: Después de login(), request.tenant sigue disponible porque TenantMainMiddleware
# ya lo estableció en esta request. Sin embargo, el redirect debe usar URL absoluta para
# que la nueva request también resuelva el tenant correctamente.

# Obtener dominio primario del tenant (en esquema public)
# ⚠️ CRÍTICO: Domain.objects está en SHARED_APPS, por lo que se consulta en el esquema actual
# Después de login(), el esquema sigue siendo el del tenant, pero Domain está en 'public'
# Necesitamos cambiar temporalmente al esquema public para consultar Domain
from django_tenants.utils import schema_context

with schema_context('public'):
    domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()

if not domain:
    messages.error(
        self.request,
        'Error crítico: tenant sin dominio primario. Contacta al administrador.'
    )
    return redirect('tenant_landing:login')

# Construir URL absoluta con el dominio del tenant
protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
dashboard_url = f"{protocol}://{domain.domain}/dashboard/"

# Redirect absoluto que garantiza que el middleware resuelva el tenant correctamente
# en la nueva request. El navegador hará una nueva request con HTTP_HOST=domain.domain,
# y TenantMainMiddleware resolverá el tenant automáticamente.
return redirect(dashboard_url)
```

### Cambios Clave

1. **URL Absoluta:** Usa `http://cliente.sintel.com/dashboard/` en lugar de `reverse('tenant_dashboard:index')`
2. **Consulta en Esquema Correcto:** Usa `schema_context('public')` para consultar `Domain` que está en `SHARED_APPS`
3. **Manejo de Errores:** Valida que el dominio existe antes de construir la URL
4. **Documentación:** Comentarios explicativos sobre por qué esta solución funciona

---

## 🔍 Por Qué Funciona

### Flujo Correcto

```
1. Request: http://cliente.sintel.com/activate?token=...
   → TenantMainMiddleware resuelve tenant → TENANT_URLCONF ✅

2. ActivateOwnerView.form_valid():
   → login(request, user)
   → request.tenant sigue disponible ✅

3. Consulta Domain en esquema public:
   → with schema_context('public'):
   → domain = Domain.objects.filter(tenant=tenant, is_primary=True).first() ✅

4. Redirect a URL absoluta:
   → redirect("http://cliente.sintel.com/dashboard/") ✅

5. Nueva request: http://cliente.sintel.com/dashboard/
   → HTTP_HOST = "cliente.sintel.com"
   → TenantMainMiddleware resuelve tenant → TENANT_URLCONF ✅
   → Dashboard se carga correctamente ✅
```

### Ventajas de la Solución

1. **Independiente del Estado:** No depende del estado del request anterior
2. **Garantiza Resolución:** El middleware siempre resuelve el tenant correctamente
3. **Sin Dependencias de URLConf:** No requiere que `reverse()` funcione en el contexto correcto
4. **Fácil de Debuggear:** La URL es explícita y verificable

---

## 🧪 Verificación

### Test Manual

1. **Crear tenant:**
   - Acceder a `http://sintel.com/console/tenants/`
   - Crear tenant con nombre "Test", schema "test", email "test@example.com"

2. **Activar tenant:**
   - Abrir link de activación del email: `http://test.sintel.com/activate?token=...`
   - Completar formulario de activación

3. **Verificar redirect:**
   - ✅ Debe redirigir a `http://test.sintel.com/dashboard/`
   - ❌ NO debe redirigir a `http://sintel.com/console/` o rutas públicas
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
    client = Client(HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    response = client.post(f'/activate/?token={token}', data={
        'password1': 'Test123!',
        'password2': 'Test123!',
    })
    
    # 4. Verificar redirect
    assert response.status_code == 302
    assert response['Location'] == f"http://{tenant.schema_name}.sintel.com/dashboard/"
    
    # 5. Seguir redirect y verificar URLConf
    dashboard_response = client.get('/dashboard/', HTTP_HOST=f"{tenant.schema_name}.sintel.com")
    assert dashboard_response.status_code == 200
```

---

## 📚 Documentación Relacionada

- **Informe del Error:** `documentacion/INFORME_ERROR_REDIRECT_TENANT.md`
- **Solución Detallada:** `documentacion/SOLUCION_REDIRECT_TENANT.md`
- **Debug Flujo Completo:** `documentacion/DEBUG_FLUJO_ACTIVACION_COMPLETO.md`
- **Enrutamiento Hostname:** `documentacion/ENRUTAMIENTO_HOSTNAME_ESTABLE.md`

---

## ✅ Estado Final

- ✅ **Problema identificado**
- ✅ **Solución implementada**
- ✅ **Código optimizado** (consulta en esquema correcto)
- ✅ **Documentación completa**
- ⏳ **Pendiente: Pruebas en producción**

---

**Fecha:** 2026-01-30  
**Versión:** v2.27  
**Estado:** ✅ **SOLUCIONADO Y OPTIMIZADO**
