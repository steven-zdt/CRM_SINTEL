from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import SolicitudAprobacionViewSet

router = DefaultRouter()
router.register(r"", SolicitudAprobacionViewSet, basename="solicitud-aprobacion")

urlpatterns = [
    path("", include(router.urls)),
]
