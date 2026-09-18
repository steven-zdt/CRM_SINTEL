"""RELEASE-CLOSE / PROVEEDORES-02: cobertura de las Reglas Criticas nuevas.

1. Todo Proveedor debe tener al menos un Representante (antes: crear_proveedor
   nunca tocaba Representante, un Proveedor podia quedar con 0).
2. NATURAL -> representante principal autogenerado desde el usuario real.
3. JURIDICA -> representante obligatorio, creacion atomica (todo o nada).
4. Un solo representante principal por proveedor -- crear/actualizar uno
   nuevo como principal degrada cualquier otro principal existente.
5. Cuentas por Pagar: abono sobre una fila originada en una Factura (sin
   CuentasPagar aun) materializa correctamente y queda reflejado en el
   listado unificado despues. DELETE respeta la politica: sin Factura +
   sin pagos -> permitido; con pagos o con Factura asociada -> rechazado.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import CuentasPagar, Proveedor, Representante
from apps.tenant.proveedores.services.business_service import (
    CuentasPagarBusinessService,
    ProveedorBusinessService,
    RepresentanteBusinessService,
)
from apps.tenant.proveedores.services.selectors import CuentasPagarSelector
from tests.tenant.base_test import SintelTenantTestCase


class ProveedorRepresentanteObligatorioTests(SintelTenantTestCase):
    """Reglas Criticas 1-4: representante obligatorio por tipo_persona."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Rep Obligatorio", nit="900777888", direccion="Calle 1",
        )
        self.service = ProveedorBusinessService()
        # TenantProfile real -- necesario para test_natural_autogenera_representante_
        # desde_usuario_real (self.user.tenant_profile es un reverse OneToOne que
        # devuelve None via getattr() si no existe, y _construir_payload_representante()
        # correctamente omite el auto-relleno en ese caso).
        from apps.tenant.perfil.models import TenantProfile
        TenantProfile.objects.get_or_create(
            user=self.user, empresa=self.empresa,
            defaults={"rol": "ADMIN", "alcance": "EMPRESA", "cargo": "Gerente de Compras"},
        )

    def test_juridica_sin_representante_es_rechazado_y_no_crea_proveedor(self):
        with self.assertRaises(ValidationError):
            self.service.crear_proveedor(
                empresa_id=self.empresa.id,
                data={
                    "tipo_persona": "JURIDICA", "tipo_documento": "NIT",
                    "numero_documento": "800900901", "razon_social": "Proveedor SAS",
                },
            )
        self.assertFalse(Proveedor.objects.filter(numero_documento="800900901").exists())

    def test_juridica_con_representante_incompleto_es_rechazado(self):
        """Falta nombre_completo -- representante_data presente pero invalido."""
        with self.assertRaises(ValidationError):
            self.service.crear_proveedor(
                empresa_id=self.empresa.id,
                data={
                    "tipo_persona": "JURIDICA", "tipo_documento": "NIT",
                    "numero_documento": "800900902", "razon_social": "Proveedor SAS 2",
                },
                representante_data={"numero_documento": "1010101010"},
            )
        self.assertFalse(Proveedor.objects.filter(numero_documento="800900902").exists())

    def test_juridica_con_representante_completo_crea_ambos_atomicamente(self):
        proveedor = self.service.crear_proveedor(
            empresa_id=self.empresa.id,
            data={
                "tipo_persona": "JURIDICA", "tipo_documento": "NIT",
                "numero_documento": "800900903", "razon_social": "Proveedor SAS 3",
            },
            representante_data={
                "tipo_documento": "CC", "numero_documento": "2020202020",
                "nombre_completo": "Representante Legal Uno",
            },
        )
        self.assertTrue(Proveedor.objects.filter(pk=proveedor.pk).exists())
        reps = Representante.objects.filter(empresa=self.empresa, proveedor=proveedor)
        self.assertEqual(reps.count(), 1)
        rep = reps.first()
        self.assertEqual(rep.nombre_completo, "Representante Legal Uno")
        self.assertTrue(rep.es_principal)

    def test_natural_sin_numero_documento_representante_es_rechazado(self):
        with self.assertRaises(ValidationError):
            self.service.crear_proveedor(
                empresa_id=self.empresa.id,
                data={
                    "tipo_persona": "NATURAL", "tipo_documento": "CC",
                    "numero_documento": "900900904", "razon_social": "Persona Natural Uno",
                },
            )
        self.assertFalse(Proveedor.objects.filter(numero_documento="900900904").exists())

    def test_natural_autogenera_representante_desde_usuario_real(self):
        proveedor = self.service.crear_proveedor(
            empresa_id=self.empresa.id,
            data={
                "tipo_persona": "NATURAL", "tipo_documento": "CC",
                "numero_documento": "900900905", "razon_social": "Persona Natural Dos",
            },
            representante_data={"tipo_documento": "CC", "numero_documento": "3030303030"},
            usuario=getattr(self.user, "tenant_profile", None),
        )
        rep = Representante.objects.get(empresa=self.empresa, proveedor=proveedor)
        self.assertEqual(rep.numero_documento, "3030303030")
        self.assertTrue(rep.es_principal)
        # email_contacto se precarga del usuario real (no se vuelve a pedir)
        self.assertEqual(rep.email_contacto, self.user.email)

    def test_resolver_o_crear_desde_factura_compra_sigue_funcionando_sin_representante(self):
        """resolver_o_crear_desde_factura_compra() resuelve/crea un
        Proveedor desde metadata fiscal de una Factura XML (sin usuario ni
        representante disponibles) -- pasa exigir_representante=False
        explicitamente a crear_proveedor() para preservar el comportamiento
        historico en vez de romper este caller automatizado (sin
        llamadores en vivo hoy, pero usado por
        backfill_proveedores_facturas_compra.py)."""
        proveedor, creado = ProveedorBusinessService.resolver_o_crear_desde_factura_compra(
            empresa_id=self.empresa.id,
            emisor_nit="800900906",
            emisor_razon_social="Emisor XML SAS",
        )
        self.assertTrue(creado)
        self.assertEqual(proveedor.numero_documento, "800900906")
        self.assertFalse(Representante.objects.filter(proveedor=proveedor).exists())


