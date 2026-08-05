"""
Fixtures compartidos para la suite de tests de apps/public/console/.

Provee:
- Usuarios: normal (no-staff) y admin (staff+superuser)
- Tenant (Client) con Domain primario
- ConsoleActionLog de ejemplo

Uso:
    Los TestCase heredan de PublicAPITestCase o Django TestCase y llaman
    a estos helpers desde setUp(). Los fixtures pytest estan disponibles
    para suites que usen pytest-django directamente.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers de creacion (usados desde setUp() en TestCase)
# ---------------------------------------------------------------------------

def make_normal_user(
    email: str = "normal@console.test",
    password: str = "Pass1234!",
) -> "User":
    """Crea un usuario activo sin permisos de staff."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )


def make_staff_user(
    email: str = "staff@console.test",
    password: str = "Pass1234!",
) -> "User":
    """Crea un usuario activo con is_staff=True e is_superuser=True."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )


def make_tenant_with_domain(
    nombre: str = "Test Empresa",
    schema_name: str = "testempresa",
    domain: str = "testempresa.sintel.net.co",
) -> tuple:
    """
    Crea un Client (tenant privado) con su Domain primario.
    Retorna (client, domain).

    NOTA: `Client.create_schema()` se parchea a no-op para evitar DDL
    (`CREATE SCHEMA`) dentro de una transaccion de TestCase. El DDL de
    PostgreSQL hace auto-commit y rompe el rollback del test.
    """
    from unittest.mock import patch

    from apps.public.tenants.models import Client, Domain

    with patch.object(Client, "create_schema", return_value=None):
        client = Client.objects.create(
            nombre=nombre,
            schema_name=schema_name,
            is_active=True,
            on_trial=False,
        )

    dom = Domain.objects.create(
        tenant=client,
        domain=domain,
        is_primary=True,
    )
    return client, dom


def make_console_action_log(
    actor: "User",
    action: str = "USER_CREATE",
    tenant=None,
    target_user: "User | None" = None,
    metadata: dict | None = None,
) -> "object":
    """Crea una entrada ConsoleActionLog para tests de auditoria."""
    from apps.public.console.models import ConsoleActionLog

    return ConsoleActionLog.objects.create(
        action=action,
        actor=actor,
        tenant=tenant,
        target_user=target_user,
        metadata=metadata or {"test": True},
    )


# ---------------------------------------------------------------------------
# Fixtures pytest (para suites que usen pytest-django directamente)
# ---------------------------------------------------------------------------

@pytest.fixture()
def normal_user(db):
    """Usuario activo sin permisos de staff."""
    return make_normal_user()


@pytest.fixture()
def staff_user(db):
    """Usuario activo con is_staff=True e is_superuser=True."""
    return make_staff_user()


@pytest.fixture()
def tenant_with_domain(db):
    """Client activo con Domain primario; retorna (client, domain)."""
    return make_tenant_with_domain()


@pytest.fixture()
def console_action_log(db, staff_user):
    """ConsoleActionLog de ejemplo creado por staff_user."""
    return make_console_action_log(actor=staff_user)
