"""
Router de documentos (enrutamiento de parsers) (FASE 3.1).

WARNING: PRINCIPIOS:
- Enruta documentos a parsers apropiados según tipo detectado
- Extensible: Nuevos tipos se agregan sin modificar routing
- Agnóstico del dominio: no conoce modelos Django
- Retorna DTO JSON unificado
- WARNING: v2.40: Prioriza parsers específicos por app antes de parsers genéricos
"""
import logging
from typing import Any

from apps.services.document_ingest.app_router import route_by_app
from apps.services.document_parser.detector import detect_document_type

logger = logging.getLogger("apps.services.document_ingest.router")


def route(
    file_bytes: bytes | str,
    filename: str | None = None,
    mime_type: str | None = None,
    media_type: str | None = None,
    kind_hint: str | None = None
) -> dict[str, Any]:
    """
    Dirige un documento al parser apropiado según el tipo detectado (FASE 3.1).
    
    WARNING: REVERSIÓN: Recibe contenido NORMALIZADO del normalizer (bytes o str según tipo).
    
    Args:
        file_bytes: Contenido del documento normalizado (bytes para XML/PDF/Excel, str para CSV/TXT)
        filename: Nombre del archivo (opcional)
        mime_type: MIME type del archivo (opcional)
        media_type: Tipo de documento ya detectado por el normalizer (opcional)
        
    Returns:
        Dict con DTO JSON unificado:
        {
            "document_type": str (ej: "invoice.ubl21", "creditnote.ubl21"),
            "dto": {...DTO_UNIFICADO...}
        }
        
    Raises:
        ValueError: Si no se puede detectar el tipo o parsear el documento
    """
    # WARNING: REVERSIÓN: Si media_type ya viene del normalizer, usarlo directamente
    # Si no, detectar (fallback para compatibilidad)
    if not media_type:
        detection_result = detect_document_type(file_bytes, filename, mime_type)
        media_type = detection_result.get("media_type") if isinstance(detection_result, dict) else None
        confidence = detection_result.get("confidence", 0.0) if isinstance(detection_result, dict) else 0.0
    else:
        confidence = 1.0  # Si viene del normalizer, confianza alta
    
    if not media_type:
        raise ValueError("No se pudo detectar el tipo de documento")
    
    # WARNING: v2.40: Intentar primero routing por app (parsers específicos)
    # Si existe un parser específico de app, usarlo en lugar del genérico
    # WARNING: CRÍTICO: Para inventario/cotizaciones, SIEMPRE intentar parser específico primero
    if isinstance(file_bytes, bytes):
        # Detectar app desde kind_hint para forzar uso de parser específico
        from apps.services.document_ingest.app_router import detect_app_from_kind_hint
        detected_app = detect_app_from_kind_hint(kind_hint)
        
        app_dto = route_by_app(
            file_bytes=file_bytes,
            media_type=media_type,
            filename=filename,
            kind_hint=kind_hint,
            app_name=detected_app  # Pasar app_name explícitamente
        )
        if app_dto:
            logger.info(
                "router_using_app_parser",
                extra={
                    "media_type": media_type,
                    "kind_hint": kind_hint,
                    "detected_app": detected_app,
                    "document_type": app_dto.get("document_type"),
                    "dto_type": app_dto.get("type")
                }
            )
            return {
                "document_type": app_dto.get("document_type", ""),
                "dto": app_dto,
            }
        elif detected_app and detected_app == "cotizaciones":
            # WARNING: CRÍTICO: Si se detectó cotizaciones pero no hay parser, es un error
            # No usar parser genérico porque validará como factura
            logger.error(
                "router_cotizaciones_parser_not_found",
                extra={
                    "media_type": media_type,
                    "kind_hint": kind_hint,
                    "detected_app": detected_app,
                    "message": "Parser específico de cotizaciones no encontrado. NO se usará parser genérico."
                }
            )
            raise ValueError(f"Parser específico de cotizaciones no encontrado para media_type: {media_type}. No se usará parser genérico para evitar validaciones de facturas.")
    
    # WARNING: REVERSIÓN: Enrutar según media_type y llamar al parser genérico correspondiente
    # Los parsers reciben contenido NORMALIZADO (bytes o str según tipo)
    if media_type == "xml":
        from apps.services.document_parser.xml_parser import parse_to_dto
        # XML normalizado viene como bytes UTF-8
        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode('utf-8')
        dto = parse_to_dto(file_bytes, filename)
        return {
            "document_type": dto.get("document_type", "invoice.ubl21"),
            "dto": dto,
        }
    
    elif media_type == "pdf":
        from apps.services.document_parser.pdf_parser import parse_to_dto
        # PDF normalizado viene como bytes (binario preservado)
        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode('utf-8')
        dto = parse_to_dto(file_bytes, filename)
        return {
            "document_type": dto.get("document_type", "invoice.ubl21"),
            "dto": dto,
        }
    
    elif media_type in ("excel", "xls", "xlsx"):
        from apps.services.document_parser.excel_parser import parse_to_dto
        # Excel normalizado viene como bytes (binario preservado)
        if isinstance(file_bytes, str):
            file_bytes = file_bytes.encode('utf-8')
        dto = parse_to_dto(file_bytes, filename, kind_hint=kind_hint)
        return {
            "document_type": dto.get("document_type", "invoice.ubl21"),
            "dto": dto,
        }
    
    elif media_type == "csv":
        from apps.services.document_parser.csv_parser import parse_to_dto
        # CSV normalizado viene como str UTF-8 (texto normalizado)
        if isinstance(file_bytes, bytes):
            file_bytes = file_bytes.decode('utf-8', errors='replace')
        dto = parse_to_dto(file_bytes, filename)
        return {
            "document_type": dto.get("document_type", "invoice.ubl21"),
            "dto": dto,
        }
    
    elif media_type == "txt":
        from apps.services.document_parser.txt_parser import parse_to_dto
        # TXT normalizado viene como str UTF-8 (texto normalizado)
        if isinstance(file_bytes, bytes):
            file_bytes = file_bytes.decode('utf-8', errors='replace')
        dto = parse_to_dto(file_bytes, filename)
        return {
            "document_type": dto.get("document_type", "invoice.ubl21"),
            "dto": dto,
        }
    
    else:
        raise ValueError(f"Tipo de documento no soportado: {media_type}")
