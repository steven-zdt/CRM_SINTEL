"""
Router de Dominio para Materialización de Documentos (FASE 7 + FASE 4).

# WARNING: PRINCIPIOS:
- Router centralizado: Selecciona función de materialización según dto["type"]
- Multi-tenant: Opera en el contexto del tenant actual (schema_context)
- Idempotencia: Delegada a cada servicio de dominio
- Separación de responsabilidades: Orquestación → Dominio dueño
- Extensible: Nuevos tipos se registran sin modificar el core

Flujo:
1. Recibe DTO JSON canónico del pipeline (document_ingest)
2. Selecciona función de materialización según dto["type"]
3. Ejecuta en contexto del tenant actual
4. Retorna objeto materializado o payload mínimo

# WARNING: FASE 4: Agregado diccionario DOMAIN_MATERIALIZERS y función materializar() simplificada
para integración directa con pipeline universal de facturas.
"""
import logging
from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from django.db import connection

logger = logging.getLogger("apps.tenant.core.document_router")


# # WARNING: FASE 4: Diccionario de materializadores para facturas (simplificado)
DOMAIN_MATERIALIZERS: dict[str, Callable[[dict[str, Any]], tuple[dict[str, Any], int]]] = {}

# Registro de materializadores por tipo de documento (FASE 7 - completo)
MATERIALIZERS: dict[str, Callable[[dict[str, Any]], tuple[dict[str, Any], int]]] = {}


def register_materializer(document_type: str, materializer_func: Callable[[dict[str, Any]], tuple[dict[str, Any], int]]) -> None:
    """
    Registra una función de materialización para un tipo de documento.
    
    Args:
        document_type: Tipo base del documento (ej: "invoice", "gasto")
        materializer_func: Función que recibe DTO y retorna (result, status_code)
    """
    MATERIALIZERS[document_type] = materializer_func
    logger.info(
        "document_router_materializer_registered",
        extra={
            "document_type": document_type,
            "materializer": materializer_func.__name__,
        }
    )


def get_materializer(document_type: str) -> Callable[[dict[str, Any]], tuple[dict[str, Any], int]] | None:
    """
    Obtiene la función de materialización para un tipo de documento.
    
    Args:
        document_type: Tipo base del documento (ej: "invoice", "gasto")
        
    Returns:
        Función de materialización o None si no está registrada
    """
    return MATERIALIZERS.get(document_type)


def materialize_document(dto: dict[str, Any], request_id: str | None = None) -> tuple[dict[str, Any], int]:
    """
    Materializa un documento desde DTO JSON canónico (FASE 7).
    
    Flujo:
    1. Extrae dto["type"] (tipo base: "invoice", "creditnote", "gasto", etc.)
    2. Selecciona materializador registrado
    3. Ejecuta en contexto del tenant actual
    4. Retorna resultado estructurado
    
    Args:
        dto: DTO JSON canónico del pipeline
        request_id: ID de la petición para logging (opcional)
        
    Returns:
        Tupla (result, status_code):
        - result: {
            "id": int,
            "numero": str,
            "created": bool,
            "error": str (si hay error),
            "message": str (si hay error),
        }
        - status_code: 200 (actualizado), 201 (creado), 409 (duplicado), 422 (validación), 415 (tipo no soportado)
        
    Raises:
        ValidationError: Si hay errores de validación o tipo no soportado
    """
    schema = getattr(connection, "schema_name", "-")
    
    # Extraer tipo base del documento
    document_type = dto.get("type") or dto.get("document_type", "")
    if not document_type:
        logger.warning(
            "document_router_missing_type",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "dto_keys": list(dto.keys()),
            }
        )
        return {
            "error": "missing_document_type",
            "message": "DTO no contiene campo 'type' o 'document_type'",
        }, 400
    
    # Normalizar tipo base (ej: "invoice.ubl21" → "invoice")
    type_base = document_type.split('.')[0] if '.' in document_type else document_type
    
    # Asegurar que los materializadores estén registrados (lazy initialization)
    _ensure_materializers_registered()
    
    # Obtener materializador
    materializer = get_materializer(type_base)
    if not materializer:
        logger.warning(
            "document_router_type_not_supported",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": type_base,
                "available_types": list(MATERIALIZERS.keys()),
            }
        )
        return {
            "error": "type_not_supported",
            "message": f"Tipo de documento '{type_base}' no soportado en dominio. Tipos disponibles: {', '.join(MATERIALIZERS.keys())}",
        }, 415
    
    # Ejecutar materializador en contexto del tenant actual
    try:
        logger.info(
            "document_router_materializing",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": type_base,
                "numero": dto.get("numero"),
            }
        )
        
        result, status_code = materializer(dto)
        
        logger.info(
            "document_router_materialized",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": type_base,
                "numero": result.get("numero"),
                "id": result.get("id"),
                "status_code": status_code,
                "created": result.get("created", False),
            }
        )
        
        return result, status_code
        
    except ValidationError as e:
        error_dict = e.message_dict if hasattr(e, 'message_dict') else {}
        error_code = error_dict.get("error", ["validation_error"])[0] if isinstance(error_dict.get("error"), list) else error_dict.get("error", "validation_error")
        error_message = error_dict.get("message", [str(e)])[0] if isinstance(error_dict.get("message"), list) else error_dict.get("message", str(e))
        
        # Determinar status code según tipo de error
        if error_code == "duplicate":
            status_code = 409
        elif error_code in ("missing_invoice", "already_has_nc", "missing_reference", "missing_cude", "missing_number", "invalid_total"):
            status_code = 422
        else:
            status_code = 422
        
        logger.warning(
            "document_router_materialization_failed",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": type_base,
                "error_code": error_code,
                "status_code": status_code,
            }
        )
        
        return {
            "error": error_code,
            "message": error_message,
        }, status_code
        
    except Exception:
        logger.exception(
            "document_router_materialization_error",
            extra={
                "request_id": request_id,
                "schema_name": schema,
                "document_type": type_base,
            }
        )
        return {
            "error": "internal_server_error",
            "message": "Error interno al intentar materializar documento",
        }, 500


