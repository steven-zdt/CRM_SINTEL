"""
Router de apps para document_ingest (v2.40).

WARNING: PRINCIPIOS:
- Detecta qué app está consumiendo el servicio
- Enruta a parsers específicos por app
- Mantiene lógica separada por app
- Extensible: nuevas apps pueden registrar sus parsers sin modificar el core
"""
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("apps.services.document_ingest.app_router")

# Registry de parsers por app y tipo de documento
_APP_PARSERS: dict[str, dict[str, Callable]] = {}


def register_app_parser(app_name: str, media_type: str, parser_func: Callable) -> None:
    """
    Registra un parser específico para una app.
    
    Args:
        app_name: Nombre de la app (ej: "cotizaciones", "facturas", "gastos")
        media_type: Tipo de medio (ej: "excel", "csv", "pdf", "xml")
        parser_func: Función parser que recibe (file_bytes, filename, kind_hint) y retorna DTO
    
    Ejemplo:
        from apps.services.document_parser.cotizaciones.excel_parser import parse_catalogo_to_dto
        register_app_parser("cotizaciones", "excel", parse_catalogo_to_dto)
    """
    if app_name not in _APP_PARSERS:
        _APP_PARSERS[app_name] = {}
    
    _APP_PARSERS[app_name][media_type] = parser_func
    
    logger.info(
        "app_parser_registered",
        extra={
            "app_name": app_name,
            "media_type": media_type,
            "parser": parser_func.__name__
        }
    )


def get_app_parser(app_name: str, media_type: str) -> Callable | None:
    """
    Obtiene el parser específico de una app para un tipo de medio.
    
    Args:
        app_name: Nombre de la app
        media_type: Tipo de medio
        
    Returns:
        Función parser o None si no existe
    """
    return _APP_PARSERS.get(app_name, {}).get(media_type)


def detect_app_from_kind_hint(kind_hint: str | None) -> str | None:
    """
    Detecta la app consumidora desde el kind_hint.
    
    Mapeo:
    - "inventario", "catalogo", "productos" → "cotizaciones"
    - "factura", "invoice" → "facturas"
    - "gasto", "expense" → "gastos"
    - etc.
    
    WARNING: v2.40: Prioriza detección de cotizaciones para catálogos de productos.
    
    Args:
        kind_hint: Hint del tipo de documento
        
    Returns:
        Nombre de la app o None
    """
    if not kind_hint:
        return None
    
    kind_lower = kind_hint.lower().strip()
    
    # WARNING: v2.40: Mapeo de hints a apps (prioridad: cotizaciones para catálogos)
    app_mapping = {
        "inventario": "cotizaciones",
        "catalogo": "cotizaciones",
        "productos": "cotizaciones",
        "cotizaciones": "cotizaciones",
        "factura": "facturas",
        "invoice": "facturas",
        "gasto": "gastos",
        "expense": "gastos",
    }
    
    # Buscar coincidencia exacta primero (más específico)
    if kind_lower in app_mapping:
        return app_mapping[kind_lower]
    
    # Buscar coincidencia parcial
    for hint, app in app_mapping.items():
        if hint in kind_lower:
            return app
    
    return None


def route_by_app(
    file_bytes: bytes,
    media_type: str,
    filename: str | None = None,
    kind_hint: str | None = None,
    app_name: str | None = None
) -> dict[str, Any] | None:
    """
    Enruta el parseo a un parser específico de app si existe.
    
    Args:
        file_bytes: Contenido del archivo
        media_type: Tipo de medio detectado (ej: "excel", "csv")
        filename: Nombre del archivo
        kind_hint: Hint del tipo de documento
        app_name: Nombre de la app (opcional, se detecta desde kind_hint si no se proporciona)
        
    Returns:
        DTO parseado o None si no hay parser específico de app
    """
    # Detectar app si no se proporciona
    if not app_name:
        app_name = detect_app_from_kind_hint(kind_hint)
    
    if not app_name:
        return None
    
    # Buscar parser específico de la app
    parser_func = get_app_parser(app_name, media_type)
    
    if parser_func:
        logger.info(
            "app_parser_used",
            extra={
                "app_name": app_name,
                "media_type": media_type,
                "kind_hint": kind_hint,
                "parser": parser_func.__name__
            }
        )
        try:
            return parser_func(file_bytes, filename, kind_hint)
        except Exception as e:
            logger.error(
                "app_parser_error",
                extra={
                    "app_name": app_name,
                    "media_type": media_type,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return None
