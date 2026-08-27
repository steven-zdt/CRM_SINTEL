"""
Business Service for ConfiguracionCotizacion v2.62.0.
"""
import logging
from .crud_service import ConfiguracionCRUDService

logger = logging.getLogger(__name__)

class ConfiguracionBusinessService:
    @staticmethod
    def crear_configuracion(empresa, datos):
        """Logica de negocio para crear configuracion."""
        return ConfiguracionCRUDService.create_configuracion(empresa, **datos)

    @staticmethod
    def actualizar_configuracion(instance, datos):
        """Logica de negocio para actualizar configuracion."""
        return ConfiguracionCRUDService.update_configuracion(instance, **datos)

    @staticmethod
    def eliminar_configuracion(instance):
        """Logica de negocio para eliminar configuracion."""
        return ConfiguracionCRUDService.delete_configuracion(instance)
