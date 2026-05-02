"""
Router de validadores (FASE 4.1 + FASE 2).

WARNING: PRINCIPIOS:
- Selecciona el validador apropiado según tipo de documento y app
- Permite registrar validadores por app
- Extensible: Nuevas apps pueden registrar sus validadores sin modificar el core
- Router por tipo de documento: Dirige validaciones según document_type del DTO
"""
from typing import Any

from .base import BaseValidator

# Registry de validadores (por app:document_type)
_validators: dict[str, BaseValidator] = {}

# Router de validaciones por tipo de documento (FASE 2)
VALIDATORS: dict[str, BaseValidator] = {}


def register_validator(validator: BaseValidator) -> None:
    """
    Registra un validador en el sistema.
    
    Registra el validador tanto en el registry por app como en el router por tipo de documento.
    
    Args:
        validator: Instancia de BaseValidator a registrar
        
    Ejemplo:
        from apps.services.document_ingest.validations.factura import FacturaValidator
        register_validator(FacturaValidator())
    """
    import logging
    logger = logging.getLogger("apps.services.document_ingest.validations")
    
    # Registrar en el registry por app:document_type
    key = f"{validator.app_name}:{validator.document_type}"
    _validators[key] = validator
    
    # WARNING: v2.40: También registrar por tipo base para búsqueda flexible
    doc_type_base = validator.document_type.split('.')[0] if '.' in validator.document_type else validator.document_type
    key_base = f"{validator.app_name}:{doc_type_base}"
    if key_base not in _validators:  # Solo si no existe ya
        _validators[key_base] = validator
    
    # Registrar en el router por tipo de documento (FASE 2)
    # WARNING: v2.40: Permitir override para asegurar que el validador correcto se registre
    # Prioridad: CotizacionesValidator sobre InventarioValidator para tipo "inventario"
    if doc_type_base == "inventario":
        # Verificar si es CotizacionesValidator (por nombre de clase, no por app_name)
        is_cotizaciones_validator = validator.__class__.__name__ == "CotizacionesValidator"
        
        if is_cotizaciones_validator:
            # Forzar registro del validador de cotizaciones para inventario (SIEMPRE override)
            old_validator = VALIDATORS.get(doc_type_base)
            VALIDATORS[doc_type_base] = validator
            logger.info(
                "validator_registered_cotizaciones_override",
                extra={
                    "app_name": validator.app_name,
                    "document_type": validator.document_type,
                    "doc_type_base": doc_type_base,
                    "validator": validator.__class__.__name__,
                    "old_validator": old_validator.__class__.__name__ if old_validator else None
                }
            )
        else:
            # Si es InventarioValidator u otro, solo registrar si no existe ya
            # (para evitar que InventarioValidator sobrescriba CotizacionesValidator)
            if doc_type_base not in VALIDATORS:
                VALIDATORS[doc_type_base] = validator
                logger.info(
                    "validator_registered_inventario",
                    extra={
                        "app_name": validator.app_name,
                        "document_type": validator.document_type,
                        "doc_type_base": doc_type_base,
                        "validator": validator.__class__.__name__
                    }
                )
            else:
                existing_validator = VALIDATORS[doc_type_base]
                # Solo sobrescribir si el existente NO es CotizacionesValidator
                if existing_validator.__class__.__name__ != "CotizacionesValidator":
                    VALIDATORS[doc_type_base] = validator
                    logger.info(
                        "validator_registered_inventario_override",
                        extra={
                            "app_name": validator.app_name,
                            "document_type": validator.document_type,
                            "doc_type_base": doc_type_base,
                            "validator": validator.__class__.__name__,
                            "old_validator": existing_validator.__class__.__name__
                        }
                    )
                else:
                    logger.debug(
                        "validator_registered_inventario_skipped",
                        extra={
                            "app_name": validator.app_name,
                            "document_type": validator.document_type,
                            "doc_type_base": doc_type_base,
                            "validator": validator.__class__.__name__,
                            "existing_validator": existing_validator.__class__.__name__
                        }
                    )
    elif doc_type_base not in VALIDATORS:
        # Solo registrar si no existe (evitar override de validadores más específicos)
        VALIDATORS[doc_type_base] = validator
    
    logger.debug(
        "validator_registered",
        extra={
            "app_name": validator.app_name,
            "document_type": validator.document_type,
            "doc_type_base": doc_type_base,
            "key": key,
            "key_base": key_base,
            "validator": validator.__class__.__name__
        }
    )


