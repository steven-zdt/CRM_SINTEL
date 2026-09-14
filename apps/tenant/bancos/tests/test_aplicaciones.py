"""Fase 5-7 y Fase 33-34 (mision Bancos v3.0): MovimientoBancarioAplicacion
-- aplicar completo, parcial, multiple, no-sobreaplicar, quitar, tenant
isolation."""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class AplicacionesTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Aplicaciones", nit="900000903", direccion="Calle 1",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA")
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta Apl", banco="Banco Test",
            tipo="AHORROS", numero="APL-1",
        )
        self.extracto = ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=1, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.tx = TransaccionBancaria.objects.create(
            empresa=self.empresa, extracto=self.extracto, fecha=date(2026, 1, 10),
            descripcion="Pago combinado", valor=Decimal("1000000.00"), saldo=Decimal("1000000.00"),
        )

    def _url(self, suffix=""):
        return f"/api/v1/bancos/transacciones/{self.tx.uuid}/aplicaciones/{suffix}"

    def test_aplicar_monto_completo_marca_conciliado(self):
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "1000000.00",
            "fecha_aplicacion": "2026-01-10", "notas": "pago unico",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        self.tx.refresh_from_db()
        self.assertTrue(self.tx.conciliado)

        lista = self.api_client.get(self._url())
        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lista.data["results"]), 1)

    def test_aplicar_monto_parcial_no_marca_conciliado(self):
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "300000.00",
            "fecha_aplicacion": "2026-01-10",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.tx.refresh_from_db()
        self.assertFalse(self.tx.conciliado)

    def test_multiples_aplicaciones_suman_hasta_completar(self):
        for monto in ("400000.00", "600000.00"):
            resp = self.api_client.post(self._url(), {
                "tipo_referencia": "OTRO_EGRESO", "monto_aplicado": monto,
                "fecha_aplicacion": "2026-01-10",
            }, format="json")
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        self.tx.refresh_from_db()
        self.assertTrue(self.tx.conciliado)
        self.assertEqual(MovimientoBancarioAplicacion.objects.filter(transaccion=self.tx).count(), 2)

    def test_no_permite_sobreaplicar(self):
        self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "700000.00",
            "fecha_aplicacion": "2026-01-10",
        }, format="json")
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "400000.00",
            "fecha_aplicacion": "2026-01-10",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp.content)
        self.assertEqual(
            MovimientoBancarioAplicacion.objects.filter(transaccion=self.tx)
            .aggregate(total=Sum("monto_aplicado"))["total"],
            Decimal("700000.00"),
        )

    def test_quitar_aplicacion(self):
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "1000000.00",
            "fecha_aplicacion": "2026-01-10",
        }, format="json")
        aplicacion_uuid = resp.data["uuid"]

        resp_del = self.api_client.delete(f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/")
        self.assertEqual(resp_del.status_code, status.HTTP_204_NO_CONTENT, resp_del.content)
        self.assertFalse(MovimientoBancarioAplicacion.objects.filter(uuid=aplicacion_uuid).exists())

    def test_referencia_sin_resolver_no_bloquea_clasificacion_manual(self):
        """Fase 30: permitir tipo_referencia=OTRO con referencia_uuid=None
        para clasificar/probar sin exigir que el documento exista."""
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "OTRO", "monto_aplicado": "500000.00",
            "fecha_aplicacion": "2026-01-10", "notas": "sin clasificar aun",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertIsNone(resp.data["referencia_uuid"])

    def test_editar_monto_de_una_aplicacion_respeta_el_guard(self):
        resp = self.api_client.post(self._url(), {
            "tipo_referencia": "GASTO", "monto_aplicado": "300000.00",
            "fecha_aplicacion": "2026-01-10",
        }, format="json")
        aplicacion_uuid = resp.data["uuid"]

        resp_ok = self.api_client.patch(
            f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/", {"monto_aplicado": "900000.00"}, format="json"
        )
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK, resp_ok.content)

        resp_excede = self.api_client.patch(
            f"/api/v1/bancos/aplicaciones/{aplicacion_uuid}/", {"monto_aplicado": "1500000.00"}, format="json"
        )
        self.assertEqual(resp_excede.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, resp_excede.content)


def _crear_admin_con_membresia(tenant, username, email):
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
def test_no_cross_tenant_application(tenant1, tenant2):
    """Fase 34: un JWT valido de tenant1 no debe poder ver ni operar sobre
    una MovimientoBancarioAplicacion de tenant2."""
    user1 = _crear_admin_con_membresia(tenant1, "apl_user1", "apl1@t.com")

    with schema_context(tenant2.schema_name):
        empresa2 = Empresa.objects.first()
        cuenta2 = CuentaBancaria.objects.create(
            empresa=empresa2, nombre="Cuenta T2", banco="Banco Test", tipo="AHORROS", numero="T2-1",
        )
        extracto2 = ExtractoBancario.objects.create(
            empresa=empresa2, cuenta=cuenta2, mes=1, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        tx2 = TransaccionBancaria.objects.create(
            empresa=empresa2, extracto=extracto2, fecha=date(2026, 1, 5),
            descripcion="TX secreta tenant2", valor=Decimal("999000.00"), saldo=Decimal("999000.00"),
        )
        aplicacion2 = MovimientoBancarioAplicacion.objects.create(
            empresa=empresa2, transaccion=tx2, tipo_referencia="GASTO",
            monto_aplicado=Decimal("999000.00"), fecha_aplicacion=date(2026, 1, 5),
            notas="SECRETO TENANT2",
        )

    client = APIClient(HTTP_HOST=f"{tenant2.schema_name}.sintel.net.co")
    client.credentials(HTTP_AUTHORIZATION=_jwt_bearer(user1))

    resp_get = client.get(f"/api/v1/bancos/aplicaciones/{aplicacion2.uuid}/")
    assert resp_get.status_code in (403, 404)
    assert b"SECRETO TENANT2" not in resp_get.content

    resp_del = client.delete(f"/api/v1/bancos/aplicaciones/{aplicacion2.uuid}/")
    assert resp_del.status_code in (403, 404)
    with schema_context(tenant2.schema_name):
        assert MovimientoBancarioAplicacion.objects.filter(uuid=aplicacion2.uuid).exists()

    resp_post = client.post(
        f"/api/v1/bancos/transacciones/{tx2.uuid}/aplicaciones/",
        {"tipo_referencia": "GASTO", "monto_aplicado": "1.00", "fecha_aplicacion": "2026-01-05"},
        format="json",
    )
    assert resp_post.status_code in (403, 404)
