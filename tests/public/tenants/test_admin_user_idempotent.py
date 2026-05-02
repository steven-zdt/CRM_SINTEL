import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_ensure_admin_idempotent():
    """
    El comando ensure_admin debe ser idempotente:
    dos ejecuciones crean solo un usuario 'admin'.
    """
    User = get_user_model()

    call_command("ensure_admin")
    call_command("ensure_admin")

    assert User.objects.filter(username="admin").count() == 1

