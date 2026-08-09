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
# IMPORTANTE: estas constantes se usan en Meta.fields de serializers.
# NUNCA incluir notacion ORM de traversal (doble guion bajo ej: sede__nombre).
# Las traversals van INLINE en .only() dentro del selector, junto con select_related.
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
    "cliente_uuid",
    "proveedor_uuid",
    "cotizacion_uuid",
    "cotizacion_numero",
    "cufe",
    "qr_url",
    "sede_id",      # DT-SEDE-02: FK id (valido en Meta.fields y en .only())
)

# Traversals ORM para .only() — NO incluir en LIST_FIELDS/DETAIL_FIELDS
# porque se usan directamente en serializer Meta.fields.
_SEDE_ONLY_TRAVERSALS = ("sede__nombre",)

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
    "cliente_uuid",
    "proveedor_uuid",
    "cotizacion_uuid",
    "cotizacion_numero",
    "cufe",
    "qr_url",
    "sede_id",       # DT-SEDE-02: FK id (valido en Meta.fields y en .only())
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
    def qs_list(empresa_id: int | None = None, search: str | None = None, sede_ids=None):
        """
        QuerySet optimizado para listado (v3.5 Zero Waste).
        empresa_id aplicado aqui (SSoT Anti-IDOR).

        [OSF Fase F7] `sede_ids=None` (default) no restringe por sede -
        comportamiento identico al de antes de esta fase. Cuando se pasa
        (perfil con alcance SEDE/AREA), usa filter_by_scope_null_safe()
        (no filter_by_scope()): el 100% de las Facturas reales tiene
        sede=NULL hoy (verificado empiricamente en F7, el campo era
        puramente informativo) - un registro sin sede queda visible para
        todos los alcances, para no ocultar datos existentes al activar el
        filtrado. `Factura` no tiene campo `area` - nunca se filtra por el.
        """
        qs = Factura.objects.select_related("nota_credito", "sede").only(
            *LIST_FIELDS,
            *NOTA_CREDITO_ONLY_FIELDS,
            *_SEDE_ONLY_TRAVERSALS,
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(cufe__icontains=search) |
                Q(receptor_razon_social__icontains=search) |
                Q(emisor_razon_social__icontains=search)
            )
        return qs.order_by("-fecha_emision", "-id")

    @staticmethod
    def qs_detail(empresa_id: int | None = None, sede_ids=None):
        """
        QuerySet optimizado para detalle.
        empresa_id aplicado aqui (SSoT Anti-IDOR).

        [OSF Fase F11] `sede_ids=None` (default) no restringe - mismo
        criterio NULL-safe de F7 (qs_list). Antes de esta fase, `retrieve`
        (y el resto de acciones a nivel de objeto en FacturaViewSet) solo
        filtraban por `empresa_id`, nunca por alcance organizacional - un
        perfil con alcance=SEDE podia ver/editar/eliminar por UUID directo
        una Factura de otra sede aunque el listado (F7) ya se la ocultara.
        """
        qs = Factura.objects.select_related("nota_credito", "sede").prefetch_related("impuestos_desglosados").only(
            *DETAIL_FIELDS,
            *NOTA_CREDITO_ONLY_FIELDS,
            *_SEDE_ONLY_TRAVERSALS,
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
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
    def obtener_cotizacion_por_uuid(
        cotizacion_uuid: str, empresa_id: int | None = None, sede_ids=None,
    ) -> dict | None:
        """
        Resuelve Cotizacion a partir de uuid vinculado en Factura.
        Usa CotizacionSelector.get_detail_by_uuid() del servicio cotizaciones.

        Params:
          cotizacion_uuid: UUID de la cotizacion (viene de Factura.cotizacion_uuid)
          empresa_id: opcional, filtra por empresa si se proporciona
          sede_ids: [OSF Fase F9] opcional, conjunto de sedes permitidas segun
            el OrganizationalScope de quien hace la peticion. Si se pasa
            (perfil con alcance SEDE/AREA), una Cotizacion cuya sede no este
            en el conjunto se trata como "no encontrada" (mismo criterio
            NULL-safe de F7: `Cotizacion.sede=None` SI es visible - el 100%
            de las Cotizaciones reales no tiene sede asignada hoy). `None`
            (default) no restringe - comportamiento identico al de antes de
            esta fase.

        Returns:
          dict con datos de Cotizacion o None si no existe (o no esta en el
          alcance organizacional del solicitante).
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

            # [OSF Fase F9] la cotizacion existe y pertenece a la empresa,
            # pero puede estar fuera del alcance organizacional de quien
            # pregunta - se trata igual que "no existe" (mismo criterio DSV
            # que las demas verificaciones de este bridge).
            if sede_ids is not None and cotizacion.sede_id is not None and cotizacion.sede_id not in sede_ids:
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

    @staticmethod
    def exists_by_uuid(cotizacion_uuid: str, empresa_id: int | None = None, sede_ids=None) -> bool:
        """Valida existencia de cotizacion por UUID (y, si se pasa `sede_ids`,
        que este dentro del alcance organizacional del solicitante - F9)."""
        return CotizacionBridge.obtener_cotizacion_por_uuid(cotizacion_uuid, empresa_id, sede_ids) is not None


class ClienteBridge:
    """Bridge de lectura hacia Clientes para resolver cliente_uuid sin snapshots."""

    @staticmethod
    def obtener_cliente_por_uuid(cliente_uuid: str, empresa_id: int | None = None) -> dict | None:
        """Retorna informacion minima del cliente vinculado."""
        if not cliente_uuid:
            return None

        try:
            from apps.tenant.clientes.models import Cliente

            qs = Cliente.objects.only(
                "id",
                "uuid",
                "empresa_id",
                "numero_documento",
                "razon_social",
                "nombre_comercial",
                "email",
                "telefono",
            )
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)

            cliente = qs.filter(uuid=cliente_uuid).first()
            if not cliente:
                return None

            return {
                "uuid": str(cliente.uuid),
                "numero_documento": cliente.numero_documento,
                "razon_social": cliente.razon_social,
                "nombre_comercial": cliente.nombre_comercial,
                "email": cliente.email,
                "telefono": cliente.telefono,
                "label": cliente.razon_social or cliente.numero_documento,
            }
        except Exception:
            return None

    @staticmethod
    def exists_by_uuid(cliente_uuid: str, empresa_id: int | None = None) -> bool:
        """Valida existencia del cliente dentro del tenant activo."""
        return ClienteBridge.obtener_cliente_por_uuid(cliente_uuid, empresa_id) is not None


class ProveedorBridge:
    """Bridge de lectura hacia Proveedores para resolver proveedor_uuid sin snapshots."""

    @staticmethod
    def obtener_proveedor_por_uuid(proveedor_uuid: str, empresa_id: int | None = None) -> dict | None:
        """Retorna informacion minima del proveedor vinculado."""
        if not proveedor_uuid:
            return None

        try:
            from apps.tenant.proveedores.models import Proveedor

            qs = Proveedor.objects.only(
                "id",
                "uuid",
                "empresa_id",
                "numero_documento",
                "digito_verificacion",
                "razon_social",
                "nombre_comercial",
                "email_contacto",
                "telefono_contacto",
            )
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)

            proveedor = qs.filter(uuid=proveedor_uuid).first()
            if not proveedor:
                return None

            numero = proveedor.numero_documento
            if proveedor.digito_verificacion:
                numero = f"{numero}-{proveedor.digito_verificacion}"

            return {
                "uuid": str(proveedor.uuid),
                "numero_documento": numero,
                "razon_social": proveedor.razon_social,
                "nombre_comercial": proveedor.nombre_comercial,
                "email": proveedor.email_contacto,
                "telefono": proveedor.telefono_contacto,
                "label": proveedor.razon_social or numero,
            }
        except Exception:
            return None

    @staticmethod
    def exists_by_uuid(proveedor_uuid: str, empresa_id: int | None = None) -> bool:
        """Valida existencia del proveedor dentro del tenant activo."""
        return ProveedorBridge.obtener_proveedor_por_uuid(proveedor_uuid, empresa_id) is not None


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


class BancosBridge:
    """
    [v3.11.0] Pull Model bridge: Facturas lee transacciones bancarias conciliadas
    sin FK directa (Bounded Context §18, ADR-001).

    Importacion dinamica de TransaccionBancaria para evitar circularidad
    entre apps.tenant.facturas y apps.tenant.bancos.
    """

    @staticmethod
    def obtener_total_conciliado(empresa_id: int, factura_uuid) -> Decimal:
        """
        Suma el valor absoluto de todas las TransaccionBancaria conciliadas
        que referencian esta factura.

        DEBITO  (valor < 0) → pago de facturas de COMPRA
        CREDITO (valor >= 0) → cobro de facturas de VENTA
        ABS garantiza suma correcta en ambos casos.

        Returns Decimal: total conciliado en bancos, 0.00 si no hay ninguno.
        """
        from django.db.models import Func, F, Sum
        from apps.tenant.bancos.models import TransaccionBancaria

        if not factura_uuid or not empresa_id:
            return Decimal('0.00')

        result = (
            TransaccionBancaria.objects
            .filter(
                empresa_id=empresa_id,
                factura_uuid=factura_uuid,
                conciliado=True,
            )
            .aggregate(
                total=Sum(Func(F('valor'), function='ABS'))
            )
        )
        return Decimal(str(result['total'] or '0.00'))
