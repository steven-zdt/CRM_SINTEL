"""
URLs UI para partials de landing.

⚠️ API-First: Estas rutas solo retornan HTML estructural (partials).
Los datos se cargan vía JavaScript desde las APIs JSON de la app.
"""
from django.urls import path
from apps.tenant.landing.views_ui import (
    LandingHeaderPartialView,
    LandingAuthPartialView,
    LandingInfoPartialView,
)

app_name = 'landing_ui'

urlpatterns = [
    path('partials/header/', LandingHeaderPartialView.as_view(), name='landing-partial-header'),
    path('partials/auth/', LandingAuthPartialView.as_view(), name='landing-partial-auth'),
    path('partials/info/', LandingInfoPartialView.as_view(), name='landing-partial-info'),
]
