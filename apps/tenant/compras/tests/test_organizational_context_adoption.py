"""
Fase 9 (proyecto OCF, documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md),
app 7/14: adopcion de OrganizationalContextMixin por OrdenCompraViewSet/
PlantillaOrdenCompraViewSet.

Caso distinto a las 6 apps anteriores de esta fase: compras (piloto
ADR-003) SI hereda SintelDSVMixin, la misma SSoT que
OrganizationalContext.resolve() duplica (Fase 2) - no hay divergencia de
mecanismo aqui. Lo que se prueba en esta app es esa PARIDAD (no una
divergencia), y que get_queryset() sigue sin migrarse por una razon
distinta: get_qs_list() ya hace un filtro sede-aware mas especifico
(alcance SEDE/AREA) que el generico context.filter().
"""
from apps.tenant.compras.api.viewsets import OrdenCompraViewSet
from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.selectors import OrdenCompraSelector
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.empresa.models import Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class ComprasOrganizationalContextAdoptionTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase9 Compras", nit="900000993", direccion="Calle 1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal Fase9 Compras")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Fase9 Compras", numero_documento="777", tipo_documento="NIT",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla Fase9", prefijo="OCF9",
            rango_desde=1, rango_hasta=100, consecutivo_actual=1, vigente=True,
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede, proveedor=self.proveedor,
            plantilla=self.plantilla, fecha="2026-06-01", consecutivo=1,
        )

    def test_ordencompraviewset_get_organizational_context_matches_the_ssot_it_already_used(self):
        """A diferencia de empresa/clientes/proveedores/inventario/ventas,
        aqui NO se espera divergencia: OrdenCompraViewSet ya usa
        SintelDSVMixin.get_empresa_id()/get_sede_id() (ADR-003), la misma
        SSoT que OrganizationalContext.resolve() duplica intencionalmente."""
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken

        factory = APIRequestFactory()
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        request.tenant = self.tenant

        view = OrdenCompraViewSet()
        view.request = request
        request.user, _ = JWTAuthentication().authenticate(request)

        context = view.get_organizational_context()

        # Paridad directa contra la SSoT que este ViewSet ya usaba:
        self.assertEqual(context.empresa_id, view.get_empresa_id())

        ids_context = set(context.filter(OrdenCompra).values_list("id", flat=True))
        ids_selector = set(
            OrdenCompraSelector.get_list(self.empresa.id).values_list("id", flat=True)
        )
        self.assertEqual(ids_context, ids_selector)
        self.assertIn(self.orden.id, ids_context)
