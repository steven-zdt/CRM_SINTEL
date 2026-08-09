"""
Endpoints del Contexto Organizacional. `ContextoSedeView` (ADR-003) permite
cambiar la "sede activa" dentro de la sesion. `ContextoOrganizacionalView`
(Fase 3 del proyecto OCF, "Organizational Resolver"; extendida en Fase F3
del proyecto OSF) expone de solo lectura el OrganizationalContext resuelto
(apps/tenant/core/services/organizational_context.py) - integracion con el
Workspace pedida por esa fase: cualquier pieza de UI/JS puede consultar
GET /api/v1/core/contexto/ para saber que empresa/sede/area/rol/alcance
aplica sin duplicar la logica de resolucion.

[OSF Fase F3] La respuesta ahora incluye ademas un bloque `scope` con
OrganizationalScope.to_dict() (apps/tenant/core/services/organizational_scope.py):
la cadena TENANT->EMPRESA->USUARIO->TENANTPROFILE->ROL->ALCANCE->SEDE/S->AREA/S
que pide la Fase F3 requiere el conjunto PLURAL de sedes/areas permitidas, que
`OrganizationalContext` (deliberadamente) no resuelve - solo su sede/area
ACTIVA, singular. Antes de esta fase, ningun endpoint exponia ese conjunto
plural a la UI. Se extiende este mismo endpoint (en vez de crear uno nuevo)
porque ya es el punto de entrada que el Workspace consulta al cargar tras el
login - mismo criterio de "no duplicar mecanismos" de toda la sesion.
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.core.services.organizational_context import (
    OrganizationalContextError,
    OrganizationalContextMixin,
)
from apps.tenant.core.services.organizational_scope import (
    OrganizationalScope,
    OrganizationalScopeError,
)

logger = logging.getLogger("tenant.core.contexto")


class ContextoOrganizacionalView(OrganizationalContextMixin, APIView):
    """
    GET /api/v1/core/contexto/

    Devuelve el OrganizationalContext resuelto para el usuario/tenant
    actual (Fase 3, OCF), mas un bloque `scope` (OrganizationalScope,
    Fase F3 OSF) con el conjunto PLURAL de sedes/areas permitidas. Funciona
    identico via JWT o Session (Dual-Auth, apps/tenant/api/base.py) -
    ambos mixins solo requieren `self.request`, sin importar que
    authentication_class lo poblo.
    """
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request, *args, **kwargs):
        try:
            context = self.get_organizational_context()
        except OrganizationalContextError as exc:
            return Response(
                {"error": "contexto_no_resuelto", "message": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        data = context.to_dict()
        try:
            data["scope"] = OrganizationalScope.resolve(request).to_dict()
        except OrganizationalScopeError as exc:
            # No deberia ocurrir si context.resolve() ya tuvo exito (mismas
            # precondiciones: usuario autenticado + empresa_id resuelto) -
            # pero ambos contratos se resuelven de forma independiente por
            # decision explicita (ver organizational_scope.py), asi que no
            # se asume - se degrada explicitamente en vez de fallar todo el
            # endpoint por un bloque que es aditivo.
            logger.warning("[ContextoOrganizacional] scope no resuelto: %s", exc)
            data["scope"] = None
        return Response(data, status=status.HTTP_200_OK)


class ContextoSedeView(APIView):
    """
    POST /api/v1/core/contexto/sede/  {"sede_uuid": "..."}

    DSV: la sede debe pertenecer a la empresa activa del tenant, y el
    perfil debe poder operar en ella (alcance EMPRESA, o la sede esta en
    sedes_asignadas) - mismo criterio que HasOrganizationalScope
    (apps/tenant/api/permissions.py), aplicado aqui al momento de elegirla
    en vez de al momento de leer un objeto ya existente.
    """
    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request, *args, **kwargs):
        from apps.tenant.empresa.models import Sede

        sede_uuid = request.data.get('sede_uuid')
        if not sede_uuid:
            return Response(
                {"error": "sede_uuid_requerido", "message": "Debe indicar sede_uuid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        perfil = getattr(request.user, 'tenant_profile', None)
        if perfil is None:
            return Response(
                {"error": "sin_perfil", "message": "El usuario no tiene un perfil en este tenant."},
                status=status.HTTP_403_FORBIDDEN,
            )

        sede = Sede.objects.filter(uuid=sede_uuid, empresa_id=perfil.empresa_id).first()
        if not sede:
            return Response(
                {"error": "sede_invalida", "message": "La sede indicada no existe o no pertenece a su empresa."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if perfil.alcance != 'EMPRESA' and not perfil.sedes_asignadas.filter(id=sede.id).exists():
            return Response(
                {"error": "sede_no_asignada", "message": "No tiene esta sede asignada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        request.session['sede_activa_id'] = sede.id
        logger.info("[ContextoSede] usuario=%s sede_activa=%s (%s)", request.user.id, sede.id, sede.nombre)
        return Response({"sede_id": sede.id, "sede_uuid": str(sede.uuid), "nombre": sede.nombre}, status=status.HTTP_200_OK)
