"""
URLs UI para partials de dashboard (DEPRECADO - UI movida a Core).

⚠️ v2.30+: Esta app solo expone APIs JSON bajo /api/v1/dashboard/.
Las páginas de usuario están en apps/tenant/core/static/tenant/core/dashboard/index.html

⚠️ DEPRECADO: Las rutas UI han sido deshabilitadas.
Todas las rutas retornan 404.
"""
from django.urls import path
from django.http import HttpResponseNotFound

app_name = 'dashboard_ui'

def deprecated_view(request):
    """Vista deprecada que retorna 404."""
    return HttpResponseNotFound('<h1>404 - Vista deprecada</h1><p>Esta ruta ha sido movida a Core. Use /static/tenant/core/dashboard/index.html</p>')

urlpatterns = [
    # ⚠️ DEPRECADO: Todas las rutas retornan 404
    path('partials/header/', deprecated_view, name='dashboard-partial-header'),
    path('partials/kpis/', deprecated_view, name='dashboard-partial-kpis'),
    path('partials/charts/', deprecated_view, name='dashboard-partial-charts'),
    path('partials/table/', deprecated_view, name='dashboard-partial-table'),
]
