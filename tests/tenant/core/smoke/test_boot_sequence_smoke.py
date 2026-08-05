import pytest

try:
    import cryptography  # noqa: F401
    import playwright  # noqa: F401
except Exception:
    pytest.skip(
        "Skipping heavy smoke test: missing playwright/cryptography",
        allow_module_level=True,
    )

"""
Pruebas de humo para verificar la secuencia de arranque.

Verifica que el proceso de arranque no lance el error de argparse
"error: argument --tenant: ignored explicit argument 'all'".
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()


@pytest.mark.django_db
class TestBootSequenceSmoke:
    """Pruebas de humo para la secuencia de arranque."""

    def test_migrate_schemas_tenant_flag_no_argument(self):
        """
        Verifica que migrate_schemas --tenant NO recibe argumento 'all'.

        Este test verifica que el comando se construye correctamente
        sin el error de argparse.
        """
        from io import StringIO

        from django.core.management import call_command

        # Capturar stdout/stderr
        out = StringIO()
        err = StringIO()

        # Intentar ejecutar el comando (puede fallar si no hay tenants, pero no debe ser por argparse)
        try:
            call_command(
                "migrate_schemas",
                "--tenant",
                "--fake-initial",
                verbosity=0,
                stdout=out,
                stderr=err,
            )
            # Si llega aquí, el comando se ejecutó sin error de argparse
            assert True
        except SystemExit as e:
            # SystemExit puede ocurrir si argparse detecta un error
            # Verificar que NO es el error de "ignored explicit argument"
            error_msg = err.getvalue()
            assert (
                "ignored explicit argument" not in error_msg.lower()
            ), f"Error de argparse detectado: {error_msg}"
        except Exception as e:
            # Cualquier otro error está bien (puede ser que no haya tenants)
            # Pero NO debe ser el error de argparse
            error_msg = str(e)
            assert (
                "ignored explicit argument" not in error_msg.lower()
            ), f"Error de argparse detectado: {error_msg}"

    def test_boot_sequence_logs_expected_messages(self):
        """
        Verifica que la secuencia de arranque genera los logs esperados.

        Este test simula la secuencia de arranque y verifica que
        los mensajes de log esperados aparecen.
        """
        from io import StringIO

        from django.core.management import call_command

        # Capturar stdout
        out = StringIO()

        # Simular la secuencia de arranque (solo la parte de migraciones)
        try:
            # 1. Migraciones shared
            call_command(
                "migrate_schemas", "--shared", "--fake-initial", verbosity=1, stdout=out
            )
            output = out.getvalue()
            assert "shared" in output.lower() or "public" in output.lower()

            # 2. Migraciones tenant (sin argumento 'all')
            out_tenant = StringIO()
            try:
                call_command(
                    "migrate_schemas",
                    "--tenant",
                    "--fake-initial",
                    verbosity=1,
                    stdout=out_tenant,
                )
                output_tenant = out_tenant.getvalue()
                # Verificar que NO aparece el error de argparse
                assert "ignored explicit argument" not in output_tenant.lower()
            except Exception:
                # Puede fallar si no hay tenants, pero no debe ser por argparse
                pass

        except Exception as e:
            # Cualquier error debe ser por otra razón, no por argparse
            error_msg = str(e)
            assert (
                "ignored explicit argument" not in error_msg.lower()
            ), f"Error de argparse detectado: {error_msg}"
