"""
REM P1-03 (docs/remediation/REM-P1-03.md): ExtractoBancario solo tenia
proteccion de aplicacion (.exists() antes de crear, TOCTOU real bajo
doble-submit) contra duplicados del mismo periodo/cuenta. Se agrego
UniqueConstraint(empresa, cuenta, anio, mes) como respaldo real de BD,
mismo periodo/cuenta que la app ya usaba como clave. TransaccionBancaria
no recibio un constraint directo (sin identificador externo confiable) --
en su lugar, procesar_archivo_extracto() ahora bloquea el extracto
(select_for_update) para que un reprocesamiento concurrente no duplique
transacciones antes de que el primero termine su delete+insert.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.bancos.services.crud_service import ExtractoBancarioCRUDService
from apps.tenant.empresa.models import Empresa
from tests.tenant.base_test import SintelTenantTestCase


class ExtractoBancarioDuplicadoP1_03Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa P1-03", nit="900000797", direccion="Calle 1",
        )
        self.cuenta = CuentaBancaria.objects.create(
            empresa=self.empresa, nombre="Cuenta P1-03", banco="Banco Test",
            tipo="AHORROS", numero="P103-1",
        )

    def test_crear_extracto_duplicado_via_servicio_es_rechazado(self):
        """El chequeo de aplicacion ya existente sigue funcionando."""
        ExtractoBancarioCRUDService.crear_extracto(
            empresa=self.empresa, data={"cuenta": self.cuenta, "mes": 6, "anio": 2026},
        )
        from rest_framework.exceptions import ValidationError as DRFValidationError
        with self.assertRaises(DRFValidationError):
            ExtractoBancarioCRUDService.crear_extracto(
                empresa=self.empresa, data={"cuenta": self.cuenta, "mes": 6, "anio": 2026},
            )

    def test_constraint_de_bd_bloquea_insercion_directa_duplicada(self):
        """Respaldo real de BD -- un INSERT directo que se salte el
        servicio tambien falla, cerrando la ventana TOCTOU."""
        ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=7, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ExtractoBancario.objects.create(
                    empresa=self.empresa, cuenta=self.cuenta, mes=7, anio=2026,
                    saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
                )

    def test_distintos_periodos_de_la_misma_cuenta_coexisten(self):
        ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=1, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        ExtractoBancario.objects.create(
            empresa=self.empresa, cuenta=self.cuenta, mes=2, anio=2026,
            saldo_inicial=Decimal("0"), saldo_final=Decimal("0"),
        )
        self.assertEqual(
            ExtractoBancario.objects.filter(empresa=self.empresa, cuenta=self.cuenta).count(), 2,
        )
