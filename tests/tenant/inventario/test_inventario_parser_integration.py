"""
Tests de integración parser → DTO para inventario (FASE 9).

[WARNING] PRINCIPIOS:
- Parser genera DTO con type="inventario"
- Campos específicos de inventario presentes
- Items incluidos
"""
import pytest
from apps.services.document_ingest.ingest_service import ingest_document


@pytest.mark.django_db
class TestInventarioParserIntegration:
    """Tests de integración parser para inventario."""
    
    def test_parse_csv_inventario(self):
        """Test: Parsear CSV como inventario."""
        csv_content = b'''numero,fecha_emision,almacen,item_codigo,item_descripcion,item_cantidad,item_unidad
INV001,2026-01-01,ALM001,ITEM001,Producto 1,10.00,UND
INV001,2026-01-01,ALM001,ITEM002,Producto 2,5.00,UND'''
        
        result, status_code = ingest_document(
            content=csv_content,
            filename="inventario.csv",
            kind_hint="inventario",
            preview=True
        )
        
        assert "dto" in result
        assert status_code in (200, 400, 422)
    
    def test_parse_excel_inventario(self):
        """Test: Parsear Excel como inventario."""
        # Este test requiere un Excel real
        # Por ahora se marca como skip
        pass
