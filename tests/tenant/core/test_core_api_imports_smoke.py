"""
Smoke tests para importaciones de Core API URLs.

⚠️ POLÍTICA: Verificar que las importaciones de URLConf no causen errores.
"""
import pytest


def test_core_api_urls_import():
    """Importar apps.tenant.core.api.urls no debe causar errores."""
    try:
        from apps.tenant.core.api import urls as core_api_urls
        assert hasattr(core_api_urls, 'urlpatterns'), "urlpatterns debe existir en core_api_urls"
        assert isinstance(core_api_urls.urlpatterns, list), "urlpatterns debe ser una lista"
        assert len(core_api_urls.urlpatterns) > 0, "urlpatterns no debe estar vacío"
    except ImportError as e:
        pytest.fail(f"Error importando apps.tenant.core.api.urls: {e}")
    except NameError as e:
        pytest.fail(f"NameError al importar apps.tenant.core.api.urls: {e}")
    except Exception as e:
        pytest.fail(f"Error inesperado al importar apps.tenant.core.api.urls: {e}")


def test_core_api_views_import():
    """Importar apps.tenant.core.api.views no debe causar errores."""
    try:
        from apps.tenant.core.api import views as core_api_views
        # Verificar que las clases principales existen
        assert hasattr(core_api_views, 'PasswordResetRequestView'), "PasswordResetRequestView debe existir"
        assert hasattr(core_api_views, 'PasswordResetValidateView'), "PasswordResetValidateView debe existir"
        assert hasattr(core_api_views, 'PasswordResetConfirmView'), "PasswordResetConfirmView debe existir"
    except ImportError as e:
        pytest.fail(f"Error importando apps.tenant.core.api.views: {e}")
    except NameError as e:
        pytest.fail(f"NameError al importar apps.tenant.core.api.views: {e}")
    except Exception as e:
        pytest.fail(f"Error inesperado al importar apps.tenant.core.api.views: {e}")


def test_tenant_urlconf_import():
    """Importar config.urls_tenant no debe causar errores."""
    try:
        from config import urls_tenant
        assert hasattr(urls_tenant, 'urlpatterns'), "urlpatterns debe existir en urls_tenant"
        assert isinstance(urls_tenant.urlpatterns, list), "urlpatterns debe ser una lista"
    except ImportError as e:
        pytest.fail(f"Error importando config.urls_tenant: {e}")
    except NameError as e:
        pytest.fail(f"NameError al importar config.urls_tenant: {e}")
    except Exception as e:
        pytest.fail(f"Error inesperado al importar config.urls_tenant: {e}")
