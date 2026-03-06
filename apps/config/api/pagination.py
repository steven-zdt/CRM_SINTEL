"""
Paginación estándar para todas las APIs.

Referencia: https://www.django-rest-framework.org/api-guide/pagination/
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar para todas las APIs.
    
    Configuración:
    - page_size: 20 resultados por página (default según requisitos)
    - page_size_query_param: Permite cambiar el tamaño de página vía query param (?page_size=50)
    - max_page_size: Máximo 200 resultados por página
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
