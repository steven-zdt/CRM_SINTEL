"""
Validadores de integridad y campos obligatorios para DTOs de documentos (FASE 4.4).

WARNING: PRINCIPIOS:
- Usa el sistema de validation plugins (validations/)
- Mantiene compatibilidad con código existente
- Delega a validadores específicos por app cuando están disponibles
- WARNING: v2.40: NUNCA usa fallback genérico para inventario/cotizaciones (valida campos de facturas)
- Fallback a validación genérica solo para otros tipos (facturas, gastos, etc.)
"""
from typing import Any

from apps.services.document_ingest.validations.router import (
    get_validator,
    get_validator_by_document_type,
)


def validate_document_dto(
    dto: dict[str, Any],
    document_type: str,
    app_name: str | None = None
) -> tuple[bool, str | None, list[str]]:
    """
    Valida un DTO de documento (FASE 4.4).
    
    Usa el sistema de validation plugins:
    1. Intenta usar validador específico de la app (si app_name está proporcionado)
    2. Si no, intenta usar validador genérico por tipo de documento
    3. Si no hay validador, usa validación genérica básica (SOLO para facturas/gastos, NO para inventario/cotizaciones)
    
    WARNING: v2.40: NUNCA usa fallback genérico para inventario/cotizaciones.
    El fallback genérico valida campos de facturas (emisor, receptor, CUFE, etc.)
    
    Args:
        dto: DTO a validar (dict JSON)
        document_type: Tipo de documento (ej: "invoice.ubl21", "creditnote.ubl21", "inventario.catalogo")
        app_name: Nombre de la app (opcional, ej: "facturas", "gastos", "cotizaciones")
        
    Returns:
        Tupla (is_valid, error_code, missing_fields):
        - is_valid: True si el DTO es válido
        - error_code: Código de error si no es válido
        - missing_fields: Lista de campos faltantes o inválidos
    """
    # WARNING: CRÍTICO: Detectar si es inventario/cotizaciones para NO usar fallback genérico
    doc_type_base = document_type.split('.')[0] if '.' in document_type else document_type
    dto_type = dto.get("type") or dto.get("document_type", "")
    dto_type_base = dto_type.split('.')[0] if '.' in dto_type else dto_type
    is_inventario_cotizaciones = (
        doc_type_base in ["inventario", "cotizaciones"] or 
        dto_type_base in ["inventario", "cotizaciones"] or
        "items" in dto  # Si tiene items, probablemente es catálogo
    )
    
    # 1. Intentar usar validador específico de la app
    if app_name:
        validator = get_validator(app_name, document_type)
        if validator:
            return validator.validate(dto, document_type)
    
    # 2. Intentar usar validador genérico por tipo de documento
    validator = get_validator_by_document_type(document_type)
    if validator:
        return validator.validate(dto, document_type)
    
    # 3. Fallback: validación genérica básica
    # WARNING: CRÍTICO: NUNCA usar fallback genérico para inventario/cotizaciones
    # El fallback genérico valida campos de facturas (emisor, receptor, CUFE, etc.)
    if is_inventario_cotizaciones:
        # Para inventario/cotizaciones, retornar error específico sin usar fallback genérico
        return False, "validator_not_found_inventario_cotizaciones", [
            f"No se encontró validador específico para tipo: {document_type}",
            "El sistema NO usará validaciones de facturas para catálogos de productos."
        ]
    
    return _validate_document_dto_generic(dto, document_type)


