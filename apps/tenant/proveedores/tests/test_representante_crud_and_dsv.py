"""PROVEEDORES-01: cobertura de Representante (gap identificado en la
auditoria -- la feature (modelo + services + 5 endpoints + UI) no tenia
ningun test dedicado).

Cubre lo que test_proveedores_api_and_service.py / test_idempotence_v2614.py
NO cubren para esta entidad: CRUD completo a nivel de servicio (DSV
explicito), unicidad de documento por proveedor, regla de negocio "no se
puede eliminar el unico representante principal", y CRUD real via HTTP
sobre RepresentanteViewSet.
"""
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import Proveedor, Representante
from apps.tenant.proveedores.services.business_service import RepresentanteBusinessService
from tests.tenant.base_test import SintelTenantTestCase


class RepresentanteServiceCRUDTests(SintelTenantTestCase):
    """CRUD + DSV a nivel de servicio (RepresentanteBusinessService)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Representantes", nit="900111222", direccion="Calle 1",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Uno", numero_documento="800111222", tipo_documento="NIT",
        )
        self.service = RepresentanteBusinessService()

    def test_crear_representante_ok(self):
        rep = self.service.crear_representante(
            empresa_id=self.empresa.id,
            proveedor_uuid=str(self.proveedor.uuid),
            data={
                "tipo_documento": "CC", "numero_documento": "1010101010",
                "nombre_completo": "Juan Perez", "cargo": "Representante Legal",
                "es_principal": True,
            },
        )
        self.assertEqual(rep.proveedor_id, self.proveedor.id)
        self.assertEqual(rep.empresa_id, self.empresa.id)
        self.assertTrue(rep.es_principal)

    def test_crear_representante_dsv_proveedor_inexistente_en_la_empresa_falla(self):
        """DSV 2 (crear_representante): el proveedor_uuid debe existir Y
        pertenecer a empresa_id. Solo puede existir 1 Empresa por schema de
        tenant (constraint singleton_key) -- el escenario real de "proveedor
        de OTRO tenant" resuelve al mismo path de codigo (0 filas al filtrar
        por empresa_id+uuid), reproducido aqui con un UUID que no existe."""
        import uuid as uuid_lib
        with self.assertRaises(ValidationError):
            self.service.crear_representante(
                empresa_id=self.empresa.id,
                proveedor_uuid=str(uuid_lib.uuid4()),
                data={"tipo_documento": "CC", "numero_documento": "222", "nombre_completo": "X"},
            )

    def test_crear_representante_empresa_inexistente_falla(self):
        with self.assertRaises(ValidationError):
            self.service.crear_representante(
                empresa_id=999999,
                proveedor_uuid=str(self.proveedor.uuid),
                data={"tipo_documento": "CC", "numero_documento": "333", "nombre_completo": "X"},
            )

    def test_unicidad_documento_por_proveedor(self):
        self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "4040404040", "nombre_completo": "A"},
        )
        with self.assertRaises(ValidationError):
            self.service.crear_representante(
                empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
                data={"tipo_documento": "CC", "numero_documento": "4040404040", "nombre_completo": "B"},
            )

    def test_mismo_documento_en_proveedores_distintos_no_colisiona(self):
        proveedor2 = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Dos", numero_documento="800222333", tipo_documento="NIT",
        )
        self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "5050505050", "nombre_completo": "A"},
        )
        # mismo numero_documento, proveedor distinto -> permitido
        rep2 = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(proveedor2.uuid),
            data={"tipo_documento": "CC", "numero_documento": "5050505050", "nombre_completo": "B"},
        )
        self.assertEqual(rep2.proveedor_id, proveedor2.id)

    def test_actualizar_representante_ok(self):
        rep = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "6060606060", "nombre_completo": "Original"},
        )
        actualizado = self.service.actualizar_representante(
            empresa_id=self.empresa.id, representante_uuid=str(rep.uuid),
            data={"nombre_completo": "Actualizado"},
        )
        self.assertEqual(actualizado.nombre_completo, "Actualizado")

    def test_actualizar_representante_inexistente_falla(self):
        import uuid as uuid_lib
        with self.assertRaises(ValidationError):
            self.service.actualizar_representante(
                empresa_id=self.empresa.id, representante_uuid=str(uuid_lib.uuid4()),
                data={"nombre_completo": "X"},
            )

    def test_eliminar_representante_no_principal_ok(self):
        self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "7070707070", "nombre_completo": "Principal", "es_principal": True},
        )
        secundario = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "7070707071", "nombre_completo": "Secundario", "es_principal": False},
        )
        self.service.eliminar_representante(empresa_id=self.empresa.id, representante_uuid=str(secundario.uuid))
        self.assertEqual(Representante.objects.filter(empresa=self.empresa, proveedor=self.proveedor).count(), 1)

    def test_no_se_puede_eliminar_el_unico_principal(self):
        rep = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "8080808080", "nombre_completo": "Unico", "es_principal": True},
        )
        with self.assertRaises(ValidationError):
            self.service.eliminar_representante(empresa_id=self.empresa.id, representante_uuid=str(rep.uuid))
        self.assertTrue(Representante.objects.filter(uuid=rep.uuid).exists())

    def test_se_puede_eliminar_principal_si_hay_otro_principal(self):
        principal1 = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "9090909090", "nombre_completo": "P1", "es_principal": True},
        )
        self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "9090909091", "nombre_completo": "P2", "es_principal": True},
        )
        # ambos son_principal=True (el modelo no exige un unico principal a nivel
        # de constraint) -- eliminar uno no deja el proveedor sin principal.
        self.service.eliminar_representante(empresa_id=self.empresa.id, representante_uuid=str(principal1.uuid))
        self.assertFalse(Representante.objects.filter(uuid=principal1.uuid).exists())


class RepresentanteHTTPTests(SintelTenantTestCase):
    """CRUD real via HTTP sobre RepresentanteViewSet (/api/v1/proveedores/representantes/)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Representantes HTTP", nit="900555666", direccion="Calle 1",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor HTTP", numero_documento="800555666", tipo_documento="NIT",
        )
        # IsTenantAdminOrReadOnly exige TenantProfile.rol == ADMIN dentro del
        # schema del tenant -- distinto de TenantMembership (public schema),
        # que SintelTenantTestCase.setup_membership() ya crea pero no basta.
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa, defaults={"rol": "ADMIN", "alcance": "EMPRESA"},
        )

    def test_create_list_update_delete_representante_http(self):
        # CREATE
        resp = self.api_client.post(
            "/api/v1/proveedores/representantes/",
            data={
                "proveedor_uuid": str(self.proveedor.uuid),
                "tipo_documento": "CC", "numero_documento": "1111111111",
                "nombre_completo": "Rep HTTP", "cargo": "Gerente", "es_principal": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        rep_uuid = resp.json()["uuid"]

        # LIST filtrado por proveedor_uuid
        resp = self.api_client.get(f"/api/v1/proveedores/representantes/?proveedor_uuid={self.proveedor.uuid}")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) and "results" in body else body
        self.assertTrue(any(r["uuid"] == rep_uuid for r in rows))

        # UPDATE
        resp = self.api_client.patch(
            f"/api/v1/proveedores/representantes/{rep_uuid}/",
            data={"nombre_completo": "Rep HTTP Editado"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["nombre_completo"], "Rep HTTP Editado")

        # DELETE (unico principal -> el service lo rechaza, 400)
        resp = self.api_client.delete(f"/api/v1/proveedores/representantes/{rep_uuid}/")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertTrue(Representante.objects.filter(uuid=rep_uuid).exists())

    def test_create_representante_sin_proveedor_uuid_es_400(self):
        resp = self.api_client.post(
            "/api/v1/proveedores/representantes/",
            data={"tipo_documento": "CC", "numero_documento": "222", "nombre_completo": "X"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_puede_editar_representante_inexistente(self):
        """DSV real (RepresentanteBusinessService.actualizar_representante via
        RepresentanteSelector.get_by_uuid filtrado por empresa_id): un UUID
        que no corresponde a ningun representante de la empresa es rechazado
        (400), nunca 200/500. Solo puede existir 1 Empresa por schema de
        tenant (constraint singleton_key) -- el aislamiento cross-tenant
        genuino (2 schemas reales) ya se prueba en
        test_cuentas_pagar_isolation_and_abono.py; este test cubre el mismo
        path de codigo (DSV: 0 filas al filtrar por empresa_id+uuid)."""
        import uuid as uuid_lib
        resp = self.api_client.patch(
            f"/api/v1/proveedores/representantes/{uuid_lib.uuid4()}/",
            data={"nombre_completo": "Hackeado"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
