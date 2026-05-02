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
    "numero",
    "naturaleza",
    "estado",
    "fecha_emision",
    "fecha_vencimiento",
    "moneda",
    "subtotal",
    "impuestos",
    "total",
    "emisor_nit",
    "emisor_razon_social",
    "receptor_nit",
    "receptor_razon_social",
    "cufe",
    "qr_url",
)

DETAIL_FIELDS = (
    "id",
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
    def get_summary(empresa_id: int | None = None) -> dict[str, Any]:
        """
        Calcula resumen neto de facturación.
        """
        base_filter = Q(nota_credito__isnull=True)
        if empresa_id:
            base_filter &= Q(empresa_id=empresa_id)
        
        ventas_qs = Factura.objects.filter(
            base_filter,
            naturaleza=Factura.Naturaleza.VENTA
        ).aggregate(
            subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
            cantidad=Count('id')
        )
        
        compras_qs = Factura.objects.filter(
            base_filter,
            naturaleza=Factura.Naturaleza.COMPRA
        ).aggregate(
            subtotal_neto=Coalesce(Sum('subtotal', output_field=DecimalField()), Decimal('0.00')),
            impuestos_neto=Coalesce(Sum('impuestos', output_field=DecimalField()), Decimal('0.00')),
            total_neto=Coalesce(Sum('total', output_field=DecimalField()), Decimal('0.00')),
            cantidad=Count('id')
        )
        
        return {
            "ventas": {
                "subtotal_neto": ventas_qs["subtotal_neto"],
                "impuestos_neto": ventas_qs["impuestos_neto"],
                "total_neto": ventas_qs["total_neto"],
                "cantidad": ventas_qs["cantidad"]
            },
            "compras": {
                "subtotal_neto": compras_qs["subtotal_neto"],
                "impuestos_neto": compras_qs["impuestos_neto"],
                "total_neto": compras_qs["total_neto"],
                "cantidad": compras_qs["cantidad"]
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
