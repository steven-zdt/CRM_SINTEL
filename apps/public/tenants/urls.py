"""
URLs del módulo tenants para el esquema público.
Landing page, login y registro de tenants.
"""

from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    # Landing page principal
    path("", views.LandingPageView.as_view(), name="landing"),
    # Selección de tenant para usuarios autenticados
    path("select/", views.TenantSelectView.as_view(), name="select"),
    # Activación de cuenta (GET: formulario, POST: procesar)
    path("activate/", views.ActivateAccountView.as_view(), name="activate"),
]
