"""
Healthcheck API para tenant.

# WARNING: FASE 5: Endpoint de salud básico (DB y schema actual).
"""
import logging

from django_tenants.utils import get_tenant, schema_context
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

health_log = logging.getLogger("core.health")


class HealthView(APIView):
    """
    Health básico del tenant: DB y schema actual.
    
    # WARNING: FASE 5: Verifica que el tenant actual tenga acceso a su esquema.
    """
    authentication_classes = []  # Público (o añade permisos si lo prefieres)
    permission_classes = []
    
    def get(self, request, *args, **kwargs):
        """
        Health básico del tenant: DB y schema actual.
        
        Returns:
            - 200 OK: {"ok": True, "schema": "tenant_name"}
            - 500 Internal Server Error: {"ok": False, "error": "..."}
        """
        try:
            tenant = get_tenant()
            schema = getattr(tenant, "schema_name", "public")
            
            # micro-check DB (consulta trivial dentro del schema)
            with schema_context(schema):
                _ = 1 + 1  # Operación trivial para verificar conexión
            
            payload = {"ok": True, "schema": schema}
            health_log.info("health_ok schema=%s", schema)
            return Response(payload, status=status.HTTP_200_OK)
            
        except Exception as ex:
            health_log.exception("health_fail: %s", ex)
            return Response(
                {"ok": False, "error": str(ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
