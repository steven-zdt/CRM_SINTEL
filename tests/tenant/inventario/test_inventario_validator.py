"""
Tests para validador de inventario (FASE 9).

⚠️ PRINCIPIOS:
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
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
            "items": [
                {"codigo": "ITEM001", "descripcion": "Producto 1", "cantidad": "10.00", "unidad": "UND"}
            ],
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario")
        assert is_valid is True
        assert error_code is None
        assert len(errors) == 0
    
    def test_validate_inventario_no_items(self):
        """Test: Error si no hay items."""
        validator = InventarioValidator()
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
            "items": [],  # Sin items
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario")
        assert is_valid is False
        assert "al menos un item" in str(errors).lower() or "items" in error_code
    
    def test_validate_inventario_invalid_date(self):
        """Test: Error si fecha inválida."""
        validator = InventarioValidator()
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "invalid-date",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
            "items": [
                {"codigo": "ITEM001", "descripcion": "Producto 1", "cantidad": "10.00", "unidad": "UND"}
            ],
        }
        
        is_valid, error_code, errors = validator.validate(dto, "inventario")
        assert is_valid is False
        assert "fecha" in str(errors).lower() or "fecha_emision" in error_code
