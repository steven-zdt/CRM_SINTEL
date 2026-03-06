"""
DTO (Data Transfer Object) unificado para documentos (FASE 3).

⚠️ PRINCIPIOS:
- Contrato estable: Formato JSON único para todos los formatos (XML, PDF, XLS, CSV, TXT)
- Agnóstico del formato: El DTO no expone detalles del formato origen
- Compatible con DRF: Estructura JSON serializable
- Soporta múltiples tipos: invoice, creditnote, gasto, inventario, recibo, orden_compra

Tipos de documentos soportados:
- invoice: Factura electrónica
- creditnote: Nota crédito
- gasto: Documento de gasto
- inventario: Documento de inventario
- recibo: Recibo de pago
- orden_compra: Orden de compra
"""
from typing import Dict, Any, Optional, Literal
from decimal import Decimal
from dataclasses import dataclass, asdict, field
from datetime import datetime

# Tipos de documentos soportados (FASE 3)
DocumentTypeBase = Literal[
    "invoice",
    "creditnote",
    "gasto",
    "inventario",
    "recibo",
    "orden_compra",
]


@dataclass
class IdentificadoresDTO:
    """Identificadores legales del documento (CUFE, UUID, etc.)."""
    cufe: Optional[str] = None
    uuid: Optional[str] = None
    numero: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PartyDTO:
    """Datos de una parte (emisor o receptor)."""
    nit: Optional[str] = None
    razon_social: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TotalesDTO:
    """Totales monetarios del documento."""
    moneda: str = "COP"
    subtotal: Decimal = Decimal('0.00')
    impuestos: Decimal = Decimal('0.00')
    total: Decimal = Decimal('0.00')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {
            "moneda": self.moneda,
            "subtotal": str(self.subtotal),
            "impuestos": str(self.impuestos),
            "total": str(self.total),
        }


@dataclass
class ReferenciaDTO:
    """Referencia a documento relacionado (para Notas Crédito)."""
    numero: Optional[str] = None
    cufe: Optional[str] = None
    tipo: Optional[str] = None  # "invoice", "creditnote", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict JSON-serializable."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DocumentoDTO:
    """
    DTO unificado para documentos (FASE 3).
    
    Soporta múltiples tipos de documentos:
    - invoice: Factura electrónica
    - creditnote: Nota crédito
    - gasto: Documento de gasto
    - inventario: Documento de inventario
    - recibo: Recibo de pago
    - orden_compra: Orden de compra
    
    ⚠️ CONTRATO ESTABLE: Esta estructura es la única representación de intercambio
    entre el pipeline y las capas de dominio para materializar documentos.
    
    ⚠️ FASE 3: El campo "type" permite que el router de validaciones dirija
    correctamente según el tipo de documento, sin depender del formato completo.
    """
    # Campos requeridos (sin default)
    document_type: str  # "invoice.ubl21", "creditnote.ubl21", "gasto", etc.
    numero: str
    identificadores: IdentificadoresDTO
    fecha_emision: str  # ISO 8601 format
    emisor: PartyDTO
    receptor: PartyDTO
    totales: TotalesDTO
    
    # Campos opcionales (con default)
    type: Optional[str] = None  # Tipo base para router: "invoice", "creditnote", "gasto", etc. (FASE 3)
    
    # Referencia (solo para Notas Crédito, OrdenCompra)
    referencia: Optional[ReferenciaDTO] = None
    
    # Motivo (solo para Notas Crédito)
    motivo: Optional[str] = None
    
    # Campos específicos para Gasto (FASE 3)
    categoria: Optional[str] = None
    centro_costo: Optional[str] = None
    
    # Campos específicos para Inventario (FASE 3)
    items: Optional[list] = None
    almacen: Optional[str] = None
    
    # Campos específicos para Recibo (FASE 3)
    metodo_pago: Optional[str] = None
    banco: Optional[str] = None
    
    # Campos específicos para OrdenCompra (FASE 3)
    proveedor: Optional[PartyDTO] = None
    fecha_entrega: Optional[str] = None
    condiciones_pago: Optional[str] = None
    
    # Metadata del parsing
    formato_origen: Optional[str] = None  # "xml", "pdf", "xlsx", etc.
    parser_usado: Optional[str] = None  # Clase del parser que procesó el documento
    sha256: Optional[str] = None  # Hash SHA-256 del documento original
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a dict JSON-serializable (FASE 3).
        
        Returns:
            Dict compatible con DRF Serializer
        """
        result = {
            "document_type": self.document_type,
            "numero": self.numero,
            "identificadores": self.identificadores.to_dict(),
            "fecha_emision": self.fecha_emision,
            "emisor": self.emisor.to_dict(),
            "receptor": self.receptor.to_dict(),
            "totales": self.totales.to_dict(),
        }
        
        # Incluir type si está definido (FASE 3)
        if self.type:
            result["type"] = self.type
        else:
            # Auto-generar type desde document_type si no está definido
            type_base = self.document_type.split('.')[0] if '.' in self.document_type else self.document_type
            result["type"] = type_base
        
        # Campos opcionales
        if self.referencia:
            result["referencia"] = self.referencia.to_dict()
        
        if self.motivo:
            result["motivo"] = self.motivo
        
        # Campos específicos por tipo (FASE 3)
        if self.categoria:
            result["categoria"] = self.categoria
        if self.centro_costo:
            result["centro_costo"] = self.centro_costo
        if self.items:
            result["items"] = self.items
        if self.almacen:
            result["almacen"] = self.almacen
        if self.metodo_pago:
            result["metodo_pago"] = self.metodo_pago
        if self.banco:
            result["banco"] = self.banco
        if self.proveedor:
            result["proveedor"] = self.proveedor.to_dict() if hasattr(self.proveedor, 'to_dict') else self.proveedor
        if self.fecha_entrega:
            result["fecha_entrega"] = self.fecha_entrega
        if self.condiciones_pago:
            result["condiciones_pago"] = self.condiciones_pago
        
        # Metadata
        if self.formato_origen:
            result["formato_origen"] = self.formato_origen
        if self.parser_usado:
            result["parser_usado"] = self.parser_usado
        if self.sha256:
            result["sha256"] = self.sha256
        
        return result
