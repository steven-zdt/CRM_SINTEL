# apps/tenant/contabilidad/integracion/extractores/base.py
from abc import ABC, abstractmethod
from typing import List, Dict

from ..dtos import TransaccionEconomica
from ..contabilizador import Contabilizador
from ..excepciones import AsientoYaExisteError


class AbstractExtractor(ABC):
    """
    Abstract base class for all accounting extractors.
    
    Extractors implement the 'Pull Model' by reading data from source apps 
    (facturas, gastos, etc.) and converting them into TransaccionEconomica DTOs.
    """

    def __init__(self, empresa_id: int):
        """
        Initialize the extractor for a specific tenant.
        
        Args:
            empresa_id: ID of the tenant empresa.
        """
        self.empresa_id = empresa_id
        self.contabilizador = Contabilizador(empresa_id)

    @abstractmethod
    def extraer_pendientes(self) -> List[TransaccionEconomica]:
        """
        Identify and extract transactions that have not been journalized yet.
        
        Returns:
            List of TransaccionEconomica DTOs ready for processing.
        """
        pass

    def contabilizar_pendientes(self) -> Dict:
        """
        Process all pending transactions and materialize them as journal entries.
        
        Returns:
            Dictionary with execution summary (count, errors, etc.)
        """
        resultados = {
            'contabilizados': 0,
            'errores': [],
            'omitidos': 0,
            'total': 0
        }
        
        pendientes = self.extraer_pendientes()
        resultados['total'] = len(pendientes)
        
        for dto in pendientes:
            try:
                self.contabilizador.contabilizar(dto)
                resultados['contabilizados'] += 1
            except AsientoYaExisteError:
                resultados['omitidos'] += 1
            except Exception as e:
                resultados['errores'].append({
                    'documento': dto.documento_origen.numero,
                    'error': str(e),
                    'ref': f"{dto.documento_origen.app_label}.{dto.documento_origen.modelo}[{dto.documento_origen.id}]"
                })
        
        return resultados
