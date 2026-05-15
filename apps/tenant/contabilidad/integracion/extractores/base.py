from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import date
from dataclasses import dataclass, field

from ..dtos import TransaccionEconomica
from ..contabilizador import Contabilizador
from ..excepciones import AsientoYaExisteError


@dataclass
class CuentaAsignada:
    """Cuenta contable ya definida en el documento de origen (antes de contabilizar)."""
    concepto: str          # 'cuenta_gasto', 'cuenta_pasivo_proveedor', 'cuenta_ingreso', etc.
    uuid: str              # UUID original del campo en el modelo
    codigo_puc: str        # Código PUC resuelto (ej: '513505')
    nombre: str            # Nombre de la cuenta (ej: 'Gastos de personal')
    monto: Decimal         # Monto que se espera registrar en esta cuenta


@dataclass
class MovimientoResumen:
    """Resumen de un movimiento del asiento ya generado."""
    cuenta_codigo: str
    cuenta_nombre: str
    debe: Decimal
    haber: Decimal


@dataclass
class DocumentoEnriquecido:
    """DTO que representa un documento en cualquier estado del ciclo contable."""
    # Identificación
    app_label: str                        # 'facturas', 'gastos', 'empleados', 'inventario'
    app_display: str                      # 'Ventas', 'Compras', 'Nómina', 'Inventario'
    modelo: str                           # 'Factura', 'DocumentoSoporte', etc.
    documento_id: int                     # PK interna
    numero: str                           # Número legible del documento
    fecha: date

    # Tipo de comprobante (normativa colombiana)
    tipo_comprobante: str                 # 'CI', 'CE', 'CN', 'CD', 'NC'
    tipo_comprobante_display: str         # 'Comprobante de Ingreso', etc.

    # Tercero (snapshot sin FK — Código de Comercio Art. 59)
    tercero_nit: str
    tercero_nombre: str

    # Valores financieros
    subtotal: Decimal
    impuestos: Decimal
    total: Decimal

    # Cuentas ya asignadas en el documento origen (antes de contabilizar)
    cuentas_asignadas: list[CuentaAsignada] = field(default_factory=list)

    # Estado contable
    estado_contable: str = 'PENDIENTE'   # 'PENDIENTE' | 'CONTABILIZADO' | 'REVERTIDO'
    asiento_uuid: Optional[str] = None
    asiento_numero: Optional[str] = None

    # Solo si ya contabilizado
    movimientos: list[MovimientoResumen] = field(default_factory=list)
    cuadra: bool = False

    def to_dict(self) -> dict:
        return {
            'app_label': self.app_label,
            'app_display': self.app_display,
            'modelo': self.modelo,
            'documento_id': self.documento_id,
            'numero': self.numero,
            'fecha': str(self.fecha),
            'tipo_comprobante': self.tipo_comprobante,
            'tipo_comprobante_display': self.tipo_comprobante_display,
            'tercero_nit': self.tercero_nit,
            'tercero_nombre': self.tercero_nombre,
            'subtotal': str(self.subtotal),
            'impuestos': str(self.impuestos),
            'total': str(self.total),
            'cuentas_asignadas': [
                {'concepto': c.concepto, 'uuid': c.uuid, 'codigo_puc': c.codigo_puc,
                 'nombre': c.nombre, 'monto': str(c.monto)}
                for c in self.cuentas_asignadas
            ],
            'estado_contable': self.estado_contable,
            'asiento_uuid': self.asiento_uuid,
            'asiento_numero': self.asiento_numero,
            'movimientos': [
                {'cuenta_codigo': m.cuenta_codigo, 'cuenta_nombre': m.cuenta_nombre,
                 'debe': str(m.debe), 'haber': str(m.haber)}
                for m in self.movimientos
            ],
            'cuadra': self.cuadra,
        }


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

    @abstractmethod
    def get_documentos_enriquecidos(self, empresa_id: int, fecha_inicio: date, fecha_fin: date) -> List[DocumentoEnriquecido]:
        """
        Retorna todos los documentos del período (pendientes + contabilizados)
        con sus cuentas PUC resueltas y estado contable.
        Según normativa colombiana: base para el Libro Diario.
        """
        raise NotImplementedError

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
