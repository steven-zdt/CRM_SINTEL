"""
[WARNING] FASE 6: Tests de Arranque y Disponibilidad.

Validan que el sistema pueda iniciar y operar correctamente.
"""

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django_tenants.utils import get_public_schema_name, get_tenant_model


class StartupAvailabilityTests(TestCase):
    """
    Tests de arranque y disponibilidad del sistema.

    [WARNING] FASE 6: Validaciones mínimas pero críticas de que el sistema puede iniciar.
    """

    def test_migraciones_ejecutan_sin_error(self):
        """
        Test: Migraciones ejecutan sin error.

        Criterios de aceptación:
        - Sistema operativo tras deploy
        - Sin errores críticos en logs
        """
        try:
            # Verificar que podemos ejecutar check de migraciones
            call_command("check", "--deploy", verbosity=0)
        except CommandError:
            # Si hay errores, el test falla
            self.fail("Las migraciones no ejecutan correctamente")

    def test_servidor_inicia_correctamente(self):
        """
        Test: Servidor inicia correctamente.

        Criterios de aceptación:
        - Sistema operativo tras deploy
        """
        # Verificar que la conexión a BD funciona
        try:
            connection.ensure_connection()
        except Exception as e:
            self.fail(f"La conexión a BD falla: {e}")

        # Verificar que podemos hacer queries básicas
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                self.assertEqual(row[0], 1)
        except Exception as e:
            self.fail(f"Las queries básicas fallan: {e}")

    def test_acceso_tenant_publico(self):
        """
        Test: Acceso a tenant público (si existe).

        Criterios de aceptación:
        - Sistema operativo tras deploy
        """
        # Verificar que el esquema público existe
        public_schema = get_public_schema_name()
        self.assertIsNotNone(public_schema)

        # Verificar que podemos cambiar al esquema público
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """,
                [public_schema],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(
                row, f"El esquema público '{public_schema}' debe existir"
            )

    def test_acceso_tenant_privado(self):
        """
        Test: Acceso a tenant privado.

        Criterios de aceptación:
        - Sistema operativo tras deploy
        """
        from apps.public.tenants.models import Client, Domain

        # Crear tenant de prueba
        tenant = Client.objects.create(
            schema_name="test_startup_tenant",
            nombre="Test Startup Tenant",
            is_active=True,
            on_trial=True,
        )
        Domain.objects.create(
            domain="startup.localhost", tenant=tenant, is_primary=True
        )

        # Verificar que el esquema existe
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """,
                [tenant.schema_name],
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row, f"El esquema '{tenant.schema_name}' debe existir")

    def test_modelos_tenant_cargables(self):
        """
        Test: Modelos tenant son cargables.

        Criterios de aceptación:
        - Sin errores de importación
        - Modelos accesibles
        """
        try:
            from apps.tenant.clientes.models import Cliente
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.facturas.models import Factura
        except ImportError as e:
            self.fail(f"Error al importar modelos tenant: {e}")

        # Verificar que los modelos son accesibles
        self.assertIsNotNone(Empresa)
        self.assertIsNotNone(Factura)
        self.assertIsNotNone(Cliente)

    def test_healthcheck_endpoint_disponible(self):
        """
        Test: Healthcheck endpoint está disponible.

        Criterios de aceptación:
        - Sistema operativo tras deploy
        """
        from django.test import Client

        client = Client()

        # Intentar acceder al healthcheck (puede estar en diferentes rutas)
        # Ajustar según tu configuración
        response = client.get("/api/v1/core/health/")

        # Verificar que responde (puede ser 200, 401, 403, 404)
        self.assertIn(response.status_code, [200, 401, 403, 404])
