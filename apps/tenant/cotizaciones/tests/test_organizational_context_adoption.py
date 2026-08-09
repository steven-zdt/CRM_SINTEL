"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 13/14: adopcion de OrganizationalContextMixin por ProductoViewSet/
ServicioViewSet/CotizacionViewSet/CotizacionItemViewSet.

Hallazgo propio de esta app (no en las anteriores): CotizacionViewSet.
get_queryset() SI usa la SSoT (SintelDSVMixin - misma que
OrganizationalContext.resolve() duplica), pero exportar_pdf()/
render_offcanvas_crear()/render_offcanvas_editar() usan
resolve_tenant_empresa() (mecanismo mas permisivo, sin exigir
TenantProfile) - una inconsistencia interna real dentro de la MISMA
ViewSet.
"""
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.cotizaciones.api.viewsets import CotizacionViewSet
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services.selectors import CotizacionSelector
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class CotizacionesOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Cotizaciones", nit="900000988", direccion="Calle 1",
        )
        self.cotizacion = Cotizacion.objects.create(
            empresa=self.empresa, numero_cotizacion="COT-F9-1", fecha_vencimiento="2026-12-31",
        )

    def test_cotizacionviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        """get_queryset() usa la SSoT - se espera paridad, no divergencia,
        para esa ruta especifica (exportar_pdf/render_offcanvas_* son un
        hallazgo aparte, documentado pero no cubierto por test dedicado
        porque no involucran OrganizationalContext directamente)."""
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = CotizacionViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(Cotizacion).values_list("id", flat=True))
        ids_selector = set(
            CotizacionSelector.get_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.cotizacion.id, ids_context)
