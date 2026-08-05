import pytest
from decimal import Decimal
from django_tenants.utils import schema_context
from rest_framework import status
from apps.tenant.gastos.models import ResolucionDIAN, DocumentoSoporte
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from apps.public.tenants.models import TenantMembership
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()

@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_creacion_gasto_completo_persistencia(client, tenant1):
    """
    Validacion de Fase 9: Verifica que el flujo de creacion consolidado
    en GastoBusinessService funcione correctamente y persista todos los datos.
    """
    with schema_context(tenant1.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username="auditor", email="auditor@sintel.net.co", password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")
        
        # Crear membresia en esquema publico (Bridge)
        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user, rol="ADMIN")
        
        # 2. Crear Resolucion DIAN
        res = ResolucionDIAN.objects.create(
            empresa=emp,
            numero_resolucion="187640000001",
            prefijo="SETT",
            rango_desde=1,
            rango_hasta=1000,
            fecha_resolucion="2026-01-01",
            fecha_inicio="2026-01-01",
            fecha_fin="2027-12-31",
            vigente=True
        )

        prov = Proveedor.objects.create(
            empresa=emp,
            razon_social="PROVEEDOR DE PRUEBA SAS",
            numero_documento="900.123.456-7",
            tipo_documento="NIT"
        )

        # Crear configuracion de retenciones (v3.7.1 Pull Model)
        from apps.tenant.contabilidad.models import ConfiguracionRetenciones
        ConfiguracionRetenciones.objects.create(
            empresa=emp,
            tipo_tercero='PROVEEDOR',
            nit_tercero='9001234567',
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('4.00'),
            naturaleza='COMPRA',
            activa=True
        )
        ConfiguracionRetenciones.objects.create(
            empresa=emp,
            tipo_tercero='PROVEEDOR',
            nit_tercero='9001234567',
            tipo_retencion='RETEICA',
            porcentaje_por_defecto=Decimal('0.69'),
            naturaleza='COMPRA',
            activa=True
        )

        # 2. Payload realista (basado en v2.62.1 y gasto_editor.js)
        payload = {
            "documento_soporte": {
                "resolucion": res.id,
                "fecha": "2026-05-06",
                "proveedor": prov.id,
                "numero_documento_proveedor": "FAC-12345",
                "subtotal": 100000.00,
                "retefuente_porcentaje": "0.04",
                "reteica_porcentaje": "0.0069",
                "total": 95310.00  # 100000 - 4000 - 690 = 95310
            },
            "descripcion": "Gasto de prueba Fase 9",
            "observaciones": "Validacion de persistencia y documento soporte"
        }

        # 3. Ejecutar Peticion
        client.force_login(user)
        response = client.post(
            "/api/v1/gastos/",
            data=payload,
            content_type="application/json",
            HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
        )

        # 4. Validaciones de Respuesta
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        data = response.json()
        assert "id" in data
        assert data["descripcion"] == "Gasto de prueba Fase 9"
        
        # 5. Validaciones de Base de Datos (Persistencia Directa)
        ds = DocumentoSoporte.objects.get(id=data["id"])
        
        assert str(ds.fecha)[:7] == "2026-05"
        assert ds.vendedor_nit == "900.123.456-7"
        assert ds.consecutivo == 1
        assert ds.prefijo == "SETT"
        assert ds.subtotal == Decimal("100000.00")
        assert ds.total_retefuente == Decimal("4000.00")
        assert ds.total_reteica == Decimal("690.00")
        assert ds.total == Decimal("95310.00")
        assert ds.numero_documento == "SETT 1"
        assert ds.empresa == emp

@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_gasto_con_resolucion_de_fecha_pasada_es_permitido(client, tenant1):
    """
    Verifica que la fecha del documento NO esta restringida por el rango de fechas
    de la resolucion DIAN. La resolucion solo controla el consecutivo/numeracion.
    Un gasto con fecha de hoy puede usar una resolucion cuyas fechas son del pasado.
    """
    with schema_context(tenant1.schema_name):
        emp = Empresa.objects.first()
        user = User.objects.create_user(username="auditor_fecha", email="fecha@sintel.net.co", password="password")
        TenantProfile.objects.create(user=user, empresa=emp, rol="ADMIN")

        with schema_context('public'):
            TenantMembership.objects.create(client=tenant1, user=user, rol="ADMIN")

        # Resolucion con fechas en el pasado (pero valida para el tenant)
        res = ResolucionDIAN.objects.create(
            empresa=emp,
            numero_resolucion="ANTIGUA-001",
            prefijo="OLD",
            rango_desde=1,
            rango_hasta=100,
            fecha_resolucion="2020-01-01",
            fecha_inicio="2020-01-01",
            fecha_fin="2020-12-31",
            vigente=True
        )

        prov = Proveedor.objects.create(
            empresa=emp,
            razon_social="Proveedor Fecha Test",
            numero_documento="888",
            tipo_documento="NIT"
        )

        payload = {
            "documento_soporte": {
                "resolucion": res.id,
                "fecha": "2026-05-06",  # Fecha fuera del rango de la resolucion -> permitido
                "proveedor": prov.id,
                "subtotal": 100,
                "total": 100
            }
        }

        client.force_login(user)
        response = client.post(
            "/api/v1/gastos/",
            data=payload,
            content_type="application/json",
            HTTP_HOST=f"{tenant1.schema_name}.sintel.net.co"
        )

        # Debe crear el gasto sin importar el rango de fechas de la resolucion
        assert response.status_code == status.HTTP_201_CREATED, (
            f"Se esperaba 201 pero se obtuvo {response.status_code}: {response.data}"
        )
