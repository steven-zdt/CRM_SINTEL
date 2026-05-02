"""
Paginación estándar para el módulo de cotizaciones.

# WARNING: MÓDULO AUTÓNOMO: Este módulo no depende de otras apps.
"""
from rest_framework.pagination import PageNumberPagination


class CotizacionesResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar para las APIs de cotizaciones.
    
    Configuración:
    - page_size: 20 resultados por página (default)
    - page_size_query_param: Permite cambiar el tamaño de página vía query param (?page_size=50)
    - max_page_size: Máximo 200 resultados por página
    
    Compatible con Tabulator Factory v2.40.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
