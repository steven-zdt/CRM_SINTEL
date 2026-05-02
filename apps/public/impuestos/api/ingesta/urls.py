"""
URLs para la API de Ingesta.

Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""

from rest_framework.routers import DefaultRouter

from apps.public.impuestos.api.ingesta.views import IngestaViewSet

# Router para ingesta
router = DefaultRouter()
router.register(r"ingesta", IngestaViewSet, basename="impuestos-ingesta")

urlpatterns = router.urls
