"""Ensure project root is on sys.path early for test runner and containers.

This helps resolve imports like `apps.*` during pytest collection when the
environment's sys.path does not include the repository root.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Register a top-level 'smoke' package pointing to the tenant facturas smoke tests
# so imports like `import smoke.test_facturas_list` resolve during pytest collection.
try:
    import sys as _sys
    import types as _types
    from pathlib import Path as _Path

    _smoke_path = str(_Path(__file__).resolve().parent.joinpath('tests', 'tenant', 'facturas', 'smoke'))
    if 'smoke' not in _sys.modules and _Path(_smoke_path).exists():
        _m = _types.ModuleType('smoke')
        _m.__path__ = [_smoke_path]
        _sys.modules['smoke'] = _m
except Exception:
    # Best-effort: do not fail import if environment differs
    pass
