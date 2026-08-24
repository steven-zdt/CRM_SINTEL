"""
Servicios DIAN UBL 2.1 para Facturacion Electronica.

Modulos:
  cufe          -- Calculo del CUFE (SHA-384 campos fiscales), especifico de Factura
  ubl21_builder -- Construccion del XML Invoice UBL 2.1, especifico de Factura

# WARNING: NOMINA-03: XadesSignerService y AttachedDocumentService se
# movieron a apps.tenant.core.dian (genericos, sin acoplamiento a Invoice --
# ver docs/nomina/NOMINA_DIAN_AUDIT.md §2-3). Se re-exportan aqui por
# compatibilidad hacia atras -- codigo existente que hacia
# `from apps.tenant.facturas.services.dian import XadesSignerService` sigue
# funcionando sin cambios.
"""
from apps.tenant.facturas.services.dian.cufe import CufeService
from apps.tenant.facturas.services.dian.ubl21_builder import UBL21BuilderService
from apps.tenant.core.dian import XadesSignerService, AttachedDocumentService

__all__ = [
    "CufeService",
    "UBL21BuilderService",
    "XadesSignerService",
    "AttachedDocumentService",
]
