import logging

import django.conf
from rest_framework.routers import DefaultRouter

from .viewsets import RequisicionCompraViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r"", RequisicionCompraViewSet, basename="requisiciones-compra")

urlpatterns = router.urls

if django.conf.settings.DEBUG:
    logger.debug(
        f"URLs de requisiciones de compra generadas: {[str(url.pattern) for url in router.urls]}"
    )
