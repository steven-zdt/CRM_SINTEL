import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.bancos.api.serializers import (
    CuentaBancariaSerializer,
    ExtractoBancarioCreateSerializer,
    ExtractoBancarioDetailSerializer,
    ExtractoBancarioListSerializer,
    MovimientoBancarioAplicacionSerializer,
    MovimientoBancarioSugerenciaSerializer,
    TransaccionBancariaConciliarSerializer,
    TransaccionBancariaDetailSerializer,
    TransaccionBancariaListSerializer,
)
from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)
from apps.tenant.bancos.services.api_mixins import (
    CuentaBancariaServiceMixin,
    ExtractoBancarioServiceMixin,
    MovimientoBancarioAplicacionServiceMixin,
    TransaccionBancariaServiceMixin,
)
from apps.tenant.bancos.services.export_service import ExtractoBancarioExportService
from apps.tenant.bancos.services.matching_service import BankTransactionMatchingService
from apps.tenant.bancos.services.selectors import (
    ExtractoBancarioKpiSelector,
    MovimientoBancarioAplicacionSelector,
    TerceroDisplaySelector,
)
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

logger = logging.getLogger(__name__)

BANCOS_CHOICES = [
    ("BANCOLOMBIA", "Bancolombia"),
    ("BANCO_BOGOTA", "Banco de Bogota"),
    ("DAVIVIENDA", "Davivienda"),
    ("BBVA", "BBVA"),
    ("OCCIDENTE", "Banco de Occidente"),
    ("POPULAR", "Banco Popular"),
    ("AV_VILLAS", "Banco AV Villas"),
]

TIPOS_CUENTA_CHOICES = [
    ("AHORROS", "Ahorros"),
    ("CORRIENTE", "Corriente"),
]

