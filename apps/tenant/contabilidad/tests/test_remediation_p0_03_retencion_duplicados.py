"""
REM P0-03 (docs/remediation/REM-P0-03.md): Retencion no tenia ninguna
proteccion estructural contra duplicados. Un retry/doble-click de
crear_retenciones_desde_dict() podia duplicar silenciosamente el monto de
retencion de un documento. Se agrego UniqueConstraint(empresa,
documento_origen_app, documento_origen_modelo, documento_origen_id, tipo,
condition=reversada=False) + idempotencia real en crear_retencion().
"""
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.contabilidad.models import Retencion
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa


class RetencionDuplicadosP0_03Tests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Empresa P0-03', nit='900000793',
        )

    def test_crear_retencion_duplicada_retorna_la_existente_idempotente(self):
        """Mismo documento_origen+tipo, dos veces: la segunda llamada NO
        crea una fila nueva, retorna la misma (idempotencia real)."""
        ret1 = RetencionesService.crear_retencion(
            empresa=self.empresa, tipo='RETEFUENTE', monto=Decimal('100.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=777,
        )
        ret2 = RetencionesService.crear_retencion(
            empresa=self.empresa, tipo='RETEFUENTE', monto=Decimal('100.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=777,
        )
        self.assertEqual(ret1.id, ret2.id)
        self.assertEqual(
            Retencion.objects.filter(
                empresa=self.empresa, documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte', documento_origen_id=777,
                tipo='RETEFUENTE',
            ).count(),
            1,
        )

    def test_constraint_de_bd_bloquea_insercion_directa_duplicada(self):
        """Verifica el respaldo real de BD (no solo la capa de aplicacion):
        un INSERT directo que se salte crear_retencion() tambien falla."""
        Retencion.objects.create(
            empresa=self.empresa, tipo='RETEICA', monto=Decimal('50.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=888,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Retencion.objects.create(
                    empresa=self.empresa, tipo='RETEICA', monto=Decimal('50.00'),
                    documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
                    documento_origen_id=888,
                )

    def test_distintos_tipos_del_mismo_documento_no_colisionan(self):
        """RETEFUENTE + RETEICA + RETEIVA del mismo documento coexisten
        (docstring del modelo: es un caso legitimo, no un duplicado)."""
        ret_fuente = RetencionesService.crear_retencion(
            empresa=self.empresa, tipo='RETEFUENTE', monto=Decimal('40.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=999,
        )
        ret_ica = RetencionesService.crear_retencion(
            empresa=self.empresa, tipo='RETEICA', monto=Decimal('10.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=999,
        )
        self.assertNotEqual(ret_fuente.id, ret_ica.id)

    def test_reversar_retencion_in_place_no_colisiona_con_el_constraint(self):
        """Caso critico del diseño: reversar_retencion() SIN
        documento_reversada_id distinto crea una segunda fila con el MISMO
        documento_origen+tipo que el original -- debe funcionar porque el
        original ya quedo reversada=True antes de insertar la nueva fila."""
        original = RetencionesService.crear_retencion(
            empresa=self.empresa, tipo='RETEIVA', monto=Decimal('30.00'),
            documento_origen_app='gastos', documento_origen_modelo='DocumentoSoporte',
            documento_origen_id=1010,
        )
        reversal = RetencionesService.reversar_retencion(
            retencion=original, empresa=self.empresa,
        )
        original.refresh_from_db()
        self.assertTrue(original.reversada)
        self.assertFalse(reversal.reversada)
        self.assertEqual(reversal.documento_origen_id, original.documento_origen_id)
        self.assertEqual(reversal.tipo, original.tipo)
        self.assertEqual(reversal.monto, Decimal('-30.00'))
