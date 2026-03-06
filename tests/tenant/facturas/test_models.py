"""
Unit tests para modelos de Facturas.

Verifica:
- Cálculo automático de totales
- Restricciones de unicidad
- Validaciones de campos
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
        """
        Verifica que el total se calcula automáticamente como subtotal + impuestos.
        """
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
            total=Decimal("0.00"),  # Se debe calcular automáticamente en save()
        )
        # El método save() calcula total = subtotal + impuestos
        f.refresh_from_db()
        assert f.total == Decimal("119.00"), f"Total esperado 119.00, obtenido {f.total}"
    
    def test_factura_numero_unico(self):
        """
        Verifica que el campo 'numero' es único (restricción de base de datos).
        """
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
        
        # Intentar crear otra factura con el mismo número debe fallar
        with pytest.raises(IntegrityError):
            Factura.objects.create(
                numero="UNICO1",  # Duplicado
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
        """
        Verifica que los campos requeridos están presentes.
        """
        # Crear factura mínima válida
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