def _validate_document_dto_generic(dto: dict[str, Any], document_type: str) -> tuple[bool, str | None, list[str]]:
    """
    Validación genérica básica (fallback cuando no hay validador específico).
    
    Args:
        dto: DTO a validar
        document_type: Tipo de documento
        
    Returns:
        Tupla (is_valid, error_code, missing_fields)
    """
    missing_fields = []
    errors = []
    
    # 1. Validar número de documento detectado
    if not dto.get("numero") or not str(dto.get("numero")).strip():
        missing_fields.append("numero")
        errors.append("Número de documento no detectado")
    
    # 2. Validar CUFE/CUDE obligatorio
    identificadores = dto.get("identificadores", {})
    cufe = identificadores.get("cufe") or identificadores.get("uuid") or identificadores.get("cude")
    
    if not cufe or not str(cufe).strip():
        missing_fields.append("identificadores.cufe|cude|uuid")
        errors.append("CUFE/CUDE obligatorio no encontrado")
    
    # 3. Validar type válido
    dto_document_type = dto.get("document_type", "")
    valid_types = ["invoice.ubl21", "creditnote.ubl21"]
    if dto_document_type not in valid_types:
        errors.append(f"Tipo de documento inválido: {dto_document_type}")
    
    # 4. Validar fechas válidas
    fecha_emision = dto.get("fecha_emision", "")
    if not fecha_emision or not _is_valid_date(fecha_emision):
        missing_fields.append("fecha_emision")
        errors.append("Fecha de emisión inválida o no detectada")
    
    # 5. Validar estructura de emisor
    emisor = dto.get("emisor", {})
    if not emisor.get("nit") or not str(emisor.get("nit")).strip():
        missing_fields.append("emisor.nit")
    if not emisor.get("razon_social") or not str(emisor.get("razon_social")).strip():
        missing_fields.append("emisor.razon_social")
    
    # 6. Validar estructura de receptor
    receptor = dto.get("receptor", {})
    if not receptor.get("nit") or not str(receptor.get("nit")).strip():
        missing_fields.append("receptor.nit")
    if not receptor.get("razon_social") or not str(receptor.get("razon_social")).strip():
        missing_fields.append("receptor.razon_social")
    
    # 7. Validar totales coherentes
    totales = dto.get("totales", {})
    if not totales.get("moneda"):
        missing_fields.append("totales.moneda")
    
    # Validar coherencia de totales
    try:
        subtotal = Decimal(str(totales.get("subtotal", "0.00")))
        impuestos = Decimal(str(totales.get("impuestos", "0.00")))
        total = Decimal(str(totales.get("total", "0.00")))
        
        # Verificar que subtotal + impuestos ≈ total (con tolerancia de 0.01)
        expected_total = subtotal + impuestos
        if abs(total - expected_total) > Decimal("0.01"):
            errors.append("Totales incoherentes: subtotal + impuestos no coincide con total")
    except (InvalidOperation, ValueError, TypeError):
        errors.append("Totales con valores numéricos inválidos")
        missing_fields.append("totales.subtotal|impuestos|total")
    
    # 8. Validar referencias obligatorias para Nota Crédito
    if document_type.startswith("creditnote") or dto_document_type.startswith("creditnote"):
        referencia = dto.get("referencia", {})
        if not referencia:
            missing_fields.append("referencia")
            errors.append("Referencia a factura obligatoria para Nota Crédito")
        else:
            ref_numero = referencia.get("numero", "")
            ref_cufe = referencia.get("cufe", "")
            if not ref_numero and not ref_cufe:
                missing_fields.append("referencia.numero|cufe")
                errors.append("Referencia debe incluir número o CUFE de factura")
    
    if missing_fields or errors:
        error_code = "validation_error" if errors else "missing_required_fields"
        return False, error_code, missing_fields + errors
    
    return True, None, []


def _is_valid_date(date_str: str) -> bool:
    """
    Valida si una fecha es válida (ISO 8601 o formatos comunes).
    
    Args:
        date_str: String de fecha a validar
        
    Returns:
        True si la fecha es válida, False en caso contrario
    """
    if not date_str or not str(date_str).strip():
        return False
    
    # Formatos comunes
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    
    # Intentar parseo ISO 8601 flexible (opcional, si dateutil está instalado)
    try:
        from dateutil import parser
        parser.parse(date_str)
        return True
    except ImportError:
        # dateutil no está instalado, continuar sin él
        pass
    except (ValueError, TypeError):
        pass
    
    return False


def validate_invoice_dto(dto: dict[str, Any]) -> tuple[bool, str | None, list[str]]:
    """
    Valida un DTO de factura (alias para compatibilidad).
    
    Args:
        dto: DTO a validar
        
    Returns:
        Tupla (is_valid, error_code, missing_fields)
    """
    return validate_document_dto(dto, "invoice.ubl21")


def validate_credit_note_dto(dto: dict[str, Any]) -> tuple[bool, str | None, list[str]]:
    """
    Valida un DTO de nota crédito (alias para compatibilidad).
    
    Args:
        dto: DTO a validar
        
    Returns:
        Tupla (is_valid, error_code, missing_fields)
    """
    return validate_document_dto(dto, "creditnote.ubl21")
