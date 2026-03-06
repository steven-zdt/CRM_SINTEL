"""
Tests para validadores de ingestión (FASE 9).

⚠️ PRINCIPIOS:
- Validadores modulares por tipo
- Plug-in friendly
- Errores deterministas
"""
import pytest
from apps.services.document_ingest.validations.router import run_validations
from apps.services.document_ingest.validations.factura import FacturaValidator
from apps.services.document_ingest.validations.nota_credito import NotaCreditoValidator
from apps.services.document_ingest.validations.gasto import GastoValidator
from apps.services.document_ingest.validations.inventario import InventarioValidator


class TestIngestValidators:
    """Tests para validadores de ingestión."""
    
    def test_validate_factura_ok(self):
        """Test: Validar factura válida."""
        dto = {
            "type": "invoice",
            "document_type": "invoice.ubl21",
            "numero": "FAC001",
            "identificadores": {"cufe": "CUFE123", "uuid": "CUFE123"},
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "1000.00", "subtotal": "840.34", "impuestos": "159.66"},
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is True
        assert error_code is None
        assert len(errors) == 0
    
    def test_validate_factura_missing_cufe(self):
        """Test: Validar factura sin CUFE."""
        dto = {
            "type": "invoice",
            "document_type": "invoice.ubl21",
            "numero": "FAC001",
            "identificadores": {},  # Sin CUFE
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "1000.00"},
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is False
        assert error_code in ("missing_required_fields", "validation_error")
        assert len(errors) > 0
    
    def test_validate_creditnote_ok(self):
        """Test: Validar nota crédito válida."""
        dto = {
            "type": "creditnote",
            "document_type": "creditnote.ubl21",
            "numero": "NC001",
            "identificadores": {"cude": "CUDE123", "uuid": "CUDE123"},
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "1000.00"},
            "referencia": {"numero": "FAC001", "cufe": "CUFE123"},
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is True
    
    def test_validate_creditnote_missing_reference(self):
        """Test: Validar nota crédito sin referencia."""
        dto = {
            "type": "creditnote",
            "document_type": "creditnote.ubl21",
            "numero": "NC001",
            "identificadores": {"cude": "CUDE123"},
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "1000.00"},
            # Sin referencia
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is False
        assert "referencia" in str(errors).lower() or "referencia" in error_code
    
    def test_validate_gasto_ok(self):
        """Test: Validar gasto válido."""
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "500.00"},
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is True
    
    def test_validate_gasto_total_zero(self):
        """Test: Validar gasto con total <= 0."""
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is False
        assert "mayor a cero" in str(errors).lower() or error_code == "validation_error"
    
    def test_validate_inventario_ok(self):
        """Test: Validar inventario válido."""
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
            "items": [
                {"codigo": "ITEM001", "descripcion": "Item 1", "cantidad": "10.00", "unidad": "UND"}
            ],
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is True
    
    def test_validate_inventario_no_items(self):
        """Test: Validar inventario sin items."""
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01",
            "emisor": {"nit": "900123456-7", "razon_social": "Empresa Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "0.00"},
            "items": [],  # Sin items
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is False
        assert "al menos un item" in str(errors).lower() or "items" in error_code
    
    def test_validate_unknown_type(self):
        """Test: Validar tipo desconocido."""
        dto = {
            "type": "unknown_type",
            "numero": "DOC001",
        }
        
        is_valid, error_code, errors = run_validations(dto)
        assert is_valid is False
        assert error_code == "no_validator_found"
