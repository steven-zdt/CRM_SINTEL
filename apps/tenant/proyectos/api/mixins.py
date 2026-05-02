"""
Mixins para la API de Proyectos v3.5

WARNING: SINTEL v3.5: Inyección de Servicios (DSV)
- Desacoplamiento: El ViewSet NO importa servicios directamente
- Propiedades: Acceso a selectors y business logic vía properties
- Consistencia: Patrón replicable en todo el tenant
"""
from .. import services

class ProyectoServiceMixin:
    """
    Mixin para inyectar la lógica de servicios en los ViewSets de Proyectos.
    """
    
    @property
    def proyecto_selector(self):
        """Selector de lectura optimizada."""
        return services.qs_list
    
    @property
    def proyecto_detail_selector(self):
        """Selector de detalle optimizado."""
        return services.qs_detail
    
    @property
    def proyecto_business_service(self):
        """Orquestador de lógica de negocio."""
        return services.business_service
    
    @property
    def proyecto_crud_service(self):
        """Persistencia pura."""
        return services.crud_service
