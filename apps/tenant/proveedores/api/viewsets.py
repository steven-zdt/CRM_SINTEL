import logging
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import render_template_safe, resolve_tenant_empresa
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.services.api_mixins import (
    ProveedorServiceMixin,
    CuentasPagarServiceMixin,
    RepresentanteServiceMixin,
)
from apps.tenant.proveedores.api.serializers import (
    ProveedorDetailSerializer,
    ProveedorListSerializer,
    FacturaCxPListSerializer,
    CuentasPagarListSerializer,
    CuentasPagarDetailSerializer,
    CuentasPagarAbonoSerializer,
    RepresentanteListSerializer,
    RepresentanteDetailSerializer,
)
from apps.tenant.proveedores.models import Proveedor, CuentasPagar, Representante
# PROVEEDORES_NIIF_CHOICES eliminado — AGENTS.md: ninguna app de negocio
# debe tener referencias contables. Contabilidad es la unica propietaria.
from apps.config.api.pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)

class ProveedorViewSet(OrganizationalContextMixin, ProveedorServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Proveedores v3.5 - Refactorizado a Service Layer (DSV Mixins).

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    get_queryset()/get_object()/etc. no migrados - resuelven la empresa via
    resolve_tenant_empresa(), mismo mecanismo ya documentado en empresa
    (Fase 9 app 1/14), que no exige TenantProfile.
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset = Proveedor.objects.none()
    serializer_class = ProveedorDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == 'list':
            return ProveedorListSerializer
        return ProveedorDetailSerializer

    def get_serializer_context(self):
        """Inyecta la empresa en el contexto del serializer para validaciones."""
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context['empresa_id'] = empresa.id
        except Exception:
            pass
        return context
    
    def get_queryset(self):
        """Zero Trust - Filtra siempre por la empresa del tenant."""
        empresa = self.get_empresa()
        return Proveedor.objects.filter(empresa=empresa)

    def get_empresa(self):
        """Zero Trust - Obtiene la empresa del tenant actual via core helper."""
        return resolve_tenant_empresa(self.request, self)

    def list(self, request):
        """Endpoint para Tabulator (Selector Modular + CuentasPagar inline)."""
        empresa = self.get_empresa()
        search = request.query_params.get('search', '').strip()

        queryset = self.proveedor_selector.get_list(empresa.id, search if search else None)

        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)

        # CuentasPagar: una query agrupada para todos los proveedores de la pagina
        uuids = [p.uuid for p in rows if p.uuid]
        cuentas_pagar_map = self.proveedor_selector.get_cuentas_pagar_resumen(empresa.id, uuids)

        ctx = self.get_serializer_context()
        ctx['cuentas_pagar_map'] = cuentas_pagar_map

        serializer = ProveedorListSerializer(rows, many=True, context=ctx)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def get_object(self):
        """
        [SSoT] Double Semantic Verification (DSV)
        Validates that the object exists AND belongs to the tenant by UUID (with PK fallback).
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        empresa = self.get_empresa()

        if not empresa:
            raise NotFound("Empresa no detectada en el contexto del tenant.")
        if not lookup_value:
            raise NotFound("ID no proporcionado.")

        # 1. Intentar por UUID si el valor parece uno (len > 10 o contiene guiones)
        if len(str(lookup_value)) > 10 or '-' in str(lookup_value):
            obj = Proveedor.objects.filter(uuid=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj
        
        # 2. Fallback a PK (si es numérico)
        if str(lookup_value).isdigit():
            obj = Proveedor.objects.filter(pk=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        logger.warning(f"[proveedores:DSV] IDOR Intent or Missing Record: Lookup {lookup_value} for Empresa {empresa.id}")
        raise NotFound("Proveedor no encontrado en su organizacion.")
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene detalle de un proveedor."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crea un proveedor delegando al Business Service."""
        empresa = self.get_empresa()
        serializer = ProveedorDetailSerializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            proveedor = self.proveedor_service.crear_proveedor(empresa.id, serializer.validated_data)
            return Response(
                ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualiza un proveedor delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=False, context=self.get_serializer_context())
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(proveedor, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, data=request.data, partial=True, context=self.get_serializer_context())
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(proveedor, serializer.validated_data)
            return Response(ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Eliminación delegando lógica de protección al Business Service."""
        proveedor = self.get_object()
        try:
            self.proveedor_service.eliminar_proveedor(proveedor)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """Renderiza offcanvas de creación (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='crear')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request):
        """Renderiza offcanvas de edición (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='editar')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """Renderiza offcanvas en modo detalle (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix='detalle')

    def get_offcanvas_response(self, request, template_suffix='crear'):
        """Helper para renderizar el Offcanvas con el contexto NIIF."""
        empresa = self.get_empresa()
        proveedor = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # v3.5.2: Priorizamos UUID para lookup seguro
            proveedor = self.proveedor_selector.get_by_uuid(empresa.id, id_instancia)
            if not proveedor and str(id_instancia).isdigit():
                # Fallback por PK para compatibilidad
                proveedor = self.proveedor_selector.get_by_id(empresa.id, id_instancia)
        
        context = {
            'proveedor': proveedor,
            'empresa': empresa,
            'tipo_persona_choices': Proveedor.TIPO_PERSONA,
            'tipo_documento_choices': Proveedor.TIPO_DOCUMENTO,
            'regimen_choices': Proveedor.REGIMEN,
            'tipo_cuenta_choices': [("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")],
            'modo_detalle': template_suffix == 'detalle',
        }
        
        # v3.5.2: Template universal unificado para evitar desincronización de IDs
        template_name = 'tenant/proveedores/offcanvas_form.html'
        return render_template_safe(context, template_name, request=request)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """Alias para retrocompatibilidad."""
        return self.get_offcanvas_response(request, template_suffix='crear')


