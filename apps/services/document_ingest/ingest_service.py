"""
Servicio de ingesta de documentos canónico (SSoT) (FASE 3.3 + FASE 5).

WARNING: PRINCIPIOS:
- Única vía de ingesta/parseo de documentos en el sistema
- Agnóstico del dominio: no conoce modelos Django
- Preview mode: permite parsear sin persistir
- Persistencia delegada a services de dominio (idempotencia legal)
- Transaccional: todo o nada (transaction.atomic)
- Soporta múltiples formatos: XML, PDF, XLS/XLSX, CSV, TXT
- Logging estructurado: Mensajes deterministas, sin trazas internas expuestas

Flujo del pipeline universal (REFACTOR - Solo Parsing):
1. route(file_bytes) → Parsea documento a DTO
2. normalize(dto) → Normaliza y agrega metadatos
3. run_validations(dto) → Valida DTO con validadores específicos por app
4. Retorna DTO sin persistir (SIEMPRE)

WARNING: REFACTOR: document_ingest SOLO actúa como parser auxiliar.
- NO persiste modelos
- NO crea registros en DB
- NO llama a servicios CRUD de apps
- Las apps deben consumir el DTO y persistir bajo su propia lógica

Responsabilidades:
- Calcular sha256
- Registrar metadatos
- Llamar a router (route)
- Normalizar DTO (normalize)
- Ejecutar validaciones (run_validations)
- Devolver DTO (sin persistir)
"""
import hashlib
import logging
from typing import Any

from django.conf import settings
from django.db import connection

from apps.services.document_ingest.app_router import detect_app_from_kind_hint
from apps.services.document_ingest.router import route
from apps.services.document_ingest.validations.router import run_validations
from apps.services.document_ingest.validators import validate_document_dto
from apps.services.document_parser.normalizers import normalize_content

# WARNING: REFACTOR: Eliminado import de materialize_document - document_ingest SOLO parsea, NO persiste
# from apps.tenant.core.document_router import materialize_document, materializar as domain_materialize

# Logger estructurado
logger = logging.getLogger("apps.services.document_ingest")


