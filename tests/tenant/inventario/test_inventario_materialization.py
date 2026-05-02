"""
Tests de materialización de inventario (FASE 9).

[WARNING] PRINCIPIOS:
- Materialización desde DTO
- Items incluidos
- Validación de cantidades
- Multi-tenant
"""
import pytest
from django_tenants.test.cases import TenantTestCase
from apps.tenant.inventario.services import materializar_inventario_desde_dto


import pytest
from django_tenants.test.cases import TenantTestCase
from apps.tenant.inventario.services import materializar_inventario_desde_dto
from apps.tenant.empresa.models import Empresa


class TestInventarioMaterialization(TenantTestCase):
    """Tests de materialización de inventario."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa singleton necesaria para materialización
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456-7",
            direccion="Calle 123",
            telefono="1234567"
        )
    
    def test_materialize_inventario_from_dto(self):
        """Test: Materializar un producto desde DTO."""
        dto = {
            "tipo": "producto",
            "codigo": "ITEM001",
            "nombre": "Producto 1",
            "precio_venta": "1500.00",
            "stock_actual": "10.00",
            "unidad": "UND"
        }
        
        result, status_code = materializar_inventario_desde_dto(dto)
        
        assert status_code == 201
        assert "id" in result
        assert result["codigo"] == "ITEM001"
        assert result["created"] is True
    
    def test_materialize_inventario_missing_fields(self):
        """Test: Error si faltan campos obligatorios."""
        dto = {
            "tipo": "producto",
            "codigo": "ITEM001",
            # falta nombre
        }
        
        result, status_code = materializar_inventario_desde_dto(dto)
        assert status_code == 422
        assert "error" in result
        assert "missing_required_fields" in result["error"]
    
    def test_materialize_inventario_invalid_type(self):
        """Test: Error si tipo inválido."""
        dto = {
            "tipo": "inexistente",
            "codigo": "ITEM001",
            "nombre": "Producto 1"
        }
        
        result, status_code = materializar_inventario_desde_dto(dto)
        assert status_code == 422
        assert "error" in result
        assert "invalid_type" in result["error"]
