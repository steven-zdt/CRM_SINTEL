"""
PLAN_INTER_APP_ESTABILIZACION_SSoT_RELACIONES_LOOP, Fase 7 (Tenant
Isolation + Empresa/Sede/Area) -- Hallazgo H7 (heredado del reporte de
gobernanza, `tools/organizational_governance`, finding TEST-001):
`approvals` declara `OrganizationalContextMixin` en `SolicitudAprobacion
ViewSet` pero no tenia cobertura de adopcion, a diferencia de las 13+
apps que si la tienen (ver `test_organizational_context_adoption.py` en
`cotizaciones`/`compras`/`bancos`/etc., mismo patron).

Hallazgo propio de esta app (igual que en `cotizaciones`): el ViewSet
declara `OrganizationalContextMixin` como clase base, pero
`get_queryset()` en realidad NO llama a `get_organizational_context()`
-- delega en `SolicitudAprobacionServiceMixin.get_qs_list()`, que usa
`SolicitudAprobacionSelector.get_list()` directo (via `SintelDSVMixin`).
El mixin organizacional queda declarado pero sin uso real en la ruta de
lectura. Este test no "arregla" eso (fuera de alcance de esta mision --
cambiar el mecanismo de filtrado es una decision aparte) sino que
confirma la PARIDAD: ambos mecanismos deben devolver el mismo resultado,
para que cualquier consumidor futuro pueda confiar en cualquiera de los
dos sin sorpresas.
"""

from apps.tenant.approvals.api.viewsets import SolicitudAprobacionViewSet
from apps.tenant.approvals.models import SolicitudAprobacion
from apps.tenant.approvals.services.selectors import SolicitudAprobacionSelector
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ApprovalsOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Approvals",
            nit="900000989",
            direccion="Calle 1",
        )
        self.perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA"
        )
        self.solicitud = SolicitudAprobacion.objects.create(
            empresa=self.empresa,
            tipo_documento=SolicitudAprobacion.TipoDocumento.REQUISICION,
            objeto_uuid="11111111-1111-1111-1111-111111111111",
            solicitante=self.perfil,
        )

    def test_solicitudaprobacionviewset_organizational_context_matches_the_selector_it_actually_uses(
        self,
    ):
        """`get_organizational_context()` (mixin declarado) y
        `SolicitudAprobacionSelector.get_list()` (lo que get_queryset()
        realmente usa via el ServiceMixin) deben devolver el mismo
        conjunto de IDs -- no se espera divergencia de datos, solo de
        mecanismo."""
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = SolicitudAprobacionViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(SolicitudAprobacion).values_list("id", flat=True))
        ids_selector = set(
            SolicitudAprobacionSelector.get_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.solicitud.id, ids_context)
