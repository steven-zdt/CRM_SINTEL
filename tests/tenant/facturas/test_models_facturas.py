"""
Unit tests para modelos de Facturas (versión renombrada para evitar colisión).
"""
import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.utils import timezone
from apps.tenant.facturas.models import Factura


@pytest.mark.django_db
class TestFacturaModels:
    """
    Tests unitarios para el modelo Factura.
    """
    def test_factura_auto_total(self):
        f = Factura.objects.create(
            numero="TST001",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=timezone.now(),
            emisor_nit="900000001",
            emisor_razon_social="EMISOR",
            receptor_nit="900000002",
            receptor_razon_social="RECEPTOR",
            moneda="COP",
            subtotal=Decimal("100.00"),
            impuestos=Decimal("19.00"),
            total=Decimal("0.00"),
        )
        f.refresh_from_db()
        assert f.total == Decimal("119.00")

    def test_factura_numero_unico(self):
        Factura.objects.create(
            numero="UNICO1",
            consecutivo=2,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ACEPTADA,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=timezone.now(),
            emisor_nit="900000001",
            emisor_razon_social="EMISOR",
            receptor_nit="900000002",
            receptor_razon_social="RECEPTOR",
            moneda="COP",
            subtotal=Decimal("0.00"),
            impuestos=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        with pytest.raises(IntegrityError):
            Factura.objects.create(
                numero="UNICO1",
                consecutivo=3,
                tipo=Factura.TipoFactura.FE,
                estado=Factura.Estado.ACEPTADA,
                naturaleza=Factura.Naturaleza.VENTA,
                fecha_emision=timezone.now(),
                emisor_nit="900000001",
                emisor_razon_social="EMISOR",
                receptor_nit="900000002",
                receptor_razon_social="RECEPTOR",
                moneda="COP",
                subtotal=Decimal("10.00"),
                impuestos=Decimal("0.00"),
                total=Decimal("10.00"),
            )

    def test_factura_campos_requeridos(self):
        f = Factura.objects.create(
            numero="MIN001",
            consecutivo=1,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=timezone.now(),
            emisor_nit="900000001",
            emisor_razon_social="EMISOR",
            receptor_nit="900000002",
            receptor_razon_social="RECEPTOR",
            moneda="COP",
            subtotal=Decimal("0.00"),
            impuestos=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        assert f.numero == "MIN001"
        assert f.emisor_nit == "900000001"
        assert f.receptor_nit == "900000002"
        assert f.moneda == "COP"
