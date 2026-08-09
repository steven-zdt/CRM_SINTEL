"""
Tests de la Jerarquia de Permisos Organizacionales (Fase 4, proyecto OCF).

Las vistas de prueba se invocan directamente (via APIRequestFactory +
.as_view()(request)) en vez de por URL real: TenantSecurityAndURLConfMiddleware
sobreescribe `request.urlconf` por tenant (confirmado en el codigo,
apps/public/tenants/middleware_urlconf.py), asi que `override_settings(
ROOT_URLCONF=...)` no tiene efecto dentro de un request de tenant - no vale
la pena registrar vistas de test en el urlconf real solo para este test.
Invocar la vista directamente SI sigue ejercitando la autenticacion DRF real
(JWTAuthentication decodifica el header Authorization dentro de
APIView.dispatch(), no en middleware de Django) - solo se omite el
middleware de Django en si (TenantMainMiddleware, etc.), que no es lo que
esta fase necesita probar (eso ya se probo en Fase 3 con un round-trip HTTP
completo).
"""
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenant.api.permissions import IsTenantMember, OrganizationalPermission
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.core.services.organizational_permissions import (
    ADMIN_EMPRESA,
    ADMIN_GLOBAL,
    ADMIN_SEDE,
    CONSULTA,
    JEFE_AREA,
    OPERADOR,
    level_meets_minimum,
    resolve_organizational_permission_level,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

_factory = APIRequestFactory()


def _jwt_bearer(user) -> str:
    return "Bearer " + str(RefreshToken.for_user(user).access_token)


class _MinSedeView(OrganizationalContextMixin, APIView):
    minimum_organizational_level = ADMIN_SEDE
    permission_classes = [IsTenantMember, OrganizationalPermission]

    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


class _NoMinimumDeclaredView(APIView):
    """No hereda OrganizationalContextMixin ni declara
    minimum_organizational_level - OrganizationalPermission no debe
    restringir nada aqui (opt-in real)."""
    permission_classes = [IsTenantMember, OrganizationalPermission]

    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


class ResolveOrganizationalPermissionLevelTests(TestCase):
    """Puramente unitario - sin DB, cubre las 6 combinaciones reales del
    mapeo (ver docstring de organizational_permissions.py)."""

    def test_is_staff_is_always_admin_global_regardless_of_rol_alcance(self):
        self.assertEqual(
            resolve_organizational_permission_level(rol="VISOR", alcance="AREA", is_staff=True),
            ADMIN_GLOBAL,
        )

    def test_admin_empresa(self):
        self.assertEqual(resolve_organizational_permission_level(rol="ADMIN", alcance="EMPRESA"), ADMIN_EMPRESA)

    def test_admin_sede(self):
        self.assertEqual(resolve_organizational_permission_level(rol="ADMIN", alcance="SEDE"), ADMIN_SEDE)

    def test_jefe_area(self):
        self.assertEqual(resolve_organizational_permission_level(rol="ADMIN", alcance="AREA"), JEFE_AREA)

    def test_operador_regardless_of_alcance(self):
        self.assertEqual(resolve_organizational_permission_level(rol="OPERADOR", alcance="EMPRESA"), OPERADOR)
        self.assertEqual(resolve_organizational_permission_level(rol="OPERADOR", alcance="AREA"), OPERADOR)

    def test_consulta(self):
        self.assertEqual(resolve_organizational_permission_level(rol="VISOR", alcance="EMPRESA"), CONSULTA)

    def test_level_meets_minimum_ordering(self):
        self.assertTrue(level_meets_minimum(ADMIN_GLOBAL, ADMIN_SEDE))  # mas privilegiado que el minimo
        self.assertTrue(level_meets_minimum(ADMIN_SEDE, ADMIN_SEDE))    # exactamente el minimo
        self.assertFalse(level_meets_minimum(OPERADOR, ADMIN_SEDE))     # menos privilegiado
        self.assertFalse(level_meets_minimum("NIVEL_INVENTADO", ADMIN_SEDE))  # fail-closed


class OrganizationalPermissionIntegrationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase4", nit="900000333", direccion="Calle 1",
        )
        Sede.objects.create(empresa=self.empresa, nombre="Principal")
        # SintelTenantTestCase.setup_user() crea self.user como staff (el
        # "admin global" del tenant de prueba) - eso hace que
        # resolve_organizational_permission_level() lo resuelva SIEMPRE como
        # ADMIN_GLOBAL sin importar rol/alcance (comportamiento CORRECTO de
        # produccion, ver docstring de is_staff en ese modulo), lo que
        # invalidaria cualquier prueba de un nivel no-global. Se desactiva
        # aqui explicitamente para poder probar los demas niveles; el nivel
        # ADMIN_GLOBAL en si se prueba por separado, activandolo a proposito.
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save(update_fields=["is_staff", "is_superuser"])

    def _request_as(self, rol: str, alcance: str, is_staff: bool = False):
        self.user.is_staff = is_staff
        self.user.save(update_fields=["is_staff"])
        TenantProfile.objects.filter(user=self.user, empresa=self.empresa).delete()
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol=rol, alcance=alcance)
        request = _factory.get("/", HTTP_AUTHORIZATION=_jwt_bearer(self.user))
        request.tenant = self.tenant
        return request

    def test_admin_empresa_meets_admin_sede_minimum_because_it_outranks_it(self):
        """ADMIN_EMPRESA es mas privilegiado que ADMIN_SEDE en el orden de
        ORGANIZATIONAL_PERMISSION_LEVELS - debe permitir, no denegar por no
        coincidir literalmente con el nivel minimo declarado."""
        request = self._request_as(rol="ADMIN", alcance="EMPRESA")
        response = _MinSedeView.as_view()(request)
        self.assertEqual(response.status_code, 200, response.data)

    def test_admin_sede_exactly_meets_its_own_minimum(self):
        request = self._request_as(rol="ADMIN", alcance="SEDE")
        response = _MinSedeView.as_view()(request)
        self.assertEqual(response.status_code, 200, response.data)

    def test_operador_denied_from_admin_sede_minimum(self):
        request = self._request_as(rol="OPERADOR", alcance="SEDE")
        response = _MinSedeView.as_view()(request)
        self.assertEqual(response.status_code, 403, response.data)

    def test_view_without_minimum_declared_is_never_restricted(self):
        """Fail-open solo cuando el ViewSet no opto por declarar un nivel -
        no es un fallback silencioso, es la semantica documentada de
        OrganizationalPermission."""
        request = self._request_as(rol="OPERADOR", alcance="AREA")
        response = _NoMinimumDeclaredView.as_view()(request)
        self.assertEqual(response.status_code, 200, response.data)

    def test_staff_user_is_admin_global_and_outranks_every_minimum(self):
        """is_staff=True (ADMIN GLOBAL) debe pasar cualquier
        minimum_organizational_level sin importar rol/alcance del
        TenantProfile - probado activando is_staff a proposito, no como
        efecto secundario accidental del fixture base (ver setUp)."""
        request = self._request_as(rol="VISOR", alcance="AREA", is_staff=True)
        response = _MinSedeView.as_view()(request)
        self.assertEqual(response.status_code, 200, response.data)
