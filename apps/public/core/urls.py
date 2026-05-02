"""
URLs del core público.
Incluye rutas básicas como workspace/, favicon.ico y redirecciones.
"""

from django.shortcuts import redirect
from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "public_core"


def favicon_view(request):
    """Favicon - redirige a static file"""
    return redirect("/static/tenant/core/favicon.ico", permanent=True)


def workspace_redirect(request):
    """Redirige /workspace/ a la consola de administración"""
    return redirect("/console/")


urlpatterns = [
    # Página principal pública
    path("", views.PublicIndexView.as_view(), name="index"),
    # Workspace redirect
    path("workspace/", workspace_redirect, name="workspace-redirect"),
    # Favicon
    path("favicon.ico", favicon_view, name="favicon"),
    # Redirecciones adicionales
    path(
        "console/tenants/",
        RedirectView.as_view(url="/console/tenants/", permanent=False),
        name="console-tenants-redirect",
    ),
]
