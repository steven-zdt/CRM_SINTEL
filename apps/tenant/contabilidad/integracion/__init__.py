"""
apps.tenant.contabilidad.integracion

Service layer package for centralized accounting integration.
Provides unified interface for all apps to materialize economic transactions into journal entries.

Core exports:
- TransaccionEconomica: DTO for all accounting transactions
- TipoTransaccion, TipoTercero: Enums for transaction classification
- Contabilizador: Entry point for materialization
- ContabilidadError and subclasses: Exception hierarchy
"""
