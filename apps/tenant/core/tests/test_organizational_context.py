"""
Tests de OrganizationalContext (Fase 2, proyecto OCF).

Validacion clave pedida por la Fase 2 ("Validar: Sin romper APIs"): estos
tests prueban que OrganizationalContext.resolve() coincide exactamente con
lo que SintelDSVMixin.get_empresa_id()/get_sede_id() ya resuelven para el
MISMO request - es una prueba de paridad, no solo de que la clase nueva
"funciona sola". Usan RequestFactory (no HTTP real) para no depender del
bug preexistente de force_login/schema_context ya documentado en
documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md (Fase 0, riesgo R-6).
"""
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextError,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class _FakeMixinHost(SintelDSVMixin):
    """Envoltorio minimo para invocar los metodos de instancia de
    SintelDSVMixin (get_empresa_id/get_sede_id) fuera de un ViewSet real,
    exactamente como los usaria un ViewSet de verdad (self.request)."""

    def __init__(self, request):
        self.request = request


def _build_request(user, tenant):
    request = RequestFactory().get("/")
    request.user = user
    request.tenant = tenant
    request.session = SessionStore()
    return request


class OrganizationalContextParityTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF", nit="900000111", direccion="Calle 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
            configuracion={"theme": "dark"},
        )

    def test_resolve_matches_existing_mixin_resolution(self):
        request = _build_request(self.user, self.tenant)
        mixin_host = _FakeMixinHost(request)

        context = OrganizationalContext.resolve(request)

        self.assertEqual(context.empresa_id, mixin_host.get_empresa_id())
        self.assertEqual(context.sede_id, mixin_host.get_sede_id())
        self.assertEqual(context.tenant_schema, self.tenant.schema_name)
        self.assertEqual(context.user_id, self.user.id)
        self.assertEqual(context.perfil_id, self.perfil.id)
        self.assertEqual(context.rol, "ADMIN")
        self.assertEqual(context.alcance, "EMPRESA")
        self.assertEqual(context.timezone, settings.TIME_ZONE)
        self.assertEqual(context.configuracion, {"theme": "dark"})

    def test_resolve_picks_up_active_sede_from_session_same_as_mixin(self):
        otra_sede = Sede.objects.create(empresa=self.empresa, nombre="Sucursal Norte")
        request = _build_request(self.user, self.tenant)
        request.session["sede_activa_id"] = otra_sede.id
        mixin_host = _FakeMixinHost(request)

        context = OrganizationalContext.resolve(request)

        self.assertEqual(context.sede_id, otra_sede.id)
        self.assertEqual(context.sede_id, mixin_host.get_sede_id())

    def test_resolve_raises_for_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        request = _build_request(AnonymousUser(), self.tenant)
        with self.assertRaises(OrganizationalContextError):
            OrganizationalContext.resolve(request)

    def test_area_id_is_none_by_design_no_active_area_concept_exists(self):
        """Fase 0 (documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md
        seccion 2.7) confirmo que ninguna app resuelve un 'area activa' hoy
        - este test fija ese comportamiento honesto (None), no un area
        inventada."""
        request = _build_request(self.user, self.tenant)
        context = OrganizationalContext.resolve(request)
        self.assertIsNone(context.area_id)
