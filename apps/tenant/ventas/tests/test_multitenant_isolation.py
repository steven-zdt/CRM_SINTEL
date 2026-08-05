import pytest
from django_tenants.utils import schema_context
from rest_framework import status
from apps.tenant.ventas.models import Venta
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.public.tenants.models import TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_multitenant_isolation_ventas(client, tenant1, tenant2):
    """
    [TEST-C1] Verifica los 3 niveles de aislamiento multi-tenant obligatorios
    (AGENTS.md 24.5) para la app ventas -- previamente sin ningun test.
    Patron: apps/tenant/gastos/tests/test_multitenant_isolation.py
    """
    # 1. Setup Tenant 1
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="user1_ventas", email="u1@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")

        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        cliente1 = Cliente.objects.create(
            empresa=emp1,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="9001",
            razon_social="Cliente Tenant 1 SAS",
            regimen_tributario="ORDINARIO",
        )

        venta1 = Venta.objects.create(
            empresa=emp1,
            cliente=cliente1,
            fecha_emision="2026-06-01",
            numero_factura="VENTA-T1-TEST",
            subtotal="100.00",
            total_neto="100.00",
        )

    # 2. Setup Tenant 2
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user2_ventas", email="u2@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")

        with schema_context('public'):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        cliente2 = Cliente.objects.create(
            empresa=emp2,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="9002",
            razon_social="Cliente Tenant 2 SAS",
            regimen_tributario="ORDINARIO",
        )

        # Varias ventas dummy para asegurar que venta2.id/uuid no coincidan por casualidad con T1
        for i in range(5):
            Venta.objects.create(
                empresa=emp2,
                cliente=cliente2,
                fecha_emision="2026-06-01",
                numero_factura=f"VENTA-T2-DUMMY-{i}",
                subtotal="10.00",
                total_neto="10.00",
            )

        venta2 = Venta.objects.create(
            empresa=emp2,
            cliente=cliente2,
            fecha_emision="2026-06-01",
            numero_factura="VENTA-T2-TEST",
            subtotal="200.00",
            total_neto="200.00",
        )

    # --- NIVEL 1: Aislamiento en listado ---
    client.force_login(user1)
    resp = client.get("/api/v1/ventas/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    numeros = [item["numero_factura"] for item in resp.json().get("results", [])]
    assert "VENTA-T1-TEST" in numeros
    assert "VENTA-T2-TEST" not in numeros

    # --- NIVEL 2: Prevencion de IDOR (acceso directo por UUID de otro tenant) ---
    resp = client.get(
        f"/api/v1/ventas/{venta2.uuid}/",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # --- NIVEL 3: Prevencion de IDOR en FKs (cliente de otro tenant en payload) ---
    payload = {
        "cliente": str(cliente2.uuid),  # Cliente VALIDO pero pertenece a tenant2
        "fecha_emision": "2026-06-10",
        "items": [
            {"descripcion": "Intento IDOR", "cantidad": "1", "precio_unitario": "50.00"},
        ],
    }
    resp = client.post(
        "/api/v1/ventas/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    # VentaBusinessService._dsv_cliente rechaza con ValueError -> 400 (ver
    # crear_venta_borrador en apps/tenant/ventas/services/business_service.py)
    assert resp.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )
    assert venta1.numero_factura == "VENTA-T1-TEST"  # sanity: setup de T1 no fue alterado


@pytest.mark.django_db
def test_multitenant_isolation_ventas_tabla_html(client, tenant1, tenant2):
    """
    Aislamiento multi-tenant de la vista HTML nueva (django-tables2 + HTMX,
    PLAN_UNICO_CORRECCIONES.md Fase 5-BIS) que reemplaza la grilla Tabulator
    de listado de Ventas. Esta vista no pasa por DRF (no es un ViewSet) --
    usa SintelDSVMixin directamente, asi que necesita su propia verificacion,
    no basta con la cobertura ya existente sobre /api/v1/ventas/.
    """
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="user1_ventas_tabla", email="u1vt@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        cliente1 = Cliente.objects.create(
            empresa=emp1, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="9101", razon_social="Cliente Tabla Tenant Uno",
            regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=emp1, cliente=cliente1, fecha_emision="2026-06-01",
            numero_factura="VENTA-TABLA-T1", subtotal="100.00", total_neto="100.00",
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user2_ventas_tabla", email="u2vt@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        cliente2 = Cliente.objects.create(
            empresa=emp2, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="9102", razon_social="Cliente Tabla Tenant Dos",
            regimen_tributario="ORDINARIO",
        )
        Venta.objects.create(
            empresa=emp2, cliente=cliente2, fecha_emision="2026-06-01",
            numero_factura="VENTA-TABLA-T2", subtotal="200.00", total_neto="200.00",
        )

    client.force_login(user1)
    resp = client.get("/ui/ventas/tabla/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "Cliente Tabla Tenant Uno" in body
    assert "Cliente Tabla Tenant Dos" not in body

    # Sin sesion: debe redirigir a login (LoginRequiredMixin), no filtrar en silencio
    from django.test import Client
    anon_client = Client()
    resp = anon_client.get("/ui/ventas/tabla/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
