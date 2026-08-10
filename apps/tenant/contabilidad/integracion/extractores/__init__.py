# apps/tenant/contabilidad/integracion/extractores/__init__.py
from .base import AbstractExtractor
from .facturas import ExtractorFacturas
from .gastos import ExtractorGastos
from .inventario import ExtractorInventario
from .nomina import ExtractorNomina

__all__ = [
    'AbstractExtractor',
    'ExtractorGastos',
    'ExtractorFacturas',
    'ExtractorNomina',
    'ExtractorInventario',
]
