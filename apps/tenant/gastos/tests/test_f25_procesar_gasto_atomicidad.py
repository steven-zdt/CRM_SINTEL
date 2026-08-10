"""
F25: mismo patron de atomicidad que F23 (ventas) y F24 (compras) encontrado en
GastoBusinessService.procesar_gasto() -- decorado @transaction.atomic, crea el
DocumentoSoporte y luego un loop de RetencionesService.crear_retencion() (escrituras
crudas, sin savepoint propio: crear_retencion() no esta decorado @transaction.atomic).
Si la retencion N falla despues de que la retencion N-1 ya se creo, el except
capturaba la excepcion y retornaba (False, ..., 500) sin volver a lanzarla y sin
transaction.set_rollback(True) -- Django confirmaba el DocumentoSoporte y la
retencion parcial pese a reportar error.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django_tenants.utils import schema_context

from apps.tenant.contabilidad.models import ConfiguracionRetenciones, Retencion
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.business_service import GastoBusinessService
from apps.tenant.proveedores.models import Proveedor


def _preparar(emp):
    res = ResolucionDIAN.objects.create(
        empresa=emp, numero_resolucion="F25-001", prefijo="F25",
        rango_desde=1, rango_hasta=1000,
        fecha_resolucion="2026-01-01", fecha_inicio="2026-01-01", fecha_fin="2027-12-31",
        vigente=True,
    )
    prov = Proveedor.objects.create(
        empresa=emp, razon_social="Proveedor F25", numero_documento="900111222", tipo_documento="NIT",
    )
    ConfiguracionRetenciones.objects.create(
        empresa=emp, tipo_tercero="PROVEEDOR", nit_tercero="900111222",
        tipo_retencion="RETEFUENTE", porcentaje_por_defecto=Decimal("4.00"),
        naturaleza="COMPRA", activa=True,
    )
    ConfiguracionRetenciones.objects.create(
        empresa=emp, tipo_tercero="PROVEEDOR", nit_tercero="900111222",
        tipo_retencion="RETEICA", porcentaje_por_defecto=Decimal("0.69"),
        naturaleza="COMPRA", activa=True,
    )
    return res, prov


def _payload(res, prov):
    return {
        "documento_soporte": {
            "resolucion": res.id, "fecha": "2026-06-01", "proveedor": prov.id,
            "numero_documento_proveedor": "FAC-F25", "subtotal": 100000.00, "total": 95310.00,
        },
        "descripcion": "Gasto F25 atomicidad",
    }


@pytest.mark.django_db
def test_fallo_en_segunda_retencion_revierte_documento_y_primera_retencion(tenant1):
    with schema_context(tenant1.schema_name):
        emp = Empresa.objects.first()
        res, prov = _preparar(emp)
        data = _payload(res, prov)

        original = RetencionesService.crear_retencion
        estado = {"n": 0}

        def _side_effect(*args, **kwargs):
            estado["n"] += 1
            if estado["n"] == 2:
                raise ValueError("Fallo simulado en la segunda retencion (F25)")
            return original(*args, **kwargs)

        documentos_antes = DocumentoSoporte.objects.count()
        retenciones_antes = Retencion.objects.count()

        with patch.object(RetencionesService, "crear_retencion", side_effect=_side_effect):
            ok, resultado, code = GastoBusinessService.procesar_gasto(emp, data)

        assert not ok, resultado
        assert code == 500

        # Rollback atomico completo: ni el DocumentoSoporte, ni la primera
        # retencion (RETEFUENTE, ya creada exitosamente antes del fallo en la
        # segunda) deben quedar persistidos.
        assert DocumentoSoporte.objects.count() == documentos_antes
        assert Retencion.objects.count() == retenciones_antes


@pytest.mark.django_db
def test_camino_feliz_sin_fallo_sigue_creando_documento_y_ambas_retenciones(tenant1):
    """Regresion: el camino feliz (sin fallo inyectado) no se ve afectado por el fix."""
    with schema_context(tenant1.schema_name):
        emp = Empresa.objects.first()
        res, prov = _preparar(emp)
        data = _payload(res, prov)

        ok, documento, code = GastoBusinessService.procesar_gasto(emp, data)
        assert ok, documento
        assert code == 201
        assert Retencion.objects.filter(
            documento_origen_app="gastos", documento_origen_modelo="DocumentoSoporte",
            documento_origen_id=documento.id,
        ).count() == 2
