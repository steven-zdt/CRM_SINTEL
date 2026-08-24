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
"""
from apps.tenant.core.dian.xades_signer import XadesSignerService
from apps.tenant.core.dian.attached_document import AttachedDocumentService

__all__ = [
    "XadesSignerService",
    "AttachedDocumentService",
]
