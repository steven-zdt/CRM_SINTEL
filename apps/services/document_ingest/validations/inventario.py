"""
Validador para catálogos de productos/inventario (v2.40).

⚠️ PRINCIPIOS:
- Validaciones específicas para catálogos de productos
- Reglas de negocio del dominio de inventario/cotizaciones
- Hereda de BaseValidator
- NO valida campos de facturas (emisor, receptor, CUFE, etc.)
"""
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal, InvalidOperation
from .base import BaseValidator


class InventarioValidator(BaseValidator):
    """
    Validador para catálogos de productos/inventario.
    
    Aplica validaciones específicas para catálogos:
    - Items con código y nombre
    - Precios válidos
    - Unidades de medida válidas
    - NO requiere campos de facturas (emisor, receptor, CUFE, etc.)
    """
    
    @property
    def document_type(self) -> str:
        """Tipo de documento que este validador procesa."""
        return "inventario.catalogo"
    
    @property
    def app_name(self) -> str:
        """Nombre de la app que usa este validador."""
        return "cotizaciones"
    
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Valida un DTO de catálogo de productos.
        
        Reglas:
        - Debe tener items (array de productos)
        - Cada item debe tener código y nombre
        - Precios deben ser numéricos válidos
        - Unidades de medida válidas
        
        Args:
            dto: DTO a validar
            document_type: Tipo de documento (debe ser "inventario.catalogo" o "inventario")
            
        Returns:
            Tupla (is_valid, error_code, missing_fields)
        """
        # Aceptar tanto "inventario.catalogo" como "inventario"
        if not (document_type.startswith("inventario") or document_type == "inventario.catalogo"):
            return False, "invalid_document_type", [f"Validador de inventario no puede validar tipo: {document_type}"]
        
        missing_fields = []
        errors = []
        
        # 1. Validar que tenga items
        items = dto.get("items", [])
        if not items or not isinstance(items, list):
            missing_fields.append("items")
            errors.append("El catálogo debe contener al menos un producto (items)")
            return False, "missing_items", missing_fields
        
        # 2. Validar cada item del catálogo
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"Item {idx + 1}: debe ser un objeto/diccionario")
                continue
            
            # Validar código (obligatorio)
            codigo = item.get("codigo")
            if not codigo or not str(codigo).strip():
                missing_fields.append(f"items[{idx}].codigo")
                errors.append(f"Item {idx + 1}: código es obligatorio")
            
            # Validar nombre (obligatorio)
            nombre = item.get("nombre")
            if not nombre or not str(nombre).strip():
                missing_fields.append(f"items[{idx}].nombre")
                errors.append(f"Item {idx + 1}: nombre es obligatorio")
            
            # Validar precio_venta (debe ser numérico válido)
            precio_venta = item.get("precio_venta")
            if precio_venta is not None:
                try:
                    # Intentar convertir a Decimal
                    precio_str = str(precio_venta).replace('$', '').replace(',', '').replace(' ', '').strip()
                    precio_decimal = Decimal(precio_str)
                    if precio_decimal < Decimal('0.00'):
                        errors.append(f"Item {idx + 1}: precio_venta no puede ser negativo")
                except (ValueError, InvalidOperation, AttributeError):
                    errors.append(f"Item {idx + 1}: precio_venta debe ser un número válido")
            else:
                # Precio es opcional, pero si está presente debe ser válido
                # Por defecto se usa 0.00 si no está presente
                pass
            
            # Validar unidad (si está presente, debe ser un string válido)
            unidad = item.get("unidad")
            if unidad is not None and not isinstance(unidad, str):
                errors.append(f"Item {idx + 1}: unidad debe ser un string")
        
        # Si hay errores, retornar inválido
        if errors or missing_fields:
            return False, "validation_errors", missing_fields + errors
        
        return True, None, []
    
    def validate_common_fields(self, dto: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Valida campos comunes para catálogos de productos.
        
        ⚠️ v2.40: NO valida campos de facturas (emisor, receptor, CUFE, etc.)
        Solo valida estructura básica del catálogo.
        
        Args:
            dto: DTO a validar
            
        Returns:
            Tupla (is_valid, missing_fields)
        """
        missing_fields = []
        
        # Para catálogos, solo validamos que tenga items
        if "items" not in dto or not dto["items"]:
            missing_fields.append("items")
        
        # Validar que document_type sea correcto
        doc_type = dto.get("document_type") or dto.get("type", "")
        if not doc_type or not (doc_type.startswith("inventario") or doc_type == "inventario.catalogo"):
            missing_fields.append("document_type (debe ser inventario.catalogo)")
        
        return len(missing_fields) == 0, missing_fields
