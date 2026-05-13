# apps/tenant/contabilidad/integracion/extractores/__init__.py
from .base import AbstractExtractor
from .gastos import ExtractorGastos
from .inventario import ExtractorInventario
from .facturas import ExtractorFacturas
from .nomina import ExtractorNomina

__all__ = [
    'AbstractExtractor',
    'ExtractorGastos',
    'ExtractorInventario',
    'ExtractorFacturas',
    'ExtractorNomina',
]
