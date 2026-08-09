"""
Tests de OrganizationalScope (Fase F2, proyecto OSF).

Cubren, en este orden:
  1. Resolucion basica (alcance EMPRESA -> sin restriccion).
  2. Resolucion con alcance SEDE/AREA -> conjuntos completos, no una sola
     "activa".
  3. La distincion real con OrganizationalContext: un perfil asignado a
     varias sedes ve TODAS en OrganizationalScope.filter() pero solo la
     activa en OrganizationalContext.filter() - esto es lo que justifica que
     ambos conceptos existan por separado (ver docstring del modulo).
"""
from django.test import RequestFactory

from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.core.services.organizational_scope import (
    OrganizationalScope,
    OrganizationalScopeError,
    area_esta_en_alcance,
    sede_esta_en_alcance,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


def _build_request(user, tenant):
    from django.contrib.sessions.backends.db import SessionStore

    request = RequestFactory().get("/")
    request.user = user
    request.tenant = tenant
    request.session = SessionStore()
    return request


class OrganizationalScopeTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OSF", nit="900000222", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B")

    def test_alcance_empresa_no_restringe(self):
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        request = _build_request(self.user, self.tenant)

        scope = OrganizationalScope.resolve(request)

        self.assertEqual(scope.empresa_id, self.empresa.id)
        self.assertEqual(scope.alcance, "EMPRESA")
        self.assertIsNone(scope.sede_ids)
        self.assertIsNone(scope.area_ids)
        self.assertTrue(scope.permits_sede(self.sede_a.id))
        self.assertTrue(scope.permits_sede(None))

    def test_alcance_sede_resuelve_conjunto_completo_no_una_sola_activa(self):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])
        request = _build_request(self.user, self.tenant)

        scope = OrganizationalScope.resolve(request)

        self.assertEqual(scope.sede_ids, frozenset({self.sede_a.id, self.sede_b.id}))
        self.assertTrue(scope.permits_sede(self.sede_a.id))
        self.assertTrue(scope.permits_sede(self.sede_b.id))

    def test_alcance_sede_sin_asignaciones_restringe_a_nada_no_a_todo(self):
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        request = _build_request(self.user, self.tenant)

        scope = OrganizationalScope.resolve(request)

        self.assertEqual(scope.sede_ids, frozenset())
        self.assertFalse(scope.permits_sede(self.sede_a.id))

    def test_context_active_sede_vs_scope_full_set_es_la_distincion_real(self):
        """Pinning del hallazgo documentado en el modulo: con un perfil
        asignado a 2 sedes y la sede activa en sesion apuntando a una sola,
        OrganizationalContext.filter() ve solo la activa mientras que
        OrganizationalScope.filter() ve las 2 asignadas - por eso no son el
        mismo contrato y no deben fusionarse."""
        from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
        from apps.tenant.proveedores.models import Proveedor

        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a, self.sede_b])

        proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Test F2", numero_documento="F2-1", tipo_documento="NIT",
        )
        plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla F2", prefijo="OSF2",
            rango_desde=1, rango_hasta=100, consecutivo_actual=1, vigente=True,
        )
        orden_a = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_a, proveedor=proveedor,
            plantilla=plantilla, fecha="2026-06-01", consecutivo=1,
        )
        orden_b = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_b, proveedor=proveedor,
            plantilla=plantilla, fecha="2026-06-01", consecutivo=2,
        )

        request = _build_request(self.user, self.tenant)
        request.session["sede_activa_id"] = self.sede_a.id

        context = OrganizationalContext.resolve(request)
        scope = OrganizationalScope.resolve(request)

        context_ids = set(context.filter(OrdenCompra).values_list("id", flat=True))
        scope_ids = set(scope.filter(OrdenCompra).values_list("id", flat=True))

        self.assertEqual(context_ids, {orden_a.id})
        self.assertEqual(scope_ids, {orden_a.id, orden_b.id})

    def test_resolve_raises_for_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        request = _build_request(AnonymousUser(), self.tenant)
        with self.assertRaises(OrganizationalScopeError):
            OrganizationalScope.resolve(request)

    def test_sede_esta_en_alcance_helper_respeta_asignaciones(self):
        """[OSF Fase F8] `sede_esta_en_alcance()` es el helper que los
        serializers de facturas/cotizaciones/gastos/proyectos/empleados
        usan en su `validate()` para no permitir asignar una sede fuera del
        alcance organizacional del usuario (antes de F8 solo validaban
        'pertenece a la empresa', nunca 'esta dentro de mi alcance')."""
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="SEDE",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        request = _build_request(self.user, self.tenant)

        self.assertTrue(sede_esta_en_alcance(self.sede_a.id, request))
        self.assertFalse(sede_esta_en_alcance(self.sede_b.id, request))

    def test_sede_esta_en_alcance_degrada_a_permitir_sin_scope_resoluble(self):
        """Mismo criterio de degradacion que F5/F7: sin request o sin scope
        resoluble (usuario anonimo), no bloquear - permite."""
        self.assertTrue(sede_esta_en_alcance(self.sede_a.id, None))

        from django.contrib.auth.models import AnonymousUser
        request = _build_request(AnonymousUser(), self.tenant)
        self.assertTrue(sede_esta_en_alcance(self.sede_a.id, request))

    def test_area_esta_en_alcance_helper_respeta_asignaciones(self):
        from apps.tenant.empresa.models import Area

        area_x = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area X F8", codigo_funcionamiento="AXF8",
        )
        area_y = Area.objects.create(
            empresa=self.empresa, sede=self.sede_a, nombre="Area Y F8", codigo_funcionamiento="AYF8",
        )
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="OPERADOR", alcance="AREA",
        )
        perfil.sedes_asignadas.set([self.sede_a])
        perfil.areas_asignadas.set([area_x])
        request = _build_request(self.user, self.tenant)

        self.assertTrue(area_esta_en_alcance(area_x.id, request))
        self.assertFalse(area_esta_en_alcance(area_y.id, request))
