"""
Throttling para la API de Ingesta.

Referencia: https://www.django-rest-framework.org/api-guide/throttling/
"""

from rest_framework.throttling import ScopedRateThrottle


class IngestaScopedThrottle(ScopedRateThrottle):
    """
    Throttle con scope específico para ingesta de documentos.

    Scope: 'impuestos_ingesta'
    Tasa configurada en REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
    """

    scope = "impuestos_ingesta"
