"""
Validador para notas crédito (FASE 4.2).

⚠️ PRINCIPIOS:
- Validaciones específicas para notas crédito
- Reglas de negocio del dominio de facturas (notas crédito)
- Hereda de BaseValidator
"""
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
from .base import BaseValidator


class NotaCreditoValidator(BaseValidator):
    """
    Validador para notas crédito.
    
    Aplica validaciones específicas para notas crédito:
    - CUDE obligatorio
    - Referencias obligatorias a factura
    - Totales coherentes
    - Fechas válidas
    - Número de documento detectado
    """
    
    @property
    def document_type(self) -> str:
        """Tipo de documento que este validador procesa."""
        return "creditnote.ubl21"
    
    @property
    def app_name(self) -> str:
        """Nombre de la app que usa este validador."""
        return "facturas"
    
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Valida un DTO de nota crédito.
        
        Reglas:
        - CUDE obligatorio
        - Referencias obligatorias a factura
        - Totales coherentes
        - Fechas válidas
        - Número de documento detectado
        
        Args:
            dto: DTO a validar
            document_type: Tipo de documento (debe ser "creditnote.ubl21")
            
        Returns:
            Tupla (is_valid, error_code, missing_fields)
        """
        if not document_type.startswith("creditnote"):
            return False, "invalid_document_type", [f"Validador de nota crédito no puede validar tipo: {document_type}"]
        
        missing_fields = []
        errors = []
        
        # 1. Validar campos comunes
        is_valid_common, missing_common = self.validate_common_fields(dto)
        if not is_valid_common:
            missing_fields.extend(missing_common)
        
        # 2. Validar número de documento detectado
        if not dto.get("numero") or not str(dto.get("numero")).strip():
            missing_fields.append("numero")
            errors.append("Número de documento no detectado")
        
        # 3. Validar CUDE obligatorio
        identificadores = dto.get("identificadores", {})
        cude = identificadores.get("cude") or identificadores.get("uuid") or identificadores.get("cufe")
        
        if not cude or not str(cude).strip():
            missing_fields.append("identificadores.cude|cufe|uuid")
            errors.append("CUDE obligatorio no encontrado")
        
        # 4. Validar fechas válidas
        fecha_emision = dto.get("fecha_emision", "")
        if not fecha_emision or not self._is_valid_date(fecha_emision):
            missing_fields.append("fecha_emision")
            errors.append("Fecha de emisión inválida o no detectada")
        
        # 5. Validar totales coherentes
        totales = dto.get("totales", {})
        try:
            subtotal = Decimal(str(totales.get("subtotal", "0.00")))
            impuestos = Decimal(str(totales.get("impuestos", "0.00")))
            total = Decimal(str(totales.get("total", "0.00")))
            
            # ⚠️ CORRECCIÓN: En UBL 2.1, el total (PayableAmount) puede incluir descuentos/cargos
            # Por lo tanto, validamos que subtotal + impuestos ≤ total (con tolerancia)
            # O que subtotal + impuestos ≈ total si no hay descuentos/cargos
            tax_inclusive = subtotal + impuestos
            
            # Tolerancia aumentada a 0.10 para manejar redondeos y descuentos menores
            # Si total < tax_inclusive (con tolerancia), hay un problema
            if total < (tax_inclusive - Decimal("0.10")):
                errors.append(f"Totales incoherentes: total ({total}) es menor que subtotal + impuestos ({tax_inclusive})")
            # Si total > tax_inclusive + 0.10, puede haber descuentos/cargos (aceptable)
            # No validamos el caso contrario porque PayableAmount puede incluir descuentos
        except (InvalidOperation, ValueError, TypeError) as e:
            errors.append(f"Totales con valores numéricos inválidos: {str(e)}")
            missing_fields.append("totales.subtotal|impuestos|total")
        
        # 6. Validar referencias obligatorias a factura
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
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Valida si una fecha es válida (ISO 8601 o formatos comunes)."""
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
            pass
        except (ValueError, TypeError):
            pass
        
        return False
