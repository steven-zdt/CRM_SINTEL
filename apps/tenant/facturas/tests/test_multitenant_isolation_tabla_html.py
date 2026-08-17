"""
Aislamiento multi-tenant de la vista HTML nueva (django-tables2 + HTMX,
PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplaza la grilla Tabulator
de Facturas. No es un backfill completo de TEST-C2 para `facturas` (esa
app sigue sin `test_multitenant_isolation.py` de 3 niveles — ver Fase 7
del plan) — este archivo cubre unicamente la superficie nueva introducida
por esta fase: FacturaTableView no es un ViewSet DRF, usa SintelDSVMixin
directamente, y por eso necesita su propia verificacion.
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_multitenant_isolation_facturas_tabla_html(client, tenant1, tenant2):
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="fact_user1", email="fu1@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        Factura.objects.create(
            empresa=emp1,
            numero="FACT-TABLA-T1",
            emisor_nit=emp1.nit,
            emisor_razon_social=emp1.razon_social,
            receptor_nit="900000001",
            receptor_razon_social="Cliente Tabla Tenant Uno",
            naturaleza=Factura.Naturaleza.VENTA,
            subtotal=1000,
            impuestos=190,
            total=1190,
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="fact_user2", email="fu2@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        Factura.objects.create(
            empresa=emp2,
            numero="FACT-TABLA-T2",
            emisor_nit=emp2.nit,
            emisor_razon_social=emp2.razon_social,
            receptor_nit="900000002",
            receptor_razon_social="Cliente Tabla Tenant Dos",
            naturaleza=Factura.Naturaleza.VENTA,
            subtotal=2000,
            impuestos=380,
            total=2380,
        )

    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    resp = client.get("/ui/facturas/tabla/venta/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Cliente Tabla Tenant Uno" in body
    assert "Cliente Tabla Tenant Dos" not in body

    # Sin sesion: LoginRequiredMixin debe redirigir, no filtrar en silencio
    from django.test import Client
    anon_client = Client()
    resp = anon_client.get("/ui/facturas/tabla/venta/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
