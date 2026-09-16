"""
GASTOS-01 (mision UI/UX, hallazgo cerrado): materializar_gasto_desde_dto()
corre sin supervision humana desde el pipeline de ingesta de correo
(document_router.py) y antes fabricaba silenciosamente una Empresa/
ResolucionDIAN falsa cuando el tenant aun no las tenia configuradas,
usandolas para crear un DocumentoSoporte real (dato fiscal legalmente
significativo). Ahora debe fallar explicito con ValidationError -- el
document_router ya distingue ese caso de un error inesperado (ver su
propio except ValidationError dedicado).
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context

from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.business_service import materializar_gasto_desde_dto


def _dto():
    return {
        "numero": "GASTOS01-TEST-001",
        "fecha_emision": "2026-06-01",
        "emisor": {"nit": "900333444", "razon_social": "Proveedor GASTOS-01 Test"},
        "totales": {"total": "150000.00"},
        "categoria": "OTROS_GASTOS",
    }


@pytest.mark.django_db
def test_sin_empresa_falla_explicito_y_no_fabrica_una(tenant1):
    with schema_context(tenant1.schema_name):
        Empresa.objects.all().delete()
        assert not Empresa.objects.exists()

        with pytest.raises(ValidationError):
            materializar_gasto_desde_dto(_dto())

        # No debe haber fabricado una Empresa placeholder para poder continuar.
        assert not Empresa.objects.exists()


@pytest.mark.django_db
def test_empresa_sin_resolucion_dian_vigente_falla_explicito_y_no_fabrica_una(tenant1):
    with schema_context(tenant1.schema_name):
        assert Empresa.objects.exists()  # sembrada por el fixture tenant1
        assert not ResolucionDIAN.objects.filter(vigente=True).exists()

        with pytest.raises(ValidationError):
            materializar_gasto_desde_dto(_dto())

        # No debe haber fabricado una Resolucion DIAN placeholder.
        assert not ResolucionDIAN.objects.exists()


@pytest.mark.django_db
def test_camino_feliz_con_empresa_y_resolucion_reales_sigue_funcionando(tenant1):
    """Regresion: el fix no rompe el camino feliz (tenant ya configurado)."""
    with schema_context(tenant1.schema_name):
        empresa = Empresa.objects.first()
        ResolucionDIAN.objects.create(
            empresa=empresa, numero_resolucion="GASTOS01-RES", prefijo="G01",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion="2026-01-01", fecha_inicio="2026-01-01", fecha_fin="2027-12-31",
            vigente=True,
        )

        resultado, status_code = materializar_gasto_desde_dto(_dto())

        assert status_code == 201
        assert resultado["created"] is True
        documento = DocumentoSoporte.objects.get(id=resultado["id"])
        assert documento.total == Decimal("150000.00")
