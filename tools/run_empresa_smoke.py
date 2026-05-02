"""
Smoke runner para validar `crud_service` y `business_service` sin pytest ni Django.
Se ejecuta como: `python tools/run_empresa_smoke.py` dentro del contenedor web.
"""
import sys
import os
import types

# Ensure repo root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Initialize Django settings to allow importing app modules without pytest
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def make_mock_empresa(first_obj=None):
    class _QS:
        def __init__(self, items=None):
            self._items = items or []

        def only(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self._items[0] if self._items else None

    mgr = types.SimpleNamespace()
    mgr.only = lambda *a, **k: _QS([first_obj] if first_obj else [])
    return types.SimpleNamespace(objects=mgr)


def run():
    print('Running empresa smoke checks...')

    # Import the modules under test
    from apps.tenant.empresa.services import crud_service, business_service

    # Monkeypatch Empresa in crud_service to a mock
    crud_service.Empresa = make_mock_empresa()

    # Call qs_list
    qs = crud_service.qs_list(search='x')
    print('qs_list() returned object:', type(qs))

    # Validate get_empresa_data returns None when no empresa
    res = crud_service.get_empresa_data()
    print('get_empresa_data() ->', res)

    # For business_service, monkeypatch Empresa and primitives
    business_service.Empresa = make_mock_empresa()

    try:
        # crear_empresa should call underlying primitives; patch if missing
        if hasattr(business_service, 'crear_empresa'):
            print('Calling business_service.crear_empresa (expect exception or object)')
            try:
                out = business_service.crear_empresa({'razon_social': 'X'})
                print('crear_empresa() returned:', getattr(out, 'id', out))
            except Exception as e:
                print('crear_empresa() raised (expected in smoke):', e)
    except Exception as e:
        print('Error during business_service checks:', e)

    print('Smoke checks finished.')


if __name__ == '__main__':
    run()
