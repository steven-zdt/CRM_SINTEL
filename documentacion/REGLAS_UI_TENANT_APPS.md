# 📐 Reglas de UI para Tenant Apps (v2.30+)

**Versión:** 1.0  
**Fecha:** 2026-02-03  
**Estado:** ✅ Regla Establecida  
**Aplicable a:** Todas las apps en `TENANT_APPS`

---

## 🎯 Objetivo

Establecer un estándar uniforme para todas las páginas de UI en `TENANT_APPS`, garantizando:
- **Consistencia visual**: Todas las páginas comparten navbar/footer
- **API-First estricto**: Sin renderizado server-side de datos
- **Mantenibilidad**: Estructura predecible y fácil de auditar
- **Experiencia de usuario**: Navegación coherente entre módulos

---

## 📋 Regla General: Template + API-First

### ✅ REQUISITO OBLIGATORIO

**TODAS las páginas de UI en `TENANT_APPS` DEBEN:**

1. **Extender `tenant/base.html`** (navbar/footer automático)
2. **Usar `TemplateView` con `LoginRequiredMixin`** (sin lógica de negocio)
3. **Obtener datos exclusivamente vía JavaScript** desde APIs REST
4. **Registrar ruta en `config/urls_tenant.py`** con nombre descriptivo
5. **Incluir tests de humo** que verifiquen renderizado y consumo de APIs

---

## 🏗️ Estructura Estándar

### 1. Template (`apps/tenant/{app}/templates/tenant/{app}/page.html`)

```django
{% extends 'tenant/base.html' %}
{% load static %}
{% load tenant_branding %}

{% block title %}Título de la Página - {% tenant_branding_name %}{% endblock %}

{% block extra_head %}
<style>
    /* Estilos específicos de la página */
</style>
{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-md p-8">
        <h1 class="text-2xl font-bold mb-6">Título de la Página</h1>
        
        <!-- Contenido de la página -->
        <!-- ⚠️ IMPORTANTE: NO renderizar datos server-side -->
        <!-- Todos los datos se obtienen vía JavaScript desde APIs -->
        
        <div id="loading" class="loading">Cargando datos...</div>
        <div id="error" class="error" style="display: none;"></div>
        <div id="success" class="success" style="display: none;"></div>
        
        <form id="main-form" style="display: none;">
            <!-- Formulario -->
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // ⚠️ API-First: Todos los datos se obtienen desde APIs REST
    // Ejemplo:
    // - GET /api/v1/{app}/... → Cargar datos
    // - POST/PATCH /api/v1/{app}/... → Guardar datos
    
    async function loadData() {
        try {
            const data = await httpRequest('/api/v1/{app}/...');
            // Poblar formulario con datos
        } catch (error) {
            // Manejar errores
        }
    }
    
    // Inicializar
    loadData();
</script>
{% endblock %}
```

### 2. Vista (`apps/tenant/{app}/views.py`)

```python
"""
Vistas para la app {app} (UI container, API-First).

⚠️ IMPORTANTE: 
- Estas vistas son contenedores de UI que extienden tenant/base.html
- Toda la lógica de datos se obtiene vía APIs REST (API-First)
- No hay lógica de negocio aquí; solo renderizan templates
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class {App}PageView(LoginRequiredMixin, TemplateView):
    """
    Vista para la página de {app} (API-First).
    
    ⚠️ API-First: Esta vista solo renderiza el template.
    Todos los datos se obtienen vía JavaScript desde:
    - GET /api/v1/{app}/...
    - POST/PATCH /api/v1/{app}/...
    
    Endpoint: GET /{app}/
    """
    template_name = 'tenant/{app}/page.html'
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo para el template.
        
        ⚠️ API-First: No se pasan datos de negocio aquí.
        El template obtiene todos los datos vía JavaScript desde las APIs.
        """
        context = super().get_context_data(**kwargs)
        # El template obtiene datos vía JavaScript, no desde el contexto
        return context
```

### 3. URL (`config/urls_tenant.py`)

```python
from apps.tenant.{app} import views as {app}_views

urlpatterns = [
    # ... otras rutas ...
    
    # ⚠️ v2.30: Página de {app} (template que extiende tenant/base.html, API-First)
    # ⚠️ REGLA: Template en apps/tenant/{app}/templates/tenant/{app}/page.html
    # Consume /api/v1/{app}/... para obtener datos (API-First)
    path('{app}/', {app}_views.{App}PageView.as_view(), name='tenant-{app}-page'),
]
```

### 4. Tests (`tests/tenant/{app}/test_{app}_page_smoke.py`)

