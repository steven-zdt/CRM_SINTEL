"""
URLs UI (HTML server-rendered) para Perfil. Fase 5-BIS.

Se incluye de forma defensiva en config/urls_tenant.py:
    path('ui/perfil/', include((perfil_ui_urlpatterns, 'perfil'), namespace='perfil_ui'))
"""
from django.urls import path

from apps.tenant.perfil.views import PerfilTableView

app_name = "perfil_ui"

urlpatterns = [
    # Tabla server-rendered (django-tables2 + HTMX) — Fase 5-BIS, reemplaza
    # la inicializacion de Tabulator en perfil.page.js
    path("tabla/", PerfilTableView.as_view(), name="perfil-tabla"),
]
