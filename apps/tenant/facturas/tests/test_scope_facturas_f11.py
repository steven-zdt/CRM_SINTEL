"""
Fase F11 (proyecto OSF), "Migrar Facturas (empresa+sede+area funcional)":
auditoria de FacturaViewSet.get_queryset() encontro que solo la accion
"list" aplicaba OrganizationalScope (F7) - retrieve/destroy/partial_update/
cambiar_estado/vincular_* solo filtraban por empresa_id, sin ningun chequeo
de sede. Un perfil alcance=SEDE podia GET/PATCH/DELETE por UUID directo una
Factura de otra sede (misma empresa) aunque el listado ya se la ocultara.

Ademas, `sede` no era editable (ausente de MANUAL_EDITABLE_FIELDS) - el DSV
de alcance ya escrito en F8 (FacturaDetailSerializer.validate()) era codigo
muerto para escritura, porque el unico camino de escritura realmente
alcanzable (Limited Edit / partial_update) nunca pasaba por ese serializer.

Este archivo cubre ambos hallazgos: aislamiento a nivel de objeto (NULL-safe,
mismo criterio de F7) y la nueva capacidad de asignar `sede` con DSV real.
"""
from rest_framework import status

from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class FacturaObjectLevelScopeF11Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test F11", nit="900000786", direccion="Calle 1",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A F11")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B F11")

    def _crear_factura(self, numero, sede=None):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1,
            fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit=self.empresa.nit, emisor_razon_social=self.empresa.razon_social,
            receptor_nit="123", receptor_razon_social="Cliente F11",
            sede=sede,
        )

    def _asignar_perfil_sede(self, sedes):
        perfil = TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="SEDE",
        )
        perfil.sedes_asignadas.set(sedes)
        return perfil

    def test_alcance_sede_no_puede_ver_factura_de_otra_sede_por_uuid_directo(self):
        factura_b = self._crear_factura("FA-F11-B", sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/facturas/{factura_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_alcance_sede_puede_ver_factura_sin_sede_null_safe(self):
        factura_sin = self._crear_factura("FA-F11-SIN")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.get(f"/api/v1/facturas/{factura_sin.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_alcance_sede_no_puede_eliminar_factura_de_otra_sede(self):
        factura_b = self._crear_factura("FA-F11-DEL-B", sede=self.sede_b)
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.delete(f"/api/v1/facturas/{factura_b.uuid}/")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)
        self.assertTrue(Factura.objects.filter(id=factura_b.id).exists())

    def test_asignar_sede_dentro_de_alcance_permite_patch(self):
        factura = self._crear_factura("FA-F11-PATCH-1")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/facturas/{factura.uuid}/",
            data={"sede": str(self.sede_a.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        factura.refresh_from_db()
        self.assertEqual(factura.sede_id, self.sede_a.id)
        self.assertEqual(resp.data.get("sede_nombre"), self.sede_a.nombre)

    def test_asignar_sede_fuera_de_alcance_rechaza_patch(self):
        factura = self._crear_factura("FA-F11-PATCH-2")
        self._asignar_perfil_sede([self.sede_a])

        resp = self.api_client.patch(
            f"/api/v1/facturas/{factura.uuid}/",
            data={"sede": str(self.sede_b.uuid)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        factura.refresh_from_db()
        self.assertIsNone(factura.sede_id)

    def test_alcance_empresa_puede_ver_y_editar_cualquier_sede(self):
        factura_b = self._crear_factura("FA-F11-EMP-B", sede=self.sede_b)
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")

        resp_get = self.api_client.get(f"/api/v1/facturas/{factura_b.uuid}/")
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK, resp_get.content)

        resp_patch = self.api_client.patch(
            f"/api/v1/facturas/{factura_b.uuid}/",
            data={"sede": str(self.sede_a.uuid)},
            format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK, resp_patch.content)
