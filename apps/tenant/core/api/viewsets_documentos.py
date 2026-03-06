"""
ViewSet para endpoint universal de documentos (FASE 8).

⚠️ PRINCIPIOS:
- API-First JSON-only: Solo retorna JSON, sin HTML dinámico
- Endpoint universal: Soporta XML, PDF, XLS/XLSX, CSV, TXT
- Pipeline unificado: document_parser → document_ingest → domain router
- Multi-tenant: Opera en contexto del tenant actual
- Preview mode: Permite validar sin persistir
"""
import logging
import base64
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import connection
from django.conf import settings
from apps.services.document_ingest.ingest_service import ingest_document

logger = logging.getLogger("apps.tenant.core.api.documentos")


class DocumentoUploadViewSet(viewsets.ViewSet):
    """
    ViewSet para upload universal de documentos (FASE 8).
    
    ⚠️ CRÍTICO: parser_classes para aceptar multipart/form-data (archivos)
    """
    parser_classes = [MultiPartParser, FormParser]
    """
    ViewSet para upload universal de documentos (FASE 8).
    
    Endpoint: POST /api/v1/documentos/upload/
    
    Soporta:
    - XML (UBL 2.1 Invoice/CreditNote)
    - PDF
    - Excel (XLS/XLSX)
    - CSV
    - TXT
    
    Parámetros:
    - file: Archivo a procesar (multipart/form-data)
    - preview: true/false (default: false)
    - tipo: Sugerencia de tipo (opcional, para optimizar detección)
    
    Returns:
    - 200 OK (preview): DTO sin persistir
    - 201 Created: Documento creado
    - 200 OK: Documento actualizado (idempotencia)
    - 400 Bad Request: Error de parsing/detección
    - 409 Conflict: Duplicado (idempotencia)
    - 415 Unsupported Media Type: Tipo no soportado
    - 422 Unprocessable Entity: Error de validación
    """
    
    @action(detail=False, methods=['post'], url_path='upload', url_name='upload')
    def upload(self, request: Request) -> Response:
        """
        Endpoint universal para upload de documentos (FASE 8).
        
        POST /api/v1/documentos/upload/
        
        Body (multipart/form-data):
        - file: Archivo a procesar
        - preview: true/false (query param o form field)
        - tipo: Sugerencia de tipo (opcional)
        
        Returns:
        JSON con estructura:
        {
            "persisted": true|false,
            "dto": {...},
            "id": 123 | null,
            "tipo": "invoice | creditnote | gasto | inventario | ...",
            "redirect_url": "/api/v1/.../123/" | null
        }
        """
        schema = getattr(connection, "schema_name", "-")
        request_id = getattr(settings, 'REQUEST_ID', getattr(request, 'id', '-'))
        
        # Extraer archivo
        if 'file' not in request.FILES:
            logger.warning(
                "documento_upload_missing_file",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                }
            )
            return Response(
                {"error": "missing_file", "message": "Campo 'file' requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        filename = uploaded_file.name
        mime_type = uploaded_file.content_type
        
        # Leer contenido
        try:
            file_content = uploaded_file.read()
        except Exception as e:
            logger.exception(
                "documento_upload_read_error",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "upload_filename": filename,
                }
            )
            return Response(
                {"error": "read_error", "message": "Error al leer archivo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extraer parámetros
        # preview puede venir como query param o form field
        preview_str = request.query_params.get('preview') or request.data.get('preview', 'false')
        preview = str(preview_str).lower() == 'true'
        
        # tipo puede venir como query param o form field
        tipo_hint = request.query_params.get('tipo') or request.data.get('tipo')
        
        logger.info(
            "documento_upload_start",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
                "size_bytes": len(file_content),
                "mime_type": mime_type,
                "preview": preview,
                "tipo_hint": tipo_hint,
            }
        )
        
        # ⚠️ REFACTOR: Llamar al pipeline universal (SOLO parsea, NO persiste)
        # El parámetro preview es ignorado - siempre devuelve DTO sin persistir
        try:
            result, status_code = ingest_document(
                content=file_content,
                filename=filename,
                mime_type=mime_type,
                kind_hint=tipo_hint,
                preview=True,  # Siempre True - document_ingest NO persiste
                async_mode=False
            )
            
            # ⚠️ REFACTOR: Construir respuesta estructurada (SOLO DTO, sin persistencia)
            doc_type = result.get("tipo") or result.get("dto", {}).get("type") or result.get("dto", {}).get("document_type", "")
            
            # ⚠️ v2.40: Extraer confidence_score del DTO si está disponible (mapeo semántico)
            dto_data = result.get("dto", {})
            confidence_score = None
            if isinstance(dto_data, dict):
                # Si el DTO tiene mapping_metadata, extraer confidence_score
                mapping_metadata = dto_data.get("mapping_metadata", {})
                if mapping_metadata:
                    confidence_score = mapping_metadata.get("average_confidence")
            
            # ⚠️ v2.60: Incluir file_content_bytes y file_type en metadata para persistencia de PDFs
            # Esto permite que el servicio de facturas guarde el archivo PDF correctamente
            metadata = result.get("metadata", {}).copy()
            
            # Detectar tipo de archivo desde mime_type o filename
            detected_file_type = "xml"  # Default
            if mime_type:
                if "pdf" in mime_type.lower():
                    detected_file_type = "pdf"
                elif "xml" in mime_type.lower() or "text/xml" in mime_type.lower():
                    detected_file_type = "xml"
            elif filename:
                if filename.lower().endswith('.pdf'):
                    detected_file_type = "pdf"
                elif filename.lower().endswith('.xml'):
                    detected_file_type = "xml"
            
            # Incluir bytes del archivo original en metadata para persistencia
            # ⚠️ CRÍTICO: Solo incluir si el archivo es PDF o XML (no incluir Excel/CSV/TXT)
            if detected_file_type in ("pdf", "xml"):
                # Usar base64 para incluir bytes en JSON de forma segura
                metadata["file_content_bytes"] = base64.b64encode(file_content).decode('utf-8')
                metadata["file_type"] = detected_file_type
                logger.info(
                    "documento_upload_metadata_file_included",
                    extra={
                        "request_id": request_id,
                        "schema_name": schema,
                        "upload_filename": filename,
                        "file_type": detected_file_type,
                        "size_bytes": len(file_content),
                    }
                )
            
            response_data = {
                "success": result.get("success", True),
                "persisted": False,  # Siempre False - document_ingest NO persiste
                "dto": dto_data,
                "sha256": result.get("sha256"),
                "metadata": metadata,
                "tipo": doc_type,
            }
            
            # ⚠️ v2.40: Agregar confidence_score si está disponible
            if confidence_score is not None:
                response_data["confidence_score"] = confidence_score
                response_data["mapping_metadata"] = dto_data.get("mapping_metadata", {})
            
            # Construir sugerencia de endpoint para persistir (la app debe llamar a su propio endpoint)
            if doc_type == "invoice" or doc_type.startswith("invoice"):
                response_data["create_endpoint"] = "/api/v1/facturas/create-from-dto/"
            elif doc_type == "creditnote" or doc_type.startswith("creditnote"):
                response_data["create_endpoint"] = "/api/v1/facturas/create-from-dto/"
            elif doc_type == "gasto":
                response_data["create_endpoint"] = "/api/v1/gastos/create-from-dto/"
            elif doc_type == "inventario":
                response_data["create_endpoint"] = "/api/v1/inventario/create-from-dto/"
            else:
                response_data["create_endpoint"] = None
            
            # Si hay error, incluirlo
            if result.get("error"):
                response_data["error"] = result.get("error")
                response_data["message"] = result.get("message")
                if result.get("missing_fields"):
                    response_data["missing_fields"] = result.get("missing_fields")
            
            # Mapear status codes del pipeline a HTTP
            http_status = status_code
            if status_code == 409:
                http_status = status.HTTP_409_CONFLICT
            elif status_code == 415:
                http_status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            elif status_code == 422:
                http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
            elif status_code == 201:
                http_status = status.HTTP_201_CREATED
            elif status_code == 200:
                http_status = status.HTTP_200_OK
            elif status_code == 400:
                http_status = status.HTTP_400_BAD_REQUEST
            elif status_code == 500:
                http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                http_status = status.HTTP_200_OK
            
            logger.info(
                "documento_upload_complete",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "upload_filename": filename,
                    "status_code": http_status,
                    "tipo": response_data.get("tipo"),
                }
            )
            
            return Response(response_data, status=http_status)
            
        except Exception as e:
            logger.exception(
                "documento_upload_error",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "upload_filename": filename,
                }
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
