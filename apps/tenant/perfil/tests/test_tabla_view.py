"""
Test de la tabla server-rendered de Perfil (Fase 5-BIS, django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. El guard [SEG-5] de auto-eliminacion: la fila del propio solicitante
   ADMIN nunca muestra el boton "eliminar", aunque su rol lo permita.
3. Otro perfil ADMIN si expone el boton "eliminar" para el solicitante.
"""
import pytest
from django.core.management import call_command
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile


@pytest.mark.django_db
def test_tabla_perfiles_oculta_boton_eliminar_en_fila_propia(client, django_user_model, tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()

        admin_user = django_user_model.objects.create(username="admin_self", email="admin_self@example.com")
        otro_user = django_user_model.objects.create(username="otro_admin", email="otro_admin@example.com")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    TenantMembership.objects.create(client=tenant, user=otro_user, is_active=True, rol="ADMIN")

    with schema_context(tenant.schema_name):
        admin_perfil = TenantProfile.objects.create(
            user=admin_user, empresa=empresa, cargo="Gerente", rol="ADMIN",
        )
        otro_perfil = TenantProfile.objects.create(
            user=otro_user, empresa=empresa, cargo="Contador", rol="ADMIN",
        )
        # django.contrib.sessions esta en TENANT_APPS (sesiones aisladas por
        # schema, ver config/settings.py) -- force_login() debe ejecutarse
        # dentro del schema del tenant para que la sesion se guarde en la
        # tabla django_session correcta (la que consultara SessionMiddleware
        # una vez el request cambie a este schema). Fuera de schema_context()
        # la sesion se guarda en 'public' y el request subsiguiente recibe
        # AnonymousUser -> redirect a /login/.
        client.force_login(admin_user)

    r = client.get("/ui/perfil/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")

    boton_eliminar_propio = f'data-action="eliminar" data-id="{admin_perfil.uuid}"'
    boton_eliminar_otro = f'data-action="eliminar" data-id="{otro_perfil.uuid}"'

    assert boton_eliminar_propio not in html, (
        "[SEG-5] La fila del propio solicitante ADMIN expone el boton eliminar — "
        "riesgo de auto-eliminacion."
    )
    assert boton_eliminar_otro in html, (
        "El ADMIN solicitante deberia poder eliminar el perfil de otro usuario."
    )

    # Boton editar debe estar presente en ambas filas (rol ADMIN tiene 'edit')
    assert f'data-action="editar" data-id="{admin_perfil.uuid}"' in html
    assert f'data-action="editar" data-id="{otro_perfil.uuid}"' in html
