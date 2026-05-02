"""
Tests para verificar que todos los middlewares en MIDDLEWARE se pueden importar.

[WARNING] IMPORTANTE: Este test previene errores de ImproperlyConfigured al iniciar el servidor.
Cada ruta en MIDDLEWARE debe ser importable sin lanzar ImportError o AttributeError.
"""
import pytest
from django.conf import settings
from django.utils.module_loading import import_string


@pytest.mark.parametrize("mw_path", settings.MIDDLEWARE)
def test_middleware_path_is_importable(mw_path):
    """
    Test: Cada ruta en MIDDLEWARE debe importar sin errores.
    
    Objetivo: Verificar que todas las rutas de middleware en settings.MIDDLEWARE
    se pueden importar correctamente, evitando errores de ImproperlyConfigured
    al iniciar el servidor.
    
    Args:
        mw_path: Ruta del middleware (ej: 'django.middleware.security.SecurityMiddleware')
    """
    # Cada ruta debe importar sin lanzar ImportError/ImproperlyConfigured
    try:
        middleware = import_string(mw_path)
        # Verificar que es callable (factory funcional) o tiene __call__ (clase)
        assert callable(middleware) or hasattr(middleware, '__call__'), \
            f"El middleware '{mw_path}' no es callable"
    except ImportError as e:
        pytest.fail(f"No se pudo importar el middleware '{mw_path}': {e}")
    except AttributeError as e:
        pytest.fail(f"El módulo del middleware '{mw_path}' no tiene el atributo esperado: {e}")
    except Exception as e:
        pytest.fail(f"Error inesperado al importar el middleware '{mw_path}': {e}")
