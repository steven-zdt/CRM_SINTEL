"""
Tests para validador de gastos (FASE 9).

⚠️ PRINCIPIOS:
- Validaciones específicas de gasto
- Total > 0
- Fecha válida
- Campos obligatorios
"""
import pytest
from apps.services.document_ingest.validations.gasto import GastoValidator


class TestGastoValidator:
    """Tests para validador de gastos."""
    
    def test_validate_gasto_ok(self):
        """Test: Validar gasto válido."""
        validator = GastoValidator()
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "500.00"},
        }
        
        is_valid, error_code, errors = validator.validate(dto, "gasto")
        assert is_valid is True
        assert error_code is None
        assert len(errors) == 0
    
    def test_validate_gasto_total_zero(self):
        """Test: Error si total <= 0."""
        validator = GastoValidator()
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
        }
        
        is_valid, error_code, errors = validator.validate(dto, "gasto")
        assert is_valid is False
        assert "mayor a cero" in str(errors).lower()
    
    def test_validate_gasto_total_negative(self):
        """Test: Error si total negativo."""
        validator = GastoValidator()
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "-100.00"},
        }
        
        is_valid, error_code, errors = validator.validate(dto, "gasto")
        assert is_valid is False
        assert "mayor a cero" in str(errors).lower()
    
    def test_validate_gasto_invalid_date(self):
        """Test: Error si fecha inválida."""
        validator = GastoValidator()
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "invalid-date",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "500.00"},
        }
        
        is_valid, error_code, errors = validator.validate(dto, "gasto")
        assert is_valid is False
        assert "fecha" in str(errors).lower() or "fecha_emision" in error_code
    
    def test_validate_gasto_missing_total(self):
        """Test: Error si falta total."""
        validator = GastoValidator()
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            # Sin totales
        }
        
        is_valid, error_code, errors = validator.validate(dto, "gasto")
        assert is_valid is False
        assert "totales" in str(errors).lower() or "totales" in error_code
