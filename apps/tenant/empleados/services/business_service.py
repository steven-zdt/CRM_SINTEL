"""
Business Service para Empleados - Lógica de negocio y orquestación.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO lógica de negocio (validaciones, cálculos, orquestación).
- Delega persistencia a crud_service.py.
- Todas las funciones son @staticmethod.
"""
import logging
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.empleados.models import Contrato, Devengo, Empleado
from apps.tenant.empleados.services.crud_service import (
    ContratoCRUDService,
    DevengoCRUDService,
    EmpleadoCRUDService,
)

logger = logging.getLogger(__name__)


class EmpleadoBusinessService:
    """Lógica de negocio para Empleado."""

    @staticmethod
    def crear_empleado(data: dict, empresa) -> Empleado:
        """Orquesta la creación de un empleado con validaciones."""
        return EmpleadoCRUDService.crear_empleado(data, empresa)

    @staticmethod
    def actualizar_empleado(empleado: Empleado, data: dict) -> Empleado:
        """
        Orquesta la actualización de un empleado.
        Si el estado cambia a RETIRADO, cancela contratos activos.
        """
        nuevo_estado = data.get('estado', empleado.estado)
        estado_anterior = empleado.estado

        empleado = EmpleadoCRUDService.actualizar_empleado(empleado, data)

        # Si se retira el empleado, cancelar contratos activos
        if estado_anterior != 'RETIRADO' and nuevo_estado == 'RETIRADO':
            count = EmpleadoBusinessService.cancelar_contratos_activos(empleado)
            if count > 0:
                logger.info(
                    f"[EmpleadoBusiness] Empleado {empleado.id} retirado. "
                    f"Cancelados {count} contrato(s) activo(s)."
                )

        return empleado

    @staticmethod
    def eliminar_empleado_retirado(empleado: Empleado) -> dict:
        """
        Elimina un empleado RETIRADO y todas sus dependencias.
        Solo permite eliminación si estado == 'RETIRADO'.
        """
        if empleado.estado != 'RETIRADO':
            raise ValidationError(
                f'Solo se pueden eliminar empleados con estado RETIRADO. '
                f'Estado actual: {empleado.estado}'
            )

        return EmpleadoCRUDService.eliminar_empleado(empleado)

    @staticmethod
    @transaction.atomic
    def cancelar_contratos_activos(empleado: Empleado) -> int:
        """Cancela todos los contratos activos de un empleado."""
        contratos_activos = empleado.contratos.filter(estado='ACTIVO')
        count = contratos_activos.count()

        if count > 0:
            hoy = timezone.now().date()
            contratos_activos.update(
                estado='INACTIVO',
                activo=False,
                fecha_fin=hoy
            )
            logger.info(
                f"[EmpleadoBusiness] Cancelados {count} contratos del empleado {empleado.id}"
            )

        return count


class ContratoBusinessService:
    """Lógica de negocio para Contrato."""

    @staticmethod
    @transaction.atomic
    def gestionar_contrato(empleado: Empleado, data: dict, contrato_existente=None) -> Contrato:
        """
        Orquesta la creación o actualización de un contrato.
        Garantiza un único contrato activo por empleado.
        """
        # Determinar estado final
        estado_final = data.get('estado', contrato_existente.estado if contrato_existente else 'ACTIVO')

        # Si el contrato quedará ACTIVO, desactivar contratos previos
        if estado_final == 'ACTIVO':
            ContratoCRUDService.desactivar_contratos_previos(empleado, contrato_existente)

        # Actualizar o crear
        if contrato_existente:
            return ContratoCRUDService.actualizar_contrato(contrato_existente, data)
        else:
            return ContratoCRUDService.crear_contrato(empleado, data)

    @staticmethod
    def preparar_datos_contrato(data: dict) -> dict:
        """Normaliza y valida payload de contrato."""
        prepared_data = dict(data)

        # Normalizar fecha_fin vacía
        if 'fecha_fin' in prepared_data:
            if prepared_data['fecha_fin'] == '' or prepared_data['fecha_fin'] is None:
                prepared_data['fecha_fin'] = None

        # Normalizar montos a Decimal
        for campo in ['auxilio_transporte', 'prestamos_empresa']:
            if campo not in prepared_data or prepared_data[campo] is None:
                prepared_data[campo] = Decimal('0.00')
            elif isinstance(prepared_data[campo], str):
                prepared_data[campo] = Decimal(prepared_data[campo] or '0.00')

        # Default estado
        if 'estado' not in prepared_data or prepared_data['estado'] is None:
            prepared_data['estado'] = 'ACTIVO'

        return prepared_data


