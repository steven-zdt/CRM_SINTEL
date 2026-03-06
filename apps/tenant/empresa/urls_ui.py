"""
URLs UI para partials de empresa (DEPRECADO - UI movida a Core).

⚠️ v2.30+: Esta app solo expone APIs JSON bajo /api/v1/empresas/.
Las páginas de usuario están en apps/tenant/core/static/tenant/core/empresa/index.html

⚠️ DEPRECADO: Las rutas UI han sido deshabilitadas.
Todas las rutas retornan 404.
"""
from django.urls import path
from django.http import HttpResponseNotFound

app_name = 'empresa_ui'

def deprecated_view(request):
    """Vista deprecada que retorna 404."""
    return HttpResponseNotFound('<h1>404 - Vista deprecada</h1><p>Esta ruta ha sido movida a Core. Use /static/tenant/core/empresa/index.html</p>')

urlpatterns = [
    # ⚠️ DEPRECADO: Todas las rutas retornan 404
    path('partials/card/', deprecated_view, name='empresa-card-partial'),
]
