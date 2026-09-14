"""
Regresion (2026-09-12, hallazgo B-1, docs/remediation/AUDIT_BASELINE_20260912.md):
_BancosTableViewBase._resolver_empresa_id() (views.py) solo atrapaba
DRFValidationError, a diferencia de BaseServiceMixin._get_empresa_id_seguro()
(usado por la API de creacion), que atrapa cualquier excepcion y cae al
singleton Empresa del schema del tenant. Si get_empresa_id() fallaba por
cualquier otro motivo justo en el GET que repuebla el panel de extractos
(ej. justo despues de subir uno), la tabla server-rendered caia
silenciosamente a queryset vacio, aunque la fila existiera en BD -- mismo
sintoma reportado ("subi el extracto y no aparece").

Fix: _resolver_empresa_id() ahora atrapa cualquier excepcion y cae al
mismo fallback amplio (singleton Empresa).
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile

User = get_user_model()


@pytest.mark.django_db
def test_extractos_tabla_no_queda_vacia_si_get_empresa_id_falla_por_otro_motivo(client, tenant1):
    with schema_context(tenant1.schema_name):
        empresa = Empresa.objects.first()
        user = User.objects.create_user(username="b1_user", email="b1@t.com", password="password")
        TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user, rol="ADMIN")

        cuenta = CuentaBancaria.objects.create(
            empresa=empresa, nombre="Cuenta B1", banco="BANCOLOMBIA",
            tipo="CORRIENTE", numero="B1-001",
        )
        ExtractoBancario.objects.create(
            empresa=empresa, cuenta=cuenta, mes=1, anio=2026,
            saldo_inicial=1000, saldo_final=2000,
        )

    with schema_context(tenant1.schema_name):
        client.force_login(user)
    host = f"{tenant1.schema_name}.sintel.net.co"

    # Antes del fix: cualquier excepcion distinta de DRFValidationError
    # (ej. AttributeError, simulando una falla real de resolucion de
    # perfil/tenant_profile) hacia que _resolver_empresa_id() devolviera
    # None sin fallback, y la tabla se renderizaba vacia pese a que el
    # extracto existe en BD.
    with patch(
        "apps.tenant.api.mixins.SintelDSVMixin.get_empresa_id",
        side_effect=AttributeError("simulando fallo real de resolucion de tenant_profile"),
    ):
        resp = client.get("/ui/bancos/extractos/tabla/", HTTP_HOST=host)

    assert resp.status_code == status.HTTP_200_OK, resp.content
    body = resp.content.decode()
    assert "No hay extractos bancarios registrados" not in body, (
        "La tabla sigue cayendo a vacio cuando get_empresa_id() falla por "
        "un motivo distinto de DRFValidationError -- el fallback amplio no funciona."
    )
