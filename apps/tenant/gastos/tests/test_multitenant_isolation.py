import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor

User = get_user_model()


@pytest.mark.django_db
def test_multitenant_isolation_gastos(client, tenant1, tenant2):
    """
    Verifica que los datos de un tenant no sean visibles ni accesibles para otro.
    """
    # 1. Setup Tenant 1
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="user1", email="u1@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")

        # Crear membresia en publico
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        res1 = ResolucionDIAN.objects.create(
            empresa=emp1,
            numero_resolucion="RES1",
            prefijo="G1",
            rango_desde=1,
            rango_hasta=100,
            fecha_resolucion="2026-01-01",
            fecha_fin="2027-01-01",
            vigente=True,
        )

        prov1 = Proveedor.objects.create(
            empresa=emp1, razon_social="Proveedor 1", numero_documento="999", tipo_documento="NIT"
        )

        DocumentoSoporte.objects.create(
            empresa=emp1,
            resolucion_dian=res1,
            consecutivo=1,
            fecha="2026-05-01",
            proveedor=prov1,
            subtotal=1000,
            total=1000,
            descripcion="Gasto T1",
            categoria_contable="ARRENDAMIENTOS",
        )

    # 2. Setup Tenant 2
    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user2", email="u2@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")

        # Crear membresia en publico
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        # Crear varias resoluciones dummy para asegurar que res2.id sea diferente a res1.id
        for i in range(5):
            ResolucionDIAN.objects.create(
                empresa=emp2,
                numero_resolucion=f"DUMMY{i}",
                prefijo="DX",
                rango_desde=1,
                rango_hasta=10,
                fecha_resolucion="2026-01-01",
                fecha_fin="2027-01-01",
                vigente=False,
            )

        res2 = ResolucionDIAN.objects.create(
            empresa=emp2,
            numero_resolucion="RES2",
            prefijo="G2",
            rango_desde=1,
            rango_hasta=100,
            fecha_resolucion="2026-01-01",
            fecha_fin="2027-01-01",
            vigente=True,
        )

        prov2 = Proveedor.objects.create(
            empresa=emp2, razon_social="Proveedor 2", numero_documento="888", tipo_documento="NIT"
        )

        # Crear varios documentos en T2 para que g2.id sea mayor que cualquier ID en T1
        for i in range(5):
            DocumentoSoporte.objects.create(
                empresa=emp2,
                resolucion_dian=res2,
                consecutivo=10 + i,
                fecha="2026-05-01",
                proveedor=prov2,
                subtotal=100,
                total=100,
                descripcion=f"Gasto T2-{i}",
                categoria_contable="SERVICIOS_PUBLICOS",
            )

        g2 = DocumentoSoporte.objects.create(
            empresa=emp2,
            resolucion_dian=res2,
            consecutivo=20,
            fecha="2026-05-01",
            proveedor=prov2,
            subtotal=2000,
            total=2000,
            descripcion="Gasto T2",
            categoria_contable="SERVICIOS_PUBLICOS",
        )

    # 3. Validar Aislamiento en Listado
    # force_login debe escribir la sesion en el esquema del tenant: sessions
    # esta en TENANT_APPS (aislado por esquema) y la request real solo la lee
    # despues de que TenantMainMiddleware cambia de esquema (ver settings.py).
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    resp = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    results = data.get("results", [])

    ids = [item["descripcion"] for item in results]
    assert "Gasto T1" in ids
    assert "Gasto T2" not in ids

    # 4. Validar Prevencion de IDOR (Acceso Directo)
    resp = client.get(
        f"/api/v1/gastos/{g2.uuid}/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    # 5. Validar Aislamiento en Creacion (Prevencion de IDOR en FKs)
    payload = {
        "descripcion": "Intento IDOR",
        "categoria_contable": "ARRENDAMIENTOS",
        "documento_soporte": {
            "fecha": "2026-05-06",
            "subtotal": 500,
            "proveedor": prov1.id,  # Proveedor VALIDO para T1 pero...
            "resolucion": res2.id,  # Intento de usar resolucion de otro tenant
        },
    }
    resp = client.post(
        "/api/v1/gastos/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    # Debe fallar porque res2 no pertenece a la empresa de user1
    assert resp.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )


@pytest.mark.django_db
def test_multitenant_isolation_gastos_tabla_html(client, tenant1, tenant2):
    """
    Aislamiento multi-tenant del listado de Gastos: KPIs de Documentos
    Soporte (vista HTML, django-tables2 + HTMX para Resoluciones DIAN) +
    grilla de Documentos Soporte (migrada a DataTables -- POST
    /api/v1/gastos/dt/, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md).
    La vista de KPIs no pasa por DRF (no es un ViewSet) — usa SintelDSVMixin
    directamente, asi que necesita su propia verificacion, no basta con la
    cobertura ya existente sobre /api/v1/gastos/.
    """
    with schema_context(tenant1.schema_name):
        emp1 = Empresa.objects.first()
        user1 = User.objects.create_user(username="user1b", email="u1b@t.com", password="password")
        TenantProfile.objects.create(user=user1, empresa=emp1, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant1, user=user1, rol="ADMIN")

        res1 = ResolucionDIAN.objects.create(
            empresa=emp1,
            numero_resolucion="RES1B",
            prefijo="G1B",
            rango_desde=1,
            rango_hasta=100,
            fecha_resolucion="2026-01-01",
            fecha_fin="2027-01-01",
            vigente=True,
        )
        prov1 = Proveedor.objects.create(
            empresa=emp1,
            razon_social="Proveedor Tenant Uno",
            numero_documento="111",
            tipo_documento="NIT",
        )
        DocumentoSoporte.objects.create(
            empresa=emp1,
            resolucion_dian=res1,
            consecutivo=1,
            fecha="2026-05-01",
            proveedor=prov1,
            subtotal=1000,
            total=1000,
            descripcion="Gasto Tabla T1",
            categoria_contable="ARRENDAMIENTOS",
        )

    with schema_context(tenant2.schema_name):
        emp2 = Empresa.objects.first()
        user2 = User.objects.create_user(username="user2b", email="u2b@t.com", password="password")
        TenantProfile.objects.create(user=user2, empresa=emp2, rol="ADMIN")
        with schema_context("public"):
            TenantMembership.objects.create(client=tenant2, user=user2, rol="ADMIN")

        res2 = ResolucionDIAN.objects.create(
            empresa=emp2,
            numero_resolucion="RES2B",
            prefijo="G2B",
            rango_desde=1,
            rango_hasta=100,
            fecha_resolucion="2026-01-01",
            fecha_fin="2027-01-01",
            vigente=True,
        )
        prov2 = Proveedor.objects.create(
            empresa=emp2,
            razon_social="Proveedor Tenant Dos",
            numero_documento="222",
            tipo_documento="NIT",
        )
        DocumentoSoporte.objects.create(
            empresa=emp2,
            resolucion_dian=res2,
            consecutivo=1,
            fecha="2026-05-01",
            proveedor=prov2,
            subtotal=2000,
            total=2000,
            descripcion="Gasto Tabla T2",
            categoria_contable="SERVICIOS_PUBLICOS",
        )

    # Nivel 1: grilla de Documentos Soporte (DataTables) no debe filtrar
    # datos de otro tenant
    with schema_context(tenant1.schema_name):
        client.force_login(user1)
    dt_payload = {
        "draw": 1,
        "start": 0,
        "length": 10,
        "search": {"value": ""},
        "order": [],
        "columns": [],
    }
    resp = client.post(
        "/api/v1/gastos/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    vendedores = [row["ds_vendedor"] for row in resp.json()["data"]]
    assert "Proveedor Tenant Uno" in vendedores
    assert "Proveedor Tenant Dos" not in vendedores

    # Nivel 1 (KPIs de Documentos Soporte): la vista HTML no debe filtrar en
    # silencio -- responde 200 con sesion valida.
    resp = client.get(
        "/ui/gastos/tabla-documentos/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
    )
    assert resp.status_code == status.HTTP_200_OK

    # Nivel 1 (Resoluciones): migro a DataTables -- POST, no la vista HTML
    # django-tables2 retirada.
    resp = client.post(
        "/api/v1/gastos/resoluciones/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code == status.HTTP_200_OK
    numeros_resolucion = [row["numero_resolucion"] for row in resp.json()["data"]]
    assert "RES1B" in numeros_resolucion
    assert "RES2B" not in numeros_resolucion

    # Sin sesion: la vista HTML de KPIs debe redirigir a login (LoginRequiredMixin);
    # los endpoints DataTables (DRF) deben rechazar con 401/403 -- ninguno filtra en silencio.
    from django.test import Client

    anon_client = Client()
    resp = anon_client.get(
        "/ui/gastos/tabla-documentos/", HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
    )
    assert resp.status_code in (status.HTTP_302_FOUND, status.HTTP_403_FORBIDDEN)
    resp = anon_client.post(
        "/api/v1/gastos/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    resp = anon_client.post(
        "/api/v1/gastos/resoluciones/dt/",
        data=dt_payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
