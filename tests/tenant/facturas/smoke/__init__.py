"""Smoke tests package marker for tenant facturas.

This makes `smoke.test_facturas_list` imports resolve as a package.
"""

__all__ = []

"""
Smoke tests para endpoints de facturas.

[WARNING] OBJETIVO: Verificar que los endpoints están correctamente registrados
y responden correctamente desde el dominio del tenant.
"""

# Ensure imports like `import smoke.test_facturas_list` resolve during pytest
# by registering a top-level `smoke` package pointing to this package.
import sys
import types
from pathlib import Path

_pkg_path = str(Path(__file__).resolve().parent)
if "smoke" not in sys.modules:
    _m = types.ModuleType("smoke")
    _m.__path__ = [_pkg_path]
    sys.modules["smoke"] = _m
