"""
Tests de materialización de gastos (FASE 9).

[WARNING] PRINCIPIOS:
- Materialización desde DTO
- Idempotencia por número
- Transaccional
- Multi-tenant
"""
import pytest
from django_tenants.test.cases import TenantTestCase
from apps.tenant.gastos.services import materializar_gasto_desde_dto


class TestGastoMaterialization(TenantTestCase):
    """Tests de materialización de gastos."""
    
    def test_materialize_gasto_from_dto(self):
        """Test: Materializar gasto desde DTO."""
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01T00:00:00Z",
            "emisor": {
                "nit": "900123456-7",
                "razon_social": "Proveedor Test"
            },
            "receptor": {
                "nit": "800987654-3",
                "razon_social": "Cliente Test"
            },
            "totales": {
                "total": "500.00"
            },
            "categoria": "Viaticos",
        }
        
        result, status_code = materializar_gasto_desde_dto(dto)
        
        assert status_code == 201
        assert "id" in result
        assert result["numero"] == "GAS001"
        assert result["created"] is True
    
    def test_materialize_gasto_missing_number(self):
        """Test: Error si falta número."""
        dto = {
            "type": "gasto",
            # Sin numero
            "fecha_emision": "2026-01-01T00:00:00Z",
            "totales": {"total": "500.00"},
        }
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            materializar_gasto_desde_dto(dto)
    
    def test_materialize_gasto_missing_required_fields(self):
        """Test: Error si faltan campos obligatorios."""
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            # Faltan campos obligatorios
        }
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            materializar_gasto_desde_dto(dto)
    
    def test_materialize_gasto_invalid_total(self):
        """Test: Error si total inválido."""
        dto = {
            "type": "gasto",
            "numero": "GAS001",
            "fecha_emision": "2026-01-01T00:00:00Z",
            "emisor": {"nit": "900123456-7", "razon_social": "Proveedor Test"},
            "receptor": {"nit": "800987654-3", "razon_social": "Cliente Test"},
            "totales": {"total": "invalid"},  # Total inválido
        }
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            materializar_gasto_desde_dto(dto)
