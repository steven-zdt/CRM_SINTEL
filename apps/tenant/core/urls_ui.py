"""
URLs UI para el workspace compositor (core).

⚠️ v2.40: Sistema de Workspace Compositor.
Se incluye en config/urls_tenant.py con path('', include('apps.tenant.core.urls_ui')).

⚠️ API-First: Estas rutas solo sirven HTML estructural.
Los datos se cargan vía JavaScript desde las APIs JSON.

⚠️ REGLA DE NEGOCIO (v2.40): 
- Solo rutas UI (HTML/views), no APIs.
- Las APIs se registran en config/api_urls.py bajo /api/v1/.
- El workspace es la interfaz principal del tenant autenticado.

⚠️ ARQUITECTURA:
- El workspace renderiza tenant/core/workspace.html con todos los módulos integrados.
- Cada módulo carga datos vía JavaScript desde /api/v1/{modulo}/.
- Lazy loading con DOMUtils.onVisibleOnce para optimizar carga inicial.
"""
from django.urls import path
from apps.tenant.core import views_ui

# ⚠️ UI Routes (partials HTML sin datos, API-First)
# Workspace compositor
# ⚠️ CRÍTICO: Se incluye en config/urls_tenant.py con path('', include(...))
# La ruta 'workspace/' definida aquí genera la URL final: /workspace/
app_name = 'core_ui'

urlpatterns = [
    # Workspace compositor (vista principal del tenant autenticado)
    # ⚠️ v2.40: Endpoint: GET /workspace/
    # Renderiza tenant/core/workspace.html con todos los módulos integrados
    # Los módulos cargan datos vía JavaScript desde /api/v1/{modulo}/
    # ⚠️ SEGURIDAD: LoginRequiredMixin garantiza autenticación
    # El middleware require_tenant_membership valida membresía en rutas privadas
    path('workspace/', views_ui.WorkspaceView.as_view(), name='workspace'),
]
