"""
ViewSet unificado para Landing API (v2.30).

⚠️ POLÍTICA v2.30:
- Único ViewSet con acciones: /info/ y /auth/activate/
- Endpoints públicos (AllowAny) para información de tenant y activación
- Arquitectura API-First: solo JSON, no HTML
- Auth (login, logout, password-reset) está centralizado en Core API: /api/v1/core/auth/*
"""
from django.contrib.auth import login, get_user_model
from django.conf import settings
from django_tenants.utils import schema_context
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.public.tenants.models import Domain, TenantMembership
from apps.public.tenants.services.invitations import verify_invitation_token

from apps.tenant.landing.api.serializers import (
    TenantPublicInfoSerializer,
    OwnerActivationSerializer,
)

User = get_user_model()


class LandingViewSet(viewsets.ViewSet):
    """
    ViewSet unificado para Landing API (v2.30).
    
    ⚠️ IMPORTANTE: Este ViewSet NO tiene queryset porque no opera sobre
    un modelo específico, sino sobre request.tenant (inyectado por middleware).
    
    Acciones:
    - GET /api/v1/landing/info/ → Información pública del tenant
    - GET|POST /api/v1/landing/auth/activate/ → Activación de owner
    """
    permission_classes = [permissions.AllowAny]  # ✅ Público: información de landing y activación
    
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
    
    @action(detail=False, methods=['get', 'post'], url_path='auth/activate', url_name='activate')
    def activate(self, request):
        """
        Endpoint de activación de owner (API-First).
        
        GET /api/v1/landing/auth/activate/?token=...:
        - Valida token
        - Retorna información del usuario y tenant
        - Retorna 409 CONFLICT si el usuario ya tiene contraseña usable
        
        POST /api/v1/landing/auth/activate/?token=...:
        - Valida token
        - Valida membresía activa
        - Establece/actualiza contraseña
        - Loguea usuario
        - Retorna URL absoluta de redirección al dashboard
        """
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {"detail": "Token de activación no proporcionado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # GET: Verificar token y retornar información
        if request.method == 'GET':
            try:
                # ⚠️ POLÍTICA: Usar servicio de dominio
                result = verify_activation_token(request, token)
                return Response({
                    "user": result['user'],
                    "tenant": result['tenant'],
                    "token_valid": result['token_valid'],
                }, status=status.HTTP_200_OK)
            except InvalidTokenError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except UserNotFoundError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_404_NOT_FOUND
                )
            except TenantMismatchError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except AlreadyActivatedError as e:
                return Response(
                    {
                        "detail": str(e),
                        "redirect_url": "/static/tenant/landing/login.html",
                        "login_api_url": "/api/v1/core/auth/login/",
                    },
                    status=status.HTTP_409_CONFLICT
                )
            except Exception as e:
                logger.error(
                    "LandingViewSet.activate (GET): error inesperado: error=%s",
                    str(e),
                    exc_info=True
                )
                return Response(
                    {"detail": "Error interno al validar el token de activación."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # POST: Procesar activación
        password1 = request.data.get('password1')
        password2 = request.data.get('password2')
        
        if not password1 or not password2:
            return Response(
                {"detail": "Ambas contraseñas son requeridas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # ⚠️ POLÍTICA: Usar servicio de dominio
            result = process_activation(request, token, password1, password2)
            return Response(result, status=status.HTTP_200_OK)
        except InvalidTokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except TenantMismatchError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except AlreadyActivatedError as e:
            return Response(
                {
                    "detail": str(e),
                    "redirect_url": "/static/tenant/landing/login.html",
                    "login_api_url": "/api/v1/core/auth/login/",
                },
                status=status.HTTP_409_CONFLICT
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "LandingViewSet.activate (POST): error inesperado: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar la activación."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
