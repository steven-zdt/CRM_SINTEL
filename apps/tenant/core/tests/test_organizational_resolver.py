"""
Tests del "Organizational Resolver" (Fase 3, proyecto OCF).

Prueba que OrganizationalContext se integra correctamente con los puntos de
entrada pedidos por la fase, sin introducir middleware nuevo (decision ya
tomada en ADR-003/ADR-004):
  - JWT: round-trip HTTP real con Bearer token (rest_framework_simplejwt) -
    no depende de sesion/cookies, asi que no puede verse afectado por el bug
    preexistente de force_login (Fase 0, riesgo R-6).
  - Session (equivalente probado): APIClient.force_authenticate(), mismo
    mecanismo que ya usa SintelTenantTestCase.api_client en el resto del
    proyecto - evita depender del round-trip de cookies real, que si esta
    afectado por R-6.
  - DRF: ContextoOrganizacionalView (APIView) via ambos mecanismos arriba.
  - HTMX / vista plana no-DRF: OrganizationalContextMixin usado por una
    vista Django comun (no APIView), igual que la usarian
    OrdenCompraTableView/FacturaTableView si lo adoptaran.
  - Middleware: implicito en el round-trip JWT real (pasa por
    TenantMainMiddleware/AuthenticationMiddleware sin cambios).
"""
from django.http import JsonResponse
from django.test import RequestFactory
from django.views import View
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenant.core.services.organizational_context import (
    OrganizationalContext,
    OrganizationalContextMixin,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


def _jwt_bearer(user) -> str:
    return "Bearer " + str(RefreshToken.for_user(user).access_token)


class _PlainHtmxStyleView(OrganizationalContextMixin, View):
    """Vista Django comun (no DRF) - simula como OrdenCompraTableView/
    FacturaTableView (que ya usan SintelDSVMixin sin heredar de DRF)
    adoptarian OrganizationalContextMixin en una fase futura."""

    def get(self, request, *args, **kwargs):
        context = self.get_organizational_context()
        return JsonResponse(context.to_dict())


class OrganizationalResolverIntegrationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase3", nit="900000222", direccion="Calle 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal")
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

    def test_contexto_endpoint_via_jwt_real_http_roundtrip(self):
        """Integracion con JWT + Middleware: round-trip HTTP real (no
        RequestFactory), pasando por TenantMainMiddleware/AuthenticationMiddleware
        sin cambios, autenticado solo con un Bearer token."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        client.credentials(HTTP_AUTHORIZATION=_jwt_bearer(self.user))

        resp = client.get("/api/v1/core/contexto/")

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["empresa_id"], self.empresa.id)
        self.assertEqual(data["sede_id"], self.sede.id)
        self.assertEqual(data["rol"], "ADMIN")
        self.assertEqual(data["alcance"], "EMPRESA")
        self.assertEqual(data["tenant_schema"], self.tenant.schema_name)

    def test_contexto_endpoint_via_session_equivalent_force_authenticate(self):
        """Integracion con Session (via force_authenticate, mismo mecanismo
        que self.api_client ya usa en todo el proyecto - evita el bug
        preexistente de cookies/force_login, Fase 0 riesgo R-6)."""
        resp = self.api_client.get("/api/v1/core/contexto/")

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["empresa_id"], self.empresa.id)
        self.assertEqual(data["sede_id"], self.sede.id)

    def test_organizational_context_mixin_works_in_plain_non_drf_view(self):
        """Integracion con HTMX / vistas server-rendered: el mismo mixin
        funciona identico en una vista Django comun (no APIView/ViewSet),
        sin ninguna dependencia de DRF."""
        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()

        response = _PlainHtmxStyleView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertEqual(data["empresa_id"], self.empresa.id)
        self.assertEqual(data["sede_id"], self.sede.id)

    def test_contexto_endpoint_incluye_scope_plural_ademas_del_contexto_singular(self):
        """[OSF Fase F3] El endpoint que el Workspace consulta al cargar
        tras el login ahora tambien resuelve OrganizationalScope: la cadena
        ROL->ALCANCE->SEDE/S->AREA/S que pide la fase necesita el conjunto
        PLURAL, no solo la sede activa que ya devolvia `sede_id`."""
        otra_sede = Sede.objects.create(empresa=self.empresa, nombre="Sucursal Sur")
        self.perfil.alcance = "SEDE"
        self.perfil.save(update_fields=["alcance"])
        self.perfil.sedes_asignadas.set([self.sede, otra_sede])

        resp = self.api_client.get("/api/v1/core/contexto/")

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        # Contexto (OCF): una sola sede activa (fallback a la primera por nombre).
        self.assertEqual(data["sede_id"], self.sede.id)
        # Scope (OSF F3): el conjunto COMPLETO de sedes asignadas, no una sola.
        self.assertEqual(
            set(data["scope"]["sede_ids"]), {self.sede.id, otra_sede.id},
        )
        self.assertEqual(data["scope"]["empresa_id"], self.empresa.id)
        self.assertEqual(data["scope"]["alcance"], "SEDE")
        self.assertIsNone(data["scope"]["area_ids"])

    def test_contexto_endpoint_scope_sin_restriccion_para_alcance_empresa(self):
        resp = self.api_client.get("/api/v1/core/contexto/")

        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIsNone(data["scope"]["sede_ids"])
        self.assertIsNone(data["scope"]["area_ids"])

    def test_mixin_caches_context_within_same_request(self):
        """get_organizational_context() no debe re-resolver en cada
        llamada dentro del mismo request/instancia - una sola resolucion
        por request, tal como pide la Fase 2."""
        request = RequestFactory().get("/")
        request.user = self.user
        request.tenant = self.tenant
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()

        host = _PlainHtmxStyleView()
        host.request = request
        first = host.get_organizational_context()
        second = host.get_organizational_context()
        self.assertIs(first, second)
        self.assertIsInstance(first, OrganizationalContext)