class RepresentantePrincipalUnicoTests(SintelTenantTestCase):
    """Regla: un solo es_principal=True por proveedor, reforzada en backend."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test Principal Unico", nit="900777889", direccion="Calle 1",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Principal Unico",
            numero_documento="800900907", tipo_documento="NIT",
        )
        self.service = RepresentanteBusinessService()

    def test_crear_segundo_principal_degrada_al_primero(self):
        p1 = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "4040404041", "nombre_completo": "P1", "es_principal": True},
        )
        self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "4040404042", "nombre_completo": "P2", "es_principal": True},
        )
        p1.refresh_from_db()
        principales = Representante.objects.filter(
            empresa=self.empresa, proveedor=self.proveedor, es_principal=True,
        )
        self.assertFalse(p1.es_principal)
        self.assertEqual(principales.count(), 1)
        self.assertEqual(principales.first().numero_documento, "4040404042")

    def test_actualizar_a_principal_degrada_al_anterior(self):
        p1 = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "4040404043", "nombre_completo": "P1", "es_principal": True},
        )
        p2 = self.service.crear_representante(
            empresa_id=self.empresa.id, proveedor_uuid=str(self.proveedor.uuid),
            data={"tipo_documento": "CC", "numero_documento": "4040404044", "nombre_completo": "P2", "es_principal": False},
        )
        self.service.actualizar_representante(
            empresa_id=self.empresa.id, representante_uuid=str(p2.uuid),
            data={"es_principal": True},
        )
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.es_principal)
        self.assertTrue(p2.es_principal)


class CuentasPagarMaterializacionYDeleteTests(SintelTenantTestCase):
    """Regla FACTURA: abono materializa desde Factura; DELETE respeta origen
    y pagos registrados."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test CxP Delete", nit="900777890", direccion="Calle 1",
        )
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor CxP Delete",
            numero_documento="800900908", tipo_documento="NIT",
        )

    def _crear_factura_compra(self, numero="FC-001", total="1000.00"):
        from apps.tenant.facturas.models import Factura

        hoy = timezone.now()
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, consecutivo=1, fecha_emision=hoy,
            emisor_nit=self.proveedor.numero_documento, emisor_razon_social=self.proveedor.razon_social,
            receptor_nit="900000000", receptor_razon_social="Empresa Receptora",
            naturaleza="COMPRA", proveedor_uuid=self.proveedor.uuid,
            total=Decimal(total), payment_due_date=(hoy + timedelta(days=30)).date(),
        )

    def test_abono_sobre_fila_origen_factura_materializa_y_persiste_en_listado(self):
        factura = self._crear_factura_compra()

        # 1. Antes del abono: la fila viene de la Factura directamente.
        filas = CuentasPagarSelector.qs_list_unificado(empresa_id=self.empresa.id)
        fila_factura = next(f for f in filas if f.uuid == factura.uuid)
        self.assertEqual(fila_factura.origen, "FACTURA")
        self.assertEqual(fila_factura.valor_pagado, Decimal("0.00"))

        # 2. Abonar usando el UUID de la Factura (lo que envia el boton
        # "Abono" de la tabla) -- antes de este fix, esto fallaba 400.
        actualizada = CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(factura.uuid), monto="400.00",
            observaciones="primer abono", empresa_id=self.empresa.id,
        )
        self.assertEqual(actualizada.valor_pagado, Decimal("400.00"))
        self.assertEqual(actualizada.factura_uuid, factura.uuid)

        # 3. El listado unificado, en la SIGUIENTE carga, debe reflejar el
        # abono (la CuentasPagar materializada es ahora la fuente
        # autoritativa) -- no volver a mostrar Factura.total/estado_pago
        # crudo (el hallazgo real que este fix cierra).
        filas_despues = CuentasPagarSelector.qs_list_unificado(empresa_id=self.empresa.id)
        fila_despues = next(f for f in filas_despues if f.factura_uuid == factura.uuid)
        self.assertEqual(fila_despues.valor_pagado, Decimal("400.00"))
        self.assertEqual(fila_despues.saldo, Decimal("600.00"))
        self.assertEqual(fila_despues.estado_pago, "PAGO_PARCIAL")
        self.assertFalse(fila_despues.puede_eliminar)

    def test_delete_cxp_manual_sin_pagos_permitido(self):
        cxp = CuentasPagar.objects.create(
            empresa=self.empresa, proveedor=self.proveedor, numero_factura="OC-100",
            valor_total=Decimal("500.00"), fecha_emision=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=15),
        )
        CuentasPagarBusinessService.eliminar_cuenta_pagar(
            cuenta_pagar_uuid=str(cxp.uuid), empresa_id=self.empresa.id,
        )
        self.assertFalse(CuentasPagar.objects.filter(uuid=cxp.uuid).exists())

    def test_delete_cxp_con_pagos_es_rechazado(self):
        cxp = CuentasPagar.objects.create(
            empresa=self.empresa, proveedor=self.proveedor, numero_factura="OC-101",
            valor_total=Decimal("500.00"), fecha_emision=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timedelta(days=15),
        )
        CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(cxp.uuid), monto="100.00", observaciones="",
            empresa_id=self.empresa.id,
        )
        with self.assertRaises(ValidationError):
            CuentasPagarBusinessService.eliminar_cuenta_pagar(
                cuenta_pagar_uuid=str(cxp.uuid), empresa_id=self.empresa.id,
            )
        self.assertTrue(CuentasPagar.objects.filter(uuid=cxp.uuid).exists())

    def test_delete_cxp_con_factura_asociada_es_rechazado(self):
        factura = self._crear_factura_compra(numero="FC-002")
        CuentasPagarBusinessService.registrar_abono(
            cuenta_pagar_uuid=str(factura.uuid), monto="100.00", observaciones="",
            empresa_id=self.empresa.id,
        )
        cxp = CuentasPagar.objects.get(factura_uuid=factura.uuid)
        with self.assertRaises(ValidationError):
            CuentasPagarBusinessService.eliminar_cuenta_pagar(
                cuenta_pagar_uuid=str(cxp.uuid), empresa_id=self.empresa.id,
            )
        self.assertTrue(CuentasPagar.objects.filter(uuid=cxp.uuid).exists())

    def test_delete_cxp_inexistente_falla(self):
        import uuid as uuid_lib
        with self.assertRaises(ValidationError):
            CuentasPagarBusinessService.eliminar_cuenta_pagar(
                cuenta_pagar_uuid=str(uuid_lib.uuid4()), empresa_id=self.empresa.id,
            )
