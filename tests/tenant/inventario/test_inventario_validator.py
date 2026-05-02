"""
Tests para validador de inventario (FASE 9).

[WARNING] PRINCIPIOS:
- Validaciones específicas de inventario
- Al menos 1 item
- Cantidades > 0
- Unidades válidas
"""
import pytest
from apps.services.document_ingest.validations.inventario import InventarioValidator


class TestInventarioValidator:
    """Tests para validador de inventario."""
    
    def test_validate_inventario_ok(self):
        """Test: Validar inventario válido."""
        validator = InventarioValidator()
        dto = {
            "type": "inventario.catalogo",
            "items": [
                {"codigo": "ITEM001", "nombre": "Producto 1", "cantidad": "10.00", "unidad": "UND"}
            ],
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario.catalogo")
        assert is_valid is True
        assert error_code is None
        assert len(errors) == 0
    
    def test_validate_inventario_no_items(self):
        """Test: Error si no hay items."""
        validator = InventarioValidator()
        dto = {
            "type": "inventario.catalogo",
            "items": [],  # Sin items
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario.catalogo")
        assert is_valid is False
        assert "items" in str(errors).lower() or "items" in error_code
    
    def test_validate_inventario_invalid_date(self):
        """Test: Validador de catálogo ignora campos de fecha emisión."""
        validator = InventarioValidator()
        dto = {
            "type": "inventario.catalogo",
            "fecha_emision": "invalid-date",
            "items": [
                {"codigo": "ITEM001", "nombre": "Producto 1", "cantidad": "10.00", "unidad": "UND"}
            ],
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario.catalogo")
        # El validador actual de inventario ignora la fecha_emision ya que es para catalogos
        assert is_valid is True
