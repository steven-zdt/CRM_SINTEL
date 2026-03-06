"""
DTOs específicos para Cotizaciones (v2.40).

⚠️ PRINCIPIOS:
- DTOs específicos para el módulo de cotizaciones
- Estructuras específicas para catálogos de productos
"""
from typing import Dict, Any, Optional, List, Literal
from decimal import Decimal
from dataclasses import dataclass, asdict

# Tipos de documentos específicos de cotizaciones
CotizacionesDocumentType = Literal[
    "inventario.catalogo",
]


@dataclass
class ProductoDTO:
    """DTO para un producto en un catálogo."""
    codigo: str
    nombre: str
    marca: Optional[str] = None
    referencia: Optional[str] = None
    unidad: str = "UND"
    precio_venta: str = "0.00"
    descripcion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CatalogoDTO:
    """DTO para un catálogo de productos."""
    document_type: str = "inventario.catalogo"
    type: str = "inventario"
    items: List[Dict[str, Any]] = None
    mapping_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        result = {
            "document_type": self.document_type,
            "type": self.type,
            "items": self.items,
        }
        if self.mapping_metadata:
            result["mapping_metadata"] = self.mapping_metadata
        return result


__all__ = [
    'ProductoDTO',
    'CatalogoDTO',
    'CotizacionesDocumentType',
]
