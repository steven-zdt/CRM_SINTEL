"""
Business Service for ConfiguracionCotizacion v2.62.0.
"""
import logging
from .crud_service import ConfiguracionCRUDService

logger = logging.getLogger(__name__)

class ConfiguracionBusinessService:
    @staticmethod
    def crear_configuracion(empresa, datos):
        """Lógica de negocio para crear configuración."""
        return ConfiguracionCRUDService.create_configuracion(empresa, **datos)

    @staticmethod
    def actualizar_configuracion(instance, datos):
        """Lógica de negocio para actualizar configuración."""
        return ConfiguracionCRUDService.update_configuracion(instance, **datos)
