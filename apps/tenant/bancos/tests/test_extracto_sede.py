"""
BAN-11 (.agent/AUDITORIA_FLUJO_COMPLETO.md §10, patron DT-SEDE-01): campo
`sede` FK opcional en ExtractoBancario para KPIs por sede -- mismo patron ya
usado en gastos.DocumentoSoporte.sede.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class ExtractoBancarioSedeTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa BAN-11", nit="900000812", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta BAN-11", banco="Banco Test",
            tipo="AHORROS", numero="BAN11-1",
        )
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Sede BAN-11")

    def test_crear_extracto_con_sede_de_la_misma_empresa(self):
        resp = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {
                "cuenta": str(self.cuenta.uuid), "mes": 6, "anio": 2026,
                "sede": str(self.sede.uuid),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        extracto = ExtractoBancario.objects.get(uuid=resp.data["uuid"])
        self.assertEqual(extracto.sede_id, self.sede.id)

    def test_crear_extracto_sin_sede_sigue_funcionando(self):
        """Sede es opcional -- no debe romper el flujo existente sin sede."""
        resp = self.api_client.post(
            "/api/v1/bancos/extractos/",
            {"cuenta": str(self.cuenta.uuid), "mes": 8, "anio": 2026},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        extracto = ExtractoBancario.objects.get(uuid=resp.data["uuid"])
        self.assertIsNone(extracto.sede_id)


def _crear_admin_con_membresia(tenant, username, email):
    """Mismo helper que test_cross_tenant_isolation.py: usuario ADMIN con
    TenantProfile + TenantMembership en el tenant dado."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="x")
        TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN", alcance="EMPRESA")
    with schema_context("public"):
        TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN", is_active=True)
    return user


def _jwt_bearer(user):
    return "Bearer " + str(RefreshToken.for_user(user).access_token)


@pytest.mark.django_db
def test_crear_extracto_con_sede_de_otro_tenant_es_rechazado(tenant1, tenant2):
    """Empresa es singleton por schema -- el escenario real de 'sede de otra
    empresa' es una sede de OTRO tenant (schema distinto). Al estar los
    schemas fisicamente aislados, el UUID de esa sede ni siquiera resuelve
    en el schema de tenant1 (aislamiento mas fuerte que una comparacion
    empresa_id en el mismo schema)."""
    user1 = _crear_admin_con_membresia(tenant1, "sede_user1", "sede_u1@t.com")

    with schema_context(tenant2.schema_name):
        empresa2 = Empresa.objects.first()
        sede_tenant2 = Sede.objects.create(empresa=empresa2, nombre="Sede de Tenant 2")

    with schema_context(tenant1.schema_name):
        empresa1 = Empresa.objects.first()
        cuenta1 = CuentaBancaria.objects.create(
            empresa=empresa1, nombre="Cuenta Tenant1", banco="Banco Test",
            tipo="AHORROS", numero="T1-SEDE-1",
        )

    client = APIClient(HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    client.credentials(HTTP_AUTHORIZATION=_jwt_bearer(user1))

    resp = client.post(
        "/api/v1/bancos/extractos/",
        {"cuenta": str(cuenta1.uuid), "mes": 9, "anio": 2026, "sede": str(sede_tenant2.uuid)},
        format="json",
    )
    # NOTA: create() de ExtractoBancarioViewSet envuelve serializer.is_valid()
    # en un try/except que delega a handle_service_error() -- mismo mapeo a
    # 422 (no 400) ya documentado para otros errores de validacion en este
    # ViewSet (ver test_remediation_p1_04_fecha_pago_vs_documento.py).
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
        f"Una sede de otro tenant nunca debe poder asignarse a un extracto "
        f"(status={resp.status_code}, body={resp.content[:300]})"
    )
    with schema_context(tenant1.schema_name):
        assert not ExtractoBancario.objects.filter(mes=9, anio=2026).exists()