def ingest_document(
    content: bytes,
    filename: str | None = None,
    mime_type: str | None = None,
    kind_hint: str | None = None,
    preview: bool = True,
    async_mode: bool = False
) -> tuple[dict[str, Any], int]:
    """
    WARNING: REFACTOR: Ingesta un documento SOLO para parseo (NO persiste).
    
    Flujo del pipeline universal (REFACTOR - Solo Parsing):
    1. route(file_bytes) → Parsea documento a DTO
    2. normalize(dto) → Normaliza y agrega metadatos
    3. run_validations(dto) → Valida DTO con validadores específicos por app
    4. Retorna DTO sin persistir (SIEMPRE)
    
    WARNING: IMPORTANTE: Este servicio NO persiste modelos. Las apps deben consumir el DTO
    y persistir bajo su propia lógica mediante sus propios endpoints.
    
    Responsabilidades:
    - Calcular sha256
    - Registrar metadatos
    - Llamar a router (route)
    - Normalizar DTO (normalize)
    - Ejecutar validaciones (run_validations)
    - Devolver DTO (sin persistir)
    - Delegar al dominio si preview=False (materialize)
    
    Args:
        content: Contenido del documento en bytes
        filename: Nombre del archivo (opcional, para detección por extensión)
        mime_type: MIME type del archivo (opcional)
        kind_hint: Tipo sugerido (opcional, para optimizar detección)
        preview: Si True, solo parsea sin persistir. Si False, persiste también.
        async_mode: Si True, procesa de forma asíncrona (FASE 5: placeholder para futuro)
        
    Returns:
        Tupla (payload, status_code):
        - payload: {
            "persisted": false|true,
            "dto": {...DTO_UNIFICADO...},
            "sha256": str (hash del documento),
            "metadata": {...},
            "error": str (si hay error),
            "message": str (si hay error),
        }
        - status_code: 200 (preview), 201 (creado), 400 (error), 409 (duplicado), 422 (validación)
    """
    # Contexto para logging
    schema = getattr(connection, "schema_name", "-")
    request_id = getattr(settings, 'REQUEST_ID', '-')
    
    # 1. Calcular sha256 (FASE 3.3)
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # 2. Registrar metadatos (FASE 3.3)
    metadata = {
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "sha256": sha256_hash,
        "kind_hint": kind_hint,
    }
    
    logger.info(
        "document_ingest_start",
        extra={
            "request_id": request_id,
            "schema_name": schema,
            "upload_filename": filename,
            "size_bytes": len(content),
            "sha256": sha256_hash,
        }
    )
    
    # 3. WARNING: REVERSIÓN: Normalización SIEMPRE aplicada a TODOS los tipos (XML, CSV, XLS/XLSX, TXT, PDF)
    # Enforcer: Obligar normalización antes de rutear/parsear
    # NO hay bypass, NO hay short-circuit, NO hay raw passthrough
    try:
        normalization_result = normalize_content(
            content=content,
            filename=filename,
            mime_type=mime_type
        )
        
        media_type = normalization_result.get("media_type", "unknown")
        normalized_content = normalization_result.get("normalized")
        normalization_meta = normalization_result.get("meta", {})
        
        if normalized_content is None:
            raise ValueError("Normalización no produjo contenido válido")
        
        logger.info(
            "document_ingest_normalization_ok",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
                "media_type": media_type,
                "cleanups": normalization_meta.get("cleanups", []),
            }
        )
        
        # Si el contenido normalizado es string (CSV/TXT), convertir a bytes para el router
        # El router y parsers deben manejar ambos tipos según el media_type
        if isinstance(normalized_content, str):
            # Para CSV/TXT, el router recibirá el string normalizado
            # Mantener como string para que los parsers CSV/TXT lo consuman directamente
            pass
        elif not isinstance(normalized_content, bytes):
            # Para Excel (DataFrame) o otros tipos, el router debe manejar el tipo específico
            pass
        
    except ValueError as e:
        # Tipo no reconocido o contenido insalvable
        logger.warning(
            "document_ingest_normalization_failed",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
                "error": str(e)[:200],
            }
        )
        return {
            "persisted": False,
            "dto": {},
            "sha256": sha256_hash,
            "metadata": metadata,
            "error": "unsupported_media_type" if "no reconocido" in str(e) or "no soportado" in str(e) else "normalization_error",
            "message": str(e),
        }, 415 if "no reconocido" in str(e) or "no soportado" in str(e) else 400
    except Exception:
        logger.exception(
            "document_ingest_normalization_exception",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
            }
        )
        return {
            "persisted": False,
            "dto": {},
            "sha256": sha256_hash,
            "metadata": metadata,
            "error": "normalization_error",
            "message": "Error al normalizar contenido del documento",
        }, 400
    
    # 4. Llamar a router (FASE 5: route)
    # WARNING: REVERSIÓN: Pasar contenido normalizado y media_type al router
    # WARNING: v2.40: El router prioriza parsers específicos por app antes de parsers genéricos
    # El router debe consumir EXCLUSIVAMENTE el contenido normalizado
    try:
        # Detectar app consumidora para logging
        app_name = detect_app_from_kind_hint(kind_hint)
        if app_name:
            logger.info(
                "document_ingest_app_detected",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "app_name": app_name,
                    "kind_hint": kind_hint,
                    "media_type": media_type,
                }
            )
        
        route_result = route(normalized_content, filename, mime_type, media_type=media_type, kind_hint=kind_hint)
        document_type = route_result.get("document_type", "")
        dto_dict = route_result.get("dto", {})
        
        logger.info(
            "document_ingest_routing_ok",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": document_type,
                "upload_filename": filename,
            }
        )
    except ValueError as e:
        # WARNING: v2.61.5: Captura y mejora de presentación de errores para inyección en UI
        error_detail = {
            "error_code": "unknown_document_type",
            "message": f"Tipo de documento no reconocido o no soportado: {str(e)}",
            "technical_detail": str(e)
        }
        logger.warning(
            "document_ingest_routing_failed",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
                "kind_hint": kind_hint,
                "error": str(e)[:200],
            }
        )
        return {
            "persisted": False,
            "dto": {},
            "sha256": sha256_hash,
            "metadata": metadata,
            "error": error_detail["error_code"],
            "message": error_detail["message"],
            "ui_feedback": error_detail, # WARNING: Inyectable por error_injector
        }, 400
    except Exception as e:
        error_message = str(e)
        logger.exception(
            "document_ingest_parse_error",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "upload_filename": filename,
                "kind_hint": kind_hint,
                "error_message": error_message,
                "error_type": type(e).__name__,
            }
        )
        return {
            "persisted": False,
            "dto": {},
            "sha256": sha256_hash,
            "metadata": metadata,
            "error": "parse_error",
            "message": f"Error al parsear documento: {error_message}",
        }, 400
    
    # 5. Normalizar DTO (FASE 5: normalize)
    # Agregar metadatos al DTO
    dto_dict["formato_origen"] = _detect_format_from_filename(filename)
    dto_dict["sha256"] = sha256_hash
    
    # Asegurar que tenga campo "type" si no lo tiene (para router de validaciones)
    if "type" not in dto_dict and "document_type" in dto_dict:
        doc_type = dto_dict.get("document_type", "")
        type_base = doc_type.split('.')[0] if '.' in doc_type else doc_type
        dto_dict["type"] = type_base
    
    # 6. Ejecutar validaciones (FASE 5: run_validations)
    # WARNING: v2.40: El router prioriza validadores específicos por app (cotizaciones sobre inventario genérico)
    logger.info(
        "document_ingest_validation_start",
        extra={
            "request_id": request_id,
            "schema_name": schema,
            "document_type": document_type,
            "dto_type": dto_dict.get("type"),
            "dto_document_type": dto_dict.get("document_type"),
            "has_items": bool(dto_dict.get("items")),
        }
    )
    is_valid, error_code, missing_fields = run_validations(dto_dict)
    
    # WARNING: v2.40: Fallback a validación tradicional solo si NO es catálogo de inventario/cotizaciones
    # Los catálogos de productos NO deben usar validaciones de facturas
    doc_type_base = dto_dict.get("type") or (document_type.split('.')[0] if '.' in document_type else document_type)
    
    # WARNING: CRÍTICO: NUNCA usar fallback genérico para inventario/cotizaciones
    # El fallback genérico valida campos de facturas (emisor, receptor, CUFE, etc.)
    if not is_valid and error_code == "validator_not_found":
        if doc_type_base in ["inventario", "cotizaciones"]:
            # Para catálogos de inventario/cotizaciones, NO usar fallback genérico
            logger.error(
                "document_ingest_validator_not_found_inventario_cotizaciones",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "document_type": document_type,
                    "doc_type_base": doc_type_base,
                    "dto_type": dto_dict.get("type"),
                    "dto_document_type": dto_dict.get("document_type"),
                    "has_items": bool(dto_dict.get("items")),
                    "message": "Validador de inventario/cotizaciones no encontrado, pero NO se usará fallback genérico (valida campos de facturas)",
                }
            )
            # Retornar error específico sin usar fallback genérico
            return {
                "persisted": False,
                "dto": dto_dict,
                "sha256": sha256_hash,
                "metadata": metadata,
                "error": "validator_not_found",
                "message": f"No se encontró validador específico para el tipo de documento '{document_type}' en el módulo de inventario/cotizaciones. El sistema NO usará validaciones de facturas para catálogos de productos.",
                "missing_fields": missing_fields,
            }, 422
        else:
            # Solo para otros tipos (facturas, gastos, etc.) usar fallback genérico
            logger.warning(
                "document_ingest_validator_not_found",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "document_type": document_type,
                    "doc_type_base": doc_type_base,
                    "fallback_to_generic": True,
                }
            )
            is_valid, error_code, missing_fields = validate_document_dto(dto_dict, document_type)
    
    if not is_valid:
        # WARNING: CRÍTICO: Si el error es validator_not_found_inventario_cotizaciones, ya se retornó arriba
        if error_code == "validator_not_found_inventario_cotizaciones":
            # El error ya fue retornado arriba, no hacer nada más
            pass
        else:
            # Log detallado para debugging
            logger.warning(
                "document_ingest_validation_failed",
                extra={
                    "request_id": request_id,
                    "schema_name": schema,
                    "document_type": document_type,
                    "dto_type": dto_dict.get("type"),
                    "dto_document_type": dto_dict.get("document_type"),
                    "error_code": error_code,
                    "missing_fields": missing_fields[:10],  # Limitar a 10 para no saturar logs
                    "dto_keys": list(dto_dict.keys())[:20],  # Primeras 20 claves del DTO
                    "has_numero": bool(dto_dict.get("numero")),
                    "has_identificadores": bool(dto_dict.get("identificadores")),
                    "has_fecha_emision": bool(dto_dict.get("fecha_emision")),
                    "has_totales": bool(dto_dict.get("totales")),
                    "has_items": bool(dto_dict.get("items")),
                }
            )
            return {
                "persisted": False,
                "dto": dto_dict,
                "sha256": sha256_hash,
                "metadata": metadata,
                "document_type": dto_dict.get("document_type") or document_type,
                "type": dto_dict.get("type"),
                "error": error_code,
                "message": f"Validación fallida: {', '.join(missing_fields[:5])}",
                "missing_fields": missing_fields,
            }, 422
    
    # 7. Preview mode: retornar DTO sin persistir (FASE 5)
    if preview:
        logger.info(
            "document_ingest_preview_ok",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": document_type,
                "numero": dto_dict.get("numero"),
            }
        )
        return {
            "persisted": False,
            "dto": dto_dict,
            "sha256": sha256_hash,
            "metadata": metadata,
            "document_type": dto_dict.get("document_type") or document_type,
            "type": dto_dict.get("type"),
        }, 200
    
    # 8. WARNING: REFACTOR: document_ingest SOLO parsea y devuelve DTO, NO persiste
    # La persistencia debe ser manejada por las apps individuales mediante sus propios endpoints
    # El parámetro `preview` ahora es ignorado - siempre devolvemos DTO sin persistir
    logger.info(
        "document_ingest_dto_ready",
        extra={
            "request_id": request_id,
            "schema_name": schema,
            "document_type": document_type,
            "numero": dto_dict.get("numero"),
        }
    )
    return {
        "success": True,
        "persisted": False,  # Siempre False - document_ingest NO persiste
        "dto": dto_dict,
        "sha256": sha256_hash,
        "metadata": metadata,
        "document_type": dto_dict.get("document_type") or document_type,
        "type": dto_dict.get("type"),
        "tipo": dto_dict.get("type") or dto_dict.get("document_type", ""),
    }, 200


def _detect_format_from_filename(filename: str | None) -> str | None:
    """
    Detecta el formato del archivo desde su nombre.
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        str: Formato detectado (ej: "xml", "pdf", "xlsx") o None
    """
    if not filename:
        return None
    
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
    
    format_mapping = {
        'xml': 'xml',
        'pdf': 'pdf',
        'xls': 'xls',
        'xlsx': 'xlsx',
        'csv': 'csv',
        'txt': 'txt',
    }
    
    return format_mapping.get(ext) if ext else None
    """
    Detecta el formato del archivo desde su nombre.
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        str: Formato detectado (ej: "xml", "pdf", "xlsx") o None
    """
    if not filename:
        return None
    
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
    
    format_mapping = {
        'xml': 'xml',
        'pdf': 'pdf',
        'xls': 'xls',
        'xlsx': 'xlsx',
        'csv': 'csv',
        'txt': 'txt',
    }
    
    return format_mapping.get(ext) if ext else None
