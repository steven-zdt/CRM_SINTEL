"""
Vistas API públicas para validación de tokens de acceso a documentos compartidos.

WARNING: v3.3: API-First - Endpoints DRF para acceso público a documentos
WARNING: Seguridad: Validación de hash SHA256 para integridad
"""

import logging

from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.public.services import obtener_datos_documento_publico, validar_token_documento

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def validar_token_acceso(request):
    """
    Valida un token de acceso público a un documento.

    WARNING: API-First: Endpoint público (AllowAny) para validación de tokens

    Métodos:
    - GET: Validar token desde query params
    - POST: Validar token desde body JSON

    Query Params (GET):
        - token: Hash de acceso
        - tipo: Tipo de documento ('cotizacion', 'proyecto')
        - id: ID del documento
        - tenant: Schema del tenant

    Body (POST):
        {
            "token": "hash...",
            "tipo_documento": "cotizacion",
            "documento_id": 123,
            "tenant_schema": "empresa_x"
        }

    Returns:
        200 OK: Token válido
        {
            "valido": true,
            "tipo_documento": "cotizacion",
            "documento_id": 123,
            "tenant_schema": "empresa_x",
            "expiracion": 1234567890,
            "expiracion_fecha": "2024-12-31T23:59:59Z"
        }

        400 Bad Request: Token inválido o expirado
        {
            "valido": false,
            "error": "Hash de acceso inválido o expirado"
        }
    """
    try:
        if request.method == "GET":
            token = request.query_params.get("token")
            tipo_documento = request.query_params.get("tipo") or request.query_params.get(
                "tipo_documento"
            )
            documento_id = request.query_params.get("id") or request.query_params.get(
                "documento_id"
            )
            tenant_schema = request.query_params.get("tenant") or request.query_params.get(
                "tenant_schema"
            )
        else:  # POST
            data = request.data
            token = data.get("token")
            tipo_documento = data.get("tipo_documento") or data.get("tipo")
            documento_id = data.get("documento_id") or data.get("id")
            tenant_schema = data.get("tenant_schema") or data.get("tenant")

        if not all([token, tipo_documento, documento_id, tenant_schema]):
            return Response(
                {
                    "valido": False,
                    "error": "Parámetros incompletos. Se requieren: token, tipo_documento, documento_id, tenant_schema",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convertir documento_id a int
        try:
            documento_id = int(documento_id)
        except (ValueError, TypeError):
            return Response(
                {"valido": False, "error": "documento_id debe ser un número entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar token
        resultado = validar_token_documento(
            token=token,
            tipo_documento=tipo_documento,
            documento_id=documento_id,
            tenant_schema=tenant_schema,
        )

        if resultado["valido"]:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except ValidationError as e:
        logger.warning(f"[public.api] Error de validación: {e}")
        return Response({"valido": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"[public.api] Error inesperado validando token: {e}", exc_info=True)
        return Response(
            {"valido": False, "error": "Error interno del servidor"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def obtener_documento_publico(request):
    """
    Obtiene los datos públicos de un documento validado por token.

    WARNING: API-First: Endpoint público (AllowAny) para obtener datos de documentos compartidos
    WARNING: Seguridad: Requiere token válido en query params

    Query Params:
        - token: Hash de acceso (requerido)
        - tipo: Tipo de documento ('cotizacion', 'proyecto')
        - id: ID del documento
        - tenant: Schema del tenant

    Returns:
        200 OK: Datos públicos del documento
        {
            "valido": true,
            "documento": {
                "id": 123,
                "numero": "COT-001",
                "fecha_emision": "2024-01-01",
                ...
            }
        }

        400 Bad Request: Token inválido o expirado
        404 Not Found: Documento no encontrado
    """
    try:
        token = request.query_params.get("token")
        tipo_documento = request.query_params.get("tipo") or request.query_params.get(
            "tipo_documento"
        )
        documento_id = request.query_params.get("id") or request.query_params.get("documento_id")
        tenant_schema = request.query_params.get("tenant") or request.query_params.get(
            "tenant_schema"
        )

        if not all([token, tipo_documento, documento_id, tenant_schema]):
            return Response(
                {
                    "error": "Parámetros incompletos. Se requieren: token, tipo_documento, documento_id, tenant_schema"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convertir documento_id a int
        try:
            documento_id = int(documento_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "documento_id debe ser un número entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar token primero
        resultado_validacion = validar_token_documento(
            token=token,
            tipo_documento=tipo_documento,
            documento_id=documento_id,
            tenant_schema=tenant_schema,
        )

        if not resultado_validacion["valido"]:
            return Response(
                {"error": resultado_validacion.get("error", "Token inválido o expirado")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cambiar al schema del tenant para obtener datos
        with schema_context(tenant_schema):
            # WARNING: NOTA: La implementación completa requiere importar los modelos del tenant
            # Por ahora retornamos estructura base
            datos_publicos = obtener_datos_documento_publico(
                tipo_documento=tipo_documento,
                documento_id=documento_id,
                tenant_schema=tenant_schema,
            )

            if not datos_publicos:
                return Response(
                    {"error": "Documento no encontrado"}, status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"valido": True, "documento": datos_publicos}, status=status.HTTP_200_OK
            )

    except ValidationError as e:
        logger.warning(f"[public.api] Error de validación: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"[public.api] Error obteniendo documento público: {e}", exc_info=True)
        return Response(
            {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
