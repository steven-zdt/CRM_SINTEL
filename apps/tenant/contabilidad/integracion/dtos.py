"""
Data Transfer Objects for accounting transactions.

These frozen dataclasses define the contract between source apps (facturas, gastos, empleados, etc.)
and the centralized Contabilizador service. Using immutable DTOs ensures data integrity and
simplifies testing.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class TipoTransaccion(str, Enum):
    """Classification of economic events that generate journal entries."""
    VENTA_FACTURA = "VENTA_FACTURA"
    VENTA_NOTA_CREDITO = "VENTA_NOTA_CREDITO"
    VENTA_NOTA_DEBITO = "VENTA_NOTA_DEBITO"
    COMPRA_NOTA_CREDITO = "COMPRA_NOTA_CREDITO"
    COMPRA_GASTO = "COMPRA_GASTO"
    COMPRA_INVENTARIO = "COMPRA_INVENTARIO"
    SALIDA_INVENTARIO_VENTA = "SALIDA_INVENTARIO_VENTA"
    BAJA_INVENTARIO = "BAJA_INVENTARIO"
    AJUSTE_INVENTARIO = "AJUSTE_INVENTARIO"
    INVENTARIO_COSTO_VENTA = "INVENTARIO_COSTO_VENTA"
    NOMINA_LIQUIDACION = "NOMINA_LIQUIDACION"
    NOMINA_PROVISION = "NOMINA_PROVISION"
    NOMINA_PAGO = "NOMINA_PAGO"
    NOMINA_RETIRO = "NOMINA_RETIRO"
    PAGO_PROVEEDOR = "PAGO_PROVEEDOR"
    RECAUDO_CLIENTE = "RECAUDO_CLIENTE"
    ACTIVO_FIJO_COMPRA = "ACTIVO_FIJO_COMPRA"


class TipoTercero(str, Enum):
    """Classification of external parties involved in transactions."""
    CLIENTE = "CLIENTE"
    PROVEEDOR = "PROVEEDOR"
    EMPLEADO = "EMPLEADO"
    OTRO = "OTRO"


@dataclass(frozen=True)
class TerceroSnapshot:
    """
    Snapshot of third-party data at transaction moment (no FK).
    Prevents corruption if third-party master data changes.
    """
    tipo: TipoTercero
    id_origen: int                  # PK in origin app
    nit: str                        # Tax ID
    razon_social: str               # Legal name


@dataclass(frozen=True)
class ImpuestoLinea:
    """Tax applied to a transaction line."""
    tipo: str                       # IVA_GENERADO, IVA_DESCONTABLE, RETEFUENTE, RETEICA, RETEIVA, ARL, PENSION, SALUD, etc.
    base: Decimal                   # Taxable base
    porcentaje: Decimal             # Rate (19.0, 4.0, etc.)
    valor: Decimal                  # Calculated amount
    lado: str = 'HABER'             # 'DEBE' or 'HABER' - which side of journal entry


@dataclass(frozen=True)
class LineaTransaccion:
    """
    Economic line item of transaction (invoice line, payroll deduction, etc.).
    Multiple lines aggregate to form complete journal entry.
    """
    concepto: str                   # VENTA_PRODUCTO, AUXILIO_TRANSPORTE, PROVISION_CESANTIAS, etc.
    monto: Decimal                  # Principal amount (before taxes)
    lado: str = 'DEBE'              # 'DEBE' or 'HABER' - which side of journal entry
    impuestos: list['ImpuestoLinea'] = field(default_factory=list)
    centro_costo_id: Optional[int] = None  # Project/cost center for reporting
    cuenta_hint: Optional[str] = None      # Override default PUC account (advanced)


@dataclass(frozen=True)
class DocumentoOrigen:
    """Traceability to source document for idempotence and audit."""
    app_label: str                  # facturas, gastos, empleados
    modelo: str                     # Factura, DocumentoSoporte, Devengo
    id: int                         # PK in source app
    numero: str                     # Human-readable document number


@dataclass(frozen=True)
class TransaccionEconomica:
    """
    Unified DTO for all accounting transactions.

    Contract between source apps and Contabilizador. Immutable to ensure
    data integrity across service boundaries.

    Example:
        >>> factura_dto = TransaccionEconomica(
        ...     tipo=TipoTransaccion.VENTA_FACTURA,
        ...     fecha=date(2026, 5, 3),
        ...     descripcion="Factura venta INV-001",
        ...     tercero=TerceroSnapshot(...),
        ...     lineas=[...],
        ...     documento_origen=DocumentoOrigen(...)
        ... )
        >>> asiento = Contabilizador(empresa_id=1).contabilizar(factura_dto)
    """
    tipo: TipoTransaccion
    fecha: date
    descripcion: str
    tercero: TerceroSnapshot
    lineas: list[LineaTransaccion]
    documento_origen: DocumentoOrigen
    observaciones: str = ""
    periodo_contable_id: Optional[int] = None  # If None, inferred from fecha
    empresa_id: Optional[int] = None           # Injected by Contabilizador from context


# ============================================================================
# DTOs PARA FLUJO MANUAL (On-Demand UI)
# ============================================================================

@dataclass(frozen=True)
class LineaManual:
    """
    Linea de asiento con cuenta PUC explicita asignada por el usuario en la UI.
    No requiere resolucion de ReglaContable.
    """
    cuenta_codigo: str          # Codigo PUC nivel 6 (ej: 130505)
    debe: Decimal = Decimal('0')
    haber: Decimal = Decimal('0')
    descripcion: str = ''
    tercero_nit: str = ''
    tercero_razon_social: str = ''
    centro_costo_id: Optional[int] = None


@dataclass(frozen=True)
class ComprobanteManualDTO:
    """
    DTO para contabilizacion manual On-Demand desde la UI.

    El usuario selecciona el documento pendiente, asigna manualmente
    la cuenta PUC por cada linea y genera el asiento directamente.
    No pasa por ReglaContable ni Contabilizador automatico.
    """
    empresa_id: int
    fecha: date
    descripcion: str
    app_label: str              # 'facturas' | 'gastos'
    modelo: str                 # 'Factura' | 'DocumentoSoporte'
    documento_id: int           # PK en la app origen
    documento_numero: str       # Numero legible (FV-001, DS-001, etc.)
    tipo_comprobante_id: int    # ID del TipoComprobante (CC, RC, etc.)
    periodo_uuid: str           # UUID del PeriodoContable seleccionado
    lineas: list                # List[LineaManual]
