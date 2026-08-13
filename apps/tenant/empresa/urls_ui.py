"""
URLs UI para partials de empresa (DEPRECADO - UI movida a Core).

# WARNING: v2.30+: Esta app solo expone APIs JSON bajo /api/v1/empresas/.
Las páginas de usuario están en apps/tenant/core/static/tenant/core/empresa/index.html

# WARNING: DEPRECADO: Las rutas UI han sido deshabilitadas.
Todas las rutas retornan 404.
"""
from django.http import HttpResponseNotFound
from django.urls import path

from apps.tenant.empresa.views import (
    AreaTableView, EmpresaTableView, MailInboxConfigTableView, SedeTableView,
)

app_name = 'empresa_ui'

def deprecated_view(request):
    """Vista deprecada que retorna 404."""
    return HttpResponseNotFound('<h1>404 - Vista deprecada</h1><p>Esta ruta ha sido movida a Core. Use /static/tenant/core/empresa/index.html</p>')

urlpatterns = [
    # # WARNING: DEPRECADO: Todas las rutas retornan 404
    path('partials/card/', deprecated_view, name='empresa-card-partial'),
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la grilla de Sede en sede_list.js. NO es parte de la deprecacion de
    # arriba: el grid de Sede vive en el tab activo de workspace.html
    # (tenant/empresa/empresa_list.html), no en el shell estatico legacy.
    path('sedes/tabla/', SedeTableView.as_view(), name='sede-tabla'),
    # Idem para Area — reemplaza la grilla en area_list.js
    path('areas/tabla/', AreaTableView.as_view(), name='area-tabla'),
    # Idem para Empresa (singleton) — reemplaza la grilla en empresa_list.js
    path('empresa/tabla/', EmpresaTableView.as_view(), name='empresa-tabla'),
    # Idem para MailInboxConfig — reemplaza la grilla en mailinboxconfig_list.js
    # (ver plan_refactorizacion.md: la grilla Tabulator nunca funciono, IDs
    # #grid-mailinboxconfig/#search-mailinboxconfig no coincidian con el
    # template, que usaba #grid-mailinbox/#search-mailinbox)
    path('mailinboxconfig/tabla/', MailInboxConfigTableView.as_view(), name='mailinboxconfig-tabla'),
]
