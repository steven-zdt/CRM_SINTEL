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
from apps.tenant.facturas.services import FacturaSelectors, FacturaServiceMixin, FacturaBusinessService
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


class FacturaViewSet(FacturaServiceMixin, BaseTenantViewSet):

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
        # Garantiza que el perfil exista y obtén empresa_id de forma segura
        from apps.tenant.perfil.services.perfil_service import get_or_create_profile
        perfil = get_or_create_profile(self.request.user)
        empresa_id = perfil.empresa_id
        search = self.request.query_params.get('search', None)

        if self.action == "list":
            qs = self.get_qs_list(search=search).filter(empresa_id=empresa_id)
        elif self.action == "retrieve":
            qs = self.get_qs_detail().filter(empresa_id=empresa_id)
        elif self.action == "destroy":
            qs = Factura.objects.filter(empresa_id=empresa_id).only('id', 'estado', 'empresa_id')
        elif self.action in ("partial_update", "update"):
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

        return qs.order_by("-fecha_emision", "-id")
    
    def get_serializer_class(self):
        """
        Selecciona el serializer según la acción.

        # WARNING: v2.61.2: Acciones @action que no usan serializer retornan None.
        # WARNING: v2.95: PATCH (partial_update) usa FacturaWriteSerializer con permisos de escritura
        """
        # # WARNING: v2.61.2: Acciones que no usan serializer (trabajan directamente con request.data)
        if self.action in ['create-from-dto', 'materialize', 'importar-ubl', 'upload-ubl', 'upload-document',
                           'summary', 'xml', 'app-response', 'update-inbox-state', 'gestor-offcanvas',
                           'lista-centro-costos']:
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
        from apps.tenant.perfil.services.perfil_service import get_or_create_profile
        empresa_id = get_or_create_profile(request.user).empresa_id

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
    
    @action(detail=False, methods=["post"], url_path="importar-ubl")
    def importar_ubl(self, request: Request) -> Response:
        """
        # WARNING: DEPRECATED: Este endpoint está deprecado.
        Use POST /api/v1/core/documentos/upload/ en su lugar.
        Este endpoint será removido en v2.40.
        
        Importa una factura desde XML UBL 2.1 (texto pegado).
        Delega al endpoint universal de documentos.
        
        Body:
        {
            "xml": "<Invoice xmlns=\"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2\">...</Invoice>"
        }
        
        Returns:
            201 Created con FacturaDetailSerializer
        """
        # TODO: Deprecar este endpoint - delegar al endpoint universal
        serializer = ImportUBLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Convertir XML string a bytes y crear un archivo temporal
        xml_content = serializer.validated_data["xml"]
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        
        # Usar el servicio universal
        from apps.services.document_ingest.ingest_service import ingest_document
        result, status_code = ingest_document(
            content=xml_bytes,
            filename="imported.xml",
            preview=False,
            async_mode=False
        )
        
        # Si se persistió, obtener la factura
        if result.get("persisted") and result.get("id"):
            from apps.tenant.facturas.models import Factura
            try:
                factura = Factura.objects.get(pk=result.get("id"))
                output_serializer = FacturaDetailSerializer(factura, context={'request': request})
                return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            except Factura.DoesNotExist:
                pass
        
        # Si no se pudo obtener la factura, retornar el resultado del pipeline
        return Response(result, status=status_code)
    
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
        from apps.tenant.perfil.services.perfil_service import get_or_create_profile
        perfil = get_or_create_profile(request.user)
        
        qs = FacturaSelectors.qs_centros_costo().filter(empresa_id=perfil.empresa_id)
        
        # Serialización ligera para máxima velocidad
        data = list(qs.values('id', 'numero', 'receptor_razon_social'))
        return Response(data)
    
    @action(detail=False, methods=["post"], url_path="upload-ubl", parser_classes=[MultiPartParser, FormParser])
    def upload_ubl(self, request: Request) -> Response:
        """
        # WARNING: DEPRECATED: Este endpoint está deprecado.
        Use POST /api/v1/core/documentos/upload/ en su lugar.
        Este endpoint será removido en v2.40.
        
        # WARNING: v2.61.2: OPTIMIZADO - Pre-validación de idempotencia y batch processing.
        
        Sube uno o múltiples archivos XML UBL 2.1 y los importa (async o sync).
        Delega al endpoint universal de documentos.
        
        Body (multipart/form-data):
        - file: <archivo.xml> (archivo único)
        - files[]: <archivo1.xml>, <archivo2.xml>, ... (múltiples archivos - batch processing)
        - files: <archivo1.xml>, <archivo2.xml>, ... (alternativa a files[])
        
        Query params:
        - async=true (default): Encola tarea Celery y retorna 202 + task_id
        - async=false: Parsea y materializa en la misma request (201/200)
        - preview=true: Solo retorna DTO sin persistir
        
        # WARNING: v2.61.2: DELEGACIÓN A CELERY - Si hay más de 10 archivos, el procesamiento se delega
        automáticamente a Celery para no bloquear la conexión del usuario, independientemente del
        parámetro async. Use GET /api/v1/facturas/ingest/{task_id}/status/ para consultar el estado.
        
        Returns:
            - async=true (single file): 202 Accepted con {"task_id": str, "status": "queued"}
            - async=false (single file): 201/200 con datos de factura materializada
            - async=false (batch <= 10 archivos): 200 OK con {"creados": X, "duplicados": Y, "errores": Z, "resultados": [...]}
            - batch > 10 archivos: 202 Accepted con {"task_id": str, "status": "queued", "total_files": N, "message": "..."}
            - 400 Bad Request si falta archivo XML
            - 409 Conflict si es duplicado
            - 415 Unsupported Media Type si el tipo no es soportado
            - 422 Unprocessable Entity si hay error de validación
            
        # WARNING: CONSULTA DE ESTADO: Para batch > 10 archivos, use GET /api/v1/facturas/ingest/{task_id}/status/
        """
        # # WARNING: NORMALIZACIÓN: Obtener contexto para logging
        schema = getattr(connection, "schema_name", "-")
        rid = request.META.get("REQUEST_ID", "-")
        
        # # WARNING: v2.61.2: BATCH PROCESSING - Soportar files[] o files (múltiples archivos)
        xml_files = request.FILES.getlist('files[]') or request.FILES.getlist('files') or []
        single_file = request.FILES.get('file')
        
        # Si hay files[] o files, usar batch processing; si no, usar file único
        if xml_files:
            return self._upload_ubl_batch(request, xml_files, rid, schema)
        
        if not single_file:
            log_up.warning(
                "upload_ubl missing file",
                extra={"request_id": rid, "schema_name": schema}
            )
            return Response({"error": "missing_xml", "message": "Falta archivo XML."}, status=400)
        
        use_async = request.query_params.get('async', 'true').lower() != 'false'
        preview_mode = request.query_params.get('preview', 'false').lower() == 'true'
        
        try:
            xml_bytes = single_file.read()
            size = len(xml_bytes or b"")
        except Exception as e:
            log_up.warning(
                "upload_ubl error reading file",
                extra={"request_id": rid, "schema_name": schema, "error": str(e)}
            )
            return Response({"error": "read_error", "message": "Error al leer el archivo XML."}, status=400)
        
        # # WARNING: v2.61.2: PRE-VALIDACIÓN DE IDEMPOTENCIA (La "Vía Rápida")
        # Extraer CUFE con regex antes del parsing completo - ejecuta en los primeros milisegundos
        if not preview_mode and not use_async:
            cufe_rapido = fast_get_cufe(xml_bytes)
            
            if cufe_rapido:
                # Verificar si la factura ya existe por CUFE
                # # WARNING: v2.61.5: IDOR fix - filtrar por empresa del tenant (Zero-Trust)
                empresa_id = getattr(getattr(request.user, 'tenant_profile', None), 'empresa_id', None)
                if not empresa_id:
                    empresa_id = Empresa.objects.only('id').values_list('id', flat=True).first()
                factura_existente = Factura.objects.filter(
                    cufe=cufe_rapido,
                    empresa_id=empresa_id
                ).only('id', 'numero', 'naturaleza', 'cufe').first() if empresa_id else None
                
                if factura_existente:
                    # # WARNING: v2.61.2: Retornar 200 OK inmediatamente sin parsing completo
                    # Esto evita desperdiciar CPU en archivos que ya existen en la base de datos
                    log_up.info(
                        "upload_ubl duplicate detected (fast pre-validation)",
                        extra={
                            "request_id": rid,
                            "schema_name": schema,
                            "cufe": cufe_rapido,
                            "factura_id": factura_existente.id,
                            "numero": factura_existente.numero,
                            "skipped_parsing": True
                        }
                    )
                    return Response({
                        "id": factura_existente.id,
                        "numero": factura_existente.numero,
                        "naturaleza": factura_existente.naturaleza,
                        "cufe": factura_existente.cufe,
                        "created": False,
                        "message": "Factura ya existe (idempotente - pre-validación rápida)"
                    }, status=200)
        
        # TODO: Deprecar este endpoint - delegar al endpoint universal
        # Usar el servicio universal directamente
        try:
            # Usar el servicio a través del mixin
            payload, code = self.service_importar_documento(
                xml_bytes,
                filename=single_file.name,
                preview=preview_mode,
                async_mode=use_async
            )
            
            # Si es async, el formato ya es compatible
            if use_async and isinstance(payload, dict) and "task_id" in payload:
                log_up.info(
                    "upload_ubl async enqueued (universal pipeline)",
                    extra={
                        "request_id": rid,
                        "schema_name": schema,
                        "task_id": payload.get("task_id")
                    }
                )
                return Response(payload, status=202)
            
            # Si es sync, retornar payload directamente
            log_up.info(
                "upload_ubl done (universal pipeline)",
                extra={
                    "request_id": rid,
                    "schema_name": schema,
                    "size": size,
                    "preview": preview_mode,
                    "status_code": code,
                    "numero": payload.get("numero") if isinstance(payload, dict) else None,
                }
            )
            resp = Response(payload, status=code)
            if not preview_mode and code in (200, 201):
                resp["HX-Trigger"] = "listaFacturasChanged"
            return resp
        except Exception as e:
            log_up.exception(
                "upload_ubl error (universal pipeline)",
                extra={
                    "request_id": rid,
                    "schema_name": schema,
                    "size": size,
                    "async": use_async
                }
            )
            return Response({"error": "internal", "message": str(e)}, status=500)
    
    def _upload_ubl_batch(self, request: Request, xml_files: list, rid: str, schema: str) -> Response:
        """
        # WARNING: v2.61.2: BATCH PROCESSING - Procesa múltiples archivos XML y retorna resumen.
        
        # WARNING: DELEGACIÓN A CELERY: Si hay más de 10 archivos, delega el procesamiento a Celery
        usando batch_upload_facturas_task para no bloquear la conexión del usuario.
        
        Args:
            request: Request object
            xml_files: Lista de archivos XML a procesar
            rid: Request ID para logging
            schema: Schema name para logging
            
        Returns:
            - Si <= 10 archivos: Response con resumen sincrónico
            - Si > 10 archivos: 202 Accepted con task_id para consultar estado
        """
        from apps.tenant.facturas.models import Factura
        
        preview_mode = request.query_params.get('preview', 'false').lower() == 'true'
        use_async = request.query_params.get('async', 'true').lower() != 'false'
        
        if preview_mode:
            # Batch preview no soportado
            return Response({
                "error": "preview_batch_not_supported",
                "message": "Batch processing no soporta modo preview. Use preview=false."
            }, status=400)
        
        # # WARNING: v2.61.2: DELEGACIÓN A CELERY - Si hay más de 10 archivos, usar Celery
        BATCH_SIZE_THRESHOLD = 10
        if len(xml_files) > BATCH_SIZE_THRESHOLD:
            # Delegar a Celery para no bloquear la conexión del usuario
            try:
                # # WARNING: IMPORT LAZY: Importar tarea Celery solo cuando se necesita
                from apps.services.document_ingest.tasks import batch_upload_facturas_task
                
                # Preparar datos de archivos (codificar en base64 para serialización)
                files_data = []
                for xml_file in xml_files:
                    try:
                        xml_bytes = xml_file.read()
                        content_b64 = base64.b64encode(xml_bytes).decode('utf-8')
                        files_data.append({
                            "filename": xml_file.name,
                            "content_b64": content_b64
                        })
                    except Exception as e:
                        log_up.warning(
                            "upload_ubl_batch error reading file for async",
                            extra={
                                "request_id": rid,
                                "schema_name": schema,
                                "filename": xml_file.name,
                                "error": str(e)
                            }
                        )
                        # Continuar con otros archivos
                        continue
                
                if not files_data:
                    return Response({
                        "error": "no_valid_files",
                        "message": "No se pudieron leer los archivos para procesamiento asíncrono."
                    }, status=400)
                
                # Obtener esquema del tenant actual
                tenant_schema = getattr(connection, "schema_name", schema)
                
                # Obtener usuario que inició la carga
                started_by_id = request.user.id if request.user and request.user.is_authenticated else None
                
                # Encolar tarea Celery
                async_res = batch_upload_facturas_task.apply_async(
                    kwargs={
                        "schema_name": tenant_schema,
                        "files_data": files_data,
                        "started_by_id": started_by_id
                    },
                    queue="high_priority"  # Cola de alta prioridad
                )
                
                log_up.info(
                    "upload_ubl_batch enqueued to Celery",
                    extra={
                        "request_id": rid,
                        "schema_name": schema,
                        "task_id": async_res.id,
                        "total_files": len(files_data)
                    }
                )
                
                return Response({
                    "task_id": async_res.id,
                    "status": "queued",
                    "total_files": len(files_data),
                    "message": f"Procesamiento de {len(files_data)} archivos encolado. Use GET /api/v1/facturas/ingest/{async_res.id}/status/ para consultar el estado."
                }, status=202)
                
            except Exception as e:
                log_up.exception(
                    "upload_ubl_batch error enqueuing to Celery",
                    extra={
                        "request_id": rid,
                        "schema_name": schema,
                        "total_files": len(xml_files)
                    }
                )
                return Response({
                    "error": "async_enqueue_error",
                    "message": f"Error al encolar procesamiento asíncrono: {str(e)}"
                }, status=500)
        
        # # WARNING: PROCESAMIENTO SÍNCRONO - Para <= 10 archivos
        if use_async:
            # Para batch pequeño, no usar async (procesar directamente)
            log_up.info(
                "upload_ubl_batch processing synchronously (small batch)",
                extra={
                    "request_id": rid,
                    "schema_name": schema,
                    "total_files": len(xml_files)
                }
            )
        
        resultados = []
        creados = 0
        duplicados = 0
        errores = 0
        
        for xml_file in xml_files:
            try:
                xml_bytes = xml_file.read()
                size = len(xml_bytes or b"")
                
                # # WARNING: v2.61.2: PRE-VALIDACIÓN DE IDEMPOTENCIA (La "Vía Rápida") - Extraer CUFE con regex
                cufe_rapido = fast_get_cufe(xml_bytes)
                
                if cufe_rapido:
                    # # WARNING: v2.61.5: IDOR fix - filtrar por empresa del tenant (Zero-Trust)
                    _emp_id = getattr(getattr(self.request.user, 'tenant_profile', None), 'empresa_id', None)
                    if not _emp_id:
                        _emp_id = Empresa.objects.only('id').values_list('id', flat=True).first()
                    factura_existente = Factura.objects.filter(
                        cufe=cufe_rapido,
                        empresa_id=_emp_id
                    ).only('id', 'numero', 'cufe').first() if _emp_id else None
                    if factura_existente:
                        # Duplicado detectado sin parsing completo
                        resultados.append({
                            "filename": xml_file.name,
                            "status": "duplicate",
                            "factura_id": factura_existente.id,
                            "numero": factura_existente.numero,
                            "cufe": cufe_rapido
                        })
                        duplicados += 1
                        continue
                
                # Procesar archivo normalmente via mixin
                payload, code = self.service_importar_documento(
                    xml_bytes,
                    filename=xml_file.name,
                    preview=False,
                    async_mode=False
                )
                
                if code == 201:
                    creados += 1
                    resultados.append({
                        "filename": xml_file.name,
                        "status": "created",
                        "factura_id": payload.get("id"),
                        "numero": payload.get("numero")
                    })
                elif code == 200:
                    duplicados += 1
                    resultados.append({
                        "filename": xml_file.name,
                        "status": "duplicate",
                        "factura_id": payload.get("id"),
                        "numero": payload.get("numero")
                    })
                else:
                    errores += 1
                    resultados.append({
                        "filename": xml_file.name,
                        "status": "error",
                        "error": payload.get("error", "unknown"),
                        "message": payload.get("message", "Error desconocido")
                    })
                    
            except Exception as e:
                errores += 1
                resultados.append({
                    "filename": xml_file.name,
                    "status": "error",
                    "error": "exception",
                    "message": str(e)
                })
                log_up.warning(
                    "upload_ubl_batch error processing file",
                    extra={
                        "request_id": rid,
                        "schema_name": schema,
                        "filename": xml_file.name,
                        "error": str(e)
                    }
                )
        
        log_up.info(
            "upload_ubl_batch completed",
            extra={
                "request_id": rid,
                "schema_name": schema,
                "total": len(xml_files),
                "creados": creados,
                "duplicados": duplicados,
                "errores": errores
            }
        )
        
        resp = Response({
            "creados": creados,
            "duplicados": duplicados,
            "errores": errores,
            "total": len(xml_files),
            "resultados": resultados
        }, status=200)
        if creados > 0:
            resp["HX-Trigger"] = "listaFacturasChanged"
        return resp
    
    @action(detail=False, methods=["post"], url_path="upload-document", parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request: Request) -> Response:
        """
        Endpoint universal para subir documentos (XML, PDF, XLS/XLSX, CSV, TXT) (FASE 3).
        
        # WARNING: v2.36 FASE 3: Endpoint universal protegido por feature flag.
        Usa el pipeline universal de documentos cuando FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True.
        
        Body (multipart/form-data):
        - file: <archivo> (XML, PDF, XLS/XLSX, CSV, TXT)
        
        Query params:
        - preview=true|false: Modo preview (solo retorna DTO sin persistir)
        - async=true|false: Modo asíncrono (actualmente procesa síncronamente pero retorna formato compatible)
        
        Returns:
            - 200 OK: Preview mode (DTO sin persistir)
            - 201 Created: Documento creado
            - 200 OK: Documento actualizado (idempotencia)
            - 400 Bad Request: Error de parsing/detección o archivo faltante
            - 403 Forbidden: Endpoint deshabilitado (FEATURE_UPLOAD_DOCUMENT_ENDPOINT=False)
            - 409 Conflict: Duplicado (idempotencia)
            - 415 Unsupported Media Type: Tipo no soportado
            - 422 Unprocessable Entity: Error de validación
        """
        # # WARNING: FASE 3: Verificar feature flag
        if not getattr(settings, 'FEATURE_UPLOAD_DOCUMENT_ENDPOINT', False):
            return Response(
                {"error": "endpoint_disabled", "message": "Este endpoint está deshabilitado."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener archivo
        file = request.FILES.get("file")
        if not file:
            log_up.warning(
                "upload_document missing file",
                extra=safe_extra({
                    "request_id": request.META.get("REQUEST_ID", "-"),
                    "schema_name": getattr(connection, "schema_name", "-"),
                })
            )
            return Response(
                {"error": "missing_file", "message": "Campo 'file' requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extraer parámetros
        preview = request.query_params.get("preview", "false").lower() == "true"
        async_mode = request.query_params.get("async", "false").lower() == "true"
        
        # Leer contenido del archivo
        try:
            file_content = file.read()
        except Exception as e:
            log_up.warning(
                "upload_document read error",
                extra=safe_extra({
                    "request_id": request.META.get("REQUEST_ID", "-"),
                    "schema_name": getattr(connection, "schema_name", "-"),
                    "upload_filename": file.name,
                    "error": str(e)[:200],
                })
            )
            return Response(
                {"error": "read_error", "message": "Error al leer archivo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Llamar a importar_documento via mixin
        try:
            payload, code = self.service_importar_documento(
                file_content,
                filename=file.name,
                preview=preview,
                async_mode=async_mode
            )
            
            # Log de éxito
            log_up.info(
                "upload_document success",
                extra=safe_extra({
                    "request_id": request.META.get("REQUEST_ID", "-"),
                    "schema_name": getattr(connection, "schema_name", "-"),
                    "upload_filename": file.name,
                    "size": len(file_content),
                    "preview": preview,
                    "async_mode": async_mode,
                    "status_code": code,
                    "persisted": payload.get("persisted", False) if isinstance(payload, dict) else False,
                })
            )
            
            return Response(payload, status=code)
            
        except Exception:
            log_up.exception(
                "upload_document error",
                extra=safe_extra({
                    "request_id": request.META.get("REQUEST_ID", "-"),
                    "schema_name": getattr(connection, "schema_name", "-"),
                    "upload_filename": file.name,
                })
            )
            return Response(
                {
                    "error": "internal_server_error",
                    "message": "Error interno al procesar documento",
                    "persisted": False,
                    "dto": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="ingest/(?P<task_id>[^/]+)/status")
    def ingest_status(self, request: Request, task_id: str = None) -> Response:
        """
        Consulta el estado de una tarea de ingesta XML.
        
        # WARNING: FASE 2: Endpoint para polling del estado de tarea Celery.
        # WARNING: NUNCA 500: Siempre retorna 200 con JSON estructurado (apto para UI).
        
        Args:
            task_id: ID de la tarea Celery (retornado por upload_ubl?async=true)
        
        Returns:
            - 200 OK: JSON estructurado con:
              - state: PENDING | STARTED | SUCCESS | FAILURE | UNKNOWN
              - result: payload si SUCCESS
              - error_code/message/hint cuando hay problemas
        """
        # # WARNING: NORMALIZACIÓN: Pasar request para contexto de logging
        from apps.services.document_ingest.tasks import get_task_status
        payload, code = get_task_status(task_id, request=request)
        return Response(payload, status=code)
    
    @action(detail=False, methods=["post"], url_path="create-from-dto", parser_classes=[JSONParser])
    def create_from_dto(self, request: Request) -> Response:
        """
        # WARNING: REFACTOR: Crea una factura o nota crédito desde DTO parseado por document_ingest.
        
        Este endpoint recibe un DTO del pipeline universal y lo persiste bajo la lógica
        propia de la app facturas. El pipeline universal SOLO parsea, NO persiste.
        
        POST /api/v1/facturas/create-from-dto/
        
        Body (JSON):
        {
            "dto": {...DTO_UNIFICADO...},
            "persist_anexos": true|false,  # Opcional, default: true
            "file_content_bytes": "base64_encoded_bytes",  # Opcional, bytes del archivo en base64
            "file_type": "xml"|"pdf"  # Opcional, tipo de archivo
        }
        
        Returns:
            - 201 Created: Factura/NC creada {"id": int, "numero": str, "naturaleza": str, "created": true}
            - 200 OK: Factura/NC actualizada {"id": int, "numero": str, "naturaleza": str, "created": false}
            - 400 Bad Request: Falta 'dto' en el cuerpo
            - 422 Unprocessable Entity: Falta SSoT empresa o DTO inválido con missing_fields
            - 409 Conflict: Duplicado o restricción violada
            - 413 Payload Too Large: XML/anexo excede tamaño permitido
            
        # WARNING: PROPAGACIÓN DE ERRORES 422:
        Si la validación falla (ej. falta emisor.razon_social), se retorna un JSON estructurado:
        {
            "error": "missing_required_fields",
            "message": "Faltan campos obligatorios: emisor.razon_social, emisor.nit",
            "missing_fields": ["emisor.razon_social", "emisor.nit"]
        }
        
        El módulo error_injector.js intercepta estos errores y los muestra en el Offcanvas.
        """
        import logging
        
        logger = logging.getLogger(__name__)
        
        # # WARNING: v2.61.2: Logging para debugging
        schema = getattr(connection, "schema_name", "-")
        rid = request.META.get("REQUEST_ID", "-")
        log_up.debug(
            "create_from_dto called",
            extra=safe_extra({
                "request_id": rid,
                "schema_name": schema,
                "has_dto": "dto" in request.data,
                "action": self.action,
            })
        )
        
        dto = request.data.get("dto")
        persist_anexos = bool(request.data.get("persist_anexos", True))
        
        # # WARNING: v2.60: Extraer file_content_bytes y file_type si vienen en el request
        file_content_bytes_b64 = request.data.get("file_content_bytes")
        file_type = request.data.get("file_type", "xml")
        
        file_bytes = None
        if file_content_bytes_b64:
            try:
                file_bytes = base64.b64decode(file_content_bytes_b64)
            except Exception as e:
                logger.warning(f"Error decodificando file_content_bytes en create_from_dto: {e}")
        
        if not dto:
            log_up.warning(
                "create_from_dto missing dto",
                extra=safe_extra({
                    "request_id": rid,
                    "schema_name": schema,
                })
            )
            return Response({"error": "missing_dto", "message": "Falta 'dto' en el cuerpo."}, status=400)
        
        # # WARNING: v2.60: Pasar file_bytes y file_type a materializar_factura_desde_result
        # # WARNING: PROPAGACIÓN: Los errores 422 con missing_fields se propagan directamente
        payload, code = self.service_materializar(
            dto, 
            empresa_id=getattr(getattr(self.request.user, 'tenant_profile', None), 'empresa_id', None) or Empresa.objects.only('id').values_list('id', flat=True).first()
        )
        
        # # WARNING: LOGGING: Registrar errores 422 con missing_fields para debugging
        if code == 422 and "missing_fields" in payload:
            logger.warning(f"[create_from_dto] Error 422 - Campos faltantes: {payload.get('missing_fields')}")
        
        log_up.info("create_from_dto", extra=safe_extra({
            "status_code": code,
            "numero": payload.get("numero") if "error" not in payload else None,
            "missing_fields": payload.get("missing_fields") if code == 422 else None,
        }))
        
        # WARNING: PROPAGACIÓN: Retornar payload tal cual (incluye missing_fields si es error 422)
        # El módulo error_injector.js intercepta htmx:responseError y muestra los campos faltantes
        resp = Response(payload, status=code)
        if code in (200, 201):
            resp["HX-Trigger"] = "listaFacturasChanged"
        return resp
    
    @action(detail=False, methods=["post"], url_path="materialize")
    def materialize(self, request: Request) -> Response:
        """
        # WARNING: DEPRECATED: Usar create_from_dto en su lugar.
        Mantenido por compatibilidad temporal.
        """
        """
        Materializa una factura desde el DTO resultante de la ingesta XML.
        
        # WARNING: FASE 2: Endpoint para materializar después de que la tarea Celery termine.
        
        Body (application/json):
        {
            "dto": <DocumentoXML-serializado>,  # Resultado de ingest_status cuando state=SUCCESS
            "persist_anexos": true|false  # Opcional, default: true
        }
        
        Returns:
            - 201 Created: Factura creada {"id": int, "numero": str, "naturaleza": str, "created": true}
            - 200 OK: Factura actualizada {"id": int, "numero": str, "naturaleza": str, "created": false}
            - 400 Bad Request: Falta 'dto' en el cuerpo
            - 422 Unprocessable Entity: Falta SSoT empresa o DTO inválido
            - 409 Conflict: Duplicado o restricción violada
            - 413 Payload Too Large: XML/anexo excede tamaño permitido
        """
        dto = request.data.get("dto")
        persist_anexos = bool(request.data.get("persist_anexos", True))
        
        if not dto:
            return Response({"error": "missing_dto", "message": "Falta 'dto' en el cuerpo."}, status=400)
        
        payload, code = self.service_materializar(dto, empresa_id=getattr(getattr(self.request.user, 'tenant_profile', None), 'empresa_id', None) or Empresa.objects.only('id').values_list('id', flat=True).first())
        log_up.info("materialize", extra=safe_extra({
            "status_code": code,
            "numero": payload.get("numero") if "error" not in payload else None,
        }))
        return Response(payload, status=code)
    
    def retrieve(self, request, *args, **kwargs):
        """Retorna detalle de factura con metadatos de anexos (sin contenido XML)."""
        # # WARNING: v2.61.5: Delegar queryset a get_queryset() -> qs_detail() que ya incluye
        # select_related(nota_credito, anexos) con .only(*DETAIL_FIELDS). No sobreescribir self.queryset.
        self.serializer_class = FacturaDetailSerializer
        return super().retrieve(request, *args, **kwargs)
    
    # # WARNING: FASE 4: Acciones detail para anexos XML
    @action(detail=True, methods=['get'], url_path='xml')
    def xml_ubl(self, request, pk=None):
        """
        Retorna el UBL XML completo de la factura.
        
        # WARNING: FASE 6: Endpoint dedicado para artefactos pesados (XML).
        - Listas y detalle NO incluyen XML (solo metadatos)
        - Este endpoint retorna el XML completo con Content-Type: application/xml
        - Inline si <= 2MB, descarga forzada si mayor
        
        Returns:
            - 200 OK: XML completo con Content-Type: application/xml
            - 204 No Content: Si no hay XML disponible
            - 404 Not Found: Si la factura no existe
        """
        factura = self.get_object()
        payload, code = self.service_obtener_xml(factura, "ubl")
        if isinstance(payload, HttpResponse):
            return payload
        return Response(payload, status=code)
    
    @action(detail=True, methods=['get'], url_path='app-response')
    def xml_app_response(self, request, pk=None):
        """
        Retorna el ApplicationResponse DIAN XML completo.
        
        # WARNING: FASE 6: Endpoint dedicado para artefactos pesados (ApplicationResponse XML).
        - Listas y detalle NO incluyen XML (solo metadatos)
        - Este endpoint retorna el XML completo con Content-Type: application/xml
        - Inline si <= 2MB, descarga forzada si mayor
        
        Returns:
            - 200 OK: XML completo con Content-Type: application/xml
            - 204 No Content: Si no hay ApplicationResponse disponible
            - 404 Not Found: Si la factura no existe
        """
        factura = self.get_object()
        payload, code = self.service_obtener_xml(factura, "app")
        if isinstance(payload, HttpResponse):
            return payload
        return Response(payload, status=code)
    
    # # WARNING: DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/facturas/ con StandardResultsSetPagination
    
    @action(detail=False, methods=['post'], url_path='update-inbox-state')
    def update_inbox_state(self, request: Request) -> Response:
        """
        Actualiza el estado del buzón IMAP después de procesar facturas.
        
        # WARNING: ZERO WASTE: Actualiza last_seen_uid para evitar reprocesar correos ya vistos.
        # WARNING: Este endpoint se llama después de que el usuario procesa facturas desde el modal.
        
        POST /api/v1/facturas/update-inbox-state/
        
        Body (JSON):
        {
            "config_id": int,  # ID de MailInboxConfig
            "last_uid": int,   # Último UID procesado
            "messages_processed": int  # Número de mensajes procesados
        }
        
        Returns:
            - 200 OK: Estado actualizado
            - 400 Bad Request: Faltan parámetros
            - 404 Not Found: Configuración no encontrada
        """
        from apps.tenant.facturas.inbox_state import update_inbox_state
        
        config_id = request.data.get('config_id')
        last_uid = request.data.get('last_uid')
        messages_processed = request.data.get('messages_processed', 0)
        
        if not config_id:
            return Response(
                {"error": "missing_config_id", "message": "Falta 'config_id' en el cuerpo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if last_uid is None:
            return Response(
                {"error": "missing_last_uid", "message": "Falta 'last_uid' en el cuerpo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Actualizar estado del buzón
            update_inbox_state(config_id, last_uid, messages_processed)
            
            log_up.info("update_inbox_state", extra=safe_extra({
                "config_id": config_id,
                "last_uid": last_uid,
                "messages_processed": messages_processed,
            }))
            
            return Response({
                "ok": True,
                "message": "Estado del buzón actualizado correctamente",
                "config_id": config_id,
                "last_uid": last_uid,
                "messages_processed": messages_processed,
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": "config_not_found", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            log_up.error("update_inbox_state_error", extra=safe_extra({
                "config_id": config_id,
                "error": str(e),
            }), exc_info=True)
            return Response(
                {"error": "update_failed", "message": f"Error al actualizar estado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        from apps.tenant.perfil.services.perfil_service import get_or_create_profile

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

            perfil = get_or_create_profile(request.user)
            empresa_id = perfil.empresa_id
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
        factura_id = request.query_params.get('id')
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
                            id=factura_id
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
                            id=factura_id
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
                        id=factura_id
                    ).only(
                        'id', 'numero', 'prefijo', 'consecutivo', 'tipo', 'estado', 'naturaleza',
                        'fecha_emision', 'fecha_vencimiento',
                        'emisor_nit', 'emisor_razon_social', 'emisor_direccion', 'emisor_email', 'emisor_telefono',
                        'receptor_nit', 'receptor_razon_social', 'receptor_direccion', 'receptor_email', 'receptor_telefono',
                        'moneda', 'categoria', 'forma_pago', 'medio_pago_codigo', 'payment_due_date',
                        'subtotal', 'impuestos', 'total',
                        'cuenta_contable_uuid',
                        'cufe', 'qr_url',
                        'anexos__pdf_file', 'anexos__ubl_xml', 'anexos__application_response_xml',
                    ).first()
                
                if not factura:
                    context['error'] = "Factura no encontrada o no pertenece a este tenant."
                    return Response(context, template_name='tenant/facturas/offcanvas_crear_factura.html')
                
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
        context['naturalezas'] = Factura.Naturaleza.choices
        context['categorias'] = Factura.Categoria.choices
        
        # Template completo para edición
        return Response(context, template_name='tenant/facturas/offcanvas_editar_factura.html')
    

class ItemFacturaViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    Endpoints para ítems de factura.

    # WARNING: NOTA: CRUD completo de ítems se recomienda gestionarlo a través de Factura (items embed).
    Este ViewSet expone list, retrieve y destroy para casos específicos.

    # WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() cuando sea necesario.

    Endpoints disponibles:
    - GET /api/v1/items-factura/ (lista de ítems con filtro por factura)
    - GET /api/v1/items-factura/{id}/ (detalle de un ítem)
    - DELETE /api/v1/items-factura/{id}/ (eliminar un ítem)
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    serializer_class = ItemFacturaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['factura_id']

    def get_queryset(self):
        """
        QuerySet optimizado - NO usa .all().
        Filtra por factura si se proporciona el parámetro factura_id o factura.
        """
        qs = ItemFactura.objects.only(
            "id", "factura_id", "linea_id", "codigo", "descripcion",
            "cantidad", "unidad_medida", "valor_unitario", "porcentaje_iva",
            "valor_iva", "porcentaje_retefuente", "valor_retefuente",
            "porcentaje_reteiva", "valor_reteiva", "porcentaje_reteica", "valor_reteica",
            "subtotal", "total", "es_servicio", "orden"
        )

        # Filtro por factura (soporta 'factura' o 'factura_id' en query params)
        factura_id = self.request.query_params.get('factura') or self.request.query_params.get('factura_id')
        if factura_id:
            qs = qs.filter(factura_id=factura_id)

        return qs.order_by('orden')


class NotaCreditoViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    NOTAS CRÉDITO — Endpoints para gestión de notas crédito.
    
    # WARNING: REGLAS DE NEGOCIO:
    Las notas crédito son documentos históricos que corrigen facturas.
    - Solo se pueden eliminar para corregir un error de carga (rollback técnico).
    - NUNCA se pueden editar, actualizar o modificar.
    - Se crean únicamente mediante importación XML UBL (pipeline canónico).
    
    Endpoints permitidos:
    - GET /notas-credito/ → Lista de notas crédito (paginada)
    - GET /notas-credito/{id}/ → Detalle de nota crédito (read-only)
    - GET /notas-credito/{id}/xml/ → XML de nota crédito (artefacto pesado)
    - DELETE /notas-credito/{id}/ → Eliminar nota crédito (rollback de error de carga)
    
    Endpoints bloqueados:
    - POST /notas-credito/ → 405 Method Not Allowed (solo importación vía pipeline XML)
    - PUT /notas-credito/{id}/ → 405 Method Not Allowed
    - PATCH /notas-credito/{id}/ → 405 Method Not Allowed
    
    # WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    [OK] Escalable (millones de notas crédito)
    [OK] Artefactos pesados (XML) solo en endpoint /xml/
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
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
        if self.action == "list":
            return NotaCredito.objects.select_related("factura").only(
                "id", "numero", "cude", "fecha_emision", "moneda",
                "subtotal", "impuestos", "total", "motivo",
                "ref_factura_numero", "ref_factura_cufe",
                "factura__numero", "factura__cufe",
                "created_at"
            )
        # Para retrieve, incluir más campos pero aún sin xml_content
        return NotaCredito.objects.select_related("factura").only(
            "id", "numero", "cude", "fecha_emision", "moneda",
            "subtotal", "impuestos", "total", "motivo",
            "ref_factura_numero", "ref_factura_cufe",
            "factura__id", "factura__numero", "factura__cufe",
            "created_at", "updated_at"
        )
    
    # # WARNING: DEPRECATED v2.40: Método datatables() eliminado - usar GET /api/v1/facturas/notas-credito/ con StandardResultsSetPagination
    
    @action(detail=True, methods=["get"], url_path="xml")
    def xml(self, request, pk=None):
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