class DevengoBusinessService:
    """Lógica de negocio para Devengo (Nómina)."""

    @staticmethod
    def validar_contrato_activo(empleado: Empleado):
        """Valida que el empleado tenga un contrato activo."""
        if not empleado.contratos.filter(activo=True, estado='ACTIVO').exists():
            raise ValidationError(
                "No se puede registrar nómina: El empleado no tiene un contrato activo."
            )

    @staticmethod
    def validar_limite_dias_mes(
        empleado_id: int,
        periodo_mes: str,
        nuevos_dias: Decimal,
        empresa_id: int,
        devengo_id_excluir: int = None
    ) -> dict:
        """
        Valida que la suma de días pagados en un mes no exceda 31.
        """
        try:
            nuevos_dias = Decimal(str(nuevos_dias))
        except (ValueError, TypeError):
            raise ValidationError("Los días laborados deben ser un número válido")

        # Sumar días existentes (no anulados)
        qs = Devengo.objects.filter(
            empleado_id=empleado_id,
            periodo_mes=periodo_mes,
            anulado=False,
            empresa_id=empresa_id
        )

        if devengo_id_excluir:
            qs = qs.exclude(pk=devengo_id_excluir)

        from django.db.models import Sum
        total_dias = qs.aggregate(total=Sum('dias_laborados'))['total'] or Decimal('0')
        total_final = total_dias + nuevos_dias

        if total_final > Decimal('31'):
            raise ValidationError(
                f"El total de días pagados en {periodo_mes} excedería el límite legal (31 días). "
                f"Ya se han registrado {total_dias} días. Con {nuevos_dias} días adicionales, "
                f"el total sería {total_final} días."
            )

        return {
            'total_dias': total_dias,
            'nuevos_dias': nuevos_dias,
            'total_final': total_final,
            'excede_limite': False
        }

    @staticmethod
    def validar_duplicado(empleado_id: int, periodo_mes: str, fecha_pago, empresa_id: int) -> dict:
        """Valida que no exista un devengo duplicado para el mismo periodo y fecha."""
        # Normalizar fecha
        if isinstance(fecha_pago, str):
            try:
                fecha_pago_obj = datetime.strptime(fecha_pago, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
        else:
            fecha_pago_obj = fecha_pago

        existente = Devengo.objects.filter(
            empleado_id=empleado_id,
            periodo_mes=periodo_mes,
            fecha_pago=fecha_pago_obj,
            anulado=False,
            empresa_id=empresa_id,
        ).only('id', 'periodo_mes', 'fecha_pago').first()

        if existente:
            return {
                "error": "Ya existe una nómina para este empleado, periodo y fecha de pago.",
                "detail": f"Ya existe una nómina registrada para el periodo {periodo_mes} "
                         f"con fecha de pago {fecha_pago_obj.strftime('%Y-%m-%d')}.",
                "devengo_existente_id": existente.id,
                "periodo_mes": periodo_mes,
                "fecha_pago": fecha_pago_obj.strftime('%Y-%m-%d'),
                "code": "duplicate_nomina",
            }
        return None

    @staticmethod
    @transaction.atomic
    def procesar_devengo(
        empleado: Empleado,
        contrato: Contrato,
        data: dict,
        empresa_id: int,
        instance: Devengo = None
    ) -> Devengo:
        """
        Orquesta el procesamiento completo de un devengo:
        - Validaciones de negocio
        - Cálculos de nómina
        - Actualización de préstamos
        - Persistencia
        """
        # Validaciones
        if contrato.empresa_id != empresa_id:
            raise ValidationError({'contrato': 'El contrato no pertenece a este tenant.'})

        if contrato.estado != 'ACTIVO' or not contrato.activo:
            raise ValidationError({
                'contrato': f'No se puede registrar nómina: El contrato no está activo '
                           f'(estado actual: {contrato.estado}).'
            })

        if instance and instance.anulado:
            raise ValidationError({'anulado': 'No se puede actualizar una nómina anulada.'})

        # Extraer datos
        dias_laborados = data.get('dias_laborados', instance.dias_laborados if instance else 30)
        otros_devengos = data.get('otros_devengos', Decimal('0'))
        prestamos = data.get('prestamos', Decimal('0'))
        periodo_mes = data.get('periodo_mes')

        # Validar límite de días
        if periodo_mes and dias_laborados:
            DevengoBusinessService.validar_limite_dias_mes(
                empleado_id=empleado.id,
                periodo_mes=periodo_mes,
                nuevos_dias=dias_laborados,
                empresa_id=empresa_id,
                devengo_id_excluir=instance.pk if instance else None
            )

        # Calcular nómina
        calculo = NominaCalculationService.calcular_liquidacion(
            contrato=contrato,
            dias_laborados=dias_laborados,
            otros_devengos=otros_devengos,
            prestamos=prestamos,
            descuentos_operativos=data.get('descuentos_operativos', Decimal('0')),
        )

        # Preparar datos finales
        data['salario_base'] = Decimal(calculo['salario_base'])
        data['auxilio_transporte'] = Decimal(calculo['auxilio_transporte'])
        data['salud_empleado'] = Decimal(calculo['salud_empleado'])
        data['pension_empleado'] = Decimal(calculo['pension_empleado'])

        # Crear o actualizar
        if instance:
            devengo = DevengoCRUDService.actualizar_devengo(instance, data)
        else:
            devengo = DevengoCRUDService.crear_devengo(empleado, data)

        return devengo

    @staticmethod
    @transaction.atomic
    def anular_devengo(devengo: Devengo, empresa_id: int) -> Devengo:
        """Anula un devengo y maneja implicaciones contables."""
        if devengo.empresa_id != empresa_id:
            raise ValidationError({'empresa': 'La nómina no pertenece a este tenant.'})

        return DevengoCRUDService.anular_devengo(devengo)

    @staticmethod
    @transaction.atomic
    def eliminar_devengo(devengo: Devengo, empresa_id: int) -> int:
        """Elimina un devengo y revierte préstamos si aplica."""
        if devengo.empresa_id != empresa_id:
            raise ValidationError({'empresa': 'La nómina no pertenece a este tenant.'})

        # Revertir préstamo si existe
        if devengo.prestamos and devengo.prestamos > 0 and devengo.contrato:
            ContratoCRUDService.actualizar_prestamo_contrato(
                devengo.contrato,
                -devengo.prestamos  # Sumar de vuelta (negativo del descuento)
            )

        return DevengoCRUDService.eliminar_devengo(devengo)


class NominaCalculationService:
    """Cálculos de nómina según normativa colombiana."""

    @staticmethod
    def calcular_liquidacion(
        contrato: Contrato,
        dias_laborados,
        horas_trabajadas=None,
        otros_devengos=0,
        prestamos=0,
        descuentos_operativos=0,
        empresa_id: int = None
    ) -> dict:
        """
        Calcula liquidación de nómina según normativa colombiana.
        Base: Ley 2101 de 2021 (46 horas semanales).
        """
        # Validaciones
        if empresa_id and contrato.empresa_id != empresa_id:
            raise ValidationError({'contrato': 'El contrato no pertenece a la empresa especificada.'})

        if contrato.estado != 'ACTIVO' or not contrato.activo:
            raise ValueError("No se puede calcular nómina para un contrato inactivo")

        # Normalizar días
        try:
            dias_laborados = Decimal(str(dias_laborados))
        except (ValueError, TypeError):
            raise ValueError("Los días laborados deben ser un número válido")

        if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('30'):
            raise ValueError("Los días laborados deben estar entre 0.5 y 30")

        # Constantes normativa
        HORAS_MENSUALES = Decimal('200')  # 46 horas * 4.33 semanas
        DIAS_MENSUALES = Decimal('30')

        # 1. SALARIO BASE PROPORCIONAL
        salario_mensual = Decimal(str(contrato.salario_mensual))

        if horas_trabajadas is not None and horas_trabajadas > 0:
            valor_hora = salario_mensual / HORAS_MENSUALES
            salario_base = valor_hora * Decimal(str(horas_trabajadas))
        else:
            factor = dias_laborados / DIAS_MENSUALES
            salario_base = salario_mensual * factor

        # 2. AUXILIO DE TRANSPORTE
        auxilio_transporte = Decimal('0')
        if contrato.tipo != 'PRESTACION':
            auxilio_mensual = Decimal(str(contrato.auxilio_transporte or 0))
            if auxilio_mensual > 0:
                factor = dias_laborados / DIAS_MENSUALES
                auxilio_transporte = auxilio_mensual * factor

        # 3. IBC (Ingreso Base de Cotización)
        ibc = salario_base  # NO incluye auxilio de transporte

        # 4. DEDUCCIONES DE LEY (4% cada una)
        salud_empleado = Decimal('0')
        pension_empleado = Decimal('0')

        if contrato.tipo in ['FIJO', 'INDEF', 'OBRA']:
            salud_empleado = ibc * Decimal('0.04')
            pension_empleado = ibc * Decimal('0.04')

        # 5. NETO A PAGAR
        devengos = salario_base + auxilio_transporte + Decimal(str(otros_devengos))
        deducciones = (
            salud_empleado + pension_empleado +
            Decimal(str(prestamos)) + Decimal(str(descuentos_operativos))
        )
        neto_pagar = devengos - deducciones

        if neto_pagar < 0:
            logger.warning(f"[NominaCalc] Neto negativo: {neto_pagar} para contrato {contrato.id}")

        return {
            "salario_base": str(salario_base.quantize(Decimal('0.01'))),
            "auxilio_transporte": str(auxilio_transporte.quantize(Decimal('0.01'))),
            "ibc": str(ibc.quantize(Decimal('0.01'))),
            "salud_empleado": str(salud_empleado.quantize(Decimal('0.01'))),
            "pension_empleado": str(pension_empleado.quantize(Decimal('0.01'))),
            "neto_pagar": str(neto_pagar.quantize(Decimal('0.01')))
        }

    @staticmethod
    def calcular_nomina_dinamica(contrato, dias_laborados, horas_extras=0, otros_devengos=0):
        """Cálculo alternativo con horas extras (v2.95)."""
        valor_hora = Decimal(contrato.salario_mensual) / Decimal(220)
        total_horas = Decimal(dias_laborados) * Decimal(8)
        salario_base = valor_hora * total_horas

        auxilio = Decimal(0)
        if contrato.tipo != 'PRESTACION':
            auxilio = (Decimal(contrato.auxilio_transporte) / 30) * Decimal(dias_laborados)

        salud = pension = Decimal(0)
        if contrato.tipo in ['FIJO', 'INDEF', 'OBRA']:
            salud = salario_base * Decimal('0.04')
            pension = salario_base * Decimal('0.04')

        neto = (salario_base + auxilio + Decimal(otros_devengos)) - (salud + pension)

        return {
            "salario_base": str(salario_base.quantize(Decimal('0.01'))),
            "salud_empleado": str(salud.quantize(Decimal('0.01'))),
            "pension_empleado": str(pension.quantize(Decimal('0.01'))),
            "neto_pagar": str(neto.quantize(Decimal('0.01')))
        }
