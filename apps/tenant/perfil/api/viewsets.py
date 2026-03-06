"""
ViewSets para la app de perfil.

⚠️ v2.30: API-First + SSoT - Solo endpoints REST (JSON-only)
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id
- El endpoint `/me/` siempre trabaja sobre `request.user`
- Service Layer: Toda la lógica de negocio está en perfil_service.py
- SessionAuthentication: Habilitado para consumo desde workspace (cookies de sesión)

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""
import json
import logging
from django.db import connection
from django.db.utils import ProgrammingError, OperationalError
from django.core.exceptions import ImproperlyConfigured
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.perfil.api.serializers import TenantProfileSerializer, TenantProfileMeUpdateSerializer
from apps.services.perfil.perfil_service import (
    obtener_o_crear_perfil,
    actualizar_perfil,
    actualizar_configuracion_ui,
    actualizar_avatar
)
from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.api.authentication import UnsafeSessionAuthentication
from rest_framework.permissions import BasePermission

log = logging.getLogger("perfil.api")


class IsOwnerOrReadOnly(BasePermission):
    """
    Permiso que permite al usuario autenticado leer/editar su propio perfil.
    
    ⚠️ IMPORTANTE: Para endpoints '/me/', la comprobación es trivial:
    request.user == perfil.user (siempre es True porque el endpoint siempre
    retorna/actualiza el perfil del usuario actual).
    
    Este permiso garantiza que solo el dueño puede editar su perfil,
    no solo tener membresía en el tenant.
    """
    def has_permission(self, request, view):
        """Verifica que el usuario esté autenticado."""
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica que el usuario sea dueño del perfil.
        
        Para endpoints '/me/', este método no se llama porque no hay objeto
        en la URL, pero se mantiene para consistencia.
        """
        # El usuario solo puede editar su propio perfil
        return obj.user == request.user


class PerfilViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Perfil del Colaborador.
    
    ⚠️ IMPORTANTE:
    - El endpoint `/me/` siempre trabaja sobre `request.user`
    - No requiere ID en la URL
    - Usa `perfil_service.obtener_o_crear_perfil` para garantizar que el objeto exista
    - Service Layer: La lógica de negocio está en perfil_service.py
    
    ⚠️ v2.30: SessionAuthentication habilitado para compatibilidad con workspace (cookies de sesión)
    ⚠️ DESARROLLO: En DEBUG=True, usa UnsafeSessionAuthentication (CSRF relajado) para evitar 403
    ⚠️ PRODUCCIÓN: En DEBUG=False, usa SessionAuthentication estricto (CSRF obligatorio)
    
    ⚠️ OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated, IsTenantMember, IsOwnerOrReadOnly]  # ✅ SEGURIDAD: Cross-Tenant Isolation + autenticación + dueño puede editar
    
    def get_authenticators(self):
        """
        Retorna las instancias de autenticación según el entorno.
        
        ⚠️ DESARROLLO: En DEBUG=True, usa UnsafeSessionAuthentication (CSRF relajado)
        ⚠️ PRODUCCIÓN: En DEBUG=False, usa SessionAuthentication estricto (CSRF obligatorio)
        
        Returns:
            List[BaseAuthentication]: Lista de instancias de autenticación
        """
        if settings.DEBUG:
            return [UnsafeSessionAuthentication()]  # ✅ Desarrollo: permite PATCH sin CSRF válido
        else:
            return [SessionAuthentication()]  # ✅ Producción: CSRF estricto
    
    def get_serializer_context(self):
        """
        Asegura que el request esté disponible en el contexto del serializer.
        Necesario para SerializerMethodField que construyen URLs absolutas (avatar_url).
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """
        QuerySet optimizado - NO usa .all() sin limitar columnas.
        """
        # Campos necesarios para perfil
        perfil_fields = (
            'id', 'user_id', 'cargo', 'departamento', 'telefono_corporativo',
            'avatar', 'configuracion', 'created_at', 'updated_at'
        )
        
        if self.action in ("list", "retrieve", "me"):
            qs = TenantProfile.objects.only(*perfil_fields).select_related('user')
        else:
            # Para create/update/delete necesitamos todos los campos
            qs = TenantProfile.objects.all()
        
        return qs
    
    def _safe_get_me_profile_response(self, request: Request, method: str = 'GET') -> Response:
        """
        Obtiene o actualiza el perfil del usuario de forma segura, manejando errores de tabla faltante.
        
        ⚠️ v2.30: Robustez multi-tenant - Maneja ProgrammingError/OperationalError
        cuando la tabla no existe (esquema sin migrar).
        
        Returns:
            Response: 200 OK con perfil, 503 si tabla no existe, 400/500 en otros errores
        """
        try:
            # Intentar obtener o crear el perfil usando el servicio
            perfil = obtener_o_crear_perfil(request.user)
            
            if method == 'GET':
                # GET: Retornar el perfil
                serializer = self.get_serializer(perfil, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            elif method == 'PATCH':
                # PATCH: Actualizar el perfil usando el servicio
                # ⚠️ v2.30: Si se envía avatar en multipart, actualizarlo primero
                if 'avatar' in request.FILES:
                    archivo_avatar = request.FILES['avatar']
                    try:
                        perfil = actualizar_avatar(request.user, archivo_avatar)
                    except ValueError as e:
                        return Response(
                            {'error': str(e)},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Preparar datos para validación
                # ⚠️ v2.30: En multipart, configuracion puede venir como string JSON
                data_para_validar = request.data.copy()
                if 'configuracion' in data_para_validar and isinstance(data_para_validar['configuracion'], str):
                    try:
                        data_para_validar['configuracion'] = json.loads(data_para_validar['configuracion'])
                    except (json.JSONDecodeError, TypeError):
                        data_para_validar['configuracion'] = {}
                
                # Validar datos con serializer de actualización parcial
                serializer = TenantProfileMeUpdateSerializer(perfil, data=data_para_validar, partial=True, context={'request': request})
                serializer.is_valid(raise_exception=True)
                
                # Extraer solo campos permitidos para actualizar
                # ⚠️ v2.30: Incluir configuracion (normalizada a {} si es null por el serializer)
                campos_permitidos = ['cargo', 'departamento', 'telefono_corporativo', 'configuracion']
                data_actualizar = {k: v for k, v in serializer.validated_data.items() if k in campos_permitidos}
                
                # Actualizar campos básicos usando el servicio
                if data_actualizar:
                    perfil = actualizar_perfil(request.user, data_actualizar)
                
                # Retornar perfil actualizado
                serializer = self.get_serializer(perfil, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        except (ProgrammingError, OperationalError) as e:
            # Error de tabla faltante (esquema sin migrar)
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'relation' in error_msg or 'table' in error_msg:
                log.warning(
                    f"Tabla TenantProfile no existe en schema '{connection.schema_name}'. "
                    f"Esquema sin migrar. Error: {e}"
                )
                return Response(
                    {
                        'detail': 'El esquema del tenant no ha sido migrado aún. '
                                 'Contacta al administrador o intenta en unos segundos.',
                        'detail_code': 'tenant_schema_unmigrated'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            # Otro error de BD (re-lanzar)
            raise
        
        except Exception as e:
            log.error(
                f"Error {'obteniendo' if method == 'GET' else 'actualizando'} perfil "
                f"para usuario {request.user.id}: {e}",
                exc_info=True
            )
            return Response(
                {'detail': f'Error al {"obtener" if method == "GET" else "actualizar"} el perfil del usuario.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR if method == 'GET' else status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get', 'patch'], url_path='me', url_name='me',
            parser_classes=[JSONParser, MultiPartParser, FormParser])
    def me(self, request: Request) -> Response:
        """
        Endpoint para obtener/actualizar el perfil del usuario actual.
        
        ⚠️ v2.30: API-First + Service Layer - Usa servicios para toda la lógica.
        ⚠️ IMPORTANTE: Este endpoint NO requiere ID en la URL.
        Siempre trabaja sobre `request.user`.
        
        GET /api/v1/perfil/perfiles/me/:
            - Retorna el perfil del usuario actual
            - Si no existe, lo crea automáticamente usando el servicio
            - Si la tabla no existe (esquema sin migrar), retorna 503
        
        PATCH /api/v1/perfil/perfiles/me/:
            - Actualiza el perfil del usuario actual usando el servicio
            - Permite actualizar: cargo, departamento, telefono_corporativo, configuracion, avatar
            - Soporta application/json y multipart/form-data (para avatar)
            - Si configuracion es null, se normaliza a {} automáticamente
            - Si se envía avatar en multipart, se actualiza junto con los demás campos
        
        Returns:
            Response: Perfil del usuario actual (GET) o perfil actualizado (PATCH)
        """
        return self._safe_get_me_profile_response(request, method=request.method)
    
    @action(detail=False, methods=['patch'], url_path='me/configuracion', url_name='me-configuracion')
    def me_configuracion(self, request: Request) -> Response:
        """
        Endpoint para actualizar la configuración de UI del perfil.
        
        ⚠️ v2.30: API-First + Service Layer - Usa servicios para toda la lógica.
        ⚠️ IMPORTANTE: Este endpoint actualiza solo el campo `configuracion`
        (JSONField) de forma segura, preservando los valores existentes si merge=True.
        
        PATCH /api/v1/perfil/perfiles/me/configuracion/:
            - Actualiza la configuración de UI del perfil
            - Body: {"clave": "valor"} o {"configuracion": {"clave": "valor"}}
            - Query param: ?merge=false para reemplazar toda la configuración (default: merge=true)
        
        Example:
            PATCH /api/v1/perfil/perfiles/me/configuracion/?merge=true
            {
                "modo_oscuro": true,
                "densidad_tablas": "compacta"
            }
        
        Returns:
            Response: Perfil actualizado con la nueva configuración
        """
        try:
            # Obtener la configuración del request
            configuracion_data = request.data.get('configuracion', request.data)
            
            if not isinstance(configuracion_data, dict):
                return Response(
                    {'error': 'La configuración debe ser un objeto JSON válido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determinar si hacer merge (default: True)
            merge = request.query_params.get('merge', 'true').lower() == 'true'
            
            # Actualizar la configuración usando el servicio
            perfil = actualizar_configuracion_ui(request.user, configuracion_data, merge=merge)
            
            # Retornar el perfil actualizado
            serializer = self.get_serializer(perfil, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except (ProgrammingError, OperationalError) as e:
            # Error de tabla faltante (esquema sin migrar)
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'relation' in error_msg or 'table' in error_msg:
                log.warning(
                    f"Tabla TenantProfile no existe en schema '{connection.schema_name}'. "
                    f"Esquema sin migrar. Error: {e}"
                )
                return Response(
                    {
                        'detail': 'El esquema del tenant no ha sido migrado aún. '
                                 'Contacta al administrador o intenta en unos segundos.',
                        'detail_code': 'tenant_schema_unmigrated'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            raise
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log.error(f"Error actualizando configuración para usuario {request.user.id}: {e}", exc_info=True)
            return Response(
                {'detail': 'Error al actualizar la configuración.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['patch'], url_path='me/avatar', url_name='me-avatar',
            parser_classes=[MultiPartParser, FormParser])
    def me_avatar(self, request: Request) -> Response:
        """
        Endpoint para actualizar el avatar del perfil.
        
        ⚠️ v2.30: API-First + Service Layer - Usa servicios para toda la lógica.
        
        PATCH /api/v1/perfil/perfiles/me/avatar/:
            - Actualiza el avatar del perfil del usuario actual
            - Content-Type: multipart/form-data
            - Body: archivo con key 'avatar'
            - Tipos permitidos: image/jpeg, image/png, image/gif, image/webp
            - Tamaño máximo: 5MB
        
        Returns:
            Response: Perfil actualizado con el nuevo avatar
        """
        # Validar que se haya enviado un archivo
        if 'avatar' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó ningún archivo. Use el campo "avatar".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        archivo = request.FILES['avatar']
        
        try:
            # Actualizar avatar usando el servicio
            perfil = actualizar_avatar(request.user, archivo)
            
            # Retornar el perfil actualizado
            serializer = self.get_serializer(perfil, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except (ProgrammingError, OperationalError) as e:
            # Error de tabla faltante (esquema sin migrar)
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'relation' in error_msg or 'table' in error_msg:
                log.warning(
                    f"Tabla TenantProfile no existe en schema '{connection.schema_name}'. "
                    f"Esquema sin migrar. Error: {e}"
                )
                return Response(
                    {
                        'detail': 'El esquema del tenant no ha sido migrado aún. '
                                 'Contacta al administrador o intenta en unos segundos.',
                        'detail_code': 'tenant_schema_unmigrated'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            raise
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            log.error(f"Error actualizando avatar para usuario {request.user.id}: {e}", exc_info=True)
            return Response(
                {'detail': 'Error al actualizar el avatar.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
