import logging
from django.conf import settings
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.base import BaseTenantViewSet

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria
from apps.tenant.bancos.services.api_mixins import (
    CuentaBancariaServiceMixin,
    ExtractoBancarioServiceMixin,
    TransaccionBancariaServiceMixin,
)
from apps.tenant.bancos.api.serializers import (
    CuentaBancariaSerializer,
    ExtractoBancarioListSerializer,
    ExtractoBancarioCreateSerializer,
    ExtractoBancarioDetailSerializer,
    TransaccionBancariaListSerializer,
    TransaccionBancariaDetailSerializer,
    TransaccionBancariaConciliarSerializer,
)

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

class CuentaBancariaViewSet(CuentaBancariaServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet to manage CuentaBancaria.
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

    def get_permissions(self):
        if settings.DEBUG:
            return []
        return [IsTenantMember(), IsTenantAdminOrReadOnly()]

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




class ExtractoBancarioViewSet(ExtractoBancarioServiceMixin, SintelDSVMixin, BaseTenantViewSet):
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

    def get_permissions(self):
        if settings.DEBUG:
            return []
        return [IsTenantMember(), IsTenantAdminOrReadOnly()]

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
        Executes parser on statement Excel to load transactions.
        """
        try:
            extracto = self.get_object()
            num_tx = self.service_procesar_extracto(extracto)
            return Response({"message": f"Se procesaron {num_tx} transacciones exitosamente."}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

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

        # Pre-cargar las transacciones con select_related para el template
        transacciones = (
            extracto.transacciones
            .only(
                'id', 'uuid', 'fecha', 'descripcion', 'sucursal', 'dcto',
                'valor', 'saldo', 'conciliado',
                'factura_uuid', 'proveedor_uuid', 'cliente_uuid',
                'notas_conciliacion',
                'empresa_id',
            )
            .order_by('-fecha', '-created_at')
        )

        context = {
            "extracto": extracto,
            "transacciones": transacciones,
            "empresa_id": empresa_id,
        }
        return Response(context, template_name="tenant/bancos/offcanvas_detalle_extracto.html")


class TransaccionBancariaViewSet(TransaccionBancariaServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para TransaccionBancaria.
    Lectura: GET list/detail con filtros por extracto_uuid, tipo_movimiento, conciliado.
    Conciliacion: PATCH /conciliar/ para vincular con factura o proveedor.
    Busqueda: GET /search-facturas/ y /search-proveedores/ para autocomplete.
    Mutaciones de datos solo via ETL (action procesar del ExtractoViewSet).
    """
    queryset = TransaccionBancaria.objects.none()
    serializer_class = TransaccionBancariaDetailSerializer
    http_method_names = ["get", "patch", "head", "options"]
    pagination_class = StandardResultsSetPagination
    renderer_classes = [JSONRenderer]

    # tipo_movimiento es @property. Se filtra manualmente en selectors.
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["descripcion", "sucursal", "dcto"]
    ordering_fields = ["fecha", "valor", "saldo", "conciliado", "created_at"]
    ordering = ["-fecha", "-created_at"]

    def get_permissions(self):
        if settings.DEBUG:
            return []
        return [IsTenantMember()]

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

    @action(detail=False, methods=["get"], url_path="search-facturas")
    def search_facturas(self, request):
        """
        Busca facturas por naturaleza (VENTA | COMPRA), numero, NIT o razon social.
        GET /api/v1/bancos/transacciones/search-facturas/?q=<term>&naturaleza=VENTA|COMPRA

        - naturaleza=VENTA: facturas emitidas al cliente.
        - naturaleza=COMPRA: facturas recibidas de proveedor.
        - sin naturaleza: ambas.
        """
        from apps.tenant.facturas.models import Factura
        from django.db.models import Q

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
        from apps.tenant.proveedores.models import Proveedor
        from django.db.models import Q

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
        from apps.tenant.clientes.models import Cliente
        from django.db.models import Q

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
