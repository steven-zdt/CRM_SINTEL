"""
URLs de API para la app tenants.

Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.public.tenants.api.viewsets import VIEWSETS

# Router para esta app
router = DefaultRouter()

# Registrar todos los ViewSets automáticamente
for prefix, viewset, basename in VIEWSETS:
    router.register(prefix, viewset, basename=basename)

urlpatterns = [
    path('', include(router.urls)),
]
