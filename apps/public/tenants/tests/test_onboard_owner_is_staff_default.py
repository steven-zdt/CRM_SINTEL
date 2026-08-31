"""
REM ONBOARDING-E2E-03 (docs/e2e/ONBOARDING_E2E_REPORT.md) -- CRITICO:
verificacion dirigida de que OnboardTenantWithOwnerSerializer.owner_is_staff
tiene default=False, no True.

Hallazgo real, encontrado en vivo durante la validacion E2E de creacion de
tenant (2026-08-31): el default anterior (True) contradecia directamente
el motor real (empresa_service.py::crear_tenant_con_owner, parametro
owner_is_staff: bool = False -- "Owners de tenant no son staff del
sistema"). El formulario de consola (/console/tenants/new/) no expone
este campo, asi que TODO tenant creado por el flujo normal via consola
heredaba is_staff=True para su owner sin que el admin que lo creaba lo
supiera o decidiera explicitamente.

Impacto verificado en vivo (no solo teorico): con la contrasena
establecida via el endpoint legitimo de soporte (admin-set-password), el
owner de un tenant recien creado podia loguearse en el panel admin del
esquema PUBLICO y acceder a /console/tenants/ + /api/public/v1/tenants/,
viendo el listado COMPLETO de tenants del sistema -- incluyendo tenants
de clientes reales (home, shelltest1, qaisotest), no solo el suyo propio.

Este test es puramente de serializer (sin DB, sin creacion de schema
real) -- rapido y dirigido, evita duplicar la cobertura de integracion
completa ya existente en otros archivos de tests/public/tenants/.
"""
from apps.public.tenants.api.serializers import OnboardTenantWithOwnerSerializer


def test_owner_is_staff_default_is_false():
    """El campo owner_is_staff debe tener default=False -- nunca True."""
    field = OnboardTenantWithOwnerSerializer().fields["owner_is_staff"]
    assert field.default is False, (
        "REGRESION CRITICA: owner_is_staff.default debe ser False. "
        "Un default=True otorga acceso de staff GLOBAL (todos los "
        "tenants del sistema) al owner de cualquier tenant nuevo creado "
        "via el formulario de consola, que no expone este campo."
    )


def test_owner_is_staff_omitted_from_payload_defaults_to_false():
    """Si el payload no incluye owner_is_staff (caso real del formulario de
    consola, que no expone este campo), validated_data debe resolver a
    False, no a True."""
    serializer = OnboardTenantWithOwnerSerializer(
        data={
            "nombre": "Test Serializer Default",
            "schema_name": "test_serializer_default_check",
            "owner_email": "owner-default-check@example.com",
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data.get("owner_is_staff") is False
