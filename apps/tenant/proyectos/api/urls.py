"""
URLs de la API de Proyectos v3.3 (DRF Router)

# WARNING: Arquitectura v2.40: Alineado con enfoque API-First y Multi-Tenant.
Este archivo se incluye en el enrutador principal (config/api_urls.py) 
bajo el prefijo /api/v1/proyectos/
"""
import logging

from rest_framework.routers import DefaultRouter

from .viewsets import ProyectoViewSet, ItemPresupuestoViewSet, TareaDiariaViewSet

logger = logging.getLogger(__name__)

# Se inicializa el router por defecto de DRF para ViewSets
router = DefaultRouter()

# # WARNING: IMPORTANTE: No incluir el prefijo 'proyectos/' aquí.
# El enrutador principal ya delega ese path. Se registra en la raíz del namespace.
router.register(r"", ProyectoViewSet, basename="proyecto")
router.register(r"items-presupuesto", ItemPresupuestoViewSet, basename="items-presupuesto")
router.register(r"tareas-diarias", TareaDiariaViewSet, basename="tareas-diarias")

urlpatterns = router.urls

# # WARNING: DEBUG: Validación de inicialización en el arranque del servidor
if urlpatterns:
    logger.info(f"[OK] ProyectoViewSet (v3.3) registrado correctamente. URLs generadas: {len(urlpatterns)}")
    for url_pattern in urlpatterns:
        logger.debug(f"   - {url_pattern.pattern} -> {getattr(url_pattern, 'name', 'N/A')}")
else:
    logger.error("[ERROR] ERROR CRÍTICO: El router de Proyectos no generó ninguna URL. Verifique el ViewSet.")