# # WARNING: FASE 4: Función simplificada para integración directa con pipeline universal
def materializar(dto: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """
    Materializa un documento desde DTO (FASE 4 - versión simplificada).
    
    # WARNING: FASE 4: Función simplificada específica para facturas.
    Usa DOMAIN_MATERIALIZERS para routing directo.
    
    Args:
        dto: DTO JSON canónico del pipeline
        
    Returns:
        Tuple (payload, status_code)
        
    Raises:
        ValueError: Si el tipo no está soportado
    """
    # Asegurar que los materializadores estén registrados
    _ensure_domain_materializers_registered()
    
    tipo = dto.get("type") or dto.get("document_type", "")
    if not tipo:
        raise ValueError("DTO no contiene campo 'type' o 'document_type'")
    
    # Normalizar tipo base (ej: "invoice.ubl21" → "invoice")
    tipo_base = tipo.split('.')[0] if '.' in tipo else tipo
    
    if tipo_base not in DOMAIN_MATERIALIZERS:
        raise ValueError(f"Tipo no soportado por Facturas: {tipo_base}. Tipos disponibles: {', '.join(DOMAIN_MATERIALIZERS.keys())}")
    
    materializer_func = DOMAIN_MATERIALIZERS[tipo_base]
    return materializer_func(dto)


def _ensure_domain_materializers_registered():
    """Registra los materializadores de facturas en DOMAIN_MATERIALIZERS (FASE 4)."""
    if DOMAIN_MATERIALIZERS:
        return  # Ya están registrados
    
    try:
        from apps.tenant.facturas.services import (
            materializar_factura_desde_dto,
            materializar_nc_desde_dto,
        )
        DOMAIN_MATERIALIZERS["invoice"] = materializar_factura_desde_dto
        DOMAIN_MATERIALIZERS["creditnote"] = materializar_nc_desde_dto
        logger.info("document_router: Materializadores de facturas registrados en DOMAIN_MATERIALIZERS")
    except ImportError as e:
        logger.warning(f"document_router: No se pudieron importar materializadores de facturas: {e}")


# Registro lazy de materializadores (solo cuando se necesite, no al importar)
_initialized = False


def _ensure_materializers_registered():
    """Registra los materializadores por defecto (lazy initialization)."""
    global _initialized
    if _initialized:
        return
    
    try:
        # Factura
        from apps.tenant.facturas.services import guardar_factura_desde_dto
        
        def materializar_factura_wrapper(dto: dict[str, Any]) -> tuple[dict[str, Any], int]:
            """Wrapper para adaptar guardar_factura_desde_dto al contrato del router."""
            result, status_code = guardar_factura_desde_dto(dto, xml_text=None)
            return result, status_code
        
        register_materializer("invoice", materializar_factura_wrapper)
    except ImportError:
        logger.warning("document_router: No se pudo importar materializador de facturas")
    
    try:
        # Nota Crédito
        from apps.tenant.facturas.services import guardar_nota_credito_desde_dto
        
        def materializar_nc_wrapper(dto: dict[str, Any]) -> tuple[dict[str, Any], int]:
            """Wrapper para adaptar guardar_nota_credito_desde_dto al contrato del router."""
            try:
                nota_credito = guardar_nota_credito_desde_dto(dto, xml_text=None)
                return {
                    "id": nota_credito.id,
                    "numero": nota_credito.numero,
                    "cude": nota_credito.cude,
                    "created": True,
                }, 201
            except ValidationError as e:
                raise e
        
        register_materializer("creditnote", materializar_nc_wrapper)
    except ImportError:
        logger.warning("document_router: No se pudo importar materializador de notas crédito")
    
    try:
        # Gasto
        import importlib.util
        import os
        services_path = os.path.join(os.path.dirname(__file__), '../gastos/services.py')
        spec = importlib.util.spec_from_file_location("gastos_services", services_path)
        gastos_services = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gastos_services)
        register_materializer("gasto", gastos_services.materializar_gasto_desde_dto)
    except (ImportError, FileNotFoundError):
        logger.warning("document_router: No se pudo importar materializador de gastos")
    
    try:
        # Inventario
        from apps.tenant.inventario.services.services import materializar_inventario_desde_dto
        register_materializer("inventario", materializar_inventario_desde_dto)
    except ImportError:
        logger.warning("document_router: No se pudo importar materializador de inventario")
    
    _initialized = True
