import base64
import logging
from decimal import Decimal

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.services.document_ingest.ingest_service import ingest_document
from apps.services.document_ingest.tasks import batch_upload_facturas_task, get_task_status
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.api.serializers import ImportUBLSerializer, FacturaDetailSerializer
from apps.tenant.facturas.utils.ubl_parser import fast_get_cufe

# Logger normalizado para facturas (upload, import, etc.)
log_up = logging.getLogger("facturas")
logger = logging.getLogger(__name__)

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


class FacturaUBLMixin:
    """
    Mixin especializado para endpoints de carga, pre-validación y procesamiento de UBL XML.
    """

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
        serializer = ImportUBLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Convertir XML string a bytes y crear un archivo temporal
        xml_content = serializer.validated_data["xml"]
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        
        # Usar el servicio universal
        result, status_code = ingest_document(
            content=xml_bytes,
            filename="imported.xml",
            preview=False,
            async_mode=False
        )
        
        # Si se persistió, obtener la factura
        if result.get("persisted") and result.get("id"):
            try:
                factura = Factura.objects.get(pk=result.get("id"))
                output_serializer = FacturaDetailSerializer(factura, context={'request': request})
                return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            except Factura.DoesNotExist:
                pass
        
        # Si no se pudo obtener la factura, retornar el resultado del pipeline
        return Response(result, status=status_code)

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
        Usa el pipeline universal de documentos when FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True.
        
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
        
        # # WARNING: v2.60: Extraer file_content_bytes y file_type si vienen en el request
        file_content_bytes_b64 = request.data.get("file_content_bytes")
        
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
        
        if not dto:
            return Response({"error": "missing_dto", "message": "Falta 'dto' en el cuerpo."}, status=400)
        
        payload, code = self.service_materializar(dto, empresa_id=getattr(getattr(self.request.user, 'tenant_profile', None), 'empresa_id', None) or Empresa.objects.only('id').values_list('id', flat=True).first())
        log_up.info("materialize", extra=safe_extra({
            "status_code": code,
            "numero": payload.get("numero") if "error" not in payload else None,
        }))
        return Response(payload, status=code)
