"""
Extractores para Dashboard v3.9.4 — Pull Model Delegado.
Cada extractor consulta los selectors.py de su app de dominio.
Nunca importa models.py directamente.
"""
from .facturas_ext import FacturasExtractor
from .inventario_ext import InventarioExtractor
from .empleados_ext import EmpleadosExtractor
from .gastos_ext import GastosExtractor
from .proyectos_ext import ProyectosExtractor

__all__ = [
    'FacturasExtractor',
    'InventarioExtractor',
    'EmpleadosExtractor',
    'GastosExtractor',
    'ProyectosExtractor',
]
