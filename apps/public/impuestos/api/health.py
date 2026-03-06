"""
Endpoint de salud para OpenSearch.

Permite monitorear el estado del clúster y verificar la configuración del alias.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status


class SearchHealthView(APIView):
    """
    Vista de salud de OpenSearch.
    
    Endpoint: GET /api/public/v1/impuestos/search/health/
    Permisos: IsAdminUser (solo staff)
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """
        Obtiene el estado de salud del clúster OpenSearch y verifica el alias.
        
        Returns:
            Response con:
            - cluster: Estado de salud del clúster
            - alias: Nombre del alias actual
            - alias_points_to: Índices a los que apunta el alias
        """
        try:
            from apps.public.impuestos.search.client import get_search_client
            from apps.public.impuestos.search.schema import INDEX_ALIAS
            
            client = get_search_client()
            
            # Obtener salud del clúster
            health = client.cluster.health()
            
            # Verificar si el alias existe y a qué índices apunta
            alias_exists = client.indices.exists_alias(name=INDEX_ALIAS)
            target = None
            if alias_exists:
                alias_info = client.indices.get_alias(name=INDEX_ALIAS)
                target = list(alias_info.keys())
            
            return Response({
                "cluster": health,
                "alias": INDEX_ALIAS,
                "alias_points_to": target,
                "alias_exists": alias_exists,
            })
            
        except Exception as e:
            return Response(
                {
                    "error": str(e),
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
