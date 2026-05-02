"""
Mixins base para la arquitectura SINTEL v3.5.
Centraliza la lógica de Double Semantic Verification (DSV) y el acceso a servicios.
"""
import logging
from typing import Any, Dict, Optional

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)

class SintelDSVMixin:
    """
    Double Semantic Verification (DSV) Mixin.
    Garantiza que toda operación DML esté vinculada estructuralmente a la empresa del tenant.
    Ref: AGENTS.md [SaaS-DEFENSE] 13.
    """

    def get_empresa_id(self) -> int:
        """Obtiene el ID de la empresa desde el perfil del usuario (SSoT)."""
        if hasattr(self.request.user, 'tenant_profile') and self.request.user.tenant_profile:
            return self.request.user.tenant_profile.empresa_id
        
        # Fallback de seguridad: Singleton de Empresa por Tenant
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise DRFValidationError("No se encontró configuración de empresa para este tenant.")
        return empresa.id

    def handle_service_error(self, exc: Exception) -> Response:
        """Mapeo estandarizado de excepciones de servicios a respuestas DRF."""
        if isinstance(exc, DRFValidationError):
            return Response(exc.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        logger.error(f"[DSV:Error] {type(exc).__name__}: {str(exc)}", exc_info=True)
        return Response(
            {
                "error": "internal_service_error",
                "message": str(exc),
                "type": type(exc).__name__
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class SintelServiceMixin:
    """Mixin para inyectar servicios en ViewSets siguiendo v3.5."""
    service_class = None
    _service_inst = None

    @property
    def service(self):
        if self._service_inst is None:
            if self.service_class is None:
                raise AttributeError(f"{self.__class__.__name__} debe definir service_class.")
            self._service_inst = self.service_class()
        return self._service_inst