def get_validator(app_name: str, document_type: str) -> BaseValidator | None:
    """
    Obtiene el validador para una app y tipo de documento específicos.
    
    Args:
        app_name: Nombre de la app (ej: "facturas", "gastos", "cotizaciones")
        document_type: Tipo de documento (ej: "invoice.ubl21", "inventario.catalogo")
        
    Returns:
        Instancia del validador o None si no existe
        
    Ejemplo:
        validator = get_validator("cotizaciones", "inventario.catalogo")
        if validator:
            is_valid, error_code, missing_fields = validator.validate(dto, document_type)
    """
    import logging
    logger = logging.getLogger("apps.services.document_ingest.validations")
    
    # Buscar por clave exacta: "app_name:document_type"
    key = f"{app_name}:{document_type}"
    validator = _validators.get(key)
    
    if validator:
        logger.debug(
            "get_validator_found",
            extra={
                "app_name": app_name,
                "document_type": document_type,
                "key": key,
                "validator": validator.__class__.__name__
            }
        )
        return validator
    
    # Si no se encuentra, buscar por tipo base también
    doc_type_base = document_type.split('.')[0] if '.' in document_type else document_type
    key_base = f"{app_name}:{doc_type_base}"
    validator = _validators.get(key_base)
    
    if validator:
        logger.debug(
            "get_validator_found_by_base",
            extra={
                "app_name": app_name,
                "document_type": document_type,
                "doc_type_base": doc_type_base,
                "key_base": key_base,
                "validator": validator.__class__.__name__
            }
        )
        return validator
    
    # Log si no se encuentra
    logger.warning(
        "get_validator_not_found",
        extra={
            "app_name": app_name,
            "document_type": document_type,
            "key": key,
            "key_base": key_base,
            "available_keys": list(_validators.keys())[:10]
        }
    )
    
    return None


def list_validators() -> list[dict[str, str]]:
    """
    Lista todos los validadores registrados.
    
    Returns:
        Lista de dicts con información de cada validador:
        [{"app_name": "...", "document_type": "...", "class": "..."}, ...]
    """
    return [
        {
            "app_name": validator.app_name,
            "document_type": validator.document_type,
            "class": validator.__class__.__name__,
        }
        for validator in _validators.values()
    ]


def get_validator_by_document_type(document_type: str) -> BaseValidator | None:
    """
    Obtiene el validador por tipo de documento (busca en todas las apps).
    
    Si hay múltiples validadores para el mismo tipo, retorna el primero encontrado.
    
    Args:
        document_type: Tipo de documento (ej: "invoice.ubl21")
        
    Returns:
        Instancia del validador o None si no existe
    """
    # Primero intentar buscar por document_type completo
    for validator in _validators.values():
        if validator.document_type == document_type:
            return validator
    
    # Si no se encuentra, intentar por tipo base (ej: "invoice.ubl21" -> "invoice")
    doc_type_base = document_type.split('.')[0] if '.' in document_type else document_type
    return VALIDATORS.get(doc_type_base)


