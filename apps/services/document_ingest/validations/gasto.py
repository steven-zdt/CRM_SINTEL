"""
Validador para gastos (FASE 4.1).

⚠️ PRINCIPIOS:
- Validaciones específicas para gastos
- Reglas de negocio del dominio de gastos
- Hereda de BaseValidator
"""
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
from .base import BaseValidator


class GastoValidator(BaseValidator):
    """
    Validador para gastos (FASE 4.1).
    
    Aplica validaciones específicas para gastos:
    - Campos obligatorios: totals, dates, parties
    - El gasto no puede ser 0 o negativo
    - Fechas válidas
    """
    
    @property
    def document_type(self) -> str:
        """Tipo de documento que este validador procesa."""
        return "gasto"
    
    @property
    def app_name(self) -> str:
        """Nombre de la app que usa este validador."""
        return "gastos"
    
    def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Valida un DTO de gasto (FASE 4.1).
        
        Reglas de validación:
        - Campos obligatorios: totals, dates, parties
        - El gasto no puede ser 0 o negativo
        - Fechas válidas
        
        Args:
            dto: DTO a validar
            document_type: Tipo de documento (debe ser "gasto")
            
        Returns:
            Tupla (is_valid, error_code, missing_fields)
        """
        if document_type != "gasto" and not document_type.startswith("gasto"):
            return False, "invalid_document_type", [f"Validador de gasto no puede validar tipo: {document_type}"]
        
        missing_fields = []
        errors = []
        
        # 1. Validar campos obligatorios: totals, dates, parties (FASE 4.1)
        required = ["totales", "fecha_emision", "emisor", "receptor"]
        for r in required:
            if r not in dto or dto[r] is None:
                missing_fields.append(r)
                errors.append(f"Campo obligatorio faltante: {r}")
        
        # 2. Validar que el gasto no sea 0 o negativo (FASE 4.1)
        if "totales" in dto and dto["totales"]:
            totales = dto["totales"]
            try:
                total = Decimal(str(totales.get("total", "0.00")))
                if total <= 0:
                    errors.append("El gasto no puede ser 0 o negativo")
            except (InvalidOperation, ValueError, TypeError):
                errors.append("Monto total inválido")
                missing_fields.append("totales.total")
        
        # 3. Validar fecha de emisión
        fecha_emision = dto.get("fecha_emision", "")
        if not fecha_emision or not self._is_valid_date(fecha_emision):
            missing_fields.append("fecha_emision")
            errors.append("Fecha de emisión inválida o no detectada")
        
        # 4. Validar estructura de parties (emisor y receptor)
        if "emisor" in dto and dto["emisor"]:
            emisor = dto["emisor"]
            if not emisor.get("nit") or not str(emisor.get("nit")).strip():
                missing_fields.append("emisor.nit")
            if not emisor.get("razon_social") or not str(emisor.get("razon_social")).strip():
                missing_fields.append("emisor.razon_social")
        
        if "receptor" in dto and dto["receptor"]:
            receptor = dto["receptor"]
            if not receptor.get("nit") or not str(receptor.get("nit")).strip():
                missing_fields.append("receptor.nit")
            if not receptor.get("razon_social") or not str(receptor.get("razon_social")).strip():
                missing_fields.append("receptor.razon_social")
        
        if missing_fields or errors:
            error_code = "validation_error" if errors else "missing_required_fields"
            return False, error_code, missing_fields + errors
        
        return True, None, []
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Valida si una fecha es válida."""
        if not date_str or not str(date_str).strip():
            return False
        
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