# (CuentaPorPagarViewSet unificado en CuentasPagarViewSet)


# ==============================================================================
# CuentasPagar ViewSet
# ==============================================================================

class CuentasPagarViewSet(OrganizationalContextMixin, CuentasPagarServiceMixin, BaseTenantViewSet):
    """
    ViewSet para el sub-modulo de Cuentas por Pagar (Control de Deudas a Proveedores).

    Endpoints:
      GET  /api/v1/proveedores/cuentas-pagar/                -> list
      GET  /api/v1/proveedores/cuentas-pagar/{uuid}/         -> retrieve
      POST /api/v1/proveedores/cuentas-pagar/                -> create (registrar_cuenta_pagar)
      POST /api/v1/proveedores/cuentas-pagar/{uuid}/registrar-abono/ -> registrar_abono
      GET  /api/v1/proveedores/cuentas-pagar/dashboard-kpis/ -> dashboard_kpis

    DSV: get_empresa() valida empresa_id en cada request.
    """

    queryset = CuentasPagar.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_empresa(self):
        """Zero Trust - Obtiene la empresa del tenant actual."""
        return resolve_tenant_empresa(self.request, self)

    def get_serializer_class(self):
        if self.action == "list":
            return CuentasPagarListSerializer
        return CuentasPagarDetailSerializer

    def list(self, request, *args, **kwargs):
        """
        Lista facturas de compra (Cuentas por Pagar) de la empresa.

        Fuente: Factura.naturaleza='COMPRA' — fuente de verdad (Bounded Context §18).
        El modelo CuentasPagar se usa para gestionar abonos manuales.

        Filtros opcionales:
          ?proveedor_uuid=<uuid>  — filtrar por proveedor (Factura.proveedor_uuid)
          ?estado_pago=SIN_PAGO|PARCIAL|PAGADA
          ?vencidas=true          — solo facturas vencidas no pagadas
          ?search=<texto>         — numero de factura, razon social o NIT del proveedor
        """
        empresa = self.get_empresa()
        proveedor_uuid = request.query_params.get("proveedor_uuid") or request.query_params.get("proveedor_id")
        estado_pago    = request.query_params.get("estado_pago")
        vencidas       = request.query_params.get("vencidas", "").lower() == "true"
        search         = (request.query_params.get("search") or "").strip() or None

        qs = self.cuentas_pagar_selector.qs_list_facturas_compra(
            empresa_id=empresa.id,
            proveedor_uuid=proveedor_uuid,
            estado_pago=estado_pago,
            vencidas=vencidas,
            search=search,
        )
        page = self.paginate_queryset(qs)
        rows = page if page is not None else list(qs)
        serializer = FacturaCxPListSerializer(rows, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Detalle de una factura especifica en Cuentas por Pagar."""
        empresa = self.get_empresa()
        uuid_val = self.kwargs.get("uuid")
        cuenta_pagar_obj = self.cuentas_pagar_selector.get_by_uuid(empresa_id=empresa.id, uuid_val=uuid_val)
        
        if not cuenta_pagar_obj:
            raise NotFound("Registro de Cuentas por Pagar no encontrado en esta empresa.")
        return Response(CuentasPagarDetailSerializer(cuenta_pagar_obj).data)

    def create(self, request, *args, **kwargs):
        """
        Registra una nueva obligacion en las Cuentas por Pagar.
        DSV: valida que el proveedor pertenezca a la empresa del tenant.
        """
        empresa = self.get_empresa()
        proveedor_uuid = request.data.get("proveedor_uuid")
        
        if not proveedor_uuid:
            return Response(
                {"error": "El proveedor_uuid es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # DSV: resolver proveedor con filtro empresa
        proveedor = Proveedor.objects.filter(
            uuid=proveedor_uuid, empresa_id=empresa.id
        ).only("id", "uuid", "empresa_id", "activo").first()
        
        if not proveedor:
            raise NotFound("Proveedor no encontrado en esta empresa.")

        # Validacion con el serializer
        serializer = CuentasPagarDetailSerializer(data=request.data, context={'empresa_id': empresa.id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Delegamos la creacion al Service Layer
            cuenta_pagar_obj = self.cuentas_pagar_service.registrar_cuenta_pagar(
                proveedor=proveedor,
                empresa_id=empresa.id,
                datos_cuenta_pagar=serializer.validated_data
            )
            return Response(
                CuentasPagarDetailSerializer(cuenta_pagar_obj).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="registrar-abono")
    def registrar_abono(self, request, *args, **kwargs):
        """
        Registra un abono parcial o total sobre una factura en las Cuentas por Pagar.
        DSV: valida empresa via get_empresa() antes de llamar al servicio.
        """
        empresa = self.get_empresa()
        uuid_val = self.kwargs.get("uuid")
        serializer = CuentasPagarAbonoSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            cuenta_pagar_obj = self.cuentas_pagar_service.registrar_abono(
                cuenta_pagar_uuid=uuid_val,
                monto=serializer.validated_data["monto"],
                observaciones=serializer.validated_data.get("observaciones", ""),
                empresa_id=empresa.id,
            )
            return Response(CuentasPagarDetailSerializer(cuenta_pagar_obj).data)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False, methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas",
    )
    def render_offcanvas(self, request):
        """Renderiza offcanvas de gestion de Cuentas por Pagar (HTMX FSD Compliant)."""
        empresa = self.get_empresa()
        uuid_val = request.query_params.get("uuid")
        cuenta_pagar_obj = None
        
        if uuid_val:
            cuenta_pagar_obj = self.cuentas_pagar_selector.get_by_uuid(empresa_id=empresa.id, uuid_val=uuid_val)
            
        context = {
            "cuentas_pagar": cuenta_pagar_obj,
            "empresa": empresa,
        }
        return render_template_safe(
            context,
            "tenant/proveedores/offcanvas_cuentas_pagar.html",
            request=request,
        )

    @action(detail=False, methods=["get"], url_path="dashboard-kpis",
            permission_classes=[IsTenantMember, IsTenantAdminOrReadOnly])
    def dashboard_kpis(self, request, *args, **kwargs):
        """
        FASE 1 — KPIs globales de Cuentas por Pagar para el Dashboard Admin.

        GET /api/v1/proveedores/cuentas-pagar/dashboard-kpis/

        Retorna:
          deuda_total_pendiente    — deuda activa total (SIN_PAGO + PARCIAL)
          total_pagado_historico   — acumulado de pagos realizados
          facturas_pendientes_count — facturas sin pagar o parciales
          facturas_pagadas_count    — facturas completamente pagadas
          deuda_vencida            — deuda con fecha_vencimiento < hoy
          facturas_vencidas_count  — facturas vencidas no pagadas
        """
        empresa = self.get_empresa()
        kpis = self.cuentas_pagar_selector.resumen_por_empresa(empresa_id=empresa.id)
        # Serializar Decimal → str para JSON (DRF no serializa Decimal automáticamente)
        return Response({
            k: str(v) if hasattr(v, 'as_tuple') else v
            for k, v in kpis.items()
        })


# ==============================================================================
# REPRESENTANTE VIEWSET — v3.17.0 (nueva entidad)
# ==============================================================================

class RepresentanteViewSet(OrganizationalContextMixin, RepresentanteServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Representantes de Proveedores (v3.17.0).
    Router plano: GET /api/v1/proveedores/representantes/?proveedor_uuid=<uuid>
    """

    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    queryset = Representante.objects.none()
    serializer_class = RepresentanteDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_serializer_class(self):
        if self.action == 'list':
            return RepresentanteListSerializer
        return RepresentanteDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context['empresa_id'] = empresa.id
        except Exception:
            pass
        return context

    def get_queryset(self):
        empresa = self.get_empresa()
        return Representante.objects.filter(empresa=empresa)

    def get_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_object(self):
        """DSV: empresa + uuid propio es suficiente (router plano, no anidado)."""
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')

        obj = Representante.objects.filter(
            empresa=empresa,
            uuid=representante_uuid
        ).first()

        if not obj:
            raise NotFound("Representante no encontrado en esta empresa.")
        return obj

    def list(self, request, *args, **kwargs):
        """
        Lista representantes.
        ?proveedor_uuid=<uuid>  — filtra por proveedor (desde offcanvas detalle)
        Sin param               — retorna todos los de la empresa (directorio global)
        """
        empresa = self.get_empresa()
        proveedor_uuid = request.query_params.get('proveedor_uuid')

        if proveedor_uuid:
            representantes_qs = self.representante_selector.get_list_por_proveedor(
                empresa_id=empresa.id,
                proveedor_uuid=proveedor_uuid
            )
        else:
            representantes_qs = self.representante_selector.get_list_por_empresa(
                empresa_id=empresa.id
            )

        page = self.paginate_queryset(representantes_qs)
        rows = page if page is not None else list(representantes_qs)

        serializer = RepresentanteListSerializer(rows, many=True, context=self.get_serializer_context())
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crea un representante. proveedor_uuid viene en el body POST."""
        empresa = self.get_empresa()
        proveedor_uuid = request.data.get('proveedor_uuid')

        if not proveedor_uuid:
            return Response(
                {"error": "El campo proveedor_uuid es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            representante = self.representante_service.crear_representante(
                empresa_id=empresa.id,
                proveedor_uuid=proveedor_uuid,
                data=serializer.validated_data
            )
            output_serializer = RepresentanteDetailSerializer(
                representante, context=self.get_serializer_context()
            )
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.exception(f"Error creando representante: {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualiza un representante (DSV via get_object)."""
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            representante = self.representante_service.actualizar_representante(
                empresa_id=empresa.id,
                representante_uuid=representante_uuid,
                data=serializer.validated_data
            )
            output_serializer = RepresentanteDetailSerializer(
                representante, context=self.get_serializer_context()
            )
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception(f"Error actualizando representante: {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Elimina un representante (con guard representante principal)."""
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get('uuid')

        try:
            self.representante_service.eliminar_representante(
                empresa_id=empresa.id,
                representante_uuid=representante_uuid
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            logger.exception(f"Error eliminando representante: {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)