def run_validations(dto_json: dict[str, Any]) -> tuple[bool, str | None, list[str]]:
    """
    Ejecuta validaciones según el tipo de documento del DTO (FASE 2).
    
    El router dirige validaciones dependiendo del "document_type" asignado por el parser.
    
    WARNING: v2.40: Prioriza validadores específicos por app (ej: cotizaciones sobre inventario genérico)
    
    Args:
        dto_json: DTO JSON con el campo "document_type" o "type"
        
    Returns:
        Tupla (is_valid, error_code, missing_fields):
        - is_valid: True si el DTO es válido
        - error_code: Código de error si no es válido
        - missing_fields: Lista de campos faltantes o errores de validación
        
    Ejemplo:
        dto = {
            "document_type": "invoice.ubl21",
            "numero": "FAC001",
            ...
        }
        is_valid, error_code, missing_fields = run_validations(dto)
    """
    import logging
    logger = logging.getLogger("apps.services.document_ingest.validations")
    
    # Obtener tipo de documento del DTO (FASE 3: soporta type y document_type)
    # Prioridad: type (base) > document_type (completo)
    doc_type = dto_json.get("type") or dto_json.get("document_type", "")
    
    if not doc_type:
        # WARNING: v2.40: Si no hay type/document_type pero tiene items, asumir que es inventario.catalogo
        if "items" in dto_json and isinstance(dto_json.get("items"), list) and len(dto_json.get("items", [])) > 0:
            logger.info(
                "validation_router_inferring_inventario_from_items",
                extra={
                    "has_items": True,
                    "items_count": len(dto_json.get("items", []))
                }
            )
            doc_type = "inventario"
        else:
            return False, "missing_document_type", ["document_type o type no encontrado en DTO"]
    
    # Extraer tipo base (ej: "invoice.ubl21" -> "invoice")
    doc_type_base = doc_type.split('.')[0] if '.' in doc_type else doc_type
    
    # WARNING: v2.40: Para inventario, buscar primero validador específico por app
    # Priorizar validador de cotizaciones sobre inventario genérico
    if doc_type_base == "inventario":
        # Buscar validador específico de cotizaciones primero
        # Intentar con document_type completo y tipo base
        doc_type_full = dto_json.get("document_type", doc_type)
        cotizaciones_validator = (
            get_validator("cotizaciones", doc_type_full) or 
            get_validator("cotizaciones", doc_type) or 
            get_validator("cotizaciones", doc_type_base)
        )
        if cotizaciones_validator:
            logger.info(
                "validation_router_using_cotizaciones_validator",
                extra={
                    "document_type": doc_type,
                    "doc_type_full": doc_type_full,
                    "doc_type_base": doc_type_base,
                    "validator": "CotizacionesValidator",
                    "has_items": bool(dto_json.get("items"))
                }
            )
            return cotizaciones_validator.validate(dto_json, doc_type)
        else:
            # Log si no se encuentra el validador de cotizaciones
            logger.error(
                "validation_router_cotizaciones_validator_not_found",
                extra={
                    "document_type": doc_type,
                    "doc_type_full": doc_type_full,
                    "doc_type_base": doc_type_base,
                    "available_validators": list(_validators.keys())[:20],
                    "validators_by_base": list(VALIDATORS.keys())
                }
            )
    
    # Buscar validador en el router por tipo base
    if doc_type_base in VALIDATORS:
        validator = VALIDATORS[doc_type_base]
        # WARNING: v2.40: Si es inventario y el validador NO es de cotizaciones, intentar buscar el de cotizaciones primero
        if doc_type_base == "inventario" and validator.app_name != "cotizaciones":
            logger.warning(
                "validation_router_inventario_not_cotizaciones",
                extra={
                    "document_type": doc_type,
                    "doc_type_base": doc_type_base,
                    "current_validator": validator.__class__.__name__,
                    "current_app": validator.app_name,
                    "has_items": bool(dto_json.get("items"))
                }
            )
            # Intentar buscar el validador de cotizaciones una vez más
            doc_type_full = dto_json.get("document_type", doc_type)
            cotizaciones_validator = (
                get_validator("cotizaciones", doc_type_full) or 
                get_validator("cotizaciones", doc_type) or 
                get_validator("cotizaciones", doc_type_base)
            )
            if cotizaciones_validator:
                logger.info(
                    "validation_router_switching_to_cotizaciones",
                    extra={
                        "document_type": doc_type,
                        "doc_type_base": doc_type_base,
                        "old_validator": validator.__class__.__name__,
                        "new_validator": cotizaciones_validator.__class__.__name__
                    }
                )
                return cotizaciones_validator.validate(dto_json, doc_type)
        
        logger.info(
            "validation_router_using_validator",
            extra={
                "document_type": doc_type,
                "doc_type_base": doc_type_base,
                "validator": validator.__class__.__name__,
                "validator_app": validator.app_name
            }
        )
        return validator.validate(dto_json, doc_type)
    
    # Si no se encuentra, intentar buscar por document_type completo
    validator = get_validator_by_document_type(doc_type)
    if validator:
        logger.info(
            "validation_router_using_validator_by_doc_type",
            extra={
                "document_type": doc_type,
                "validator": validator.__class__.__name__
            }
        )
        return validator.validate(dto_json, doc_type)
    
    # No se encontró validador para este tipo
    # WARNING: CRÍTICO: Si es inventario/cotizaciones, NO retornar validator_not_found
    # porque causaría que se use el fallback genérico que valida campos de facturas
    if doc_type_base in ["inventario", "cotizaciones"]:
        logger.error(
            "validation_router_validator_not_found_inventario_cotizaciones",
            extra={
                "document_type": doc_type,
                "doc_type_base": doc_type_base,
                "dto_keys": list(dto_json.keys())[:10],
                "has_items": bool(dto_json.get("items")),
                "available_validators": list(VALIDATORS.keys()),
                "available_app_validators": list(_validators.keys())[:20],
                "message": "CRÍTICO: No se encontró validador para inventario/cotizaciones. Esto causará error 422 sin fallback genérico."
            }
        )
        # Retornar error específico para inventario/cotizaciones
        return False, "validator_not_found_inventario_cotizaciones", [
            f"No se encontró validador específico para tipo: {doc_type}",
            "El sistema NO usará validaciones de facturas para catálogos de productos."
        ]
    
    logger.warning(
        "validation_router_validator_not_found",
        extra={
            "document_type": doc_type,
            "doc_type_base": doc_type_base,
            "dto_keys": list(dto_json.keys())[:10]
        }
    )
    return False, "validator_not_found", [f"No se encontró validador para tipo: {doc_type}"]
