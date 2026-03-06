"""
ViewSet base para modelos tenant con lookup por UUID.

⚠️ v2.37: Unificación de convenciones API-First
- lookup_field="uuid" para todos los ViewSets públicos
- Evita exposición de PK interno
- Consistente con arquitectura multitenant
"""
from rest_framework import viewsets


class BaseTenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet base para modelos tenant con lookup por UUID.
    
    ⚠️ IMPORTANTE:
    - lookup_field="uuid" garantiza que las URLs usen UUID en lugar de PK
    - lookup_url_kwarg="uuid" permite usar "uuid" en lugar de "pk" en URLs
    - Todos los ViewSets de tenant deben heredar de esta clase
    """
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
