"""
Mixins base para la arquitectura SINTEL v3.5.
Centraliza la lógica de Double Semantic Verification (DSV) y el acceso a servicios.
"""
import logging
from typing import Any, Dict, Optional

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
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

    def get_sede_id(self) -> Optional[int]:
        """Resuelve la sede activa del request (ver docs/ADR-003-contexto-
        organizacional-sede-area.md). Espeja get_empresa_id() en vez de un
        middleware que mute request.* - ver ADR-003 seccion "Decision de
        diseno" para el porque.

        Orden de resolucion (solo resuelve CUAL sede esta activa; si el
        usuario puede operar en ella es responsabilidad de
        HasOrganizationalScope, no de este metodo):
          1. request.session['sede_activa_id'], si esa sede sigue
             perteneciendo a la empresa activa (si no, se descarta de la
             sesion por quedar obsoleta - ej. cambio de empresa).
          2. La primera (por nombre) de perfil.sedes_asignadas.
          3. La Sede "Principal" de la empresa (fallback para un perfil sin
             sedes_asignadas explicitas, ej. alcance EMPRESA).
        Retorna None solo si la empresa aun no tiene ninguna Sede.
        """
        from apps.tenant.core.services.sede_context import resolve_sede_activa_id

        empresa_id = self.get_empresa_id()
        perfil = getattr(self.request.user, 'tenant_profile', None)
        return resolve_sede_activa_id(self.request, empresa_id, perfil)

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

        # [FASE 7, consolidacion OCF/OSF] self.get_object() dentro de un
        # update()/destroy() personalizado (ej. compras) llega aqui cuando
        # check_object_permissions() deniega (ej. HasOrganizationalScope) --
        # sin este caso, una denegacion de permiso real caia al generico de
        # abajo y respondia 500 en vez de 403 (el bloqueo si funcionaba, solo
        # el codigo de estado era incorrecto). Ver documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md.
        if isinstance(exc, DRFPermissionDenied):
            return Response(
                {"error": "forbidden", "message": exc.detail if hasattr(exc, "detail") else str(exc)},
                status=status.HTTP_403_FORBIDDEN
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

    def _get_sede_id_seguro(self) -> Optional[int]:
        """Obtiene sede_id (contexto organizacional activo) con fallback
        seguro. Requiere que el ViewSet herede SintelDSVMixin (get_sede_id()).
        Ver docs/ADR-003-contexto-organizacional-sede-area.md."""
        try:
            return self.get_sede_id()
        except Exception:
            sede = self._get_sede()
            return sede.id if sede else None

    def _get_sede(self):
        """Helper para obtener la Sede activa con fallback seguro."""
        from apps.tenant.empresa.models import Sede
        try:
            sede_id = self.get_sede_id()
            return Sede.objects.filter(id=sede_id).first() if sede_id else None
        except Exception:
            empresa = self._get_empresa()
            if not empresa:
                return None
            return Sede.objects.filter(empresa=empresa).order_by('nombre').first()

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
