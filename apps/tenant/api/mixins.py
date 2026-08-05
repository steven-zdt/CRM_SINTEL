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
        # 1. Intentar obtener del perfil (Produccion / Auth OK)
        if hasattr(self.request.user, 'tenant_profile') and self.request.user.tenant_profile:
            return self.request.user.tenant_profile.empresa_id

        # 2. Fallback DEBUG: solo para usuarios autenticados sin perfil en este schema.
        # NUNCA aplica a usuarios anonimos — la autenticacion es obligatoria siempre.
        from django.conf import settings
        if settings.DEBUG and self.request.user and self.request.user.is_authenticated:
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.first()
            if empresa:
                logger.warning(
                    "[DSV:DEBUG] Fallback empresa_id=%s para user=%s sin tenant_profile",
                    empresa.id, self.request.user.id,
                )
                return empresa.id

        raise DRFValidationError("No se encontro configuracion de empresa para este tenant.")

    def handle_service_error(self, exc: Exception) -> Response:
        """Mapeo estandarizado de excepciones de servicios a respuestas DRF."""
        from django.core.exceptions import ObjectDoesNotExist
        from django.http import Http404

        if isinstance(exc, DRFValidationError):
            return Response(exc.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        if isinstance(exc, (ObjectDoesNotExist, Http404)):
            return Response(
                {"error": "not_found", "message": "El recurso solicitado no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

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


class BaseServiceMixin:
    """
    # CANONICAL: BaseServiceMixin — Consolidado para 14+ api_mixins.py modules

    Proporciona acceso estándar a Selectors, CRUDService, BusinessService.
    Requiere que ViewSet defina:
    - selector_class: Clase selector para consultas
    - crud_service_class: Clase CRUD service para persistencia
    - business_service_class: Clase business service para lógica

    Requiere que ViewSet herede de SintelDSVMixin (para get_empresa_id()).

    Uso:
        class GastoViewSet(BaseServiceMixin, SintelDSVMixin, ViewSet):
            selector_class = GastoSelector
            crud_service_class = GastoCRUDService
            business_service_class = GastoBusinessService
    """

    selector_class = None
    crud_service_class = None
    business_service_class = None

    def _get_empresa_id_seguro(self) -> Optional[int]:
        """
        Obtiene empresa_id con fallback al singleton del esquema tenant.
        Utilizado cuando self.get_empresa_id() falla (ej: durante testing).
        """
        try:
            return self.get_empresa_id()
        except Exception:
            empresa = self._get_empresa()
            return empresa.id if empresa else None

    def _get_empresa(self) -> Optional[Empresa]:
        """Helper para obtener Empresa actual con fallback seguro."""
        try:
            empresa_id = self.get_empresa_id()
            return Empresa.objects.filter(id=empresa_id).first()
        except Exception:
            # Fallback final: Empresa singleton del tenant actual
            return Empresa.objects.only('id').first()

    def get_qs_list(self):
        """
        Retorna queryset de lista usando selector.
        Soporta parámetro ?search= para búsquedas fulltext.
        """
        if self.selector_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} debe definir selector_class")

        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """
        Retorna queryset de detalle usando selector.
        Filtra por lookup_field (típicamente 'uuid' o 'pk').
        """
        if self.selector_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} debe definir selector_class")

        empresa_id = self._get_empresa_id_seguro()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        return self.selector_class.get_detail(empresa_id, lookup_value)
