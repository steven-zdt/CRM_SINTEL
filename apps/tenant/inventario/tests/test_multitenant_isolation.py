"""
Aislamiento multi-tenant real (2 schemas) para Producto/CategoriaItem/ActivoFijo.

Gap real confirmado en FASE 49/50 (docs/inventario/INVENTARIO_BASELINE.md,
2026-08-27): F21 (Traslados) ya tenia un test de este tipo
(test_no_se_puede_trasladar_a_sede_de_otro_tenant), pero ningun otro modelo
del modulo lo tenia. Mismo patron: se crea el dato real en el schema de
tenant2 y se intenta referenciar desde tenant1 -- la fila es fisicamente
invisible desde ese schema (aislamiento real de django-tenants), no solo un
filtro de empresa_id que podria fallar por un bug de codigo.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import ActivoFijo, CategoriaItem, MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from apps.tenant.inventario.services.selectors import (
    ActivoFijoSelector,
    CategoriaItemSelector,
    ProductoSelector,
)


@pytest.mark.django_db
def test_producto_de_otro_tenant_no_admite_movimiento_kardex(tenant1, tenant2):
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        producto2 = Producto.objects.create(empresa=emp2, codigo="ISO-PROD", nombre="Producto Tenant2")
        producto2_id = producto2.id

    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        # El id de producto2 no existe (o pertenece a otra fila) en el schema
        # de tenant1 -- registrar_movimiento debe rechazarlo, nunca mutar
        # datos de otro tenant ni crashear con un IntegrityError crudo.
        with pytest.raises(ValidationError):
            KardexService.registrar_movimiento(
                empresa_id=emp1.id, producto_id=producto2_id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE, cantidad=Decimal("1"),
            )


@pytest.mark.django_db
def test_categoria_de_otro_tenant_no_aparece_en_get_list(tenant1, tenant2):
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        CategoriaItem.objects.create(empresa=emp2, nombre="Categoria Tenant2", aplicacion="TODO")

    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        CategoriaItem.objects.create(empresa=emp1, nombre="Categoria Tenant1", aplicacion="TODO")

        nombres = list(CategoriaItemSelector.get_list(empresa_id=emp1.id).values_list("nombre", flat=True))
        assert nombres == ["Categoria Tenant1"]


@pytest.mark.django_db
def test_activo_de_otro_tenant_no_es_accesible_por_detail(tenant1, tenant2):
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        activo2 = ActivoFijo.objects.create(
            empresa=emp2, codigo="ISO-ACT", nombre="Activo Tenant2",
            costo_adquisicion=Decimal("500.00"),
        )
        activo2_uuid = activo2.uuid

    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        with pytest.raises(ActivoFijo.DoesNotExist):
            ActivoFijoSelector.get_detail(empresa_id=emp1.id, activo_uuid=activo2_uuid)


@pytest.mark.django_db
def test_producto_de_otro_tenant_no_es_accesible_por_detail(tenant1, tenant2):
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        producto2 = Producto.objects.create(empresa=emp2, codigo="ISO-PROD-2", nombre="Producto Tenant2 B")
        producto2_uuid = producto2.uuid

    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        with pytest.raises(Producto.DoesNotExist):
            ProductoSelector.get_detail(empresa_id=emp1.id, producto_uuid=producto2_uuid)
