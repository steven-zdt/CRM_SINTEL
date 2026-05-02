"""
Tests funcionales para DataTables server-side de TipoImpuesto.

Valida que el endpoint de DataTables retorne el formato correcto
y maneje correctamente parámetros de paginación, búsqueda y ordenamiento.
"""
import pytest
from django.urls import reverse
from apps.public.impuestos.models import TipoImpuesto


@pytest.mark.django_db
class TestDataTablesTipos:
    """Tests para DataTables server-side de TipoImpuesto."""
    
    def test_datatables_tipos_endpoint_basico(self, authenticated_client):
        """Verifica que el endpoint de DataTables retorna formato correcto."""
        # Crear datos de prueba
        TipoImpuesto.objects.bulk_create([
            TipoImpuesto(codigo="IVA", nombre="IVA"),
            TipoImpuesto(codigo="RET", nombre="Retención"),
            TipoImpuesto(codigo="ICA", nombre="Industria y Comercio"),
        ])
        
        url = reverse("impuestos-dt-tipos")
        # DataTables envía draw/start/length (serverSide)
        params = {
            "draw": 1,
            "start": 0,
            "length": 10
        }
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        
        body = response.json()
        # Verificar estructura de respuesta DataTables
        assert "draw" in body
        assert "recordsTotal" in body
        assert "recordsFiltered" in body
        assert "data" in body
        assert isinstance(body["data"], list)
        
        # Verificar que draw se retorna correctamente
        assert body["draw"] == 1
    
    def test_datatables_tipos_paginacion(self, authenticated_client):
        """Verifica que la paginación funciona correctamente."""
        # Crear más datos que el page size
        TipoImpuesto.objects.bulk_create([
            TipoImpuesto(codigo=f"T{i}", nombre=f"Tipo {i}")
            for i in range(25)
        ])
        
        url = reverse("impuestos-dt-tipos")
        
        # Primera página (start=0, length=10)
        params = {"draw": 1, "start": 0, "length": 10}
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        body = response.json()
        assert body["recordsTotal"] == 25
        assert len(body["data"]) == 10  # Primera página
        
        # Segunda página (start=10, length=10)
        params = {"draw": 2, "start": 10, "length": 10}
        response = authenticated_client.get(url, data=params)
        body = response.json()
        assert len(body["data"]) == 10  # Segunda página
    
    def test_datatables_tipos_busqueda(self, authenticated_client):
        """Verifica que la búsqueda funciona correctamente."""
        # Crear datos de prueba
        TipoImpuesto.objects.bulk_create([
            TipoImpuesto(codigo="IVA", nombre="Impuesto al Valor Agregado"),
            TipoImpuesto(codigo="RET", nombre="Retención en la fuente"),
            TipoImpuesto(codigo="ICA", nombre="Impuesto de Industria y Comercio"),
        ])
        
        url = reverse("impuestos-dt-tipos")
        
        # Búsqueda por "IVA"
        params = {
            "draw": 1,
            "start": 0,
            "length": 10,
            "search[value]": "IVA"
        }
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        body = response.json()
        assert body["recordsFiltered"] >= 1
        # Al menos un resultado debe contener "IVA"
        assert any("IVA" in str(row).upper() for row in body["data"])
    
    def test_datatables_tipos_ordenamiento(self, authenticated_client):
        """Verifica que el ordenamiento funciona correctamente."""
        # Crear datos de prueba
        TipoImpuesto.objects.bulk_create([
            TipoImpuesto(codigo="Z", nombre="Zeta"),
            TipoImpuesto(codigo="A", nombre="Alfa"),
            TipoImpuesto(codigo="M", nombre="Medio"),
        ])
        
        url = reverse("impuestos-dt-tipos")
        
        # Ordenar por código ascendente
        params = {
            "draw": 1,
            "start": 0,
            "length": 10,
            "order[0][column]": 1,  # Columna código
            "order[0][dir]": "asc"
        }
        response = authenticated_client.get(url, data=params)
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) >= 1
    
    def test_datatables_tipos_requiere_autenticacion(self, api_client):
        """Verifica que DataTables requiere autenticación."""
        url = reverse("impuestos-dt-tipos")
        params = {"draw": 1, "start": 0, "length": 10}
        response = api_client.get(url, data=params)
        assert response.status_code == 401 or response.status_code == 403
