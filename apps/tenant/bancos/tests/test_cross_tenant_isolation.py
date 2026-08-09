"""
Regresion de seguridad: un JWT valido emitido para un tenant NUNCA debe
poder operar sobre otro tenant distinto.

Contexto (Auditoria Enterprise 2026-08-06, remediacion Fase 1):
IsTenantMember / HasTenantRole / IsTenantProfileAdmin / IsTenantProfileOperadorOrAdmin /
IsTenantAdminOrReadOnly (apps/tenant/api/permissions.py) omitian por completo la
verificacion de membresia/rol cuando settings.DEBUG=True, devolviendo True de
inmediato. Como DEBUG=True es habitual en entornos de desarrollo/demo, cualquier
JWT valido de CUALQUIER tenant era aceptado para leer/escribir datos de
CUALQUIER OTRO tenant con solo cambiar el header Host de la peticion.

CuentaBancariaViewSet (bancos) y GastoViewSet (gastos) tenian ademas su propio
bypass local en get_permissions() que devolvia [] (ni siquiera IsAuthenticated)
en DEBUG.

Este test reproduce el escenario exacto documentado en la auditoria
(documentacion/PLAN_PRUEBASUI_PRIVADAS.md, Fase 5) y debe fallar si el bypass
vuelve a introducirse en cualquiera de los dos archivos.
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import CuentaBancaria
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


def _crear_admin_con_membresia(tenant, username, email):
    """Crea un usuario ADMIN con TenantProfile + TenantMembership en el tenant dado."""
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        user = User.objects.create_user(username=username, email=email, password="x")
        TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN")
    with schema_context("public"):
        TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN", is_active=True)
    return user


def _jwt_bearer(user):
    return "Bearer " + str(RefreshToken.for_user(user).access_token)


@pytest.mark.django_db
def test_jwt_de_un_tenant_no_puede_leer_datos_de_otro_tenant(tenant1, tenant2):
    """Un JWT valido de tenant1 debe recibir 403 al consultar la API de tenant2,
    y JAMAS debe recibir los datos reales de tenant2."""
    user1 = _crear_admin_con_membresia(tenant1, "cross_user1", "u1@t.com")

    with schema_context(tenant2.schema_name):
        empresa2 = Empresa.objects.first()
        cuenta_secreta = CuentaBancaria.objects.create(
            empresa=empresa2,
            nombre="CUENTA SECRETA DE TENANT2",
            banco="BANCOLOMBIA",
            tipo="AHORROS",
            numero="999999999",
        )

    client = APIClient(HTTP_HOST=f"{tenant2.schema_name}.sintel.net.co")
    client.credentials(HTTP_AUTHORIZATION=_jwt_bearer(user1))

    resp_list = client.get("/api/v1/bancos/cuentas/")
    assert resp_list.status_code == 403, (
        f"Un JWT de tenant1 NO debe poder listar cuentas de tenant2 "
        f"(status={resp_list.status_code}, body={resp_list.content[:300]})"
    )
    assert b"CUENTA SECRETA" not in resp_list.content

    resp_detail = client.get(f"/api/v1/bancos/cuentas/{cuenta_secreta.uuid}/")
    assert resp_detail.status_code == 403, (
        f"Un JWT de tenant1 NO debe poder leer el detalle de una cuenta de tenant2 "
        f"(status={resp_detail.status_code}, body={resp_detail.content[:300]})"
    )
    assert b"CUENTA SECRETA" not in resp_detail.content


@pytest.mark.django_db
def test_jwt_de_su_propio_tenant_si_puede_leer_sus_datos(tenant1, tenant2):
    """Regresion inversa: el mismo usuario, contra SU propio tenant, debe
    seguir funcionando con normalidad tras el fix (sin falsos positivos)."""
    user1 = _crear_admin_con_membresia(tenant1, "own_user1", "own1@t.com")

    with schema_context(tenant1.schema_name):
        empresa1 = Empresa.objects.first()
        CuentaBancaria.objects.create(
            empresa=empresa1,
            nombre="Cuenta Propia de Tenant1",
            banco="DAVIVIENDA",
            tipo="CORRIENTE",
            numero="111111111",
        )

    client = APIClient(HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    client.credentials(HTTP_AUTHORIZATION=_jwt_bearer(user1))

    resp = client.get("/api/v1/bancos/cuentas/")
    assert resp.status_code == 200, (
        f"Un usuario ADMIN con membresia activa en su propio tenant debe poder "
        f"listar sus propias cuentas (status={resp.status_code}, body={resp.content[:300]})"
    )
    assert b"Cuenta Propia de Tenant1" in resp.content
