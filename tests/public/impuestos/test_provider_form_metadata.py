"""
Pruebas de humo para el provider de form-metadata.
"""
import pytest
from apps.public.impuestos.services import provider


@pytest.mark.django_db
def test_provider_form_metadata_smoke():
    """
    Verifica que get_empresa_form_metadata retorna estructura válida.
    """
    meta = provider.get_empresa_form_metadata()
    
    assert isinstance(meta, dict)
    
    # Verificar estructura esperada
    assert "tipo_contribuyente" in meta
    assert "regimenes_renta" in meta
    assert "responsabilidades_rut" in meta
    assert "tipos_impuesto" in meta
    assert "tarifas_iva" in meta
    
    # Verificar tipo_contribuyente
    assert isinstance(meta["tipo_contribuyente"], dict)
    assert "clases" in meta["tipo_contribuyente"]
    assert "segmentos" in meta["tipo_contribuyente"]
    assert isinstance(meta["tipo_contribuyente"]["clases"], list)
    assert isinstance(meta["tipo_contribuyente"]["segmentos"], dict)
    
    # Verificar que las listas contienen dicts con estructura esperada
    if meta["tipo_contribuyente"]["clases"]:
        assert "codigo" in meta["tipo_contribuyente"]["clases"][0]
        assert "nombre" in meta["tipo_contribuyente"]["clases"][0]
    
    assert isinstance(meta["regimenes_renta"], list)
    if meta["regimenes_renta"]:
        assert "codigo" in meta["regimenes_renta"][0]
        assert "nombre" in meta["regimenes_renta"][0]
    
    assert isinstance(meta["responsabilidades_rut"], list)
    if meta["responsabilidades_rut"]:
        assert "codigo" in meta["responsabilidades_rut"][0]
        assert "nombre" in meta["responsabilidades_rut"][0]
    
    assert isinstance(meta["tipos_impuesto"], list)
    if meta["tipos_impuesto"]:
        assert "codigo" in meta["tipos_impuesto"][0]
        assert "nombre" in meta["tipos_impuesto"][0]
    
    assert isinstance(meta["tarifas_iva"], list)
    if meta["tarifas_iva"]:
        assert "codigo" in meta["tarifas_iva"][0]
        assert "nombre" in meta["tarifas_iva"][0]
        assert "porcentaje" in meta["tarifas_iva"][0]


@pytest.mark.django_db
def test_provider_lookup_ciiu_smoke():
    """
    Verifica que search_actividades_economicas retorna estructura válida.
    """
    results = provider.search_actividades_economicas(q="SERV", limit=5)
    
    assert isinstance(results, list)
    assert len(results) <= 5
    
    if results:
        # Verificar estructura: codigo y nombre (no value/label)
        assert "codigo" in results[0]
        assert "nombre" in results[0]
        assert isinstance(results[0]["codigo"], str)
        assert isinstance(results[0]["nombre"], str)


@pytest.mark.django_db
def test_provider_lookup_ciiu_empty():
    """
    Verifica que search_actividades_economicas retorna lista vacía para queries cortas.
    """
    results = provider.search_actividades_economicas(q="A", limit=5)
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.django_db
def test_provider_lookup_ciiu_no_results():
    """
    Verifica que search_actividades_economicas retorna lista vacía si no hay resultados.
    """
    results = provider.search_actividades_economicas(q="ZZZZZZZZZZ", limit=5)
    assert isinstance(results, list)
    assert len(results) == 0
