"""
Tests funcionales para CRUD de TipoImpuesto vía API.

Valida crear, editar, listar y borrar tipos de impuesto
usando los endpoints CRUD.
"""
import pytest
from django.urls import reverse
from apps.public.impuestos.models import TipoImpuesto


@pytest.mark.django_db
class TestCRUDTipos:
    """Tests para CRUD de TipoImpuesto."""
    
    def test_crear_tipo_via_api(self, authenticated_client):
        """Crea un tipo de impuesto vía API CRUD."""
        url = reverse("tipo-impuesto-crud-list")
        payload = {
            "codigo": "IVA",
            "nombre": "Impuesto al Valor Agregado",
            "descripcion": "Impuesto sobre consumo",
            "activo": True,
            "fecha_vigencia": "2024-01-01"
        }
        response = authenticated_client.post(url, data=payload, format="json")
        assert response.status_code in (201, 200), response.data
        assert TipoImpuesto.objects.filter(codigo="IVA").exists()
        
        # Verificar que los datos se guardaron correctamente
        tipo = TipoImpuesto.objects.get(codigo="IVA")
        assert tipo.nombre == "Impuesto al Valor Agregado"
        assert tipo.activo is True
    
    def test_editar_tipo_via_api(self, authenticated_client):
        """Edita un tipo de impuesto vía API CRUD."""
        # Crear tipo inicial
        tipo = TipoImpuesto.objects.create(
            codigo="RET",
            nombre="Retención",
            activo=True
        )
        
        # Editar vía API
        url = reverse("tipo-impuesto-crud-detail", args=[tipo.id])
        payload = {
            "nombre": "Retención en la fuente",
            "descripcion": "Nueva descripción"
        }
        response = authenticated_client.patch(url, data=payload, format="json")
        assert response.status_code in (200, 202), response.data
        
        # Verificar cambios
        tipo.refresh_from_db()
        assert tipo.nombre == "Retención en la fuente"
        assert tipo.descripcion == "Nueva descripción"
    
    def test_listar_tipos_via_api(self, authenticated_client):
        """Lista tipos de impuesto vía API CRUD."""
        # Crear datos de prueba
        TipoImpuesto.objects.bulk_create([
            TipoImpuesto(codigo="IVA", nombre="IVA"),
            TipoImpuesto(codigo="RET", nombre="Retención"),
            TipoImpuesto(codigo="ICA", nombre="Industria y Comercio"),
        ])
        
        url = reverse("tipo-impuesto-crud-list")
        response = authenticated_client.get(url)
        assert response.status_code == 200
        
        data = response.json()
        # Verificar formato de respuesta (puede ser paginada o no)
        assert isinstance(data, (dict, list))
        if isinstance(data, dict):
            # Respuesta paginada
            assert "results" in data or "data" in data
        else:
            # Respuesta lista
            assert len(data) >= 3
    
    def test_obtener_detalle_tipo_via_api(self, authenticated_client):
        """Obtiene el detalle de un tipo de impuesto vía API CRUD."""
        tipo = TipoImpuesto.objects.create(
            codigo="CREE",
            nombre="CREE",
            descripcion="Impuesto de renta para la equidad"
        )
        
        url = reverse("tipo-impuesto-crud-detail", args=[tipo.id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        
        data = response.json()
        assert data["codigo"] == "CREE"
        assert data["nombre"] == "CREE"
    
    def test_borrar_tipo_via_api(self, authenticated_client):
        """Borra un tipo de impuesto vía API CRUD."""
        tipo = TipoImpuesto.objects.create(
            codigo="ICA",
            nombre="Industria y Comercio"
        )
        tipo_id = tipo.id
        
        url = reverse("tipo-impuesto-crud-detail", args=[tipo.id])
        response = authenticated_client.delete(url)
        assert response.status_code in (204, 200, 202), response.data
        
        # Verificar que fue eliminado
        assert not TipoImpuesto.objects.filter(id=tipo_id).exists()
    
    def test_crear_tipo_requiere_autenticacion(self, api_client):
        """Verifica que crear tipo requiere autenticación."""
        url = reverse("tipo-impuesto-crud-list")
        payload = {"codigo": "TEST", "nombre": "Test"}
        response = api_client.post(url, data=payload, format="json")
        assert response.status_code == 401 or response.status_code == 403
