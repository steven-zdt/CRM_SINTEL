"""
DTOs específicos para Cotizaciones (v2.40).

WARNING: PRINCIPIOS:
- DTOs específicos para el módulo de cotizaciones
- Estructuras específicas para catálogos de productos
"""
from dataclasses import asdict, dataclass
from typing import Any, Literal

# Tipos de documentos específicos de cotizaciones
CotizacionesDocumentType = Literal[
    "inventario.catalogo",
]


@dataclass
class ProductoDTO:
    """DTO para un producto en un catálogo."""
    codigo: str
    nombre: str
    marca: str | None = None
    referencia: str | None = None
    unidad: str = "UND"
    precio_venta: str = "0.00"
    descripcion: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CatalogoDTO:
    """DTO para un catálogo de productos."""
    document_type: str = "inventario.catalogo"
    type: str = "inventario"
    items: list[dict[str, Any]] = None
    mapping_metadata: dict[str, Any] | None = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def to_dict(self) -> dict[str, Any]:
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
