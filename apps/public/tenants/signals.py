"""
Signals de tenants (desactivadas por diseño).

WARNING: CERO SIGNALS:
- La creación de dominios y demás efectos colaterales ya NO se hace vía señales.
- Toda la lógica de onboarding (Client, Domain, Membership, Profile, migraciones)
  vive en servicios explícitos (Service Layer), por ejemplo en:
  - apps.services.onboarding.empresa_service.onboard_tenant

Este módulo se mantiene solo como marcador histórico. No registra ningún receiver.
"""
