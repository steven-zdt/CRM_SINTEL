"""
FacturaSelectors — Consultas optimizadas (Zero Waste) para Facturas.

Responsabilidad única: Lectura y filtrado optimizado de datos.
No realiza mutaciones ni contiene lógica de negocio pesada.

Reglas SINTEL v3.5:
- Todos los métodos son @staticmethod.
- Uso estricto de .only() y select_related() para evitar N+1.
- SSoT para constantes de visualización (LIST_FIELDS, DETAIL_FIELDS).
"""

from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse

from apps.tenant.facturas.models import Factura, FacturaAnexos


# --- Campos optimizados para alineación Serializers ↔ UI ---
LIST_FIELDS = (
    "id",
    "uuid",
    "numero",
    "naturaleza",
    "estado",
    "estado_pago",
    "dian_validation_desc",
    "fecha_emision",
    "fecha_vencimiento",
    "moneda",
    "subtotal",
    "impuestos",
    "total",
    "forma_pago",
    "medio_pago_codigo",
    "payment_due_date",
    "emisor_nit",
    "emisor_razon_social",
    "receptor_nit",
    "receptor_razon_social",
    "cuenta_contable_uuid",
    "cufe",
    "qr_url",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "numero",
    "prefijo",
    "consecutivo",
    "tipo",
    "estado",
    "naturaleza",
    "categoria",
    "fecha_emision",
    "fecha_vencimiento",
    "emisor_nit",
    "emisor_razon_social",
    "emisor_direccion",
    "emisor_email",
    "receptor_nit",
    "receptor_razon_social",
    "receptor_direccion",
    "receptor_email",
    "moneda",
    "subtotal",
    "impuestos",
    "total",
    "forma_pago",
    "medio_pago_codigo",
    "payment_due_date",
    "cuenta_contable_uuid",
    "cufe",
    "qr_url",
    "created_at",
    "updated_at",
)

ANEXO_KEYS = {"ubl_xml", "application_response_xml"}
MAX_INLINE_BYTES = 2_000_000  # 2MB


class FacturaSelectors:
    """
    Selectores para la aplicación Facturas.
    """

    @staticmethod
    def qs_list(search: str | None = None):
        """
        QuerySet optimizado para listado (v3.5 Zero Waste).
        """
        qs = Factura.objects.select_related("nota_credito").only(*LIST_FIELDS)
        
        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(cufe__icontains=search) |
                Q(receptor_razon_social__icontains=search) |
                Q(emisor_razon_social__icontains=search)
            )
        
        return qs.order_by("-fecha_emision", "-id")

    @staticmethod
    def qs_detail():
        """
        QuerySet optimizado para detalle.
        """
        return Factura.objects.select_related("nota_credito", "anexos").only(*DETAIL_FIELDS)

    @staticmethod
    def qs_centros_costo():
        """
        QuerySet ligero para selección de centros de costo (v3.5 Zero Waste).
        Retorna los campos mínimos necesarios para el dropdown.
        """
        return Factura.objects.only("id", "numero", "receptor_razon_social").order_by("-fecha_emision", "-id")

    @staticmethod
    def get_summary(empresa_id: int | None = None) -> dict[str, Any]:
        """
        Calcula resumen neto de facturación (Facturas - Notas Crédito).
        
        # WARNING: v3.7.1: Se corrige lógica para incluir facturas con NC 
        y restar el total de la NC para obtener el valor neto real.
        """
        from apps.tenant.facturas.models import NotaCredito
        
        base_filter = Q()
        if empresa_id:
            base_filter &= Q(empresa_id=empresa_id)
        
        # 1. Agregación de Facturas (Bruto)
        ventas_f = Factura.objects.filter(base_filter, naturaleza=Factura.Naturaleza.VENTA).aggregate(
            sub=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            imp=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            tot=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
            qty=Count('id')
        )
        
        compras_f = Factura.objects.filter(base_filter, naturaleza=Factura.Naturaleza.COMPRA).aggregate(
            sub=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            imp=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            tot=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
            qty=Count('id')
        )

        # 2. Agregación de Notas Crédito (Reversiones)
        ventas_nc = NotaCredito.objects.filter(base_filter, factura__naturaleza=Factura.Naturaleza.VENTA).aggregate(
            sub=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            imp=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            tot=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00'))
        )
        
        compras_nc = NotaCredito.objects.filter(base_filter, factura__naturaleza=Factura.Naturaleza.COMPRA).aggregate(
            sub=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            imp=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            tot=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00'))
        )

        return {
            "ventas": {
                "subtotal_neto": ventas_f["sub"] - ventas_nc["sub"],
                "impuestos_neto": ventas_f["imp"] - ventas_nc["imp"],
                "total_neto": ventas_f["tot"] - ventas_nc["tot"],
                "cantidad": ventas_f["qty"]
            },
            "compras": {
                "subtotal_neto": compras_f["sub"] - compras_nc["sub"],
                "impuestos_neto": compras_f["imp"] - compras_nc["imp"],
                "total_neto": compras_f["tot"] - compras_nc["tot"],
                "cantidad": compras_f["qty"]
            }
        }


    @staticmethod
    def obtener_anexo_xml(factura: Factura, tipo: str) -> tuple[HttpResponse | dict[str, Any], int]:
        """
        Obtiene anexo XML de una factura.
        """
        try:
            anexos = FacturaAnexos.objects.get(factura=factura)
        except FacturaAnexos.DoesNotExist:
            return {"error": "no_anexos", "message": "No hay anexos disponibles."}, 204
        
        if tipo == "ubl":
            xml_content = anexos.ubl_xml
            filename = f"factura_{factura.numero}_ubl.xml"
        elif tipo == "app":
            xml_content = anexos.application_response_xml
            filename = f"factura_{factura.numero}_app_response.xml"
        else:
            return {"error": "invalid_type", "message": "Tipo inválido."}, 400
        
        if not xml_content:
            return {"error": "no_xml", "message": "No hay XML disponible."}, 204
        
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        
        if len(xml_bytes) > MAX_INLINE_BYTES:
            response = HttpResponse(xml_bytes, content_type="application/xml")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response, 200
        else:
            response = HttpResponse(xml_bytes, content_type="application/xml")
            response["X-Content-Type-Options"] = "nosniff"
            return response, 200
