"""
Infraestructura DIAN generica, compartida entre apps de dominio que emiten
documentos electronicos DIAN (facturas, empleados/nomina).

# WARNING: POLITICA (NOMINA-03, ver docs/nomina/NOMINA_DIAN_AUDIT.md):
- Solo lo que es genuinamente generico por documento electronico (firma
  XAdES sobre bytes, wrapper AttachedDocument) vive aqui.
- Lo especifico de cada tipo de documento (formula CUFE vs CUNE, builder
  XML Invoice vs NominaIndividual) permanece en la app de dominio dueña.
- Ninguna app de dominio (facturas, empleados, ventas) debe ser importada
  desde aqui -- este paquete es terreno neutral, solo hacia abajo.

Modulos:
  xades_signer      -- Firma XAdES-EPES (ds:Signature) sobre bytes XML
  attached_document -- Contenedor AttachedDocument DIAN + ApplicationResponse
  transport         -- Puerto de transporte (FISCAL-02) + NullTransportAdapter
  adapters          -- DIANAdapter (FISCAL-05) -- implementacion SOAP real,
                        **NO VERIFICADA** contra el ambiente DIAN real. Ver
                        advertencia completa en adapters.py y
                        docs/fiscal/FISCAL_05_DIAN_ADAPTER.md antes de usar.
"""
from apps.tenant.core.dian.xades_signer import XadesSignerService
from apps.tenant.core.dian.attached_document import AttachedDocumentService
from apps.tenant.core.dian.transport import (
    ElectronicDocument,
    ElectronicDocumentTransportPort,
    NullTransportAdapter,
    TransmissionResult,
)
from apps.tenant.core.dian.adapters import DIANAdapter

__all__ = [
    "XadesSignerService",
    "AttachedDocumentService",
    "ElectronicDocument",
    "ElectronicDocumentTransportPort",
    "NullTransportAdapter",
    "TransmissionResult",
    "DIANAdapter",
]
