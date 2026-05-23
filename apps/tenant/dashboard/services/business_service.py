"""
Business Service para Dashboard v3.9.4 — Orquestación de Métricas.
Pull Model: Delega a extractores de cada app.
Double Semantic Verification: Valida empresa_id en cada consulta.
"""
from datetime import datetime
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone

from apps.tenant.dashboard.services.selectors import DashboardSelector
from apps.tenant.dashboard.services.dtos import DashboardMetricasDTO
from apps.tenant.dashboard.services.extractores import (
    FacturasExtractor,
    InventarioExtractor,
    EmpleadosExtractor,
    GastosExtractor,
    ProyectosExtractor,
)


class DashboardBusinessService:
    """Orquestación de lógica de negocio del dashboard."""

    CACHE_TTL = 900  # 15 minutos

    @staticmethod
    def get_user_role(user, tenant):
        """Obtiene rol del usuario."""
        return DashboardSelector.get_user_role(user, tenant)

    @staticmethod
    def get_redirect_url_by_role(role):
        """Retorna URL de redirección según rol."""
        urls = {
            'ADMIN': '/dashboard/admin/',
            'STAFF': '/dashboard/staff/',
            'USER': '/dashboard/',
        }
        return urls.get(role, '/dashboard/')

    @staticmethod
    def obtener_metricas_consolidadas(empresa_id: int) -> DashboardMetricasDTO:
        """
        Obtiene todas las métricas del dashboard de forma asíncrona.
        Implementa caché Redis para evitar consultas repetidas.

        Args:
            empresa_id: ID de la empresa (Double Semantic Verification)

        Returns:
            DashboardMetricasDTO con métricas consolidadas
        """
        # Intenta leer del caché primero
        cache_key = f"dashboard:metricas:{empresa_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # Obtener nombre y NIT de la empresa (Double Semantic Verification)
            from apps.tenant.empresa.services.selectors import EmpresaSelectors
            empresa = EmpresaSelectors.obtener_por_id(empresa_id)

            if not empresa:
                raise ValueError(f"Empresa {empresa_id} no encontrada")

            # Orquestar extractores en paralelo (en futuro con Celery)
            facturas_dto = FacturasExtractor.extraer_metricas(empresa_id)
            inventario_dto = InventarioExtractor.extraer_metricas(empresa_id)
            empleados_dto = EmpleadosExtractor.extraer_metricas(empresa_id)
            gastos_dto = GastosExtractor.extraer_metricas(empresa_id)
            proyectos_dto = ProyectosExtractor.extraer_metricas(empresa_id)

            # Consolidar en DTO principal
            metricas = DashboardMetricasDTO(
                empresa_nombre=empresa.nombre or "Sin nombre",
                empresa_nit=empresa.nit or "Sin NIT",
                fecha_actualizacion=timezone.now().isoformat(),
                facturas=facturas_dto,
                inventario=inventario_dto,
                empleados=empleados_dto,
                gastos=gastos_dto,
                proyectos=proyectos_dto,
            )

            # Guardar en caché con TTL
            cache.set(cache_key, metricas, timeout=DashboardBusinessService.CACHE_TTL)

            return metricas

        except Exception as e:
            # Log del error (en producción, esto iría a Sentry)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error obteniendo métricas para empresa {empresa_id}: {str(e)}")

            # Retornar estructura vacía pero válida
            return DashboardMetricasDTO(
                empresa_nombre="—",
                empresa_nit="—",
                fecha_actualizacion=timezone.now().isoformat(),
                facturas=FacturasExtractor.extraer_metricas(empresa_id),
                inventario=InventarioExtractor.extraer_metricas(empresa_id),
                empleados=EmpleadosExtractor.extraer_metricas(empresa_id),
            )

    @staticmethod
    def invalidar_cache(empresa_id: int):
        """Invalida el caché de métricas para una empresa."""
        cache_key = f"dashboard:metricas:{empresa_id}"
        cache.delete(cache_key)
