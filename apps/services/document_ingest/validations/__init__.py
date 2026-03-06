"""
Sistema de validadores por app (validation plugins) (FASE 4.1).

⚠️ PRINCIPIOS:
- SSoT: El pipeline produce solo DTO JSON
- El dominio aplica validaciones específicas
- Cada app puede tener su propio validador especializado
- Sin duplicar parsers
- Respetando Domain-Driven Design

Estructura:
- base.py: Clase base abstracta para validadores
- router.py: Router para seleccionar validador apropiado
- factura.py: Validador para facturas
- nota_credito.py: Validador para notas crédito
- gasto.py: Validador para gastos
- inventario.py: Validador para inventario
"""
from .base import BaseValidator
from .router import (
    get_validator,
    register_validator,
    get_validator_by_document_type,
    list_validators,
    run_validations,
    VALIDATORS,
)

# Auto-registrar validadores al importar
def _register_default_validators():
    """Registra los validadores por defecto."""
    from .factura import FacturaValidator
    from .nota_credito import NotaCreditoValidator
    from .gasto import GastoValidator
    from .inventario import InventarioValidator
    from .cotizaciones import CotizacionesValidator
    
    # ⚠️ v2.40: IMPORTANTE - Registrar CotizacionesValidator ANTES de InventarioValidator
    # para que tenga prioridad en el override del registro
    register_validator(CotizacionesValidator())
    
    # Registrar validadores de facturas
    register_validator(FacturaValidator())
    register_validator(NotaCreditoValidator())
    
    # Registrar validadores de otras apps (FASE 4)
    register_validator(GastoValidator())
    register_validator(InventarioValidator())  # Este se registrará pero no overrideará cotizaciones

# Registrar validadores por defecto
_register_default_validators()

# Exportar validadores
from .factura import FacturaValidator
from .nota_credito import NotaCreditoValidator
from .gasto import GastoValidator
from .inventario import InventarioValidator
from .cotizaciones import CotizacionesValidator

__all__ = [
    'BaseValidator',
    'get_validator',
    'register_validator',
    'get_validator_by_document_type',
    'list_validators',
    'run_validations',
    'VALIDATORS',
    'FacturaValidator',
    'NotaCreditoValidator',
    'GastoValidator',
    'InventarioValidator',
    'CotizacionesValidator',
]
