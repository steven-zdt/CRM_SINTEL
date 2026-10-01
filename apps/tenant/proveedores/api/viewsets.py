import logging
from types import SimpleNamespace

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

# PROVEEDORES_NIIF_CHOICES eliminado — AGENTS.md: ninguna app de negocio
# debe tener referencias contables. Contabilidad es la unica propietaria.
from apps.config.api.pagination import StandardResultsSetPagination
from apps.shared.datatable import ColumnFilter, ColumnFilterType, DataTableServer, DataTableSpec
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.utils import render_template_safe, resolve_tenant_empresa
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.proveedores.api.serializers import (
    CuentasPagarAbonoSerializer,
    CuentasPagarDetailSerializer,
    CuentasPagarListSerializer,
    FacturaCxPListSerializer,
    ProveedorDetailSerializer,
    ProveedorListSerializer,
    RepresentanteDetailSerializer,
    RepresentanteListSerializer,
)
from apps.tenant.proveedores.models import CuentasPagar, Proveedor, Representante
from apps.tenant.proveedores.services.api_mixins import (
    CuentasPagarServiceMixin,
    ProveedorServiceMixin,
    RepresentanteServiceMixin,
)

logger = logging.getLogger(__name__)


class ProveedorViewSet(OrganizationalContextMixin, ProveedorServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Proveedores v3.5 - Refactorizado a Service Layer (DSV Mixins).

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    get_queryset()/get_object()/etc. no migrados - resuelven la empresa via
    resolve_tenant_empresa(), mismo mecanismo ya documentado en empresa
    (Fase 9 app 1/14), que no exige TenantProfile.
    """

    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    queryset = Proveedor.objects.none()
    serializer_class = ProveedorDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "list":
            return ProveedorListSerializer
        return ProveedorDetailSerializer

    def get_serializer_context(self):
        """Inyecta la empresa en el contexto del serializer para validaciones."""
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context["empresa_id"] = empresa.id
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
        search = request.query_params.get("search", "").strip()

        queryset = self.proveedor_selector.get_list(empresa.id, search if search else None)

        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)

        # CuentasPagar: una query agrupada para todos los proveedores de la pagina
        uuids = [p.uuid for p in rows if p.uuid]
        cuentas_pagar_map = self.proveedor_selector.get_cuentas_pagar_resumen(empresa.id, uuids)

        ctx = self.get_serializer_context()
        ctx["cuentas_pagar_map"] = cuentas_pagar_map

        serializer = ProveedorListSerializer(rows, many=True, context=ctx)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="dt")
    def dt(self, request):
        """
        DataTables 3.x server-side (mismo patron ya validado en Ventas/
        Bancos/Facturas/Clientes -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md).
        Reemplaza ProveedorTable/ProveedorTableView (django-tables2,
        retirados) para el directorio. La grilla de Cuentas por Pagar
        tambien migro, ver CuentasPagarViewSet.dt() mas abajo (endpoint
        MANUAL -- su fuente es una lista Python, no un QuerySet real).
        cuentas_pagar_resumen se recalcula por pagina via serializer_context
        (misma estrategia sin N+1 que ya usa list()).
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {
                    "draw": int(request.data.get("draw", 0)) if hasattr(request, "data") else 0,
                    "recordsTotal": 0,
                    "recordsFiltered": 0,
                    "data": [],
                },
                status=status.HTTP_200_OK,
            )

        base_qs = self.proveedor_selector.get_list(empresa.id, None, None)

        def _context(req, qs_paginated):
            uuids = [p.uuid for p in qs_paginated if p.uuid]
            ctx = self.get_serializer_context()
            ctx["cuentas_pagar_map"] = self.proveedor_selector.get_cuentas_pagar_resumen(
                empresa.id, uuids
            )
            return ctx

        spec = DataTableSpec(
            fields_map={
                0: "razon_social",
                1: "tipo_persona",
                2: "numero_documento",
                3: "regimen_tributario",
                5: "activo",
            },
            search_fields=[
                "razon_social",
                "numero_documento",
                "email_contacto",
                "nombre_comercial",
            ],
            base_qs=base_qs,
            serializer=ProveedorListSerializer,
            column_filters={
                0: ColumnFilter("razon_social", ColumnFilterType.ICONTAINS),
                1: ColumnFilter("tipo_persona", ColumnFilterType.EXACT),
                2: ColumnFilter("numero_documento", ColumnFilterType.ICONTAINS),
                # Columna 3 renderiza regimen_tributario + badge de
                # retenedor; el filtro real es sobre es_retenedor (mismo
                # criterio que clientes/api/viewsets.py::ClienteViewSet.dt()).
                3: ColumnFilter("es_retenedor", ColumnFilterType.EXACT),
                5: ColumnFilter("activo", ColumnFilterType.EXACT),
            },
            serializer_context=_context,
        )
        return DataTableServer(spec).handle(request)

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
        if len(str(lookup_value)) > 10 or "-" in str(lookup_value):
            obj = Proveedor.objects.filter(uuid=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        # 2. Fallback a PK (si es numérico)
        if str(lookup_value).isdigit():
            obj = Proveedor.objects.filter(pk=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        logger.warning(
            f"[proveedores:DSV] IDOR Intent or Missing Record: Lookup {lookup_value} for Empresa {empresa.id}"
        )
        raise NotFound("Proveedor no encontrado en su organizacion.")

    def retrieve(self, request, *args, **kwargs):
        """Obtiene detalle de un proveedor."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(proveedor, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Crea un proveedor delegando al Business Service.

        `representante` (dict opcional en el body): datos del Representante
        principal a crear en la MISMA transaccion -- ver
        ProveedorBusinessService.crear_proveedor(). No es un campo del
        modelo Proveedor, se extrae de request.data antes de validar contra
        ProveedorDetailSerializer (que la ignoraria de todas formas al no
        estar declarado, pero se extrae explicito para pasarlo al service).
        """
        empresa = self.get_empresa()
        representante_data = request.data.get("representante") or None
        serializer = ProveedorDetailSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        if serializer.is_valid():
            usuario = getattr(request.user, "tenant_profile", None)
            proveedor = self.proveedor_service.crear_proveedor(
                empresa.id,
                serializer.validated_data,
                representante_data=representante_data,
                usuario=usuario,
            )
            return Response(
                ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualiza un proveedor delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(
            proveedor, data=request.data, partial=False, context=self.get_serializer_context()
        )
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(
                proveedor, serializer.validated_data
            )
            return Response(
                ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial delegando al Business Service."""
        proveedor = self.get_object()
        serializer = ProveedorDetailSerializer(
            proveedor, data=request.data, partial=True, context=self.get_serializer_context()
        )
        if serializer.is_valid():
            proveedor = self.proveedor_service.actualizar_proveedor(
                proveedor, serializer.validated_data
            )
            return Response(
                ProveedorDetailSerializer(proveedor, context=self.get_serializer_context()).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Eliminación delegando lógica de protección al Business Service."""
        proveedor = self.get_object()
        try:
            self.proveedor_service.eliminar_proveedor(proveedor)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/crear",
    )
    def render_offcanvas_crear(self, request):
        """Renderiza offcanvas de creación (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix="crear")

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/editar",
    )
    def render_offcanvas_editar(self, request):
        """Renderiza offcanvas de edición (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix="editar")

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/detalle",
    )
    def render_offcanvas_detalle(self, request):
        """Renderiza offcanvas en modo detalle (FSD Compliant)."""
        return self.get_offcanvas_response(request, template_suffix="detalle")

    def get_offcanvas_response(self, request, template_suffix="crear"):
        """Helper para renderizar el Offcanvas con el contexto NIIF."""
        empresa = self.get_empresa()
        proveedor = None
        id_instancia = request.query_params.get("id")

        if id_instancia:
            # v3.5.2: Priorizamos UUID para lookup seguro
            proveedor = self.proveedor_selector.get_by_uuid(empresa.id, id_instancia)
            if not proveedor and str(id_instancia).isdigit():
                # Fallback por PK para compatibilidad
                proveedor = self.proveedor_selector.get_by_id(empresa.id, id_instancia)

        # Datos reales del usuario actual -- solo para precargar el
        # Representante principal cuando tipo_persona=NATURAL (ver
        # ProveedorBusinessService.crear_proveedor()/_construir_payload_
        # representante()). numero_documento/tipo_documento NUNCA se
        # precargan aqui: ni User ni TenantProfile los tienen.
        tenant_profile = getattr(request.user, "tenant_profile", None)
        usuario_actual = None
        if tenant_profile is not None and not proveedor:
            nombre = f"{getattr(request.user, 'first_name', '') or ''} {getattr(request.user, 'last_name', '') or ''}".strip()
            usuario_actual = {
                "nombre_completo": nombre or getattr(request.user, "email", "") or "",
                "email_contacto": getattr(request.user, "email", "") or "",
                "telefono_contacto": getattr(tenant_profile, "telefono_corporativo", "") or "",
                "cargo": getattr(tenant_profile, "cargo", "") or "Representante Legal",
            }

        context = {
            "proveedor": proveedor,
            "empresa": empresa,
            "usuario_actual": usuario_actual,
            "tipo_persona_choices": Proveedor.TIPO_PERSONA,
            "tipo_documento_choices": Proveedor.TIPO_DOCUMENTO,
            "regimen_choices": Proveedor.REGIMEN,
            "tipo_cuenta_choices": [("AHORROS", "Ahorros"), ("CORRIENTE", "Corriente")],
            "modo_detalle": template_suffix == "detalle",
        }

        # v3.5.2: Template universal unificado para evitar desincronización de IDs
        template_name = "tenant/proveedores/offcanvas_form.html"
        return render_template_safe(context, template_name, request=request)

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="gestor-offcanvas",
    )
    def gestor_offcanvas(self, request):
        """Alias para retrocompatibilidad."""
        return self.get_offcanvas_response(request, template_suffix="crear")


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
        Lista Cuentas por Pagar de la empresa: Facturas de compra + CxP sin
        Factura asociada (generadas al aprobar una Orden de Compra o creadas
        a mano) — ver CuentasPagarSelector.qs_list_unificado() (hallazgo real
        2026-08-26: esta vista antes ignoraba por completo el modelo
        CuentasPagar salvo para abonos).

        Filtros opcionales:
          ?proveedor_uuid=<uuid>  — filtrar por proveedor
          ?estado_pago=SIN_PAGO|PARCIAL|PAGADA
          ?vencidas=true          — solo obligaciones vencidas no pagadas
          ?search=<texto>         — numero de factura/CxP, razon social o NIT del proveedor
        """
        empresa = self.get_empresa()
        proveedor_uuid = request.query_params.get("proveedor_uuid") or request.query_params.get(
            "proveedor_id"
        )
        estado_pago = request.query_params.get("estado_pago")
        vencidas = request.query_params.get("vencidas", "").lower() == "true"
        search = (request.query_params.get("search") or "").strip() or None

        qs = self.cuentas_pagar_selector.qs_list_unificado(
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

    @action(detail=False, methods=["post"], url_path="dt")
    def dt(self, request):
        """
        DataTables 3.x server-side, pero MANUAL (no via
        apps/shared/datatable.py::DataTableServer/DataTableSpec, que asume
        un QuerySet real de un solo modelo) -- qs_list_unificado() mezcla 2
        origenes (Factura(COMPRA) + CuentasPagar manuales/generadas desde
        Compras) en una lista Python ya materializada, ver su propio
        docstring: "No es un QuerySet real". Reemplaza CuentasPagarTable/
        CuentasPagarTableView (django-tables2, retirados). Reutiliza
        qs_list_unificado() (misma SSoT y filtros server-side ya validados
        por list()) para busqueda/estado_pago/vencidas -- orden y paginado
        se aplican en Python sobre la lista ya filtrada, DataTables solo
        ve el contrato {draw, recordsTotal, recordsFiltered, data}.

        estado_pago/vencidas llegan por query string en la URL del ajax
        (igual que ?naturaleza= en FacturaViewSet.dt()), no por el body de
        DataTables -- son chips de filtro top-level, no un filtro por
        columna.
        """
        empresa = self.get_empresa()
        body = request.data if hasattr(request, "data") else {}
        draw = int(body.get("draw", 0) or 0)
        start = int(body.get("start", 0) or 0)
        length = int(body.get("length", 10) or 10)
        search_value = ((body.get("search") or {}).get("value") or "").strip() or None
        estado_pago = (request.query_params.get("estado_pago") or "").strip() or None
        vencidas = request.query_params.get("vencidas", "").lower() == "true"

        records_total = len(self.cuentas_pagar_selector.qs_list_unificado(empresa_id=empresa.id))

        filas = self.cuentas_pagar_selector.qs_list_unificado(
            empresa_id=empresa.id,
            estado_pago=estado_pago,
            vencidas=vencidas,
            search=search_value,
        )
        records_filtered = len(filas)

        ORDER_FIELDS = {
            0: "numero",
            1: "emisor_razon_social",
            2: "total",
            4: "payment_due_date",
            5: "estado_pago",
        }
        order = body.get("order") or []
        if order and filas:
            field = ORDER_FIELDS.get(order[0].get("column"))
            if field:
                filas = sorted(
                    filas,
                    key=lambda f: (getattr(f, field) is None, getattr(f, field)),
                    reverse=(order[0].get("dir") == "desc"),
                )

        page = filas[start : start + length] if length > 0 else filas
        serializer = FacturaCxPListSerializer(page, many=True)
        return Response(
            {
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        """
        Detalle ("Ver") de una fila de Cuentas por Pagar -- acepta los 2
        origenes del listado unificado (ver CuentasPagarSelector.
        qs_list_unificado): una CuentasPagar real (usa el ModelSerializer
        completo), o una Factura(COMPRA) que aun no tiene CuentasPagar
        vinculada (solo lectura, sin materializar -- ver
        CuentasPagarSelector.resolver_fila_por_uuid, GET nunca escribe).
        """
        empresa = self.get_empresa()
        uuid_val = self.kwargs.get("uuid")
        cuenta_pagar_obj = self.cuentas_pagar_selector.get_by_uuid(
            empresa_id=empresa.id, uuid_val=uuid_val
        )
        if cuenta_pagar_obj:
            return Response(CuentasPagarDetailSerializer(cuenta_pagar_obj).data)

        fila = self.cuentas_pagar_selector.resolver_fila_por_uuid(
            empresa_id=empresa.id, uuid_val=uuid_val
        )
        if not fila:
            raise NotFound("Registro de Cuentas por Pagar no encontrado en esta empresa.")
        return Response(FacturaCxPListSerializer(fila).data)

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
        proveedor = (
            Proveedor.objects.filter(uuid=proveedor_uuid, empresa_id=empresa.id)
            .only("id", "uuid", "empresa_id", "activo")
            .first()
        )

        if not proveedor:
            raise NotFound("Proveedor no encontrado en esta empresa.")

        # Validacion con el serializer
        serializer = CuentasPagarDetailSerializer(
            data=request.data, context={"empresa_id": empresa.id}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Delegamos la creacion al Service Layer
            cuenta_pagar_obj = self.cuentas_pagar_service.registrar_cuenta_pagar(
                proveedor=proveedor,
                empresa_id=empresa.id,
                datos_cuenta_pagar=serializer.validated_data,
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

    def destroy(self, request, *args, **kwargs):
        """
        Elimina una Cuenta por Pagar (solo registros SIN Factura asociada y
        sin pagos -- ver CuentasPagarBusinessService.eliminar_cuenta_pagar).
        """
        empresa = self.get_empresa()
        uuid_val = self.kwargs.get("uuid")
        try:
            self.cuentas_pagar_service.eliminar_cuenta_pagar(
                cuenta_pagar_uuid=uuid_val,
                empresa_id=empresa.id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas",
    )
    def render_offcanvas(self, request):
        """
        Renderiza offcanvas de gestion de Cuentas por Pagar (HTMX FSD Compliant).

        `?modo=ver` fuerza el panel de solo lectura aunque la obligacion no
        este PAGADA todavia (accion "Ver" de la columna Acciones); sin ese
        parametro (accion "Abonar") se muestra el formulario si aplica.

        [RELEASE-CLOSE / PROVEEDORES-02] Antes usaba directamente el modelo
        CuentasPagar como contexto -- `cuentas_pagar.proveedor_nombre` no
        existe en ese modelo (es `proveedor.razon_social`), asi que el
        nombre del proveedor salia siempre vacio en este panel. Ademas fallaba
        con 404/vacio para filas originadas en una Factura sin CuentasPagar
        aun. Fix: resolver_fila_por_uuid() ya normaliza ambos origenes a la
        misma forma, GET nunca escribe (no materializa).
        """
        empresa = self.get_empresa()
        uuid_val = request.query_params.get("uuid")
        modo = (request.query_params.get("modo") or "").strip().lower()
        cuentas_pagar_ctx = None

        if uuid_val:
            fila = self.cuentas_pagar_selector.resolver_fila_por_uuid(
                empresa_id=empresa.id, uuid_val=uuid_val
            )
            if fila:
                mapa_a_cxp = {
                    "NO_PAGADA": "SIN_PAGO",
                    "PAGO_PARCIAL": "PARCIAL",
                    "PAGADA": "PAGADA",
                }
                cuentas_pagar_ctx = SimpleNamespace(
                    uuid=fila.uuid,
                    proveedor_nombre=fila.emisor_razon_social,
                    numero_factura=fila.numero,
                    fecha_vencimiento=fila.payment_due_date,
                    valor_total=fila.total,
                    saldo=fila.saldo,
                    estado_pago=mapa_a_cxp.get(fila.estado_pago, "SIN_PAGO"),
                )

        context = {
            "cuentas_pagar": cuentas_pagar_ctx,
            "empresa": empresa,
            "modo": modo,
        }
        return render_template_safe(
            context,
            "tenant/proveedores/offcanvas_cuentas_pagar.html",
            request=request,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="dashboard-kpis",
        permission_classes=[IsTenantMember, IsTenantAdminOrReadOnly],
    )
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
        return Response({k: str(v) if hasattr(v, "as_tuple") else v for k, v in kpis.items()})


# ==============================================================================
# REPRESENTANTE VIEWSET — v3.17.0 (nueva entidad)
# ==============================================================================


class RepresentanteViewSet(
    OrganizationalContextMixin, RepresentanteServiceMixin, BaseTenantViewSet
):
    """
    ViewSet para Representantes de Proveedores (v3.17.0).
    Router plano: GET /api/v1/proveedores/representantes/?proveedor_uuid=<uuid>
    """

    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    queryset = Representante.objects.none()
    serializer_class = RepresentanteDetailSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_serializer_class(self):
        if self.action == "list":
            return RepresentanteListSerializer
        return RepresentanteDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            if empresa:
                context["empresa_id"] = empresa.id
        except Exception:
            pass
        return context

    def get_queryset(self):
        empresa = self.get_empresa()
        return Representante.objects.filter(empresa=empresa)

    def get_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    @action(detail=False, methods=["post"], url_path="dt")
    def dt(self, request):
        """
        DataTables 3.x server-side (mismo patron ya validado en Ventas/
        Bancos/Facturas/Clientes/Proveedores/Compras/Gastos/Empleados -- ver
        docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md). Reemplaza el
        Tabulator client-side de representantes_directory.html (traia TODOS
        los representantes de la empresa en un solo GET sin paginacion
        server-side). Solo cubre el directorio global (sin ?proveedor_uuid) --
        el listado de representantes de UN proveedor especifico (dentro del
        offcanvas de detalle) sigue usando list() tal cual, no es una grilla
        independiente.
        """
        empresa = self.get_empresa()
        base_qs = self.representante_selector.get_list_por_empresa(empresa_id=empresa.id)

        spec = DataTableSpec(
            fields_map={0: "numero_documento", 1: "nombre_completo", 2: "cargo"},
            search_fields=["nombre_completo", "numero_documento", "email_contacto"],
            base_qs=base_qs,
            serializer=RepresentanteListSerializer,
            column_filters={
                0: ColumnFilter("numero_documento", ColumnFilterType.ICONTAINS),
                1: ColumnFilter("nombre_completo", ColumnFilterType.ICONTAINS),
                2: ColumnFilter("cargo", ColumnFilterType.ICONTAINS),
            },
        )
        return DataTableServer(spec).handle(request)

    def get_object(self):
        """DSV: empresa + uuid propio es suficiente (router plano, no anidado)."""
        empresa = self.get_empresa()
        representante_uuid = self.kwargs.get("uuid")

        obj = Representante.objects.filter(empresa=empresa, uuid=representante_uuid).first()

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
        proveedor_uuid = request.query_params.get("proveedor_uuid")

        if proveedor_uuid:
            representantes_qs = self.representante_selector.get_list_por_proveedor(
                empresa_id=empresa.id, proveedor_uuid=proveedor_uuid
            )
        else:
            representantes_qs = self.representante_selector.get_list_por_empresa(
                empresa_id=empresa.id
            )

        page = self.paginate_queryset(representantes_qs)
        rows = page if page is not None else list(representantes_qs)

        serializer = RepresentanteListSerializer(
            rows, many=True, context=self.get_serializer_context()
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Crea un representante. proveedor_uuid viene en el body POST."""
        empresa = self.get_empresa()
        proveedor_uuid = request.data.get("proveedor_uuid")

        if not proveedor_uuid:
            return Response(
                {"error": "El campo proveedor_uuid es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            representante = self.representante_service.crear_representante(
                empresa_id=empresa.id, proveedor_uuid=proveedor_uuid, data=serializer.validated_data
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
        representante_uuid = self.kwargs.get("uuid")

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            representante = self.representante_service.actualizar_representante(
                empresa_id=empresa.id,
                representante_uuid=representante_uuid,
                data=serializer.validated_data,
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
        representante_uuid = self.kwargs.get("uuid")

        try:
            self.representante_service.eliminar_representante(
                empresa_id=empresa.id, representante_uuid=representante_uuid
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            logger.exception(f"Error eliminando representante: {exc}")
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
