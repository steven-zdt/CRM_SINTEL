"""
Clase base para integraciones externas.

Todas las integraciones deben heredar de esta clase para mantener
consistencia en el manejo de errores y logging.
"""
from abc import ABC, abstractmethod
from typing import Any

from django_tenants.utils import schema_context


class BaseIntegration(ABC):
    """
    Clase base abstracta para integraciones externas.
    
    Proporciona métodos comunes y estructura para todas las integraciones.
    """
    
    def __init__(self, schema_name: str | None = None):
        """
        Inicializa la integración.
        
        Args:
            schema_name: Nombre del esquema del tenant (opcional)
        """
        self.schema_name = schema_name
    
    @abstractmethod
    def conectar(self) -> bool:
        """
        Establece conexión con el servicio externo.
        
        Returns:
            True si la conexión fue exitosa
        """
        pass
    
    @abstractmethod
    def desconectar(self) -> None:
        """Cierra la conexión con el servicio externo."""
        pass
    
    def ejecutar_en_contexto_tenant(self, funcion, *args, **kwargs):
        """
        Ejecuta una función en el contexto del tenant.
        
        WARNING: IMPORTANTE: Usa schema_context para operaciones específicas de tenant.
        
        Args:
            funcion: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Resultado de la función
        """
        if self.schema_name:
            with schema_context(self.schema_name):
                return funcion(*args, **kwargs)
        else:
            return funcion(*args, **kwargs)
    
    def validar_configuracion(self) -> dict[str, Any]:
        """
        Valida la configuración de la integración.
        
        Returns:
            Diccionario con resultado de la validación
        """
        return {
            'valida': True,
            'errores': [],
        }
    
    def obtener_estado(self) -> dict[str, Any]:
        """
        Obtiene el estado de la integración.
        
        Returns:
            Diccionario con estado de la integración
        """
        return {
            'conectado': False,
            'ultima_conexion': None,
            'errores': [],
        }
