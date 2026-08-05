import logging
from rest_framework.routers import DefaultRouter
from .viewsets import OrdenCompraViewSet, PlantillaOrdenCompraViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r'plantillas', PlantillaOrdenCompraViewSet, basename='plantilla-orden-compra')
router.register(r'', OrdenCompraViewSet, basename='ordenes-compra')

urlpatterns = router.urls

import django.conf
if django.conf.settings.DEBUG:
    logger.debug(f"URLs de compras generadas: {[str(url.pattern) for url in router.urls]}")
