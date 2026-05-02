"""
URLs de API para la app tenants.

Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.public.tenants.api.views import ActivateAccountAPIView
from apps.public.tenants.api.views import CreateTenantOnboardingAPIView
from apps.public.tenants.api.viewsets import VIEWSETS, ClientViewSet

# Router para esta app
router = DefaultRouter()

# Registrar todos los ViewSets automáticamente
for prefix, viewset, basename in VIEWSETS:
    router.register(prefix, viewset, basename=basename)

urlpatterns = [
    # Endpoint de activación de cuenta (POST JSON)
    path("tenants/activate/", ActivateAccountAPIView.as_view(), name="activate-account-api"),
    # Compatibilidad con clientes existentes y tests: exponer explícitamente
    # el endpoint POST /tenants/create/ que actualmente se espera en la UI y
    # en la suite de tests. Mapea al action `onboard` del `ClientViewSet`.
    path("tenants/create/", ClientViewSet.as_view({"post": "onboard"}), name="tenant-onboard-create"),
    # Onboarding sin fricción (OTT)
    path("tenants/onboarding/create/", CreateTenantOnboardingAPIView.as_view(), name="tenant-onboarding-create"),
    # Router URLs
    path("", include(router.urls)),
]
