"""
URLs para Landing API (v2.30).

⚠️ POLÍTICA v2.30:
- Endpoints públicos (AllowAny) SOLO para información de tenant y activación
- Arquitectura API-First: solo JSON, no HTML
- Todas las rutas están bajo /api/v1/landing/
- Auth (login, logout, password-reset) está centralizado en Core API: /api/v1/core/auth/*
- Único ViewSet con acciones: /info/ y /auth/activate/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenant.landing.api.viewsets import LandingViewSet

app_name = 'tenant_landing_api'

# Router para ViewSet unificado
router = DefaultRouter()
router.register(r'', LandingViewSet, basename='landing')

urlpatterns = [
    # ⚠️ v2.30: ViewSet unificado expone:
    # - GET /api/v1/landing/info/ → LandingViewSet.info
    # - GET|POST /api/v1/landing/auth/activate/ → LandingViewSet.activate
    path('', include(router.urls)),
    
    # ⚠️ ELIMINADO v2.30: Auth endpoints movidos a Core API
    # - /auth/login/ → /api/v1/core/auth/login/
    # - /auth/logout/ → /api/v1/core/auth/logout/
    # - /auth/password-reset/* → /api/v1/core/auth/password-reset/*
]
