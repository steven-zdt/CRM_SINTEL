"""
ViewSet unificado para Landing API (v2.30).

⚠️ POLÍTICA v2.30:
- Único ViewSet con acciones: /info/ y /auth/activate/
- Endpoints públicos (AllowAny) para información de tenant y activación
- Arquitectura API-First: solo JSON, no HTML
- Auth (login, logout, password-reset) está centralizado en Core API: /api/v1/core/auth/*
"""
import logging
from django.contrib.auth import login, get_user_model
from django.conf import settings
from django_tenants.utils import schema_context
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenant.landing.api.serializers import (
    TenantPublicInfoSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class LandingViewSet(viewsets.ViewSet):
    """
    ViewSet unificado para Landing API (v2.30).
    
    ⚠️ IMPORTANTE: Este ViewSet NO tiene queryset porque no opera sobre
    un modelo específico, sino sobre request.tenant (inyectado por middleware).
    
    Acciones:
    - GET /api/v1/landing/info/ → Información pública del tenant
    """
    permission_classes = [permissions.AllowAny]  # ✅ Público: información de landing
    
    @action(detail=False, methods=['get'], url_path='info', url_name='info')
    def info(self, request):
        """
        Retorna información pública del tenant actual.
        
        Endpoint: GET /api/v1/landing/info/
        
        Retorna:
        - nombre: Nombre del tenant
        - schema_name: Nombre del esquema
        - domain: Dominio principal
        - branding: Información de branding desde Empresa
        """
        try:
            # ⚠️ POLÍTICA: Usar servicio de dominio
            service_result = get_public_info(request)
            tenant = service_result['tenant']
            
            # Serializar con branding desde BD
            serializer = TenantPublicInfoSerializer(tenant, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "LandingViewSet.info: error inesperado: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar la información del tenant."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