class CuentaBancariaViewSet(OrganizationalContextMixin, CuentaBancariaServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet to manage CuentaBancaria.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva. Como
    compras, esta app SI hereda SintelDSVMixin - no hay divergencia de
    mecanismo con OrganizationalContext.resolve(). get_queryset() no se
    migra de todos modos: get_qs_list()/get_qs_detail() (BaseServiceMixin)
    usan el selector con sus propios .only(), y context.filter() generico
    no los replica.
    """
    queryset = CuentaBancaria.objects.none()
    serializer_class = CuentaBancariaSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "banco", "numero"]
    ordering_fields = ["nombre", "banco", "created_at"]
    ordering = ["nombre"]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return CuentaBancaria.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["empresa_id"] = self.get_empresa_id()
        except Exception:
            context["empresa_id"] = None
        return context

    def create(self, request, *args, **kwargs):
        try:
            serializer = CuentaBancariaSerializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            
            cuenta = self.service_crear_cuenta(serializer.validated_data)
            response_serializer = self.get_serializer(cuenta)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = CuentaBancariaSerializer(instance, data=request.data, partial=True, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            
            cuenta = self.service_editar_cuenta(instance, serializer.validated_data)
            response_serializer = self.get_serializer(cuenta)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.service_eliminar_cuenta(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, uuid=None):
        """B-4: soft delete -- oculta la cuenta sin perder su historial."""
        try:
            instance = self.get_object()
            cuenta = self.service_desactivar_cuenta(instance)
            return Response(self.get_serializer(cuenta).data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="activar")
    def activar(self, request, uuid=None):
        """B-4: reactiva una cuenta previamente desactivada."""
        try:
            instance = self.get_object()
            cuenta = self.service_activar_cuenta(instance)
            return Response(self.get_serializer(cuenta).data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    # --- UI / HTMX Offcanvas Actions ---

    @action(detail=False, methods=["get"], renderer_classes=[TemplateHTMLRenderer], url_path="render-offcanvas/crear")
    def render_offcanvas_crear(self, request):
        """Renders HTMX offcanvas to create a new bank account."""
        context = {
            "mode": "create",
            "bancos": BANCOS_CHOICES,
            "tipos_cuenta": TIPOS_CUENTA_CHOICES,
        }
        return Response(context, template_name="tenant/bancos/offcanvas_crear_cuenta.html")

    @action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer], url_path="render-offcanvas/editar")
    def render_offcanvas_editar(self, request, uuid=None):
        """Renders HTMX offcanvas to edit a bank account."""
        cuenta = self.get_object()
        context = {
            "mode": "edit",
            "instance": cuenta,
            "bancos": BANCOS_CHOICES,
            "tipos_cuenta": TIPOS_CUENTA_CHOICES,
        }
        return Response(context, template_name="tenant/bancos/offcanvas_editar_cuenta.html")




class ExtractoBancarioViewSet(OrganizationalContextMixin, ExtractoBancarioServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet to manage ExtractoBancario and execute statement processing.
    """
    queryset = ExtractoBancario.objects.none()
    serializer_class = ExtractoBancarioDetailSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["cuenta__nombre", "cuenta__numero"]
    ordering_fields = ["mes", "anio", "procesado", "created_at"]
    ordering = ["-anio", "-mes"]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return ExtractoBancario.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return ExtractoBancarioListSerializer
        if self.action == "create":
            return ExtractoBancarioCreateSerializer
        return ExtractoBancarioDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["empresa_id"] = self.get_empresa_id()
        except Exception:
            context["empresa_id"] = None
        return context

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            extracto = self.service_crear_extracto(serializer.validated_data)
            response_serializer = ExtractoBancarioDetailSerializer(extracto, context=self.get_serializer_context())
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.service_eliminar_extracto(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="procesar")
    def procesar(self, request, uuid=None):
        """
        Importa (XLSX/CSV) -> normaliza -> valida balance -> ingesta transacciones.

        Body opcional: {"forzar": true} -- requerido para reprocesar un
        extracto que ya tiene transacciones conciliadas/con aplicaciones
        (Fase 24, importacion no destructiva).
        """
        try:
            extracto = self.get_object()
            forzar = bool(request.data.get("forzar", False))
            resultado = self.service_procesar_extracto(extracto, forzar=forzar)
            resultado["message"] = (
                f"Se procesaron {resultado['transacciones_importadas']} transacciones exitosamente."
            )
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["get"], url_path="exportar", renderer_classes=[JSONRenderer])
    def exportar(self, request, uuid=None):
        """BAN-12: exporta el reporte de conciliacion del extracto (periodo =
        cuenta + mes/anio) a CSV -- fecha/descripcion/tipo/valor/conciliado/
        vinculo resuelto/notas de cada transaccion."""
        from django.http import HttpResponse

        extracto = self.get_object()
        empresa_id = self.get_empresa_id()
        contenido = ExtractoBancarioExportService.generar_csv_conciliacion(empresa_id, extracto)
        nombre_archivo = f"conciliacion_{extracto.cuenta.numero}_{extracto.anio}{extracto.mes:02d}.csv"
        response = HttpResponse(contenido, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        return response

    # --- UI / HTMX Offcanvas Actions ---

    @action(detail=False, methods=["get"], renderer_classes=[TemplateHTMLRenderer], url_path="render-offcanvas/crear")
    def render_offcanvas_crear(self, request):
        """Renders HTMX offcanvas to upload a statement."""
        empresa_id = self.get_empresa_id()
        cuentas = CuentaBancaria.objects.filter(empresa_id=empresa_id).only("id", "uuid", "nombre", "numero")
        context = {
            "cuentas": cuentas,
        }
        return Response(context, template_name="tenant/bancos/offcanvas_crear_extracto.html")

    @action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer], url_path="render-offcanvas/detalle")
    def render_offcanvas_detalle(self, request, uuid=None):
        """Renders HTMX offcanvas displaying details of the statement and transactions."""
        extracto = self.get_object()
        empresa_id = self.get_empresa_id()

        # Pre-cargar transacciones con DSV empresa_id explicito (no confiar solo en la FK de extracto)
        transacciones = (
            TransaccionBancaria.objects
            .filter(extracto=extracto, empresa_id=empresa_id)
            .only(
                'id', 'uuid', 'fecha', 'descripcion', 'sucursal', 'dcto',
                'valor', 'saldo', 'conciliado',
                'factura_uuid', 'proveedor_uuid', 'cliente_uuid',
                'notas_conciliacion',
                'empresa_id',
            )
            .order_by('-fecha', '-created_at')
        )

        # Fase 19: KPI resumido del extracto (ingresos/egresos/neto/pendientes/conciliados).
        from decimal import Decimal

        from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
        from django.db.models.functions import Coalesce

        cero_decimal = Value(Decimal("0.00"), output_field=DecimalField())
        kpis = transacciones.aggregate(
            ingresos=Coalesce(
                Sum(Case(When(valor__gte=0, then="valor"), output_field=DecimalField())), cero_decimal
            ),
            egresos=Coalesce(
                Sum(Case(When(valor__lt=0, then=-1 * F("valor")), output_field=DecimalField())), cero_decimal
            ),
            total=Count("id"),
            conciliadas=Count("id", filter=Q(conciliado=True)),
        )
        kpis["neto"] = kpis["ingresos"] - kpis["egresos"]
        kpis["pendientes"] = kpis["total"] - kpis["conciliadas"]

        # BAN-06/07: resolver nombre/numero real de facturas/proveedores/clientes
        # ya vinculados, en 3 queries bulk (una por tipo) en vez de mostrar el
        # UUID truncado o pedirlo al frontend via los endpoints search-* por TX.
        transacciones = list(transacciones)
        display_map = TerceroDisplaySelector.resolver(
            empresa_id,
            factura_uuids={t.factura_uuid for t in transacciones if t.factura_uuid},
            proveedor_uuids={t.proveedor_uuid for t in transacciones if t.proveedor_uuid},
            cliente_uuids={t.cliente_uuid for t in transacciones if t.cliente_uuid},
        )
        for t in transacciones:
            t.factura_display = display_map.get(str(t.factura_uuid)) if t.factura_uuid else None
            t.proveedor_display = display_map.get(str(t.proveedor_uuid)) if t.proveedor_uuid else None
            t.cliente_display = display_map.get(str(t.cliente_uuid)) if t.cliente_uuid else None

        context = {
            "extracto": extracto,
            "transacciones": transacciones,
            "empresa_id": empresa_id,
            "kpis": kpis,
        }
        return Response(context, template_name="tenant/bancos/offcanvas_detalle_extracto.html")


class TransaccionBancariaViewSet(OrganizationalContextMixin, TransaccionBancariaServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para TransaccionBancaria.
    Lectura: GET list/detail con filtros por extracto_uuid, tipo_movimiento, conciliado.
    Conciliacion: PATCH /conciliar/ para vincular con factura o proveedor.
    Busqueda: GET /search-facturas/ y /search-proveedores/ para autocomplete.
    Mutaciones de datos solo via ETL (action procesar del ExtractoViewSet).
    """
    queryset = TransaccionBancaria.objects.none()
    serializer_class = TransaccionBancariaDetailSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = StandardResultsSetPagination
    renderer_classes = [JSONRenderer]

    # tipo_movimiento es @property. Se filtra manualmente en selectors.
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["descripcion", "sucursal", "dcto"]
    ordering_fields = ["fecha", "valor", "saldo", "conciliado", "created_at"]
    ordering = ["-fecha", "-created_at"]
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return TransaccionBancaria.objects.none()

        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return TransaccionBancariaListSerializer
        if self.action == "conciliar":
            return TransaccionBancariaConciliarSerializer
        return TransaccionBancariaDetailSerializer

    @action(detail=True, methods=["patch"], url_path="conciliar")
    def conciliar(self, request, uuid=None):
        """
        Vincula una transaccion con una factura o proveedor (conciliacion bancaria manual).

        PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
        Body: { factura_uuid, proveedor_uuid, conciliado }
        """
        try:
            transaccion = self.get_object()
            serializer = TransaccionBancariaConciliarSerializer(
                transaccion, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            transaccion = self.service_conciliar_transaccion(transaccion, serializer.validated_data)
            return Response(
                TransaccionBancariaDetailSerializer(transaccion).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["get"], url_path="sugerencias")
    def sugerencias(self, request, uuid=None):
        """
        Fase 8-12: motor de sugerencias. Solo lectura -- nunca escribe.
        GET /api/v1/bancos/transacciones/{uuid}/sugerencias/
        """
        try:
            transaccion = self.get_object()
            candidatos = BankTransactionMatchingService.sugerir(transaccion)
            serializer = MovimientoBancarioSugerenciaSerializer(candidatos, many=True)
            return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["get", "post"], url_path="aplicaciones")
    def aplicaciones(self, request, uuid=None):
        """
        Fase 5-7: aplicaciones multiples por movimiento (split de pagos).
        GET  /api/v1/bancos/transacciones/{uuid}/aplicaciones/  -> lista
        POST /api/v1/bancos/transacciones/{uuid}/aplicaciones/  -> crea
        Editar/eliminar una aplicacion puntual: ver MovimientoBancarioAplicacionViewSet
        (/api/v1/bancos/aplicaciones/{uuid}/).
        """
        try:
            transaccion = self.get_object()
            empresa_id = self.get_empresa_id()

            if request.method == "GET":
                qs = MovimientoBancarioAplicacionSelector.get_list(empresa_id, transaccion_uuid=transaccion.uuid)
                serializer = MovimientoBancarioAplicacionSerializer(qs, many=True)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)

            serializer = MovimientoBancarioAplicacionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            aplicacion = self.service_crear_aplicacion(transaccion, serializer.validated_data)
            return Response(
                MovimientoBancarioAplicacionSerializer(aplicacion).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="search-facturas")
    def search_facturas(self, request):
        """
        Busca facturas por naturaleza (VENTA | COMPRA), numero, NIT o razon social.
        GET /api/v1/bancos/transacciones/search-facturas/?q=<term>&naturaleza=VENTA|COMPRA

        - naturaleza=VENTA: facturas emitidas al cliente.
        - naturaleza=COMPRA: facturas recibidas de proveedor.
        - sin naturaleza: ambas.
        """
        from django.db.models import Q

        from apps.tenant.facturas.models import Factura

        empresa_id = self.get_empresa_id()
        q          = request.query_params.get('q', '').strip()
        naturaleza = request.query_params.get('naturaleza', '').upper()
        page_size  = min(int(request.query_params.get('page_size', 15)), 30)

        qs = (
            Factura.objects
            .filter(empresa_id=empresa_id)
            .only(
                'id', 'uuid', 'numero', 'prefijo', 'naturaleza', 'tipo',
                'estado', 'estado_pago',
                'receptor_nit', 'receptor_razon_social',
                'emisor_nit',   'emisor_razon_social',
                'total', 'fecha_emision',
            )
            .order_by('-fecha_emision')
        )

        # Filtrar por naturaleza (VENTA | COMPRA)
        if naturaleza in ('VENTA', 'COMPRA'):
            qs = qs.filter(naturaleza=naturaleza)

        # Busqueda por texto: numero, NITs y razones sociales de ambas partes.
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)                |
                Q(receptor_nit__icontains=q)          |
                Q(receptor_razon_social__icontains=q) |
                Q(emisor_nit__icontains=q)            |
                Q(emisor_razon_social__icontains=q)
            )

        results = []
        for f in qs[:page_size]:
            # Para VENTA el tercero relevante es el receptor.
            # Para COMPRA el tercero relevante es el emisor.
            if f.naturaleza == 'VENTA':
                nit    = f.receptor_nit
                nombre = f.receptor_razon_social
            else:
                nit    = f.emisor_nit
                nombre = f.emisor_razon_social

            tipo_display = {
                'FE': 'Factura Electronica',
                'NC': 'Nota Credito',
                'ND': 'Nota Debito',
            }.get(f.tipo, f.tipo)

            results.append({
                'uuid':         str(f.uuid),
                'numero':       f.numero  or '',
                'prefijo':      f.prefijo or '',
                'naturaleza':   f.naturaleza or '',
                'tipo':         f.tipo    or '',
                'tipo_display': tipo_display,
                'estado':       f.estado     or '',
                'estado_pago':  f.estado_pago or '',
                'nit':          nit    or '',
                'nombre':       nombre or '',
                'total':        str(f.total),
                'fecha':        f.fecha_emision.strftime('%d/%m/%Y') if f.fecha_emision else '',
            })
        return Response({'results': results}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="search-proveedores")
    def search_proveedores(self, request):
        """
        Busca proveedores por NIT, razon_social o nombre_comercial.
        GET /api/v1/bancos/transacciones/search-proveedores/?q=<term>
        """
        from django.db.models import Q

        from apps.tenant.proveedores.models import Proveedor

        empresa_id = self.get_empresa_id()
        q          = request.query_params.get('q', '').strip()
        page_size  = min(int(request.query_params.get('page_size', 10)), 20)

        qs = Proveedor.objects.filter(empresa_id=empresa_id, activo=True).only(
            'id', 'uuid', 'tipo_documento', 'numero_documento', 'razon_social',
            'nombre_comercial', 'email_contacto', 'ciudad',
            'banco', 'tipo_cuenta', 'numero_cuenta',
        )

        if q:
            qs = qs.filter(
                Q(numero_documento__icontains=q) |
                Q(razon_social__icontains=q) |
                Q(nombre_comercial__icontains=q) |
                Q(ciudad__icontains=q)
            )

        results = [
            {
                'uuid':             str(p.uuid),
                'tipo_documento':   p.tipo_documento,
                'numero_documento': p.numero_documento,
                'razon_social':     p.razon_social,
                'nombre_comercial': p.nombre_comercial or '',
                'email':            p.email_contacto or '',
                'ciudad':           p.ciudad or '',
                'banco':            p.banco or '',
                'tipo_cuenta':      p.tipo_cuenta or '',
                'numero_cuenta':    p.numero_cuenta or '',
            }
            for p in qs[:page_size]
        ]
        return Response({'results': results}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="search-clientes")
    def search_clientes(self, request):
        """
        Busca clientes por NIT, razon_social, nombre_comercial o ciudad.
        GET /api/v1/bancos/transacciones/search-clientes/?q=<term>
        """
        from django.db.models import Q

        from apps.tenant.clientes.models import Cliente

        empresa_id = self.get_empresa_id()
        q          = request.query_params.get('q', '').strip()
        page_size  = min(int(request.query_params.get('page_size', 10)), 20)

        qs = Cliente.objects.filter(empresa_id=empresa_id, activo=True).only(
            'id', 'uuid', 'tipo_documento', 'numero_documento',
            'razon_social', 'nombre_comercial', 'email', 'ciudad',
        )
        if q:
            qs = qs.filter(
                Q(numero_documento__icontains=q) |
                Q(razon_social__icontains=q) |
                Q(nombre_comercial__icontains=q) |
                Q(ciudad__icontains=q)
            )

        results = [
            {
                'uuid': str(c.uuid),
                'tipo_documento':   c.tipo_documento,
                'numero_documento': c.numero_documento,
                'razon_social':     c.razon_social,
                'nombre_comercial': c.nombre_comercial or '',
                'email':            c.email or '',
                'ciudad':           c.ciudad or '',
            }
            for c in qs[:page_size]
        ]
        return Response({'results': results}, status=status.HTTP_200_OK)


class MovimientoBancarioAplicacionViewSet(
    OrganizationalContextMixin, MovimientoBancarioAplicacionServiceMixin, SintelDSVMixin, BaseTenantViewSet
):
    """
    Editar/eliminar una aplicacion puntual (Fase 5-7).

    Crear/listar por transaccion: ver
    TransaccionBancariaViewSet.aplicaciones() (/transacciones/{uuid}/aplicaciones/),
    que es el flujo principal desde el detalle del extracto. Este ViewSet
    cubre GET/PATCH/DELETE directos por uuid de la aplicacion (ej. desde un
    listado propio de "todas mis aplicaciones pendientes").
    """
    queryset = MovimientoBancarioAplicacion.objects.none()
    serializer_class = MovimientoBancarioAplicacionSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]
    pagination_class = StandardResultsSetPagination
    renderer_classes = [JSONRenderer]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["fecha_aplicacion", "monto_aplicado", "created_at"]
    ordering = ["-fecha_aplicacion", "-created_at"]
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return MovimientoBancarioAplicacion.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            aplicacion = self.service_editar_aplicacion(instance, serializer.validated_data)
            return Response(self.get_serializer(aplicacion).data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.service_eliminar_aplicacion(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)
