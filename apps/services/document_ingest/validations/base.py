"""
Clase base abstracta para validadores de documentos (FASE 4.1).

WARNING: PRINCIPIOS:
- Cada app puede implementar su propio validador especializado
- Valida DTO JSON unificado producido por el pipeline
- Aplica reglas de negocio específicas del dominio
- Retorna resultados estructurados para logging y errores
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseValidator(ABC):
    """
    Clase base abstracta para validadores de documentos.
    
    Cada app de negocio puede implementar su propio validador que herede de esta clase
    y aplique reglas específicas del dominio.
    
    Ejemplo:
        class FacturaValidator(BaseValidator):
            def validate(self, dto: Dict[str, Any], document_type: str) -> Tuple[bool, Optional[str], List[str]]:
                # Validaciones específicas para facturas
                ...
    """
    
    @property
    @abstractmethod
    def document_type(self) -> str:
        """
        Tipo de documento que este validador procesa.
        
        Returns:
            str: Tipo canónico (ej: "invoice.ubl21", "creditnote.ubl21", "gasto", "inventario")
        """
        pass
    
    @property
    @abstractmethod
    def app_name(self) -> str:
        """
        Nombre de la app que usa este validador.
        
        Returns:
            str: Nombre de la app (ej: "facturas", "gastos", "inventario")
        """
        pass
    
    @abstractmethod
    def validate(self, dto: dict[str, Any], document_type: str) -> tuple[bool, str | None, list[str]]:
        """
        Valida un DTO de documento.
        
        Args:
            dto: DTO a validar (dict JSON unificado)
            document_type: Tipo de documento detectado (ej: "invoice.ubl21")
            
        Returns:
            Tupla (is_valid, error_code, missing_fields):
            - is_valid: True si el DTO es válido
            - error_code: Código de error si no es válido (ej: "missing_required_fields", "business_rule_violation")
            - missing_fields: Lista de campos faltantes o errores de validación
            
        Raises:
            ValueError: Si el DTO no es del tipo esperado por este validador
        """
        pass
    
    def validate_common_fields(self, dto: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Valida campos comunes a todos los documentos (helper).
        
        Args:
            dto: DTO a validar
            
        Returns:
            Tupla (is_valid, missing_fields):
            - is_valid: True si los campos comunes son válidos
            - missing_fields: Lista de campos faltantes
        """
        missing_fields = []
        
        # Campos obligatorios comunes (mínimo absoluto)
        required_fields = [
            "numero",
            "identificadores",
            "fecha_emision",
            "emisor",
            "receptor",
            "totales",
        ]
        
        for field in required_fields:
            if field not in dto or dto[field] is None:
                # Fallback para numero si no está en raíz pero está en identificadores
                if field == "numero" and dto.get("identificadores", {}).get("numero"):
                    continue
                missing_fields.append(field)
        
        # Validar estructura de identificadores
        if "identificadores" in dto and dto["identificadores"]:
            identificadores = dto["identificadores"]
            if not any([
                identificadores.get("cufe"),
                identificadores.get("uuid"),
                identificadores.get("cude"),
                identificadores.get("numero"),
                dto.get("numero"), # Fallback a raíz
            ]):
                missing_fields.append("identificadores.cufe|cude|uuid|numero")
        
        # Validar estructura de emisor
        if "emisor" in dto and dto["emisor"]:
            emisor = dto["emisor"]
            if not emisor.get("nit") or not str(emisor.get("nit")).strip():
                missing_fields.append("emisor.nit")
            # razon_social ya no es estrictamente obligatoria para validación (Zero Waste UX)
        
        # Validar estructura de receptor
        if "receptor" in dto and dto["receptor"]:
            receptor = dto["receptor"]
            if not receptor.get("nit") or not str(receptor.get("nit")).strip():
                missing_fields.append("receptor.nit")
            # razon_social ya no es estrictamente obligatoria para validación
        
        # Validar estructura de totales
        if "totales" in dto and dto["totales"]:
            totales = dto["totales"]
            if not totales.get("moneda"):
                missing_fields.append("totales.moneda")
            if totales.get("total") is None:
                missing_fields.append("totales.total")
        
        return len(missing_fields) == 0, missing_fields
