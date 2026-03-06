"""
Views para ingesta de facturas desde correo.

⚠️ FASE 4: Endpoints JSON-only para orquestar ingesta por correo.
- Complementa POST /api/v1/facturas/upload-ubl/ (no lo reemplaza)
- SessionAuthentication + CSRF para UI privada
- Permisos: IsTenantAdminOrStaff (TODO: permisos finos por TenantMembership)
"""
import logging
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenant.facturas.api.serializers import (
    MailIngestionRunCreateSerializer,
    MailIngestionRunListSerializer,
)
from apps.tenant.facturas.models import MailIngestionRun
from apps.tenant.empresa.models import MailInboxConfig
# ⚠️ IMPORT LAZY: enqueue_mail_ingestion se importa dentro del método (evita ciclos)
# from apps.tenant.facturas.services_mail_ingestion import enqueue_mail_ingestion
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly

logger = logging.getLogger(__name__)


class MailIngestionRunCreateAPIView(APIView):
    """
    POST /api/v1/facturas/ingesta-correo/run/
    
    Encola tarea de ingesta de correo y devuelve 202 con run_id y task_id.
    
    ⚠️ ASÍNCRONO: La tarea se ejecuta en Celery (cola high_priority).
    ⚠️ PERMISOS: IsTenantAdminOrReadOnly (TODO: permisos finos)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    
    def post(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.facturas.services_mail_ingestion import enqueue_mail_ingestion
        
        serializer = MailIngestionRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            run = enqueue_mail_ingestion(
                config_id=data["config_id"],
                limit_messages=data.get("limit_messages", 50),
                started_by=request.user,
            )
            
            return Response(
                {
                    "run_id": run.id,
                    "task_id": run.task_id,
                    "status": run.status,
                    "redirect_url": "/workspace/#facturas",  # JSON-only pattern
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except MailInboxConfig.DoesNotExist:
            return Response(
                {"error": "config_not_found", "message": "La configuración de buzón no existe o no está activa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": "internal_error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MailIngestionRunsListAPIView(generics.ListAPIView):
    """
    GET /api/v1/facturas/ingesta-correo/runs/
    
    Lista ejecuciones recientes de ingesta por correo (JSON-only).
    
    ⚠️ PAGINACIÓN: Usa paginación estándar de DRF.
    ⚠️ PERMISOS: IsTenantAdminOrReadOnly (TODO: permisos finos)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    serializer_class = MailIngestionRunListSerializer
    
    def get_queryset(self):
        """Retorna todas las ejecuciones del tenant (aislamiento por esquema automático)."""
        return MailIngestionRun.objects.all()


class MailIngestionPreviewAPIView(APIView):
    """
    POST /api/v1/facturas/ingesta-correo/preview/
    
    Pre-visualiza facturas desde correo sin persistirlas (solo metadatos).
    
    ⚠️ PRE-VISUALIZACIÓN: Extrae metadatos de facturas encontradas pero NO las persiste.
    ⚠️ SINCRONIZACIÓN: El usuario debe seleccionar cuáles procesar después.
    ⚠️ PERMISOS: IsTenantAdminOrReadOnly (TODO: permisos finos)
    
    Body (JSON):
    {
        "config_id": int,  # ID de MailInboxConfig
        "limit_messages": int  # Opcional, default: 50
    }
    
    Returns:
    {
        "ok": bool,
        "processed": int,
        "xml_detected": int,
        "pending_invoices": [
            {
                "numero": str,
                "fecha_emision": str,
                "emisor_nit": str,
                "emisor_razon_social": str,
                "receptor_nit": str,
                "receptor_razon_social": str,
                "subtotal": str,
                "impuestos": str,
                "total": str,
                "moneda": str,
                "cufe": str,
                "source_email_id": str,
                "source_filename": str,
                "xml_text": str,  # XML completo para persistir
                "dto": dict,  # DTO completo para persistir
                "file_bytes_b64": str  # XML codificado en base64
            },
            ...
        ],
        "details": List[Dict]
    }
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    
    def post(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.facturas.services_mail_ingestion import preview_mail_ingestion
        from apps.tenant.empresa.models import MailInboxConfig
        
        # ⚠️ v2.60: config_id y limit_messages son opcionales con valores por defecto
        config_id = request.data.get("config_id")
        limit_messages = request.data.get("limit_messages", 50)
        
        # Si no se proporciona config_id, intentar obtener la primera configuración activa
        if not config_id:
            try:
                active_config = MailInboxConfig.objects.filter(is_active=True).first()
                if active_config:
                    config_id = active_config.id
                    logger.info(f"[MailIngestionPreviewAPIView] Usando configuración activa por defecto: {config_id}")
                else:
                    return Response(
                        {
                            "error": "no_active_config",
                            "message": "No hay configuraciones de buzón activas. Configure un buzón primero.",
                            "missing_fields": ["config_id"]
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Exception as e:
                logger.error(f"[MailIngestionPreviewAPIView] Error obteniendo configuración por defecto: {e}", exc_info=True)
                return Response(
                    {
                        "error": "config_error",
                        "message": f"Error al obtener configuración de buzón: {str(e)}",
                        "missing_fields": ["config_id"]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        # ⚠️ VALIDACIÓN DE SEGURIDAD: Verificar que la configuración pertenezca al tenant actual
        # El aislamiento por tenant es automático, pero validamos explícitamente para mejor mensaje de error
        try:
            config = MailInboxConfig.objects.filter(id=config_id, is_active=True).first()
            if not config:
                return Response(
                    {
                        "error": "config_not_found",
                        "message": f"La configuración de buzón (ID: {config_id}) no existe o no está activa para este tenant.",
                        "missing_fields": ["config_id"]
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception as e:
            logger.error(f"[MailIngestionPreviewAPIView] Error validando configuración: {e}", exc_info=True)
            return Response(
                {
                    "error": "config_validation_error",
                    "message": f"Error al validar la configuración de buzón: {str(e)}",
                    "missing_fields": ["config_id"]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            result = preview_mail_ingestion(
                config_id=config_id,
                limit_messages=limit_messages,
            )
            
            if not result.get("ok"):
                # ⚠️ DIAGNÓSTICO: Retornar código de estado apropiado según el tipo de error
                error_type = result.get("error", "mailbox_error")
                if error_type == "authentication_error" or error_type == "auth_failed":
                    status_code = status.HTTP_401_UNAUTHORIZED
                elif error_type == "connection_error":
                    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                elif error_type == "config_not_found" or error_type == "config_error":
                    status_code = status.HTTP_404_NOT_FOUND
                else:
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
                return Response(
                    result,
                    status=status_code,
                )
            
            # ⚠️ v2.60: Incluir config_id en la respuesta para que el frontend pueda usarlo
            response_data = result.copy()
            response_data['config_id'] = config_id
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": "invalid_config", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "internal_error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )