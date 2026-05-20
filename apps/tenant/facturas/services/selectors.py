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

NOTA_CREDITO_ONLY_FIELDS = (
    "nota_credito__id",
    "nota_credito__numero",
)

ANEXO_KEYS = {"ubl_xml", "application_response_xml"}
MAX_INLINE_BYTES = 2_000_000  # 2MB


class FacturaSelectors:
    """
    Selectores para la aplicación Facturas.
    """

    @staticmethod
    def qs_list(empresa_id: int | None = None, search: str | None = None):
        """
        QuerySet optimizado para listado (v3.5 Zero Waste).
        empresa_id aplicado aqui (SSoT Anti-IDOR).
        """
        qs = Factura.objects.select_related("nota_credito").only(
            *LIST_FIELDS,
            *NOTA_CREDITO_ONLY_FIELDS,
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(cufe__icontains=search) |
                Q(receptor_razon_social__icontains=search) |
                Q(emisor_razon_social__icontains=search)
            )
        return qs.order_by("-fecha_emision", "-id")

    @staticmethod
    def qs_detail(empresa_id: int | None = None):
        """
        QuerySet optimizado para detalle.
        empresa_id aplicado aqui (SSoT Anti-IDOR).
        """
        qs = Factura.objects.select_related("nota_credito", "anexos").only(
            *DETAIL_FIELDS,
            *NOTA_CREDITO_ONLY_FIELDS,
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def qs_centros_costo(empresa_id: int | None = None):
        """
        QuerySet ligero para selección de centros de costo (v3.5 Zero Waste).
        Retorna los campos mínimos necesarios para el dropdown.
        """
        qs = Factura.objects.only("id", "uuid", "numero", "receptor_razon_social")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs.order_by("-fecha_emision", "-id")

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


class CotizacionBridge:
    """
    Selector dinamico para resolver Cotizaciones vinculadas a Facturas.
    Integración con apps.tenant.cotizaciones sin acoplamiento circular.
    """
    @staticmethod
    def obtener_cotizacion_por_uuid(cotizacion_uuid: str, empresa_id: int | None = None) -> dict | None:
        """
        Resuelve Cotizacion a partir de uuid vinculado en Factura.
        Usa CotizacionSelector.get_detail_by_uuid() del servicio cotizaciones.

        Params:
          cotizacion_uuid: UUID de la cotizacion (viene de Factura.cotizacion_uuid)
          empresa_id: opcional, filtra por empresa si se proporciona

        Returns:
          dict con datos de Cotizacion o None si no existe
        """
        if not cotizacion_uuid:
            return None

        try:
            from apps.tenant.cotizaciones.services.selectors import CotizacionSelector

            # Si tenemos empresa_id, usarlo para validación DSV
            if empresa_id:
                cotizacion = CotizacionSelector.get_detail_by_uuid(
                    uuid=cotizacion_uuid,
                    empresa_id=empresa_id
                ).first()
            else:
                # Sin empresa_id, acceso abierto (inter-app)
                from apps.tenant.cotizaciones.models import Cotizacion
                cotizacion = Cotizacion.objects.filter(uuid=cotizacion_uuid).first()

            if not cotizacion:
                return None

            return {
                'uuid': str(cotizacion.uuid),
                'numero_cotizacion': cotizacion.numero_cotizacion,
                'estado': cotizacion.estado,
                'fecha_emision': cotizacion.fecha_emision.isoformat() if cotizacion.fecha_emision else None,
                'fecha_vencimiento': cotizacion.fecha_vencimiento.isoformat() if cotizacion.fecha_vencimiento else None,
                'total_con_impuestos': float(cotizacion.total_con_impuestos) if cotizacion.total_con_impuestos else 0.0,
                'cliente_razon_social': cotizacion.cliente.razon_social if cotizacion.cliente else None,
            }
        except Exception as e:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning(f"Error resolviendo cotizacion {cotizacion_uuid}: {e}")
            return None


class InventarioItemBridge:
    """
    Selector dinamico para resolver items de inventario (Productos/Servicios)
    desde el modulo de facturacion sin acoplamiento circular.
    """
    @staticmethod
    def buscar_catalogo(empresa_id: int, search: str = "") -> list[dict[str, Any]]:
        """
        Busca productos y servicios en el catalogo de inventario.
        Usa .only() para rendimiento maximo y union manual para evitar N+1.
        """
        from apps.tenant.inventario.models import Producto, Servicio

        # Busqueda de Productos
        prod_qs = Producto.objects.filter(empresa_id=empresa_id)
        if search:
            prod_qs = prod_qs.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search)
            )
        productos = prod_qs.only('uuid', 'codigo', 'nombre', 'precio_venta').order_by('nombre')[:50]

        # Busqueda de Servicios
        serv_qs = Servicio.objects.filter(empresa_id=empresa_id)
        if search:
            serv_qs = serv_qs.filter(
                Q(codigo__icontains=search) | Q(nombre__icontains=search)
            )
        servicios = serv_qs.only('uuid', 'codigo', 'nombre', 'precio_venta').order_by('nombre')[:50]

        catalogo = []
        for p in productos:
            catalogo.append({
                'uuid': str(p.uuid),
                'codigo': p.codigo,
                'nombre': p.nombre,
                'precio_venta': float(p.precio_venta) if p.precio_venta else 0.0,
                'tipo': 'PRODUCTO'
            })
        for s in servicios:
            catalogo.append({
                'uuid': str(s.uuid),
                'codigo': s.codigo,
                'nombre': s.nombre,
                'precio_venta': float(s.precio_venta) if s.precio_venta else 0.0,
                'tipo': 'SERVICIO'
            })

        # Ordenar catalogo final por nombre
        catalogo.sort(key=lambda x: x['nombre'])
        return catalogo

    @staticmethod
    def resolver_item(empresa_id: int, item_uuid: Any, item_tipo: str) -> dict[str, Any] | None:
        """
        Resuelve un item especifico de inventario (Producto o Servicio) por su UUID.
        """
        from apps.tenant.inventario.models import Producto, Servicio

        if item_tipo == 'PRODUCTO':
            try:
                p = Producto.objects.only('uuid', 'codigo', 'nombre', 'precio_venta').get(
                    empresa_id=empresa_id, uuid=item_uuid
                )
                return {
                    'uuid': str(p.uuid),
                    'codigo': p.codigo,
                    'nombre': p.nombre,
                    'precio_venta': float(p.precio_venta) if p.precio_venta else 0.0,
                    'tipo': 'PRODUCTO'
                }
            except Producto.DoesNotExist:
                return None
        elif item_tipo == 'SERVICIO':
            try:
                s = Servicio.objects.only('uuid', 'codigo', 'nombre', 'precio_venta').get(
                    empresa_id=empresa_id, uuid=item_uuid
                )
                return {
                    'uuid': str(s.uuid),
                    'codigo': s.codigo,
                    'nombre': s.nombre,
                    'precio_venta': float(s.precio_venta) if s.precio_venta else 0.0,
                    'tipo': 'SERVICIO'
                }
            except Servicio.DoesNotExist:
                return None
        return None

