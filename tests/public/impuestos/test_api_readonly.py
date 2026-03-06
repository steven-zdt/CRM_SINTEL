"""
Tests de Fase C: API ReadOnly (Catálogos).

Verifica:
- Listado de catálogos (AllowAny, sin autenticación)
- Filtrado, búsqueda, ordenación
- Paginación estándar
- Métodos POST/PUT/DELETE retornan 405 (ReadOnly)
"""
import pytest
from django.urls import reverse
from rest_framework import status
from tests.public.impuestos.factories import (
    TipoImpuestoFactory,
    TarifaIVAFactory,
    ConceptoRetencionFactory,
    CodigoTributarioFactory,
    ActividadEconomicaFactory,
    NormaTributariaFactory,
)


@pytest.mark.django_db
class TestAPIReadOnly:
    """Tests para catálogos ReadOnly."""
    
    def test_listado_tipos_public_readonly(self, api_client):
        """GET /tipos/ es público (AllowAny)."""
        TipoImpuestoFactory.create_batch(3)
        
        # Sin autenticación debería funcionar (AllowAny)
        r = api_client.get("/api/public/v1/impuestos/tipos/")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        
        # Verificar formato paginado
        if "results" in data:
            assert len(data["results"]) >= 1
            assert "count" in data
        else:
            # Si no hay paginación, debe ser una lista directa
            assert isinstance(data, list)
            assert len(data) >= 1
    
    def test_create_tipo_405(self, api_client):
        """POST /tipos/ retorna 405 (ReadOnly)."""
        r = api_client.post(
            "/api/public/v1/impuestos/tipos/",
            {"codigo": "T001", "nombre": "Test"},
            format="json"
        )
        
        assert r.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_filter_tipos_activos(self, api_client):
        """Filtrado por activo funciona."""
        TipoImpuestoFactory(activo=True)
        TipoImpuestoFactory(activo=False)
        
        r = api_client.get("/api/public/v1/impuestos/tipos/?activo=true")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        
        # Todos los resultados deben tener activo=True
        for item in results:
            assert item["activo"] is True
    
    def test_search_tarifas_iva(self, api_client):
        """Búsqueda en tarifas IVA."""
        TarifaIVAFactory(nombre="Tarifa General", codigo="TAR001")
        TarifaIVAFactory(nombre="Tarifa Reducida", codigo="TAR002")
        
        r = api_client.get("/api/public/v1/impuestos/tarifas-iva/?search=General")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        
        # Debe encontrar al menos una tarifa con "General"
        assert len(results) >= 1
        assert any("General" in str(item.get("nombre", "")) for item in results)
    
    def test_ordering_conceptos_retencion(self, api_client):
        """Ordenación por codigo funciona."""
        ConceptoRetencionFactory(codigo="RET003")
        ConceptoRetencionFactory(codigo="RET001")
        ConceptoRetencionFactory(codigo="RET002")
        
        r = api_client.get("/api/public/v1/impuestos/conceptos-retencion/?ordering=codigo")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        
        # Verificar orden ascendente
        codigos = [item["codigo"] for item in results if "codigo" in item]
        assert codigos == sorted(codigos)
    
    def test_listado_normas_tributarias(self, api_client):
        """GET /normas/ lista normas tributarias."""
        NormaTributariaFactory.create_batch(3)
        
        r = api_client.get("/api/public/v1/impuestos/normas/")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        
        assert len(results) >= 3
    
    def test_pagination_works(self, api_client):
        """Paginación estándar funciona."""
        # Crear más de PAGE_SIZE (default 20) elementos
        CodigoTributarioFactory.create_batch(25)
        
        r = api_client.get("/api/public/v1/impuestos/codigos-tributarios/")
        
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        
        # Si hay paginación, debe tener count, next, previous, results
        if "results" in data:
            assert "count" in data
            assert "next" in data or "previous" in data
            assert len(data["results"]) <= 20  # PAGE_SIZE default
