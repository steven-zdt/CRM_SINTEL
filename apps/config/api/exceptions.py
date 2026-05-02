"""
Excepciones personalizadas para APIs.

Referencia: https://www.django-rest-framework.org/api-guide/exceptions/
"""
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    Handler personalizado para excepciones de DRF.
    
    Formatea las respuestas de error de manera consistente.
    Agrega un campo detail_code para facilitar el manejo de errores en el frontend.
    
    WARNING: v2.60: Maneja tanto diccionarios como listas en response.data
    """
    # Llamar al handler por defecto de DRF
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Agregar código de detalle si está disponible
        # WARNING: v2.60: response.data puede ser un dict, list o str (dependiendo del tipo de error)
        detail_code = getattr(exc, "default_code", "error")
        
        if isinstance(response.data, dict):
            # Caso normal: diccionario con errores de validación por campo
            response.data["detail_code"] = detail_code
        elif isinstance(response.data, list):
            # Caso especial: lista de errores (poco común en DRF, pero puede ocurrir)
            response.data = {
                "detail": response.data[0] if response.data else "Error de validación",
                "detail_code": detail_code,
                "errors": response.data
            }
        elif isinstance(response.data, str):
            # Caso especial: string simple (poco común)
            response.data = {
                "detail": response.data,
                "detail_code": detail_code
            }
        else:
            # Caso de seguridad: si es otro tipo, convertir a string
            response.data = {
                "detail": str(response.data) if response.data else "Error desconocido",
                "detail_code": detail_code
            }
    
    return response
