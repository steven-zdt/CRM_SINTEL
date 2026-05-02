"""
CRUD Service para Empleados - Persistencia transaccional pura.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO operaciones de persistencia (Create, Read, Update, Delete).
- Sin lógica de negocio, solo acceso a datos con @transaction.atomic.
- Todas las funciones son @staticmethod.
"""
import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.empleados.models import Contrato, Devengo, Empleado

logger = logging.getLogger(__name__)


class EmpleadoCRUDService:
    """Operaciones CRUD puras para Empleado."""

    @staticmethod
    @transaction.atomic
    def crear_empleado(data: dict, empresa) -> Empleado:
        """Crea un nuevo empleado."""
        empleado = Empleado.objects.create(empresa=empresa, **data)
        logger.info(f"[EmpleadoCRUD] Creado empleado ID={empleado.id}")
        return empleado

    @staticmethod
    @transaction.atomic
    def actualizar_empleado(empleado: Empleado, data: dict) -> Empleado:
        """Actualiza un empleado existente."""
        for key, value in data.items():
            setattr(empleado, key, value)
        empleado.save()
        logger.info(f"[EmpleadoCRUD] Actualizado empleado ID={empleado.id}")
        return empleado

    @staticmethod
    @transaction.atomic
    def eliminar_empleado(empleado: Empleado) -> dict:
        """Elimina un empleado y retorna conteo de dependencias eliminadas."""
        empleado_id = empleado.id

        # Contar dependencias antes de eliminar
        contratos_count = empleado.contratos.count()
        devengos_count = empleado.nominas.count()

        # Eliminar dependencias
        if devengos_count > 0:
            empleado.nominas.all().delete()
        if contratos_count > 0:
            empleado.contratos.all().delete()

        empleado.delete()

        logger.info(
            f"[EmpleadoCRUD] Eliminado empleado ID={empleado_id}. "
            f"Contratos: {contratos_count}, Devengos: {devengos_count}"
        )

        return {
            'contratos_eliminados': contratos_count,
            'devengos_eliminados': devengos_count,
            'empleado_eliminado': True
        }


class ContratoCRUDService:
    """Operaciones CRUD puras para Contrato."""

    @staticmethod
    @transaction.atomic
    def crear_contrato(empleado: Empleado, data: dict) -> Contrato:
        """Crea un nuevo contrato."""
        # Asignar empresa desde empleado si no viene en data
        if 'empresa' not in data:
            data['empresa'] = empleado.empresa

        # Sincronizar campos legacy y nuevos
        if 'estado' in data:
            data['activo'] = (data['estado'] == 'ACTIVO')
        if 'estado' not in data:
            data['estado'] = 'ACTIVO'
        if 'activo' not in data:
            data['activo'] = True

        contrato = Contrato.objects.create(empleado=empleado, **data)
        logger.info(f"[ContratoCRUD] Creado contrato ID={contrato.id} para empleado {empleado.id}")
        return contrato

    @staticmethod
    @transaction.atomic
    def actualizar_contrato(contrato: Contrato, data: dict) -> Contrato:
        """Actualiza un contrato existente."""
        # Sincronizar campos legacy y nuevos
        if 'estado' in data:
            data['activo'] = (data['estado'] == 'ACTIVO')

        for key, value in data.items():
            setattr(contrato, key, value)
        contrato.save()
        logger.info(f"[ContratoCRUD] Actualizado contrato ID={contrato.id}")
        return contrato

    @staticmethod
    @transaction.atomic
    def desactivar_contratos_previos(empleado: Empleado, contrato_excluir=None):
        """Desactiva contratos previos activos de un empleado."""
        qs_previos = Contrato.objects.filter(
            empleado=empleado,
            estado='ACTIVO',
            empresa_id=empleado.empresa_id
        )

        if contrato_excluir:
            qs_previos = qs_previos.exclude(pk=contrato_excluir.pk)

        count = qs_previos.update(activo=False, estado='INACTIVO')
        logger.info(f"[ContratoCRUD] Desactivados {count} contratos previos del empleado {empleado.id}")
        return count


class DevengoCRUDService:
    """Operaciones CRUD puras para Devengo (Nómina)."""

    @staticmethod
    @transaction.atomic
    def crear_devengo(empleado: Empleado, data: dict) -> Devengo:
        """Crea un nuevo registro de nómina."""
        # Asignar empresa desde empleado si no viene en data
        if 'empresa' not in data:
            data['empresa'] = empleado.empresa

        devengo = Devengo.objects.create(empleado=empleado, **data, anulado=False)
        logger.info(f"[DevengoCRUD] Creado devengo ID={devengo.id} para empleado {empleado.id}")
        return devengo

    @staticmethod
    @transaction.atomic
    def actualizar_devengo(devengo: Devengo, data: dict) -> Devengo:
        """Actualiza un registro de nómina existente."""
        for key, value in data.items():
            setattr(devengo, key, value)
        devengo.save()
        logger.info(f"[DevengoCRUD] Actualizado devengo ID={devengo.id}")
        return devengo

    @staticmethod
    @transaction.atomic
    def anular_devengo(devengo: Devengo) -> Devengo:
        """Marca un devengo como anulado (inmutabilidad contable)."""
        if devengo.anulado:
            raise ValueError("El desprendible ya está anulado.")

        devengo.anulado = True
        devengo.save(update_fields=['anulado'])
        logger.info(f"[DevengoCRUD] Anulado devengo ID={devengo.id}")
        return devengo

    @staticmethod
    @transaction.atomic
    def eliminar_devengo(devengo: Devengo) -> int:
        """Elimina un devengo y retorna su ID."""
        devengo_id = devengo.id
        devengo.delete()
        logger.info(f"[DevengoCRUD] Eliminado devengo ID={devengo_id}")
        return devengo_id

    @staticmethod
    @transaction.atomic
    def actualizar_prestamo_contrato(contrato: Contrato, monto_diferencia: Decimal):
        """Actualiza el saldo de préstamo en un contrato."""
        contrato.refresh_from_db()
        prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
        nuevo_prestamo = max(Decimal('0'), prestamo_actual - monto_diferencia)
        contrato.prestamos_empresa = nuevo_prestamo
        contrato.save(update_fields=['prestamos_empresa'])
        logger.info(
            f"[DevengoCRUD] Préstamo actualizado: contrato {contrato.id}, "
            f"diferencia={monto_diferencia}, nuevo_saldo={nuevo_prestamo}"
        )
        return contrato
