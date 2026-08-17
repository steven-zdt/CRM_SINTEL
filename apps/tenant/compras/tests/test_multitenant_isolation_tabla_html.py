"""
Aislamiento multi-tenant de la vista HTML nueva (django-tables2 + HTMX,
PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplaza la grilla Tabulator
de Ordenes de Compra. `compras` no tenia ningun test en
apps/tenant/compras/tests/ antes de este archivo (los existentes viven en
tests/tenant/compras/, con otro patron) — este archivo cubre unicamente la
superficie nueva de esta fase, no es el backfill completo de TEST-A1
(pendiente en Fase 7 del plan).
"""
import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.compras.models import OrdenCompra
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor

User = get_user_model()


@pytest.mark.django_db
def test_multitenant_isolation_compras_tabla_html(client, tenant1, tenant2):
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="compra_user1", email="cu1@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        sede1 = Sede.objects.create(empresa=emp1, nombre="Principal")
        prov1 = Proveedor.objects.create(empresa=emp1, razon_social="Proveedor Compras Tenant Uno", numero_documento="777", tipo_documento="NIT")
        OrdenCompra.objects.create(
            empresa=emp1, sede=sede1, proveedor=prov1, consecutivo=1, fecha="2026-05-01",
            subtotal=1000, impuestos=190, total=1190,
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="compra_user2", email="cu2@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        sede2 = Sede.objects.create(empresa=emp2, nombre="Principal")
        prov2 = Proveedor.objects.create(empresa=emp2, razon_social="Proveedor Compras Tenant Dos", numero_documento="888", tipo_documento="NIT")
        OrdenCompra.objects.create(
            empresa=emp2, sede=sede2, proveedor=prov2, consecutivo=1, fecha="2026-05-01",
            subtotal=2000, impuestos=380, total=2380,
        )

    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    resp = client.get("/ui/compras/tabla/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Proveedor Compras Tenant Uno" in body
    assert "Proveedor Compras Tenant Dos" not in body

    from django.test import Client
    anon_client = Client()
    resp = anon_client.get("/ui/compras/tabla/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
