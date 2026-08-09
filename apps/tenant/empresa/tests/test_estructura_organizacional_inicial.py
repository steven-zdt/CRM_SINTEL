"""
Tests de asegurar_estructura_organizacional_inicial (ADR-003, extendida en
Fase F4 del proyecto OSF).

Cubre el hallazgo real de F4: la version original solo verificaba "la
empresa ya tiene alguna Sede" para decidir si saltarse todo el seed - una
empresa con Sede pero sin ninguna Area (creada por otra via, ej. CRUD manual)
nunca recibia su Area "General". Confirmado empiricamente contra los 3
tenants reales del entorno de desarrollo (`shelltest1` tenia 1 Sede y 0 Area)
antes de corregir la funcion.
"""
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.empresa.services.business_service import (
    asegurar_estructura_organizacional_inicial,
)
from tests.tenant.base_test import SintelTenantTestCase


class AsegurarEstructuraOrganizacionalInicialTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F4", nit="900000333", direccion="Calle 1",
        )

    def test_empresa_sin_ninguna_sede_crea_principal_y_general(self):
        Sede.objects.filter(empresa=self.empresa).delete()

        sede = asegurar_estructura_organizacional_inicial(self.empresa)

        self.assertEqual(sede.nombre, "Principal")
        self.assertTrue(Area.objects.filter(sede=sede, nombre="General").exists())

    def test_empresa_con_sede_pero_sin_area_crea_solo_el_area_faltante(self):
        """Fix de F4: no basta con 'ya tiene una Sede' para saltarse todo -
        una Sede huerfana (sin Area) debe recibir su Area 'General', sin
        crear una segunda Sede."""
        Sede.objects.filter(empresa=self.empresa).delete()
        sede_existente = Sede.objects.create(empresa=self.empresa, nombre="Bodega Central")

        sede = asegurar_estructura_organizacional_inicial(self.empresa)

        self.assertEqual(sede.id, sede_existente.id)
        self.assertEqual(Sede.objects.filter(empresa=self.empresa).count(), 1)
        self.assertTrue(Area.objects.filter(sede=sede_existente, nombre="General").exists())

    def test_empresa_con_sede_y_area_es_no_op(self):
        Sede.objects.filter(empresa=self.empresa).delete()
        sede_existente = Sede.objects.create(empresa=self.empresa, nombre="Principal")
        Area.objects.create(
            empresa=self.empresa, sede=sede_existente, nombre="General", codigo_funcionamiento="GEN",
        )

        sede = asegurar_estructura_organizacional_inicial(self.empresa)

        self.assertEqual(sede.id, sede_existente.id)
        self.assertEqual(Area.objects.filter(sede=sede_existente).count(), 1)
