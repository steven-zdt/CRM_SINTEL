"""
F24.11/F24.12: aislamiento multi-tenant real del circuito completo
(Compra+Venta+Contabilidad) y DSV ante manipulacion de UUIDs entre tenants.

2 schemas reales (tenant1/tenant2, mismo patron de F21/F22/F23). Empresa es
singleton por schema (F21), por lo que "otro tenant" se modela como un
schema fisico distinto, no como una segunda Empresa en el mismo schema.

VENTAS-COMPRAS-FACTURAS-01 (2026-09-09): `procesar_y_facturar_venta()`
rechaza por defecto (Fase 8). Las 2 funciones que llaman a Ventas mockean
el flag a True -- siguen probando el aislamiento DSV/multi-tenant real
del circuito Compra+Venta+Contabilidad, no el bloqueo de produccion.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenant.clientes.models import Cliente
from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import RecepcionCompraBusinessService
from apps.tenant.contabilidad.integracion.extractores.inventario import ExtractorInventario
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, ReglaContable
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.inventario.models import MovimientoInventario, Producto
from apps.tenant.inventario.services.business_service import KardexService
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.ventas.services.business_service import VentaBusinessService

_REGLAS_INVENTARIO = (
    ("COMPRA_INVENTARIO", "INVENTARIO_PRODUCTO", "143505"),
    ("COMPRA_INVENTARIO", "PASIVO_COMPRA_INVENTARIO", "220505"),
    ("SALIDA_INVENTARIO_VENTA", "COSTO_VENTA_PRODUCTO", "613501"),
    ("SALIDA_INVENTARIO_VENTA", "INVENTARIO_PRODUCTO", "143505"),
)


def _crear_perfil(empresa, sufijo):
    User = get_user_model()
    with schema_context(get_public_schema_name()):
        user = User.objects.create_user(
            username=f"f24-{sufijo}@sintel.test", email=f"f24-{sufijo}@sintel.test", password="testpass123",
        )
    return TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN", alcance="EMPRESA")


def _preparar_tenant(empresa, sufijo, stock="50"):
    sede = Sede.objects.create(empresa=empresa, nombre=f"Sede {sufijo}")
    cliente = Cliente.objects.create(
        empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
        numero_documento=f"F24-MT-{sufijo}", razon_social=f"Cliente MT F24 {sufijo}",
        regimen_tributario="ORDINARIO",
    )
    producto = Producto.objects.create(
        empresa=empresa, codigo=f"PROD-MT-F24-{sufijo}", nombre=f"Producto MT F24 {sufijo}",
        stock_actual=Decimal("0"), costo_promedio=Decimal("10.00"),
    )
    if Decimal(stock) > 0:
        KardexService.registrar_movimiento(
            empresa_id=empresa.id, producto_id=producto.id,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            cantidad=Decimal(stock), costo_unitario=Decimal("10.00"), sede_id=sede.id,
        )
    hoy = timezone.localdate()
    PeriodoContable.objects.get_or_create(
        empresa=empresa, periodo=hoy.strftime("%Y-%m"),
        defaults={"fecha_inicio": date(hoy.year, 1, 1), "fecha_fin": date(hoy.year, 12, 31), "estado": "ABIERTO"},
    )
    for tipo_tx, concepto, cuenta in _REGLAS_INVENTARIO:
        ReglaContable.objects.get_or_create(
            empresa=empresa, tipo_transaccion=tipo_tx, concepto=concepto,
            defaults={"cuenta_codigo": cuenta, "activo": True},
        )
    return sede, cliente, producto


@pytest.mark.django_db
@mock.patch("apps.tenant.ventas.services.business_service.EMISION_FISCAL_VENTA_AUTORIZADA", True)
def test_producto_uuid_de_otro_tenant_es_rechazado_limpiamente_en_venta(tenant1, tenant2):
    """
    F24.12 DSV: inyectar en el payload de una venta de tenant1 el UUID de un
    Producto que existe fisicamente solo en el schema de tenant2. Con
    django-tenants (aislamiento fisico por schema) el ORM de tenant1 no puede
    ver esa fila -- BusinessService debe rechazar limpiamente (ok=False, 404),
    nunca 200 con datos ajenos, nunca una excepcion no controlada.
    """
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        _sede2, _cliente2, producto_ajeno = _preparar_tenant(emp2, "T2-DSV")
        producto_ajeno_uuid = str(producto_ajeno.uuid)

    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        sede1, cliente1, _producto1 = _preparar_tenant(emp1, "T1-DSV")

        payload = {
            "cliente": str(cliente1.uuid), "fecha_emision": "2026-06-05",
            "items": [{
                "descripcion": "Venta con UUID ajeno", "cantidad": "1", "precio_unitario": "20.00",
                "porcentaje_iva": "19", "producto_id": producto_ajeno_uuid,
            }],
        }
        ok, resultado, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=emp1, payload=payload, sede_id=sede1.id,
        )
        assert not ok
        assert code in (400, 404, 422)
        # Nada debe haberse creado en tenant1 a partir de un UUID que no le pertenece.
        assert MovimientoInventario.objects.filter(empresa=emp1).exclude(
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        ).count() == 0


@pytest.mark.django_db
@mock.patch("apps.tenant.ventas.services.business_service.EMISION_FISCAL_VENTA_AUTORIZADA", True)
def test_flujo_completo_compra_venta_asiento_independiente_por_tenant(tenant1, tenant2):
    """
    F24.11: el circuito completo (Compra->Movimiento->Kardex->Venta->
    SALIDA_VENTA->Extractor->Asiento) corrido en 2 tenants reales no debe
    dejar rastro cruzado -- ni en stock, ni en movimientos, ni en asientos.
    """
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        sede1, cliente1, producto1 = _preparar_tenant(emp1, "T1-E2E", stock="0")
        proveedor1 = Proveedor.objects.create(
            empresa=emp1, razon_social="Proveedor T1", numero_documento="T1-PROV", tipo_documento="NIT",
        )
        plantilla1 = PlantillaOrdenCompra.objects.create(
            empresa=emp1, nombre="Plantilla T1", prefijo="T1",
            rango_desde=1, rango_hasta=1000, consecutivo_actual=1, vigente=True,
        )
        orden1 = OrdenCompra.objects.create(
            empresa=emp1, sede=sede1, proveedor=proveedor1, plantilla=plantilla1,
            fecha="2026-06-01", consecutivo=1, numero_documento="T1-OC-1", estado="APROBADA",
        )
        item_oc1 = ItemOrdenCompra.objects.create(
            empresa=emp1, orden_compra=orden1, descripcion="Compra T1",
            item_inventario_uuid=producto1.uuid, cantidad=Decimal("20"), valor_unitario=Decimal("10.00"),
            subtotal=Decimal("200.00"), total=Decimal("200.00"),
        )
        perfil1 = _crear_perfil(emp1, "T1-E2E")
        ok, recepcion1, code = RecepcionCompraBusinessService.crear_recepcion(
            {"orden_compra": orden1, "fecha": "2026-06-02"},
            [{"item_orden_compra": item_oc1, "cantidad_recibida": Decimal("20")}],
            emp1, sede1, perfil1,
        )
        assert ok, recepcion1
        ok, recepcion1, code = RecepcionCompraBusinessService.confirmar_recepcion(recepcion1.uuid, emp1.id)
        assert ok, recepcion1

        payload1 = {
            "cliente": str(cliente1.uuid), "fecha_emision": "2026-06-05",
            "items": [{
                "descripcion": "Venta T1", "cantidad": "5", "precio_unitario": "20.00",
                "porcentaje_iva": "19", "producto_id": str(producto1.uuid),
            }],
        }
        ok, venta1, code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=emp1, payload=payload1, sede_id=sede1.id,
        )
        assert ok, venta1

        resultado1 = ExtractorInventario(empresa_id=emp1.id).contabilizar_pendientes()
        assert resultado1["contabilizados"] == 2  # ENTRADA_COMPRA + SALIDA_VENTA
        assert resultado1["errores"] == []
        asientos_t1 = AsientoContable.objects.filter(empresa=emp1).count()
        assert asientos_t1 == 2

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        # tenant2 nunca ejecuto ninguna operacion -- debe seguir completamente vacio.
        assert Producto.objects.filter(codigo="PROD-MT-F24-T1-E2E").count() == 0
        assert MovimientoInventario.objects.filter(empresa=emp2).count() == 0
        assert AsientoContable.objects.filter(empresa=emp2).count() == 0
