"""
Test funcional de las acciones de PerfilViewSet no cubiertas por ningun test
existente (Batch 3, mision UI/UX): update, assign-rol y los guards de
seguridad de destroy() -- ninguno tenia cobertura via API antes de esta
sesion (test_models.py/test_tabla_view.py solo cubren el modelo y la grilla).

Verifica:
- PATCH /api/v1/perfil/perfiles/me/ (autoedicion)
- PATCH /api/v1/perfil/perfiles/{uuid}/assign-rol/ (solo ADMIN puede asignar)
- DELETE /api/v1/perfil/perfiles/{uuid}/ Guard 1: prohibe auto-eliminacion
- DELETE /api/v1/perfil/perfiles/{uuid}/ positivo: perfil ajeno no-admin-primario

Nota (hallazgo documentado, no corregido esta sesion -- ver checklist de la
mision): PerfilViewSet no hereda BaseTenantViewSet y su lookup acepta tanto
UUID como ID entero crudo (viola la regla "UUID lookup, not PK" de
CLAUDE.md). Estos tests usan UUID deliberadamente (el camino correcto).
"""
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class PerfilViewSetWorkspaceTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Perfil CRUD", nit="900555666", direccion="Calle 1",
        )
        # self.user ya es ADMIN + is_primary_admin=True (SintelTenantTestCase.setup_membership()).
        self.perfil_propio, _ = TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa, defaults={"rol": "ADMIN", "alcance": "EMPRESA"},
        )

        # Segundo usuario/perfil: NO admin, NO admin primario -- el caso "normal" a eliminar.
        with schema_context("public"):
            self.otro_user = User.objects.create_user(
                email="otro-perfil@test.local", username="otro-perfil", password="testpass123",
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.otro_user, rol="OPERADOR", is_primary_admin=False,
            )
        self.perfil_ajeno = TenantProfile.objects.create(
            user=self.otro_user, empresa=self.empresa, rol="OPERADOR", alcance="EMPRESA",
        )

    def test_me_patch_autoedicion(self):
        resp = self.api_client.patch(
            "/api/v1/perfil/perfiles/me/", data={"cargo": "Nuevo Cargo"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["cargo"], "Nuevo Cargo")

    def test_assign_rol_como_admin_funciona(self):
        resp = self.api_client.patch(
            f"/api/v1/perfil/perfiles/{self.perfil_ajeno.uuid}/assign-rol/",
            data={"rol": "ADMIN"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.perfil_ajeno.refresh_from_db()
        self.assertEqual(self.perfil_ajeno.rol, "ADMIN")

    def test_assign_rol_rol_invalido_es_rechazado(self):
        resp = self.api_client.patch(
            f"/api/v1/perfil/perfiles/{self.perfil_ajeno.uuid}/assign-rol/",
            data={"rol": "SUPERUSUARIO"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_destroy_auto_eliminacion_es_rechazada(self):
        """Guard 1: un usuario no puede eliminar su propio perfil, ni siquiera siendo ADMIN."""
        resp = self.api_client.delete(f"/api/v1/perfil/perfiles/{self.perfil_propio.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertTrue(TenantProfile.objects.filter(uuid=self.perfil_propio.uuid).exists())

    def test_destroy_perfil_ajeno_no_admin_primario_es_permitido(self):
        resp = self.api_client.delete(f"/api/v1/perfil/perfiles/{self.perfil_ajeno.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(TenantProfile.objects.filter(uuid=self.perfil_ajeno.uuid).exists())
