"""
ViewSets para la app facturas.

# WARNING: v2.30: API-First (DRF JSON-only) - Solo endpoints REST.
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id
- Service Layer: Toda la lógica de negocio está en services.py
- SessionAuthentication: Habilitado para consumo desde workspace (cookies de sesión)

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""
import base64
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, ItemFactura, NotaCredito

# Logger normalizado para facturas (upload, import, etc.)
log_up = logging.getLogger("facturas")

# Claves estándar de LogRecord que NO se pueden pisar
_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "asctime",
    "message"
}

def safe_extra(d: dict) -> dict:
    """
    Devuelve un nuevo dict sin colisión con LogRecord; renombra claves reservadas añadiendo sufijo '_x'.
    
    # WARNING: FORÉNSICA: Evita KeyError "Attempt to overwrite ..." cuando una clave en 'extra'
    colisiona con atributos estándar de LogRecord.
    """
    if not d:
        return {}
    out = {}
    for k, v in d.items():
        out[k + "_x" if k in _RESERVED else k] = v
    return out

from django.conf import settings

# # WARNING: DEPRECATED v2.40: DataTableSpec y DataTableServer eliminados - usar StandardResultsSetPagination
from django.http import HttpResponse

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.facturas.api.mixins import FacturaUBLMixin, FacturaMailMixin, FacturaXMLMixin
from apps.tenant.facturas.inbox_state import update_inbox_state
from apps.tenant.facturas.services import FacturaSelectors, FacturaServiceMixin, FacturaBusinessService, FacturaCRUDService
from apps.tenant.facturas.services.selectors import InventarioItemBridge
from apps.tenant.facturas.utils.ubl_parser import fast_get_cufe
from .serializers import (
    FacturaDetailSerializer,
    FacturaListSerializer,
    FacturaWriteSerializer,
    ImportUBLSerializer,
    ItemFacturaSerializer,
    NotaCreditoDetailSerializer,
    NotaCreditoListSerializer,
)


def mini_error(message: str, code: str, status_code: int) -> Response:
    """
    Helper minimalista para respuestas de error.
    
    Formato: {"error": code, "message": message}
    """
    return Response({"error": code, "message": message}, status=status_code)


def resolve_empresa_id_from_request(request: Request) -> int:
    """
    Resuelve empresa_id sin crear perfiles durante lecturas.

    En pruebas y rutas legacy puede existir usuario autenticado sin
    TenantProfile. Facturas ya usa el singleton Empresa como fallback
    controlado para compatibilidad.
    """
    user = getattr(request, "user", None)
    for attr in ("perfil", "tenant_profile"):
        perfil = getattr(user, attr, None)
        empresa_id = getattr(perfil, "empresa_id", None)
        if empresa_id:
            return empresa_id

    empresa_id = getattr(user, "empresa_id", None)
    if empresa_id:
        return empresa_id

    empresa_id = Empresa.objects.only("id").values_list("id", flat=True).first()
    if empresa_id:
        return empresa_id

    raise ValidationError({"empresa": "No se pudo resolver la empresa activa del tenant."})


class FacturaViewSet(FacturaUBLMixin, FacturaMailMixin, FacturaXMLMixin, FacturaServiceMixin, BaseTenantViewSet):

    """
    FACTURAS MODULE — CONTROL CONTABLE
    
    # WARNING: REGLAS DE NEGOCIO v2.95:
    Las facturas son documentos históricos importados desde sistemas externos.
    - [OK] ELIMINACIÓN: Se habilita la eliminación directa sin restricciones.
    - [OK] La factura puede eliminarse incluso si tiene notas de crédito asociadas.
    - [OK] No hay validaciones que bloqueen la eliminación por vínculos contables o documentos relacionados.
    - # WARNING: EDICIÓN: NUNCA se pueden editar, actualizar o modificar (inmutabilidad solo para edición).
    - Las correcciones fiscales se realizan mediante Notas Crédito/Débito.
    
    Endpoints permitidos:
    - GET /facturas/ → Lista de facturas (paginada)
    - GET /facturas/{id}/ → Detalle de factura (read-only)
    - GET /facturas/{id}/xml/ → XML de factura (auditoría)
    - POST /facturas/upload-ubl/ → Importar factura desde XML UBL (único POST permitido)
    - DELETE /facturas/{id}/ → Eliminar factura (sin restricciones)
    - PATCH /facturas/{id}/ → Edición limitada: fecha_vencimiento, estado, retenciones, formas de pago (v2.95)

    Endpoints bloqueados:
    - POST /facturas/ → 405 Method Not Allowed (solo importación vía upload-ubl)
    - PUT /facturas/{id}/ → 405 Method Not Allowed (uso PATCH en su lugar)
    
    # WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    [OK] Escalable (millones de facturas)
    [OK] Perfecto para supervisión contable
    """
    """
    # WARNING: v2.40: ViewSet para Facturas con Tabulator Factory.
    Usa StandardResultsSetPagination para paginación remota.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]  # # WARNING: v2.40: JSON (principal) + FormParser (legacy) + MultiPartParser (upload)
    renderer_classes = [JSONRenderer]  # # WARNING: v2.40: Solo JSON (no BrowsableAPIRenderer)

    # # WARNING: v2.95: EDICIÓN LIMITADA - PATCH permite cambios en campos específicos (vencimiento, estado, retenciones, formas de pago)
    # GET, DELETE y POST (solo upload-ubl) permitidos. PATCH permitido con restricciones en allowed_fields
    http_method_names = ['get', 'head', 'options', 'post', 'patch', 'delete']
    
    # # WARNING: NO usar queryset = Factura.objects.all()
    # Se define en get_queryset() con only() para optimización
    
    # Filtros y búsqueda
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "estado": ["exact"],
        "naturaleza": ["exact"],
        "fecha_emision": ["date__gte", "date__lte", "date", "gte", "lte", "exact"],
        "cliente_uuid": ["exact"],
        "proveedor_uuid": ["exact"],
    }
    search_fields = ["numero", "cufe", "receptor_razon_social", "emisor_razon_social"]
    ordering_fields = ["fecha_emision", "consecutivo", "total"]
    ordering = ["-fecha_emision", "-consecutivo"]
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_list() y qs_detail() del service.

        # WARNING: v2.40: Alineado con Service Layer Pattern y Tabulator Factory.
        - LIST: usa qs_list() (LIST_FIELDS) con soporte ?search=
        - RETRIEVE: usa qs_detail() (DETAIL_FIELDS)
        - DESTROY: .only() minimo (Zero-Trust DML)

        # WARNING: v2.61.5: Anti-IDOR — empresa_id aplicado en TODAS las acciones
        como defensa en profundidad (django-tenants aisla por schema, pero el filtro
        explicito garantiza que un usuario no acceda a facturas de otra empresa
        dentro del mismo schema).

        Filtros soportados:
        - naturaleza: VENTA|COMPRA
        - nit: busca en emisor_nit o receptor_nit
        - estado: filtro exacto
        - search: busqueda general (Tabulator)
        """
        empresa_id = resolve_empresa_id_from_request(self.request)
        search = self.request.query_params.get('search', None)

        if self.action == "list":
            qs = self.get_qs_list(search=search).filter(empresa_id=empresa_id)
        elif self.action == "retrieve":
            qs = self.get_qs_detail().filter(empresa_id=empresa_id)
        elif self.action == "destroy":
            qs = Factura.objects.filter(empresa_id=empresa_id).only('id', 'estado', 'empresa_id')
        elif self.action in ("partial_update", "update", "cambiar_estado", "vincular_cotizacion", "vincular_cliente", "vincular_proveedor"):
            qs = Factura.objects.filter(empresa_id=empresa_id)
        else:
            qs = self.get_qs_list(search=search).filter(empresa_id=empresa_id)

        request = self.request

        if nat := request.GET.get("naturaleza"):
            if nat in ("VENTA", "COMPRA"):
                qs = qs.filter(naturaleza=nat)

        if nit := request.GET.get("nit"):
            qs = qs.filter(Q(emisor_nit__icontains=nit) | Q(receptor_nit__icontains=nit))

        if estado := request.GET.get("estado"):
            qs = qs.filter(estado=estado)

        if tipo_impuesto := request.GET.get("tipo_impuesto"):
            qs = qs.filter(impuestos_desglosados__tipo_impuesto=tipo_impuesto).distinct()

        return qs.order_by("-fecha_emision", "-id")

    # WARNING: [PERF-N1] N+1 en el listado: FacturaListSerializer.get_retefuente/
    # get_reteica/get_reteiva llamaban a obj.total_retencion_fuente/etc (una query
    # por tipo por fila -- 3 queries x 20 filas = 60 queries extra solo para
    # retenciones). Se intercepta paginate_queryset() (sin reescribir list(), que
    # sigue siendo el ModelViewSet por defecto) para construir un solo mapa
    # {factura_id: {tipo: monto}} con una unica query agrupada y pasarlo al
    # serializer via contexto. Las demas fuentes de N+1 de este mismo listado
    # (cliente/proveedor bridge, banco) quedan documentadas en REPORTE_FASE_4.md
    # como seguimiento pendiente, no resueltas en este cambio.
    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        rows = page if page is not None else queryset
        self._retenciones_map = self._build_retenciones_map(rows)
        return page

    def _build_retenciones_map(self, facturas):
        ids = [f.id for f in facturas]
        if not ids:
            return {}
        try:
            empresa_id = resolve_empresa_id_from_request(self.request)
        except Exception:
            return {}
        if not empresa_id:
            return {}
        from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
        try:
            return RetencionesService.totales_retenciones_por_documentos(
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_ids=ids,
                empresa_id=empresa_id,
            )
        except Exception:
            return {}

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if hasattr(self, '_retenciones_map'):
            ctx['retenciones_map'] = self._retenciones_map
        return ctx

    def get_serializer_class(self):
        """
        Selecciona el serializer según la acción.

        # WARNING: v2.61.2: Acciones @action que no usan serializer retornan None.
        # WARNING: v2.95: PATCH (partial_update) usa FacturaWriteSerializer con permisos de escritura
        """
        # # WARNING: v2.61.2: Acciones que no usan serializer (trabajan directamente con request.data)
        if self.action in ['create-from-dto', 'materialize', 'importar-ubl', 'upload-ubl', 'upload-document',
                           'summary', 'xml', 'app-response', 'update-inbox-state', 'gestor-offcanvas',
                           'lista-centro-costos', 'por_estado', 'cambiar_estado', 'vincular_cotizacion',
                           'vincular_cliente', 'vincular_proveedor']:
            return None

        if self.action == "list":
            return FacturaListSerializer
        elif self.action in ["partial_update", "update"]:
            return FacturaWriteSerializer
        return FacturaDetailSerializer
    
    def get_serializer(self, *args, **kwargs):
        """
        # WARNING: v2.61.2: Si get_serializer_class retorna None, no crear serializer.
        Esto evita errores cuando las acciones @action no usan serializer.
        """
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return None
        return super().get_serializer(*args, **kwargs)
    
    def update(self, request: Request, *args, **kwargs) -> Response:
        """
        Bloqueado: Las facturas son inmutables.
        
        # WARNING: IMPORTANTE: Las facturas NO pueden ser editadas.
        Las correcciones se realizan mediante Notas Crédito/Débito.
        
        Returns:
            405 Method Not Allowed
        """
        return Response(
            {
                "detail": "Las facturas son documentos contables inmutables. "
                         "Las correcciones se realizan mediante Notas Crédito/Débito."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        Edición limitada: Solo campos permitidos via Service Layer.

        # WARNING: SINTEL v3.5: Delegación a BusinessService para DSV y Sanitización.
        """
        factura = self.get_object()
        empresa_id = resolve_empresa_id_from_request(request)

        try:
            with transaction.atomic():
                factura = FacturaBusinessService.actualizar_factura_limitado(
                    factura=factura,
                    data=request.data,
                    empresa_id=empresa_id
                )

            serializer = self.get_serializer(factura)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({"error": "validation_error", "detail": msgs}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, IntegrityError, ProtectedError) as e:
            return Response(
                {"error": "update_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log_up.error(f"[facturas:partial_update] Unexpected error: {str(e)}", extra={"factura_id": factura.id})
            return Response(
                {"error": "internal_error", "detail": "Ocurrió un error inesperado al actualizar la factura."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=["patch"], url_path="vincular-cotizacion")
    def vincular_cotizacion(self, request: Request, uuid=None) -> Response:
        """
        Vincula o desvincula una cotización a esta factura.
        # WARNING: SINTEL v3.5: Delegación a BusinessService.
        """
        factura = self.get_object()
        empresa_id = resolve_empresa_id_from_request(request)

        # Wrap in dict to match business service expected data
        data = {"cotizacion_uuid": request.data.get("cotizacion_uuid")}

        try:
            with transaction.atomic():
                factura = FacturaBusinessService.actualizar_factura_limitado(
                    factura=factura,
                    data=data,
                    empresa_id=empresa_id
                )

            # Retrieve detail serializer manually since get_serializer_class returns None for actions
            return Response(FacturaDetailSerializer(factura).data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({"error": "validation_error", "detail": msgs}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, IntegrityError, ProtectedError) as e:
            return Response(
                {"error": "update_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["patch"], url_path="vincular-cliente")
    def vincular_cliente(self, request: Request, uuid=None) -> Response:
        """
        Vincula un cliente a una factura de venta.
        """
        factura = self.get_object()
        empresa_id = resolve_empresa_id_from_request(request)

        try:
            with transaction.atomic():
                factura = FacturaBusinessService.vincular_cliente(
                    factura=factura,
                    cliente_uuid=request.data.get("cliente_uuid"),
                    empresa_id=empresa_id,
                )

            return Response(
                FacturaDetailSerializer(factura, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({"error": "validation_error", "detail": msgs}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, IntegrityError, ProtectedError) as e:
            return Response(
                {"error": "update_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log_up.error(f"[facturas:vincular_cliente] Unexpected error: {str(e)}", extra={"factura_id": factura.id})
            return Response(
                {"error": "internal_error", "detail": "Ocurrió un error inesperado al vincular el cliente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["patch"], url_path="vincular-proveedor")
    def vincular_proveedor(self, request: Request, uuid=None) -> Response:
        """
        Vincula un proveedor a una factura de compra.
        """
        factura = self.get_object()
        empresa_id = resolve_empresa_id_from_request(request)

        try:
            with transaction.atomic():
                factura = FacturaBusinessService.vincular_proveedor(
                    factura=factura,
                    proveedor_uuid=request.data.get("proveedor_uuid"),
                    empresa_id=empresa_id,
                )

            return Response(
                FacturaDetailSerializer(factura, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msgs = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({"error": "validation_error", "detail": msgs}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, IntegrityError, ProtectedError) as e:
            return Response(
                {"error": "update_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log_up.error(f"[facturas:vincular_proveedor] Unexpected error: {str(e)}", extra={"factura_id": factura.id})
            return Response(
                {"error": "internal_error", "detail": "Ocurrió un error inesperado al vincular el proveedor."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Bloqueado: Las facturas solo se crean mediante importación UBL.
        
        # WARNING: IMPORTANTE: Las facturas son documentos históricos importados.
        No se pueden crear manualmente. Use /upload-ubl/ o /importar-ubl/.
        
        Returns:
            405 Method Not Allowed
        """
        return Response(
            {
                "detail": "Las facturas son documentos históricos importados. "
                         "Use /api/v1/facturas/upload-ubl/ para importar desde XML UBL."
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Eliminación directa de facturas (sin restricciones de inmutabilidad).
        
        # WARNING: NUEVA POLÍTICA v2.95:
        - Se habilita la eliminación directa de facturas sin restricciones.
        - La factura puede eliminarse incluso si tiene notas de crédito asociadas.
        - No hay validaciones que bloqueen la eliminación por vínculos contables o documentos relacionados.
        - La inmutabilidad solo aplica para EDICIÓN (update/partial_update), no para eliminación.
        
        # WARNING: OBJETIVO: Simplificar el manejo del ciclo de facturación permitiendo la depuración 
        y gestión operativa sin restricciones innecesarias.
        
        # WARNING: MAPEO DE ERRORES:
        - 404 si no existe (DRF maneja automáticamente)
        - 409 si hay dependencias protegidas a nivel de base de datos (ProtectedError/IntegrityError)
        - 204 si borra ok
        
        # WARNING: v2.95: Service Layer Pattern - Usa services.eliminar_factura()
        
        Returns:
            204 No Content si se elimina exitosamente
            409 Conflict solo si hay restricciones de integridad a nivel de BD (muy raro)
            500 Internal Server Error solo para errores inesperados
        """
        log_del = logging.getLogger("facturas.delete")
        
        try:
            instance = self.get_object()  # Si no existe -> DRF lanza 404 automáticamente

            # # WARNING: v2.95: Eliminación directa sin validaciones de negocio
            # Se eliminan todas las restricciones de CUFE, estado, notas de crédito, etc.
            # La eliminación se permite siempre, excepto por restricciones de integridad de BD

            # Guardar datos ANTES de eliminar (avoid refresh_from_db() en instancia deletada)
            factura_id = instance.id
            factura_numero = instance.numero
            factura_cufe = instance.cufe
            factura_estado = instance.estado

            # Eliminar usando servicio (a través del mixin de herencia)
            self.service_eliminar(instance)

            log_del.info("delete_ok", extra=safe_extra({
                "id": factura_id,
                "numero": factura_numero,
                "cufe": factura_cufe,
                "estado": factura_estado,
            }))
            
            resp = Response(status=status.HTTP_204_NO_CONTENT)
            resp["HX-Trigger"] = "listaFacturasChanged"
            return resp
            
        except Http404:
            raise
        except ProtectedError as ex:
            # Solo errores de integridad a nivel de BD (muy raro, solo si hay FK con PROTECT)
            log_del.warning("protected_relation", extra=safe_extra({
                "error": str(ex)[:200],
            }))
            return Response(
                {"error": "protected_relation", "message": "Existen registros relacionados que impiden la eliminación a nivel de base de datos."},
                status=status.HTTP_409_CONFLICT
            )
        except IntegrityError as ex:
            # Solo errores de integridad a nivel de BD
            log_del.warning("integrity_error", extra=safe_extra({
                "error": str(ex)[:200],
            }))
            return Response(
                {"error": "integrity_error", "message": "No se puede eliminar por restricciones de integridad de base de datos."},
                status=status.HTTP_409_CONFLICT
            )
        except Exception:
            # Loggea el ex pero no expongas detalles sensibles
            log_del.exception("delete_failed")
            return Response(
                {"error": "delete_failed", "message": "No fue posible eliminar la factura."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="por-estado")
    def por_estado(self, request: Request) -> Response:
        """
        Filtra facturas por estado.

        GET /api/v1/facturas/por-estado/?estado=ACEPTADA

        Params:
            estado (str): Uno de BORRADOR|ENVIADA|ACEPTADA|RECHAZADA|ANULADA

        Returns:
            200 OK con lista paginada de facturas del estado solicitado.
            400 Bad Request si falta el parametro estado.
        """
        estado = request.query_params.get("estado")
        if not estado:
            return Response(
                {"error": "missing_param", "detail": "El parametro 'estado' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_states = {choice[0] for choice in Factura.Estado.choices}
        if estado not in valid_states:
            return Response(
                {"error": "invalid_estado", "detail": f"Estado invalido. Opciones: {sorted(valid_states)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(estado=estado)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = FacturaListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = FacturaListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request: Request, uuid=None) -> Response:
        """
        Cambia el estado de una factura.

        POST /api/v1/facturas/{uuid}/cambiar-estado/
        Body: {"estado": "ENVIADA"}

        Params:
            estado (str): Uno de BORRADOR|ENVIADA|ACEPTADA|RECHAZADA|ANULADA

        Returns:
            200 OK con FacturaDetailSerializer.
            400 Bad Request si el estado es invalido o falta.
        """
        nuevo_estado = request.data.get("estado")
        if not nuevo_estado:
            return Response(
                {"error": "missing_param", "detail": "El campo 'estado' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_states = {choice[0] for choice in Factura.Estado.choices}
        if nuevo_estado not in valid_states:
            return Response(
                {"error": "invalid_estado", "detail": f"Estado invalido. Opciones: {sorted(valid_states)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        factura = self.get_object()
        empresa_id = resolve_empresa_id_from_request(request)

        # DSV: verificar propiedad del tenant
        if factura.empresa_id != empresa_id:
            return Response(
                {"error": "forbidden", "detail": "La factura no pertenece a la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            factura = FacturaCRUDService.actualizar(factura, {"estado": nuevo_estado})
        except Exception as e:
            log_up.error(f"[facturas:cambiar_estado] Error: {e}", extra={"factura_uuid": str(factura.uuid)})
            return Response(
                {"error": "update_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FacturaDetailSerializer(factura, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        """
        Endpoint para obtener resumen de facturación neta.
        
        # WARNING: v2.40: Excluye facturas con Nota de Crédito asociada.
        Retorna desglose por naturaleza (VENTA/COMPRA) con subtotal, impuestos y total neto.
        
        Returns:
            {
                "ventas": {
                    "subtotal_neto": "100000.00",
                    "impuestos_neto": "19000.00",
                    "total_neto": "119000.00",
                    "cantidad": 5
                },
                "compras": {
                    "subtotal_neto": "50000.00",
                    "impuestos_neto": "9500.00",
                    "total_neto": "59500.00",
                    "cantidad": 2
                }
            }
        """
        try:
            # Obtener empresa del tenant (opcional, para filtrado futuro)
            empresa_id = None
            if hasattr(request.user, 'empresa_id'):
                empresa_id = request.user.empresa_id
            
            summary = self.get_summary(empresa_id=empresa_id)
            
            summary_serialized = {
                "ventas": {k: str(v) if isinstance(v, Decimal) else v for k, v in summary["ventas"].items()},
                "compras": {k: str(v) if isinstance(v, Decimal) else v for k, v in summary["compras"].items()}
            }
            
            return Response(summary_serialized, status=status.HTTP_200_OK)
        except Exception as e:
            log_up.error(f"Error obteniendo resumen de facturación: {e}", exc_info=True)
            return Response(
                {"error": "error_calculando_resumen", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='lista-centro-costos')
    def lista_centro_costos(self, request):
        """
        Endpoint ligero para selección de centros de costo en Proyectos.
        
        # WARNING: v3.5 Zero Waste:
        - Usa selector optimizado qs_centros_costo()
        - Retorna solo ID, Número y Receptor
        - Filtrado automático por tenant mediante perfil
        """
        empresa_id = resolve_empresa_id_from_request(request)

        qs = FacturaSelectors.qs_centros_costo().filter(empresa_id=empresa_id)
        
        # Serialización ligera para máxima velocidad
        data = list(qs.values('id', 'numero', 'receptor_razon_social'))
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        """Retorna detalle de factura con metadatos de anexos (sin contenido XML)."""
        # # WARNING: v2.61.5: Delegar queryset a get_queryset() -> qs_detail() que ya incluye
        # select_related(nota_credito, anexos) con .only(*DETAIL_FIELDS). No sobreescribir self.queryset.
        self.serializer_class = FacturaDetailSerializer
        return super().retrieve(request, *args, **kwargs)
    
    # # WARNING: FASE 4: Acciones detail para anexos XML y Buzón IMAP delegadas a mixins (FacturaXMLMixin, FacturaMailMixin)
    
    @action(detail=False, methods=['get'], url_path='obtener-retenciones')
    def obtener_retenciones(self, request: Request) -> Response:
        """
        Obtiene retenciones aplicables desde Cliente (VENTA).
        Para COMPRA, retorna defaults (0.00) ya que las retenciones están en el XML.

        Query params:
        - nit: NIT del cliente (solo para VENTA)
        - naturaleza: VENTA o COMPRA

        Returns:
            {
                "aplica_retefuente": bool,
                "retefuente_porcentaje": Decimal,
                "aplica_reteica": bool,
                "reteica_porcentaje": Decimal,
                "aplica_reteiva": bool,
                "reteiva_porcentaje": Decimal,
            }
        """
        naturaleza = request.query_params.get('naturaleza', 'VENTA')

        try:
            # COMPRA: retenciones ya están en el XML, no extraer de Proveedores
            if naturaleza == 'COMPRA':
                return Response({
                    "aplica_retefuente": False,
                    "retefuente_porcentaje": "0.00",
                    "aplica_reteica": False,
                    "reteica_porcentaje": "0.00",
                    "aplica_reteiva": False,
                    "reteiva_porcentaje": "0.00",
                }, status=status.HTTP_200_OK)

            # VENTA: extraer desde Cliente
            nit = request.query_params.get('nit')
            if not nit:
                return Response({
                    "error": "missing_nit",
                    "message": "Parámetro 'nit' es obligatorio"
                }, status=status.HTTP_400_BAD_REQUEST)

            empresa_id = resolve_empresa_id_from_request(request)
            retenciones = self.service_obtener_retenciones_cliente(nit, empresa_id)

            # Convertir Decimal a string para JSON
            result = {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in retenciones.items()
            }

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Error obteniendo retenciones")
            return Response({
                "error": "internal_error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        # WARNING: v2.60: Devuelve el HTML del formulario de factura para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/facturas/gestor-offcanvas/?id=<factura_id>
        
        Reglas:
        - Si recibe `id`, devuelve la factura en modo lectura (ReadOnly) si ya está emitida,
          o permite edición si es borrador.
        - Si no recibe `id`, devuelve formulario vacío para nueva factura.
        
        # WARNING: ZERO TRUST: Valida que la factura pertenezca al tenant del usuario.
        # WARNING: ZERO WASTE: Solo carga campos necesarios para el visualizador.
        
        Returns:
            HTML template con el formulario Offcanvas (ruta centralizada en core)
        """
        # Acepta ?id= (cargarOffcanvas) o ?uuid= (btn Ver legacy)
        factura_id = request.query_params.get('id') or request.query_params.get('uuid')
        context = {}

        # # WARNING: v2.60: Determinar qué template usar según el modo
        # - Modo simple (subida/detalle): tenant/facturas/partials/offcanvas_factura.html
        # - Modo edición completa: tenant/facturas/partials/offcanvas_form.html
        use_simple_template = request.query_params.get('simple', 'true').lower() == 'true'

        if factura_id:
            try:
                # # WARNING: ZERO TRUST: Validar que la factura pertenece al tenant
                # Obtener empresa del tenant (patrón Singleton)
                empresa = Empresa.objects.only('id').first()
                if not empresa:
                    context['error'] = "No se encontró la empresa (SSoT) configurada para este tenant."
                    template_name = 'tenant/facturas/offcanvas_crear_factura.html' if use_simple_template else 'tenant/facturas/offcanvas_editar_factura.html'
                    return Response(context, template_name=template_name)

                # # WARNING: ZERO WASTE: Solo cargar campos necesarios para el visualizador
                # # WARNING: v2.61.2: Si es modo readonly, cargar también items para el template de solo lectura
                readonly_mode = request.query_params.get('readonly', 'false').lower() == 'true'
                if use_simple_template:
                    if readonly_mode:
                        # Template de solo lectura: cargar campos básicos + items
                        factura = Factura.objects.select_related('anexos').prefetch_related('items').filter(
                            empresa=empresa,
                            uuid=factura_id
                        ).only(
                            'id',
                            'numero',
                            'emisor_razon_social',
                            'emisor_nit',
                            'receptor_razon_social',
                            'receptor_nit',
                            'subtotal',
                            'impuestos',
                            'total',
                            'moneda',
                            'estado',
                            'fecha_emision',
                            'cufe',
                            'anexos__pdf_file',
                            'anexos__ubl_xml'
                        ).first()
                    else:
                        # Template simple: solo campos básicos para detalle/subida
                        factura = Factura.objects.select_related('anexos').filter(
                            empresa=empresa,
                            uuid=factura_id
                        ).only(
                            'id',
                            'numero',
                            'receptor_razon_social',
                            'receptor_nit',
                            'total',
                            'moneda',
                            'estado',
                            'fecha_emision',
                            'cufe',
                            'anexos__pdf_file',
                            'anexos__ubl_xml'
                        ).first()
                else:
                    # Template completo: mas campos para edicion
                    # # WARNING: v2.61.5: Zero Waste - .only() con campos necesarios para el editor
                    factura = Factura.objects.select_related('anexos').prefetch_related('items').filter(
                        empresa=empresa,
                        uuid=factura_id
                    ).only(
                        'id', 'uuid', 'numero', 'prefijo', 'consecutivo', 'tipo', 'estado', 'estado_pago', 'naturaleza',
                        'fecha_emision', 'fecha_vencimiento',
                        'emisor_nit', 'emisor_razon_social', 'emisor_direccion', 'emisor_email', 'emisor_telefono',
                        'receptor_nit', 'receptor_razon_social', 'receptor_direccion', 'receptor_email', 'receptor_telefono',
                        'moneda', 'categoria', 'forma_pago', 'medio_pago_codigo', 'payment_due_date',
                        'subtotal', 'impuestos', 'total',
                        'cotizacion_uuid', 'cotizacion_numero',
                        'cliente_uuid', 'proveedor_uuid',
                        'cufe', 'qr_url',
                        'dian_validation_code', 'dian_validation_desc', 'dian_validation_fecha',
                        'anexos__pdf_file', 'anexos__ubl_xml', 'anexos__application_response_xml',
                    ).first()

                if not factura:
                    context['error'] = "Factura no encontrada o no pertenece a este tenant."
                    return Response(context, template_name='tenant/facturas/offcanvas_crear_factura.html')

                context['factura'] = factura

                # Resolver fichas de cliente/proveedor via Bridge (sin N+1)
                from apps.tenant.facturas.services.selectors import ClienteBridge, ProveedorBridge
                if factura.cliente_uuid:
                    context['cliente_info'] = ClienteBridge.obtener_cliente_por_uuid(
                        str(factura.cliente_uuid), empresa.id
                    )
                if factura.proveedor_uuid:
                    context['proveedor_info'] = ProveedorBridge.obtener_proveedor_por_uuid(
                        str(factura.proveedor_uuid), empresa.id
                    )

                # Determinar si es modo lectura o edición
                # # WARNING: REGLA: Solo borradores pueden editarse
                context['readonly'] = factura.estado != Factura.Estado.BORRADOR
                context['es_emitida'] = factura.estado in [
                    Factura.Estado.ENVIADA,
                    Factura.Estado.ACEPTADA,
                    Factura.Estado.RECHAZADA,
                    Factura.Estado.ANULADA
                ]
                
                # # WARNING: v2.61.2: Si es modo simple y readonly, usar template de solo lectura
                readonly_mode = request.query_params.get('readonly', 'false').lower() == 'true'
                if use_simple_template and (context['es_emitida'] or readonly_mode):
                    # Usar template de solo lectura si está en modo readonly o la factura está emitida
                    if readonly_mode:
                        return Response(context, template_name='tenant/facturas/offcanvas_detalle_factura.html')
                    return Response(context, template_name='tenant/facturas/offcanvas_crear_factura.html')
            except Exception as e:
                log_up.warning(f"Error al obtener factura para Offcanvas: {e}", exc_info=True)
                context['error'] = "No se pudo cargar la factura."
        else:
            # Modo creación (subida de archivo)
            context['factura'] = None
            context['readonly'] = False
            context['es_emitida'] = False
            
            # Si es modo simple, usar template simple para subida
            if use_simple_template:
                return Response(context, template_name='tenant/facturas/offcanvas_crear_factura.html')
        
        # Pasar choices para selects (solo necesario para template completo)
        context['tipos_factura'] = Factura.TipoFactura.choices
        context['estados'] = Factura.Estado.choices
        context['estados_pago'] = Factura.EstadoPago.choices
        context['naturalezas'] = Factura.Naturaleza.choices
        context['categorias'] = Factura.Categoria.choices

        # v3.11.0: datos de conciliacion bancaria para el JS del editor
        if context.get('factura'):
            _f = context['factura']
            context['total_pagado_bancos'] = str(_f.total_pagado_bancos)
            context['saldo_pendiente']     = str(_f.saldo_pendiente)
        else:
            context['total_pagado_bancos'] = '0.00'
            context['saldo_pendiente']     = '0.00'

        # Template completo para edición
        return Response(context, template_name='tenant/facturas/offcanvas_editar_factura.html')

    @action(detail=False, methods=["get"], url_path="inventario-catalogo")
    def inventario_catalogo(self, request: Request) -> Response:
        """
        Busca productos y servicios unificados del inventario.
        """
        from .serializers import CatalogoItemInventarioSerializer

        empresa_id = resolve_empresa_id_from_request(request)

        search = request.query_params.get("q", "")
        catalogo = InventarioItemBridge.buscar_catalogo(empresa_id=empresa_id, search=search)

        serializer = CatalogoItemInventarioSerializer(catalogo, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="trazabilidad-inventario")
    def trazabilidad_inventario(self, request: Request, pk=None) -> Response:
        """
        Retorna la trazabilidad de los items de la factura con respecto al inventario.
        """
        factura = self.get_object()
        items = factura.items.all().only(
            "id", "uuid", "codigo", "descripcion", "cantidad",
            "item_inventario_uuid", "item_inventario_tipo", "item_inventario_codigo"
        )
        
        empresa_id = resolve_empresa_id_from_request(request)

        trazabilidad = []
        for item in items:
            info = None
            if item.item_inventario_uuid and item.item_inventario_tipo:
                info = InventarioItemBridge.resolver_item(
                    empresa_id=empresa_id,
                    item_uuid=item.item_inventario_uuid,
                    item_tipo=item.item_inventario_tipo
                )
            trazabilidad.append({
                "item_factura_id": item.id,
                "item_factura_uuid": str(item.uuid),
                "codigo_factura": item.codigo,
                "descripcion_factura": item.descripcion,
                "cantidad": float(item.cantidad),
                "vinculado": info is not None,
                "item_inventario": info
            })
            
        return Response(trazabilidad, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='buscar-para-movimiento')
    def buscar_para_movimiento(self, request):
        """
        Búsqueda de facturas para vincular con movimientos de inventario.
        GET /api/v1/facturas/buscar-para-movimiento/?q=FV-2026-001&naturaleza=VENTA
        Retorna: [{ numero, fecha, receptor_razon_social, total, naturaleza }]
        """
        query = request.query_params.get('q', '').strip()
        naturaleza = request.query_params.get('naturaleza', '').strip()

        if len(query) < 2:
            return Response([], status=status.HTTP_200_OK)

        empresa_id = resolve_empresa_id_from_request(request)
        qs = Factura.objects.filter(empresa_id=empresa_id).only(
            'uuid', 'numero', 'fecha_emision', 'receptor_razon_social', 'receptor_nit',
            'total', 'naturaleza'
        )

        # Búsqueda por número o cliente
        qs = qs.filter(
            Q(numero__icontains=query) | Q(receptor_razon_social__icontains=query)
        )

        # Filtro por naturaleza si se proporciona
        if naturaleza in ('VENTA', 'COMPRA'):
            qs = qs.filter(naturaleza=naturaleza)

        # Ordenar por fecha descendente, límite 20 resultados
        qs = qs.order_by('-fecha_emision')[:20]

        resultados = [
            {
                'uuid': str(f.uuid),
                'numero': f.numero,
                'fecha': f.fecha_emision.strftime('%d/%m/%Y') if f.fecha_emision else '',
                'cliente': f.receptor_razon_social or f.receptor_nit or 'N/A',
                'total': str(f.total),
                'naturaleza': f.naturaleza
            }
            for f in qs
        ]

        return Response(resultados, status=status.HTTP_200_OK)

class ItemFacturaViewSet(BaseTenantViewSet):
    """
    Endpoints para ítems de factura.

    # WARNING: NOTA: CRUD completo de ítems se recomienda gestionarlo a través de Factura (items embed).
    Este ViewSet expone list, retrieve, update (parcial) y destroy para casos específicos.
    v3.9.2: Actualización de campos item_inventario_* para vinculación.

    # WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() cuando sea necesario.

    Endpoints disponibles:
    - GET /api/v1/items-factura/ (lista de ítems con filtro por factura)
    - GET /api/v1/items-factura/{uuid}/ (detalle de un ítem)
    - PATCH /api/v1/items-factura/{uuid}/ (actualizar ítem — campos item_inventario_* v3.9.2+)
    - DELETE /api/v1/items-factura/{uuid}/ (eliminar un ítem)
    """
    permission_classes = [IsTenantMember, IsAuthenticated]
    serializer_class = ItemFacturaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['factura_id']
    http_method_names = ["get", "head", "options", "patch", "delete"]

    def get_queryset(self):
        """
        QuerySet optimizado - NO usa .all().
        Filtra por factura si se proporciona el parámetro factura_id o factura.
        Incluye campos de inventario para vinculación v3.9.2+.
        """
        empresa_id = resolve_empresa_id_from_request(self.request)

        qs = ItemFactura.objects.filter(empresa_id=empresa_id).only(
            "id", "uuid", "empresa_id", "factura_id", "linea_id", "codigo", "descripcion",
            "cantidad", "unidad_medida", "valor_unitario", "porcentaje_iva",
            "valor_iva", "porcentaje_retefuente", "valor_retefuente",
            "porcentaje_reteiva", "valor_reteiva", "porcentaje_reteica", "valor_reteica",
            "subtotal", "total", "es_servicio", "orden",
            "item_inventario_uuid", "item_inventario_tipo", "item_inventario_codigo"
        )

        # Filtro por factura (soporta 'factura' o 'factura_id' en query params)
        factura_id = self.request.query_params.get('factura') or self.request.query_params.get('factura_id')
        if factura_id:
            qs = qs.filter(factura_id=factura_id)

        return qs.order_by('orden')


class NotaCreditoViewSet(BaseTenantViewSet):
    """
    NOTAS CRÉDITO — Endpoints para gestión de notas crédito.
    
    # WARNING: REGLAS DE NEGOCIO:
    Las notas crédito son documentos históricos que corrigen facturas.
    - Solo se pueden eliminar para corregir un error de carga (rollback técnico).
    - NUNCA se pueden editar, actualizar o modificar.
    - Se crean únicamente mediante importación XML UBL (pipeline canónico).
    
    Endpoints permitidos:
    - GET /notas-credito/ → Lista de notas crédito (paginada)
    - GET /notas-credito/{uuid}/ → Detalle de nota crédito (read-only)
    - GET /notas-credito/{uuid}/xml/ → XML de nota crédito (artefacto pesado)
    - DELETE /notas-credito/{uuid}/ → Eliminar nota crédito (rollback de error de carga)
    
    Endpoints bloqueados:
    - POST /notas-credito/ → 405 Method Not Allowed (solo importación vía pipeline XML)
    - PUT /notas-credito/{uuid}/ → 405 Method Not Allowed
    - PATCH /notas-credito/{uuid}/ → 405 Method Not Allowed
    
    # WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    [OK] Escalable (millones de notas crédito)
    [OK] Artefactos pesados (XML) solo en endpoint /xml/
    """
    permission_classes = [IsTenantMember, IsAuthenticated]
    http_method_names = ["get", "head", "options", "delete"]  # # WARNING: v2.40: POST eliminado (datatables deprecated)
    
    def get_serializer_class(self):
        """Usa ListSerializer para list, DetailSerializer para retrieve."""
        if self.action == "list":
            return NotaCreditoListSerializer
        return NotaCreditoDetailSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado - NO usa .all().
        
        # WARNING: OPTIMIZACIÓN: Para list, solo campos esenciales (sin xml_content).
        """
        empresa_id = resolve_empresa_id_from_request(self.request)

        if self.action == "list":
            return NotaCredito.objects.select_related("factura").filter(empresa_id=empresa_id).only(
                "id", "uuid", "empresa_id", "numero", "cude", "fecha_emision", "moneda",
                "subtotal", "impuestos", "total", "motivo",
                "ref_factura_numero", "ref_factura_cufe",
                "factura__numero", "factura__cufe",
                "created_at"
            )
        # Para retrieve, incluir más campos pero aún sin xml_content
        return NotaCredito.objects.select_related("factura").filter(empresa_id=empresa_id).only(
            "id", "uuid", "empresa_id", "numero", "cude", "fecha_emision", "moneda",
            "subtotal", "impuestos", "total", "motivo",
            "ref_factura_numero", "ref_factura_cufe",
            "factura__id", "factura__numero", "factura__cufe",
            "created_at", "updated_at"
        )
    
    # # WARNING: DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/facturas/notas-credito/ con StandardResultsSetPagination
    
    @action(detail=True, methods=["get"], url_path="xml")
    def xml(self, request, uuid=None):
        """
        Endpoint dedicado para XML completo (artefacto pesado).
        
        # WARNING: ARQUITECTURA: Artefactos pesados solo en endpoints /xml/
        [OK] No se incluye en listas/detalles (optimización)
        """
        nota = self.get_object()
        
        if not nota.xml_content:
            return Response({
                "error": "not_found",
                "message": "No se encontró XML para esta nota crédito."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Retornar XML como HttpResponse para archivos grandes
        response = HttpResponse(
            nota.xml_content,
            content_type="application/xml; charset=utf-8"
        )
        response["Content-Disposition"] = f'inline; filename="nota_credito_{nota.numero}.xml"'
        return response
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /notas-credito/{id}/ → Eliminar nota crédito (rollback técnico).
        
        # WARNING: REGLA: Solo para corregir errores de carga.
        # WARNING: PROTECCIÓN: OneToOneField con PROTECT evita borrado accidental de factura.
        """
        try:
            nota = self.get_object()
            nota.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError as e:
            log_up.warning(f"Intento de borrar nota crédito {kwargs.get('pk')} protegida: {str(e)}")
            return Response({
                "error": "protected",
                "message": "No se puede eliminar esta nota crédito porque está protegida."
            }, status=status.HTTP_409_CONFLICT)
