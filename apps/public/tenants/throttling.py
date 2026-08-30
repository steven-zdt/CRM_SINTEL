"""
Throttling para la API pública de tenants.

Referencia: https://www.django-rest-framework.org/api-guide/throttling/
"""

from rest_framework.throttling import ScopedRateThrottle


class OnboardingCreateThrottle(ScopedRateThrottle):
    """
    Throttle dedicado para la creación de tenants via self-service (Vía B).

    REM ONBOARDING-07 (documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md
    Hallazgo #7): antes de esto, `CreateTenantOnboardingAPIView` solo heredaba
    el throttle generico `AnonRateThrottle` (500/dia por IP) -- el mismo limite
    que rige, por ejemplo, consultas de catalogo DIAN. Cada request exitoso a
    este endpoint dispara un `CREATE SCHEMA` + migracion completa de
    TENANT_APPS -- una operacion cara en recursos de BD que merece un limite
    propio y mas estricto, mismo patron ya usado por `IngestaScopedThrottle`.

    Scope: 'tenant_onboarding_create'
    Tasa configurada en REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
    """

    scope = "tenant_onboarding_create"
