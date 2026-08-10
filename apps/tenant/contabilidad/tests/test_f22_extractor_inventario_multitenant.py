"""
F22.14: aislamiento multi-tenant real del ExtractorInventario (2 schemas,
fixtures tenant1/tenant2 -- mismo patron ya establecido en
test_multitenant_isolation_tabla_html.py y en F21). Empresa es un singleton
por schema (ver F21_TEST_MATRIX.md), asi que "Empresa A / Empresa B" solo
puede modelarse como 2 tenants reales, no 2 filas de Empresa en un schema.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService


def _preparar_tenant(empresa, cantidad, costo_unitario):
    # Ver nota identica en test_f22_extractor_inventario_integration.py:
    # created_at es timezone.now() real, el periodo debe cubrir la fecha real.
    hoy = timezone.localdate()
    PeriodoContable.objects.create(
        empresa=empresa, periodo=hoy.strftime('%Y-%m'),
        fecha_inicio=date(hoy.year, 1, 1), fecha_fin=date(hoy.year, 12, 31), estado="ABIERTO",
    )
    ReglaContable.objects.create(
        empresa=empresa, tipo_transaccion="AJUSTE_INVENTARIO", concepto="INVENTARIO_PRODUCTO",
        cuenta_codigo="143505", activo=True,
    )
    ReglaContable.objects.create(
        empresa=empresa, tipo_transaccion="AJUSTE_INVENTARIO", concepto="INGRESO_AJUSTE_INVENTARIO",
        cuenta_codigo="425050", activo=True,
    )
    producto = Producto.objects.create(
        empresa=empresa, codigo="PROD-MT-F22", nombre="Producto Multitenant F22", stock_actual=Decimal("0"),
    )
    movimiento = KardexService.registrar_movimiento(
        empresa_id=empresa.id, producto_id=producto.id,
        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        cantidad=Decimal(cantidad), costo_unitario=Decimal(costo_unitario),
    )
    return producto, movimiento


@pytest.mark.django_db
def test_extractor_de_un_tenant_no_extrae_movimientos_de_otro_tenant(tenant1, tenant2):
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        _, mov1 = _preparar_tenant(emp1, "10", "5.00")
        empresa1_id = emp1.id

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        _, mov2 = _preparar_tenant(emp2, "99", "1.00")
        empresa2_id = emp2.id

    with schema_context(tenant1.schema_name):
        extractor1 = ExtractorInventario(empresa_id=empresa1_id)
        pendientes1 = extractor1.extraer_pendientes()
        ids_extraidos1 = {dto.documento_origen.id for dto in pendientes1}

        # Solo puede ver el movimiento de su propio schema (tenant2 ni siquiera
        # existe en la tabla de este schema) -- ademas de empresa_id, el
        # aislamiento real lo da el propio schema de PostgreSQL.
        assert ids_extraidos1 == {mov1.id}

        resultado1 = extractor1.contabilizar_pendientes()
        assert resultado1['contabilizados'] == 1
        assert AsientoContable.objects.filter(empresa_id=empresa1_id).count() == 1

    with schema_context(tenant2.schema_name):
        extractor2 = ExtractorInventario(empresa_id=empresa2_id)
        pendientes2 = extractor2.extraer_pendientes()
        ids_extraidos2 = {dto.documento_origen.id for dto in pendientes2}

        assert ids_extraidos2 == {mov2.id}
        # El asiento creado en tenant1 no existe en absoluto en el schema de tenant2.
        assert AsientoContable.objects.count() == 0
