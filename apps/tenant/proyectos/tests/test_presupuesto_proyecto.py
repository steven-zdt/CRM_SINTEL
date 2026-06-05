"""
Tests para Presupuesto Manual (v3.5.2) - ItemPresupuestoProyecto

Tests para validar:
1. Calculo matematico correcto de utilidad planeada
2. DSV (Double Semantic Verification) - rechaza item de otro tenant
3. Bloqueo de edicion en Fase CIERRE - crear item
4. Bloqueo de edicion en Fase CIERRE - eliminar item
"""
from decimal import Decimal
import pytest
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import Proyecto, ItemPresupuestoProyecto
from apps.tenant.proyectos.services import PresupuestoBusinessService


@pytest.mark.django_db
class TestPresupuestoProyecto:
    """Suite de tests para ItemPresupuestoProyecto."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Configuracion inicial para cada test."""
        self.empresa1 = Empresa.objects.create(
            razon_social='Empresa 1',
            nit='123456789'
        )
        self.empresa2 = Empresa.objects.create(
            razon_social='Empresa 2',
            nit='987654321'
        )
        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa1,
            nombre='Proyecto Test',
            tipo_servicio='PROYECTO_INTEGRAL',
            valor_contrato_proyectado=Decimal('1000000.00'),
            fase_actual='PLANEACION'
        )

    def test_calculo_utilidad_planeada_correcta(self):
        """
        TEST 1: Calculo matematico correcto de utilidad planeada.

        Scenario:
        - Valor contrato: $1,000,000
        - Item 1: MANO_OBRA, cantidad=2, valor_unitario=100,000 -> subtotal=$200,000
        - Item 2: MATERIALES, cantidad=10, valor_unitario=30,000 -> subtotal=$300,000
        - costo_planeado_total debe ser $500,000
        - utilidad_planeada debe ser $500,000 (1,000,000 - 500,000)
        - margen_planeado debe ser 50.00% (500,000 / 1,000,000 * 100)
        """
        PresupuestoBusinessService.crear_item(
            empresa=self.empresa1,
            proyecto=self.proyecto,
            data={
                'categoria': 'MANO_OBRA',
                'descripcion': 'Instalacion tecnica',
                'cantidad': Decimal('2'),
                'valor_unitario': Decimal('100000.00')
            }
        )

        PresupuestoBusinessService.crear_item(
            empresa=self.empresa1,
            proyecto=self.proyecto,
            data={
                'categoria': 'MATERIALES',
                'descripcion': 'Materiales varios',
                'cantidad': Decimal('10'),
                'valor_unitario': Decimal('30000.00')
            }
        )

        # Recargar proyecto para obtener valores calculados
        self.proyecto.refresh_from_db()

        assert self.proyecto.costo_planeado_total == Decimal('500000.00')
        assert self.proyecto.utilidad_planeada == Decimal('500000.00')
        assert self.proyecto.margen_planeado == Decimal('50.00')

    def test_dsv_item_otro_empresa_rechazado(self):
        """
        TEST 2: DSV (Double Semantic Verification) - rechaza item de otro tenant.

        Scenario:
        - Crear proyecto en Empresa 1
        - Intentar agregar item vinculado a Empresa 2
        - Debe lanzar ValidationError
        """
        with pytest.raises(ValidationError):
            PresupuestoBusinessService.crear_item(
                empresa=self.empresa2,  # <- Diferente empresa
                proyecto=self.proyecto,  # <- Proyecto pertenece a empresa1
                data={
                    'categoria': 'EQUIPOS',
                    'descripcion': 'Test',
                    'cantidad': Decimal('1'),
                    'valor_unitario': Decimal('10000.00')
                }
            )

    def test_cierre_bloquea_crear_item(self):
        """
        TEST 3: Bloqueo de creacion de items en Fase CIERRE.

        Scenario:
        - Proyecto en fase CIERRE
        - Intentar crear item
        - Debe lanzar ValidationError con mensaje sobre CIERRE
        """
        self.proyecto.fase_actual = 'CIERRE'
        self.proyecto.save()

        with pytest.raises(ValidationError, match='Cierre'):
            PresupuestoBusinessService.crear_item(
                empresa=self.empresa1,
                proyecto=self.proyecto,
                data={
                    'categoria': 'EQUIPOS',
                    'descripcion': 'Test',
                    'cantidad': Decimal('1'),
                    'valor_unitario': Decimal('10000.00')
                }
            )

    def test_cierre_bloquea_eliminar_item(self):
        """
        TEST 4: Bloqueo de eliminacion de items en Fase CIERRE.

        Scenario:
        - Crear item en proyecto (fase PLANEACION)
        - Cambiar proyecto a fase CIERRE
        - Intentar eliminar item
        - Debe lanzar ValidationError con mensaje sobre CIERRE
        """
        item = PresupuestoBusinessService.crear_item(
            empresa=self.empresa1,
            proyecto=self.proyecto,
            data={
                'categoria': 'MATERIALES',
                'descripcion': 'Item test',
                'cantidad': Decimal('5'),
                'valor_unitario': Decimal('20000.00')
            }
        )

        # Cambiar fase a CIERRE
        self.proyecto.fase_actual = 'CIERRE'
        self.proyecto.save()

        # Recargar item para que tenga la relacion actualizada
        item.refresh_from_db()

        with pytest.raises(ValidationError, match='Cierre'):
            PresupuestoBusinessService.eliminar_item(item)

    def test_recalculo_automatico_al_eliminar_item(self):
        """
        TEST EXTRA: Verificar que al eliminar un item, se recalcula el total planeado.

        Scenario:
        - Crear 2 items
        - Verificar totales (200,000 + 300,000 = 500,000)
        - Eliminar primer item
        - Verificar que totales se actualizan (solo 300,000)
        """
        item1 = PresupuestoBusinessService.crear_item(
            empresa=self.empresa1,
            proyecto=self.proyecto,
            data={
                'categoria': 'MANO_OBRA',
                'cantidad': Decimal('2'),
                'valor_unitario': Decimal('100000.00')
            }
        )

        item2 = PresupuestoBusinessService.crear_item(
            empresa=self.empresa1,
            proyecto=self.proyecto,
            data={
                'categoria': 'MATERIALES',
                'cantidad': Decimal('10'),
                'valor_unitario': Decimal('30000.00')
            }
        )

        self.proyecto.refresh_from_db()
        assert self.proyecto.costo_planeado_total == Decimal('500000.00')

        # Eliminar primer item
        PresupuestoBusinessService.eliminar_item(item1)

        self.proyecto.refresh_from_db()
        assert self.proyecto.costo_planeado_total == Decimal('300000.00')
        assert self.proyecto.utilidad_planeada == Decimal('700000.00')
