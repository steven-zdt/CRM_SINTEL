"""
Tests de materialización de inventario (FASE 9).

⚠️ PRINCIPIOS:
- Materialización desde DTO
- Items incluidos
- Validación de cantidades
- Multi-tenant
"""
import pytest
from django_tenants.test.cases import TenantTestCase
from apps.tenant.inventario.services import materializar_inventario_desde_dto


class TestInventarioMaterialization(TenantTestCase):
    """Tests de materialización de inventario."""
    
    def test_materialize_inventario_from_dto(self):
        """Test: Materializar inventario desde DTO."""
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01T00:00:00Z",
            "emisor": {
                "nit": "900123456-7",
                "razon_social": "Empresa Test"
            },
            "receptor": {
                "nit": "800987654-3",
                "razon_social": "Cliente Test"
            },
            "totales": {"total": "0.00"},
            "almacen": "ALM001",
            "items": [
                {
                    "codigo": "ITEM001",
                    "descripcion": "Producto 1",
                    "cantidad": "10.00",
                    "unidad": "UND"
                }
            ],
        }
        
        result, status_code = materializar_inventario_desde_dto(dto)
        
        assert status_code == 201
        assert "id" in result
        assert result["numero"] == "INV001"
        assert result["created"] is True
    
    def test_materialize_inventario_no_items(self):
        """Test: Error si no hay items."""
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01T00:00:00Z",
            "almacen": "ALM001",
            "items": [],  # Sin items
        }
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            materializar_inventario_desde_dto(dto)
    
    def test_materialize_inventario_invalid_quantity(self):
        """Test: Error si cantidad inválida."""
        dto = {
            "type": "inventario",
            "numero": "INV001",
            "fecha_emision": "2026-01-01T00:00:00Z",
            "almacen": "ALM001",
            "items": [
                {
                    "codigo": "ITEM001",
                    "descripcion": "Producto 1",
                    "cantidad": "0.00",  # Cantidad inválida
                    "unidad": "UND"
                }
            ],
        }
        
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            materializar_inventario_desde_dto(dto)
