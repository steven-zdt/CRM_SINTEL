import logging
from rest_framework.routers import DefaultRouter
from .viewsets import OrdenCompraViewSet, PlantillaOrdenCompraViewSet, RecepcionCompraViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r'plantillas', PlantillaOrdenCompraViewSet, basename='plantilla-orden-compra')
# [F21] Debe registrarse ANTES del router de prefijo vacio de abajo: el
# patron de detalle de OrdenCompraViewSet (^(?P<uuid>[^/.]+)/$) matchearia
# "recepciones/" como si fuera un uuid si se registrara despues.
router.register(r'recepciones', RecepcionCompraViewSet, basename='recepciones-compra')
router.register(r'', OrdenCompraViewSet, basename='ordenes-compra')

urlpatterns = router.urls

import django.conf
if django.conf.settings.DEBUG:
    logger.debug(f"URLs de compras generadas: {[str(url.pattern) for url in router.urls]}")
