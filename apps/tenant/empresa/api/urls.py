"""
URLs de API para la app empresa.

# WARNING: v2.40: Arquitectura API-First con Tabulator Factory.
- Todas las rutas están bajo /api/v1/empresas/
- Usa routers de DRF para generar endpoints automáticamente
- Endpoint Tabulator: GET /api/v1/empresas/ con StandardResultsSetPagination
- Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.tenant.empresa.api.viewsets import (
    EmpresaViewSet,
    MailInboxConfigViewSet,
    SedeViewSet,
    AreaViewSet,
    actividades_lookup,
    ciiu_lookup,
    form_metadata,
)

# Router para esta app
router = DefaultRouter()

# # WARNING: IMPORTANTE: No incluir el prefijo aquí porque ya está en config/api_urls.py
# El router se incluye con path('empresas/', include(...)), así que registramos sin prefijo
# # WARNING: CRÍTICO: Registrar rutas específicas ANTES de la ruta vacía para evitar conflictos
router.register(r'mail-inbox-config', MailInboxConfigViewSet, basename='mail-inbox-config')
router.register(r'sedes', SedeViewSet, basename='sedes')
router.register(r'areas', AreaViewSet, basename='areas')
router.register(r'', EmpresaViewSet, basename='empresas')

# URLs generadas por el router + endpoints auxiliares
urlpatterns = router.urls + [
    path('empresa/form-metadata/', form_metadata, name='empresa-form-metadata'),
    path('empresa/actividades-lookup/', actividades_lookup, name='empresa-actividades-lookup'),
    path('empresa/ciiu-lookup/', ciiu_lookup, name='empresa-ciiu-lookup'),
]