```python
"""
Pruebas de humo para la página de {app} (template que extiende tenant/base.html).

⚠️ POLÍTICA API-First: El template no renderiza datos server-side;
todos los datos se obtienen vía JavaScript desde las APIs REST.
"""
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.tenant.core.tests import SintelTenantTestCase
from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership

User = get_user_model()


class {App}PageSmokeTestCase(SintelTenantTestCase):
    """Pruebas de humo para la página de {app}."""

    def setUp(self):
        """Configurar datos de prueba."""
        super().setUp()
        # ... setup ...

    def test_{app}_page_requires_login(self):
        """Verifica que la página requiere autenticación."""
        url = reverse('tenant-{app}-page')
        response = self.client.get(url, HTTP_HOST='test-tenant.sintel.com')
        self.assertIn(response.status_code, [302, 401])

    def test_{app}_page_renders_template(self):
        """Verifica que la página renderiza el template correcto."""
        self.client.force_login(self.user)
        url = reverse('tenant-{app}-page')
        response = self.client.get(url, HTTP_HOST='test-tenant.sintel.com')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenant/{app}/page.html')
        # Verificar marcadores del formulario
        self.assertContains(response, 'main-form')
```

---

## ✅ Checklist de Cumplimiento

Para cada app en `TENANT_APPS` que tenga una página de UI:

- [ ] **Template existe** en `apps/tenant/{app}/templates/tenant/{app}/page.html`
- [ ] **Template extiende** `{% extends 'tenant/base.html' %}`
- [ ] **Vista existe** en `apps/tenant/{app}/views.py` con `TemplateView + LoginRequiredMixin`
- [ ] **Ruta registrada** en `config/urls_tenant.py` con nombre `tenant-{app}-page`
- [ ] **JavaScript consume APIs** (no hay datos renderizados server-side)
- [ ] **Tests de humo** existen en `tests/tenant/{app}/test_{app}_page_smoke.py`
- [ ] **No hay lógica de negocio** en la vista (solo renderiza template)
- [ ] **CSRF token** manejado correctamente en JavaScript para POST/PATCH

---

## 🚫 Prohibiciones

### ❌ NO HACER

1. **NO renderizar datos server-side** en templates (excepto branding dinámico)
2. **NO poner lógica de negocio** en vistas de UI (usar APIs)
3. **NO crear shells estáticos** para páginas principales (usar templates)
4. **NO duplicar navbar/footer** (siempre extender `tenant/base.html`)
5. **NO usar vistas de función** para páginas principales (usar `TemplateView`)

### ✅ EXCEPCIONES

- **Shells estáticos** están permitidos para:
  - Landing page (`/static/tenant/landing/index.html`)
  - Páginas de activación/reset password (temporal, sin navbar)
- **Vistas de función** están permitidas para:
  - Redirecciones simples
  - Endpoints auxiliares

---

## 🔍 Auditoría

### Script de Verificación

Ejecutar el script de auditoría para verificar cumplimiento:

```bash
python scripts/audit_tenant_ui_compliance.py
```

El script verifica:
- ✅ Existencia de templates en estructura correcta
- ✅ Templates extienden `tenant/base.html`
- ✅ Vistas usan `TemplateView + LoginRequiredMixin`
- ✅ Rutas registradas en `urls_tenant.py`
- ✅ Tests de humo existen
- ✅ JavaScript consume APIs (no hay datos server-side)

---

## 📚 Ejemplos de Referencia

### ✅ Implementación Correcta

**App:** `apps/tenant/empresa`
- ✅ Template: `apps/tenant/empresa/templates/tenant/empresa/page.html`
- ✅ Vista: `EmpresaPageView(LoginRequiredMixin, TemplateView)`
- ✅ Ruta: `path('empresa/', empresa_views.EmpresaPageView.as_view(), name='tenant-empresa-page')`
- ✅ Tests: `tests/tenant/empresa/test_empresa_page_smoke.py`
- ✅ JavaScript: Consume `/api/v1/empresas/mi-empresa/`, `/api/v1/empresa/form-metadata/`, etc.

---

## 🔄 Migración de Apps Existentes

Para migrar una app existente a este estándar:

1. **Crear template** que extienda `tenant/base.html`
2. **Mover lógica de datos** a JavaScript (consumir APIs)
3. **Crear vista** `TemplateView` simple
4. **Registrar ruta** en `urls_tenant.py`
5. **Crear tests** de humo
6. **Eliminar** vistas antiguas y shells estáticos obsoletos

---

## 📝 Notas de Implementación

### JavaScript Helper Functions

Para facilitar el consumo de APIs, usar funciones helper estándar:

```javascript
// Obtener CSRF token desde cookie
function getCSRFToken() {
    return getCookie('csrftoken') || '';
}

// Cliente HTTP simple con CSRF
async function httpRequest(url, options = {}) {
    const defaultOptions = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
    };
    const mergedOptions = { ...defaultOptions, ...options, headers: { ...defaultOptions.headers, ...(options.headers || {}) } };
    const response = await fetch(url, mergedOptions);
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
    }
    return response.json();
}
```

---

## 🎯 Beneficios

1. **Consistencia**: Todas las páginas se ven y se comportan igual
2. **Mantenibilidad**: Estructura predecible facilita cambios
3. **Performance**: Sin renderizado server-side innecesario
4. **Escalabilidad**: APIs pueden ser consumidas por otros clientes
5. **Testing**: Tests de humo garantizan funcionamiento básico

---

**Última Actualización:** 2026-02-03  
**Mantenedor:** Equipo de Desarrollo SINTEL
