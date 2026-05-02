"""Public API urls for accounts (users exposed under /api/public/v1/users/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.public.accounts.api.public_viewsets import PublicUserViewSet

router = DefaultRouter()
router.register(r"users", PublicUserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
]
