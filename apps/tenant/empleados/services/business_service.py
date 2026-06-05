"""
Business Service para Empleados - Logica de negocio y orquestacion.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO logica de negocio (validaciones, calculos, orquestacion).
- Delega persistencia a crud_service.py.
- Todas las funciones son @staticmethod.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.empleados.models import Contrato, Devengo, Empleado
from apps.tenant.empleados.services.crud_service import (
    ContratoCRUDService,
    DevengoCRUDService,
    EmpleadoCRUDService,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes monetarias — SSoT para toda la lógica de nómina
# ---------------------------------------------------------------------------
MONEY_Q = Decimal('0.01')          # Cuantizador COP: 2 decimales
_DIAS_MENSUALES = Decimal('30')     # Base comercial Colombia (mes = 30 días)
_HORAS_MENSUALES = Decimal('200')   # Ley 2101/2021: jornada mensual de referencia


def _to_decimal(value, *, allow_negative: bool = False) -> Decimal:
    """
    Convierte cualquier valor numérico entrante a Decimal sin trampa de float.

    Regla de oro: SIEMPRE usar str(value) como puente para evitar
    la imprecisión binaria de float (ej. float(0.1) → 0.100000000000000005...).

    Args:
        value: int, float, str, Decimal o None.
        allow_negative: si False (default), aplica max(0, resultado).

    Returns:
        Decimal seguro, nunca lanza excepción.
    """
    try:
        if isinstance(value, Decimal):
            result = value
        else:
            result = Decimal(str(value)) if value is not None else Decimal('0.00')
    except Exception:
        result = Decimal('0.00')

    if not allow_negative:
        return max(Decimal('0.00'), result)
    return result


class EmpleadoBusinessService:
    """Logica de negocio para Empleado."""

    @staticmethod
    def crear_empleado(data: dict, empresa) -> Empleado:
        """Orquesta la creacion de un empleado con validaciones."""
        return EmpleadoCRUDService.crear_empleado(data, empresa)

    @staticmethod
    def actualizar_empleado(empleado: Empleado, data: dict) -> Empleado:
        """
        Orquesta la actualizacion de un empleado.
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
    def eliminar_empleado_retirado(empleado: Empleado, empresa_id: int = None) -> dict:
        """
        Elimina un empleado RETIRADO y sus dependencias en cascada.
        Condiciones de bloqueo: estado != RETIRADO, contrato activo, nomina activa,
        tareas asignadas en proyectos.
        DSV: verifica empresa_id si se proporciona.
        """
        if empresa_id is not None and empleado.empresa_id != empresa_id:
            raise ValidationError('El empleado no pertenece a la empresa activa.')
        if empleado.estado != 'RETIRADO':
            raise ValidationError(
                f'Solo se pueden eliminar empleados con estado RETIRADO. '
                f'Estado actual: {empleado.estado}.'
            )
        if Contrato.objects.filter(empleado=empleado, estado='ACTIVO').exists() or Contrato.objects.filter(empleado=empleado, activo=True).exists():
            raise ValidationError(
                'No se puede eliminar el empleado porque tiene un contrato activo. '
                'Finalice o cancele el contrato primero.'
            )
        if Devengo.objects.filter(empleado=empleado, anulado=False).exists():
            raise ValidationError(
                'No se puede eliminar el empleado porque tiene nominas activas. '
                'Anule las nominas antes de eliminar.'
            )
        from django.apps import apps as django_apps
        TareaCorta = django_apps.get_model('tenant_proyectos', 'TareaCorta')
        if TareaCorta.objects.filter(empleado=empleado).exists():
            raise ValidationError(
                'No se puede eliminar el empleado porque tiene tareas asignadas en proyectos. '
                'Desvincule las tareas primero.'
            )
        return EmpleadoCRUDService.eliminar_empleado(empleado)

    @staticmethod
    @transaction.atomic
    def cancelar_contratos_activos(empleado: Empleado) -> int:
        """Cancela todos los contratos activos de un empleado."""
        contratos_activos = empleado.contratos.filter(
            empresa_id=empleado.empresa_id,
            estado='ACTIVO',
        )
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
    """Logica de negocio para Contrato."""

    @staticmethod
    @transaction.atomic
    def gestionar_contrato(empleado: Empleado, data: dict, contrato_existente=None) -> Contrato:
        """
        Orquesta la creacion o actualizacion de un contrato.
        Garantiza un unico contrato activo por empleado.
        """
        # Determinar estado final
        estado_final = data.get('estado', contrato_existente.estado if contrato_existente else 'ACTIVO')

        # Si el contrato quedara ACTIVO, desactivar contratos previos
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

        # Normalizar fecha_fin vacia
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
    """Logica de negocio para Devengo (Nomina)."""

    @staticmethod
    def validar_contrato_activo(empleado: Empleado):
        """Valida que el empleado tenga un contrato activo."""
        if not empleado.contratos.filter(
            empresa_id=empleado.empresa_id,
            activo=True,
            estado='ACTIVO',
        ).only('id').exists():
            raise ValidationError(
                "No se puede registrar nomina: El empleado no tiene un contrato activo."
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
        Valida que la suma de dias pagados en un mes no exceda 31.
        """
        try:
            nuevos_dias = Decimal(str(nuevos_dias))
        except (ValueError, TypeError):
            raise ValidationError("Los dias laborados deben ser un numero valido")

        # Sumar dias existentes (no anulados)
        qs = Devengo.objects.filter(
            empleado_id=empleado_id,
            periodo_mes=periodo_mes,
            anulado=False,
            empresa_id=empresa_id
        )

        if devengo_id_excluir:
            qs = qs.exclude(pk=devengo_id_excluir)

        total_dias = qs.aggregate(total=Sum('dias_laborados'))['total'] or Decimal('0')
        total_final = total_dias + nuevos_dias

        if total_final > Decimal('31'):
            raise ValidationError(
                f"El total de dias pagados en {periodo_mes} excederia el limite legal (31 dias). "
                f"Ya se han registrado {total_dias} dias. Con {nuevos_dias} dias adicionales, "
                f"el total seria {total_final} dias."
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
                "error": "Ya existe una nomina para este empleado, periodo y fecha de pago.",
                "detail": f"Ya existe una nomina registrada para el periodo {periodo_mes} "
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
        - Calculos de nomina
        - Actualizacion de prestamos
        - Persistencia
        """
        # Validaciones
        if not empleado:
            raise ValidationError({'empleado': 'Debe especificar un empleado valido.'})
        if not contrato:
            raise ValidationError({'contrato': 'Debe especificar un contrato valido.'})

        if empleado.empresa_id != empresa_id:
            raise ValidationError({'empleado': 'El empleado no pertenece a este tenant.'})

        if contrato.empresa_id != empresa_id:
            raise ValidationError({'contrato': 'El contrato no pertenece a este tenant.'})

        if contrato.empleado_id != empleado.id:
            raise ValidationError({'contrato': 'El contrato no pertenece al empleado indicado.'})

        if empleado.estado == 'RETIRADO':
            raise ValidationError({'empleado': 'No se puede registrar nomina a un empleado retirado.'})

        if contrato.estado != 'ACTIVO' or not contrato.activo:
            raise ValidationError({
                'contrato': f'No se puede registrar nomina: El contrato no esta activo '
                           f'(estado actual: {contrato.estado}).'
            })

        if instance and instance.anulado:
            raise ValidationError({'anulado': 'No se puede actualizar una nomina anulada.'})

        # Extraer datos
        dias_laborados = data.get('dias_laborados', instance.dias_laborados if instance else 30)
        otros_devengos = data.get('otros_devengos', Decimal('0'))
        prestamos = data.get('prestamos', Decimal('0'))
        periodo_mes = data.get('periodo_mes')

        # Validar limite de dias
        if periodo_mes and dias_laborados:
            DevengoBusinessService.validar_limite_dias_mes(
                empleado_id=empleado.id,
                periodo_mes=periodo_mes,
                nuevos_dias=dias_laborados,
                empresa_id=empresa_id,
                devengo_id_excluir=instance.pk if instance else None
            )

        # Calcular nomina
        calculo = NominaCalculationService.calcular_liquidacion(
            contrato=contrato,
            dias_laborados=dias_laborados,
            otros_devengos=otros_devengos,
            prestamos=prestamos,
            descuentos_operativos=data.get('descuentos_operativos', Decimal('0')),
            horas_extras_diurnas=data.get('horas_extras_diurnas', 0),
            horas_extras_nocturnas=data.get('horas_extras_nocturnas', 0),
            recargo_nocturno_horas=data.get('recargo_nocturno_horas', 0),
            recargo_festivo_horas=data.get('recargo_festivo_horas', 0),
        )

        # Preparar datos finales
        data['salario_base']       = Decimal(calculo['salario_base'])
        data['auxilio_transporte'] = Decimal(calculo['auxilio_transporte'])
        data['valor_horas_extras'] = Decimal(calculo['valor_horas_extras'])
        data['salud_empleado']     = Decimal(calculo['salud_empleado'])
        data['pension_empleado']   = Decimal(calculo['pension_empleado'])
        data['neto_pagar']         = Decimal(calculo['neto_pagar'])

        # Crear o actualizar — el @transaction.atomic del metodo ya cubre todo el bloque
        if instance:
            devengo = DevengoCRUDService.actualizar_devengo(instance, data)
        else:
            # FASE 1: Resolucion DIAN
            from apps.tenant.empleados.models import ResolucionDIAN, TransmisionNominaDIAN
            import hashlib
            from django.utils.dateparse import parse_date as _parse_date

            fecha_pago = data.get('fecha_pago')
            if not fecha_pago:
                fecha_pago = timezone.now().date()
            elif isinstance(fecha_pago, str):
                parsed = _parse_date(fecha_pago)
                fecha_pago = parsed if parsed else timezone.now().date()
            elif isinstance(fecha_pago, datetime):
                fecha_pago = fecha_pago.date()

            # Prioridad 1: resolución asignada específicamente al empleado
            resolucion_activa = None
            if empleado.resolucion_dian_id:
                resolucion_activa = ResolucionDIAN.objects.filter(
                    id=empleado.resolucion_dian_id,
                    empresa_id=empresa_id,
                    vigente=True,
                    fecha_inicio__lte=fecha_pago,
                    fecha_fin__gte=fecha_pago,
                ).select_for_update().first()

            # Prioridad 2: resolución activa general de la empresa (fallback)
            if not resolucion_activa:
                resolucion_activa = ResolucionDIAN.objects.filter(
                    empresa_id=empresa_id,
                    vigente=True,
                    fecha_inicio__lte=fecha_pago,
                    fecha_fin__gte=fecha_pago,
                ).select_for_update().first()

            if not resolucion_activa:
                logger.warning(
                    "[DIAN-NOMINA] Sin resolucion activa. empresa_id=%s | fecha_pago=%s",
                    empresa_id, fecha_pago
                )
                raise ValidationError({
                    'resolucion': (
                        'No existe una resolucion DIAN activa y vigente para la fecha de pago '
                        f'{fecha_pago}. Configure una resolucion en Nomina Electronica.'
                    )
                })

            consecutivo_actual = resolucion_activa.consecutivo

            # Defensa en profundidad: verifica rango inferior
            # (invariante garantizado por ResolucionDIAN.save(), pero auditado aqui)
            if consecutivo_actual < resolucion_activa.rango_desde:
                logger.error(
                    "[DIAN-NOMINA] Consecutivo %s fuera del rango autorizado [%s-%s]. "
                    "empresa_id=%s | resolucion_uuid=%s",
                    consecutivo_actual, resolucion_activa.rango_desde,
                    resolucion_activa.rango_hasta, empresa_id, resolucion_activa.uuid
                )
                raise ValidationError({
                    'resolucion': (
                        f'El consecutivo actual ({consecutivo_actual}) esta por debajo del '
                        f'rango autorizado ({resolucion_activa.rango_desde}). '
                        'Corrija la resolucion en Configuracion > Nomina Electronica.'
                    )
                })

            if consecutivo_actual > resolucion_activa.rango_hasta:
                logger.error(
                    "[DIAN-NOMINA] Resolucion agotada. consecutivo=%s rango_hasta=%s. "
                    "empresa_id=%s | resolucion_uuid=%s",
                    consecutivo_actual, resolucion_activa.rango_hasta,
                    empresa_id, resolucion_activa.uuid
                )
                raise ValidationError({
                    'resolucion': (
                        f'La resolucion {resolucion_activa.numero_resolucion} ha agotado '
                        f'sus consecutivos disponibles (ultimo: {resolucion_activa.rango_hasta}). '
                        'Solicite una nueva resolucion a la DIAN.'
                    )
                })

            # Remover 'empleado' de data para evitar conflicto con crear_devengo
            data_copy = data.copy()
            data_copy.pop('empleado', None)
            devengo = DevengoCRUDService.crear_devengo(empleado, data_copy)

            # Generar numero de documento y CUNE
            numero_documento = resolucion_activa.formar_consecutivo(consecutivo_actual)
            cune_raw = f"{numero_documento}{devengo.uuid}{fecha_pago}"
            cune = hashlib.sha256(cune_raw.encode('utf-8')).hexdigest()

            TransmisionNominaDIAN.objects.create(
                empresa_id=empresa_id,
                devengo=devengo,
                resolucion=resolucion_activa,
                numero_documento=numero_documento,
                cune=cune,
                estado_dian='PENDIENTE'
            )

            # Incrementar consecutivo
            resolucion_activa.consecutivo = consecutivo_actual + 1
            resolucion_activa.save(update_fields=['consecutivo'])

        return devengo

    @staticmethod
    @transaction.atomic
    def anular_devengo(devengo: Devengo, empresa_id: int) -> Devengo:
        """Anula un devengo y maneja implicaciones contables."""
        if devengo.empresa_id != empresa_id:
            raise ValidationError({'empresa': 'La nomina no pertenece a este tenant.'})

        return DevengoCRUDService.anular_devengo(devengo)

    @staticmethod
    @transaction.atomic
    def eliminar_devengo(devengo: Devengo, empresa_id: int) -> int:
        """Elimina un devengo y revierte prestamos si aplica."""
        if devengo.empresa_id != empresa_id:
            raise ValidationError({'empresa': 'La nomina no pertenece a este tenant.'})

        # Revertir prestamo si existe
        if devengo.prestamos and devengo.prestamos > 0 and devengo.contrato:
            ContratoCRUDService.actualizar_prestamo_contrato(
                devengo.contrato,
                -devengo.prestamos  # Sumar de vuelta (negativo del descuento)
            )

        return DevengoCRUDService.eliminar_devengo(devengo)


class NominaCalculationService:
    """Calculos de nomina segun normativa colombiana."""

    @staticmethod
    def calcular_liquidacion(
        contrato: Contrato,
        dias_laborados,
        horas_trabajadas=None,
        otros_devengos=0,
        prestamos=0,
        descuentos_operativos=0,
        empresa_id: int = None,
        horas_extras_diurnas=0,
        horas_extras_nocturnas=0,
        recargo_nocturno_horas=0,
        recargo_festivo_horas=0,
    ) -> dict:
        """
        Calcula liquidacion de nomina segun normativa colombiana.
        Base: Ley 2101 de 2021 — jornada 42h/semana vigente desde 2026
        (_HORAS_MENSUALES = 200 = 42h x 4.76 semanas/mes, practica laboral colombiana).
        """
        # Validaciones
        if empresa_id and contrato.empresa_id != empresa_id:
            raise ValidationError({'contrato': 'El contrato no pertenece a la empresa especificada.'})

        if contrato.estado != 'ACTIVO' or not contrato.activo:
            raise ValueError("No se puede calcular nomina para un contrato inactivo")

        # ---------------------------------------------------------------
        # SANITIZACIÓN DE ENTRADAS — Fase 1: todos a Decimal seguro
        # _to_decimal() usa str(value) como puente: evita float trap.
        # allow_negative=False garantiza que ninguna hora/descuento sea < 0.
        # ---------------------------------------------------------------
        try:
            dias_laborados = _to_decimal(dias_laborados)
        except Exception:
            raise ValueError("Los dias laborados deben ser un numero valido")

        if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('31'):
            raise ValueError("Los dias laborados deben estar entre 0.5 y 31")

        # Salario y auxilio vienen de DecimalField — igual pasan por _to_decimal
        # para homogeneizar el tipo y proteger contra None inesperado.
        salario_mensual = _to_decimal(contrato.salario_mensual)
        auxilio_mensual = _to_decimal(contrato.auxilio_transporte)

        # GUARDIA FASE 2: salario_mensual nunca debe ser 0 para evitar cálculos absurdos.
        # El modelo ya tiene MinValueValidator(0.01), pero defensa en profundidad.
        if salario_mensual <= Decimal('0'):
            raise ValidationError({
                'salario_mensual': 'El salario mensual debe ser mayor a cero.'
            })

        # Parámetros opcionales: horas y descuentos deben ser >= 0
        h_extra_diurnas   = _to_decimal(horas_extras_diurnas)
        h_extra_nocturnas = _to_decimal(horas_extras_nocturnas)
        h_rec_nocturno    = _to_decimal(recargo_nocturno_horas)
        h_rec_festivo     = _to_decimal(recargo_festivo_horas)
        otros             = _to_decimal(otros_devengos)
        p_prestamos       = _to_decimal(prestamos)
        p_descuentos      = _to_decimal(descuentos_operativos)

        # ---------------------------------------------------------------
        # TOPES DE HORAS EXTRAS — FASE 4: prevenir ingresos absurdos
        # CST art. 168: max 2h extras/día → ~62h/mes en la práctica.
        # Aplicamos 80h/tipo como tope generoso que atrapa errores de
        # digitación (ej. "800" en vez de "8").
        # ---------------------------------------------------------------
        _MAX_HE_POR_TIPO = Decimal('80')
        _MAX_HE_TOTAL    = Decimal('200')   # No más de un mes completo en H.E.

        _he_map = {
            'horas_extras_diurnas':   h_extra_diurnas,
            'horas_extras_nocturnas': h_extra_nocturnas,
            'recargo_nocturno_horas': h_rec_nocturno,
            'recargo_festivo_horas':  h_rec_festivo,
        }
        for campo_he, val_he in _he_map.items():
            if val_he > _MAX_HE_POR_TIPO:
                raise ValidationError({
                    campo_he: (
                        f'Las horas ingresadas ({val_he}h) superan el tope por tipo '
                        f'({_MAX_HE_POR_TIPO}h). Verifique el valor.'
                    )
                })

        total_he = h_extra_diurnas + h_extra_nocturnas + h_rec_nocturno + h_rec_festivo
        if total_he > _MAX_HE_TOTAL:
            raise ValidationError({
                'horas_extras': (
                    f'El total de horas extras y recargos ({total_he}h) supera el '
                    f'maximo permitido de {_MAX_HE_TOTAL}h por periodo.'
                )
            })

        # VALOR HORA BASE — SSoT para salario proporcional por horas Y para H.E.
        # Ley 2101/2021: base mensual = 200 horas (jornada semanal 42h × 4.76 sem/mes ≈ 200h)
        # _HORAS_MENSUALES = 200 (constante, nunca cero → sin riesgo de ZeroDivisionError)
        valor_hora_base = salario_mensual / _HORAS_MENSUALES

        # 1. SALARIO BASE PROPORCIONAL
        # Modo horas: aplica cuando se registran horas efectivas (ej. contratos part-time)
        # Modo días: base comercial 30 días/mes (norma general Colombia)
        # _DIAS_MENSUALES = 30 (constante, nunca cero → sin riesgo de ZeroDivisionError)
        h_trabajadas = _to_decimal(horas_trabajadas) if horas_trabajadas is not None else Decimal('0')

        # TOPE: horas_trabajadas no puede superar la jornada mensual legal
        if h_trabajadas > _HORAS_MENSUALES:
            raise ValidationError({
                'horas_trabajadas': (
                    f'Las horas trabajadas ({h_trabajadas}h) superan la jornada mensual '
                    f'maxima de {_HORAS_MENSUALES}h (Ley 2101/2021).'
                )
            })

        if h_trabajadas > Decimal('0'):
            salario_base = valor_hora_base * h_trabajadas
        else:
            salario_base = salario_mensual * (dias_laborados / _DIAS_MENSUALES)

        # 2. AUXILIO DE TRANSPORTE
        # Normativa: contratos PRESTACION no tienen auxilio (art. 2 Ley 1393/2010).
        # Se fuerza a 0 explícitamente para blindar el cálculo del IBC.
        if contrato.tipo == 'PRESTACION' or auxilio_mensual <= Decimal('0'):
            auxilio_transporte = Decimal('0')
        else:
            auxilio_transporte = auxilio_mensual * (dias_laborados / _DIAS_MENSUALES)

        # 3. IBC (Ingreso Base de Cotizacion)
        # Normativa: el auxilio de transporte NO integra salario ni hace parte del IBC.
        # (art. 30 Ley 100/1993 — excluido expresamente)
        ibc = salario_base   # ← SOLO salario_base, NUNCA + auxilio_transporte

        # 4. DEDUCCIONES DE LEY (empleado: 4% salud + 4% pensión sobre IBC)
        # Solo aplica para contratos laborales; PRESTACION no cotiza por el empleador.
        salud_empleado   = Decimal('0')
        pension_empleado = Decimal('0')
        if contrato.tipo in ('FIJO', 'INDEF', 'OBRA'):
            salud_empleado   = ibc * Decimal('0.04')   # art. 204 Ley 100/1993
            pension_empleado = ibc * Decimal('0.04')   # art. 20 Ley 100/1993

        # 5. HORAS EXTRAS Y RECARGOS (Decreto 2663/1950 — arts. 168, 170, 179 CST)
        # valor_hora_base ya calculado arriba (SSoT, sin recalcular).
        # Factores (sobre valor_hora_base):
        #   H.E. Diurna    × 1.25  (+25% art. 168 CST)
        #   H.E. Nocturna  × 1.75  (+75% art. 168 CST)
        #   Rec. Nocturno  × 0.35  (+35% extra sobre hora ordinaria, art. 168 CST)
        #   Rec. Festivo   × 1.75  (política empresa — homologado a H.E. nocturna)
        valor_horas_extras = (
            h_extra_diurnas   * Decimal('1.25') +
            h_extra_nocturnas * Decimal('1.75') +
            h_rec_nocturno    * Decimal('0.35') +
            h_rec_festivo     * Decimal('1.75')
        ) * valor_hora_base

        # 6. NETO A PAGAR
        devengos    = salario_base + auxilio_transporte + valor_horas_extras + otros
        deducciones = salud_empleado + pension_empleado + p_prestamos + p_descuentos
        neto_pagar  = devengos - deducciones

        # FASE 4: neto negativo es un error de negocio, no solo una advertencia.
        # El operador debe ajustar descuentos o registrar descuentos parciales
        # en varios periodos antes de que el sistema persista datos incoherentes.
        if neto_pagar < Decimal('0'):
            raise ValidationError({
                'neto_pagar': (
                    f'El neto a pagar no puede ser negativo '
                    f'(devengos: {devengos.quantize(MONEY_Q)}, '
                    f'deducciones: {deducciones.quantize(MONEY_Q)}). '
                    f'Reduzca los descuentos o distribuya en varios periodos.'
                )
            })

        # Cuantizar SOLO en el retorno (no en intermedios para no acumular error de redondeo)
        return {
            "salario_base":       str(salario_base.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "auxilio_transporte": str(auxilio_transporte.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "ibc":                str(ibc.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "valor_horas_extras": str(valor_horas_extras.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "salud_empleado":     str(salud_empleado.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "pension_empleado":   str(pension_empleado.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
            "neto_pagar":         str(neto_pagar.quantize(MONEY_Q, rounding=ROUND_HALF_UP)),
        }

    @staticmethod
    def calcular_dias_360(fecha_inicio, fecha_fin):
        """
        Calcula dias entre dos fechas usando base comercial 30/360 (metodo europeo).
        Regla: d1=31 y d2=31 siempre se ajustan a 30, sin condicion sobre el otro.
        Inclusivo: cuenta ambos extremos (+1).
        Base legal: practica comercial colombiana para liquidacion de prestaciones sociales.
        """
        y1, m1, d1 = fecha_inicio.year, fecha_inicio.month, fecha_inicio.day
        y2, m2, d2 = fecha_fin.year, fecha_fin.month, fecha_fin.day

        if d1 == 31:
            d1 = 30
        if d2 == 31:
            d2 = 30  # Siempre, sin condicion sobre d1 — estandar 30/360 europeo

        dias = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1) + 1
        return max(0, dias)

    @staticmethod
    def calcular_liquidacion_prestaciones(
        contrato: Contrato,
        tipo_liquidacion: str,
        fecha_corte,
        dias_salario_pendiente=0,
        indemnizacion=0
    ) -> dict:
        """
        Calcula liquidacion de prestaciones sociales (Primas, Cesantias, Intereses, Vacaciones)
        y liquidacion definitiva.
        """
        from datetime import date
        from django.utils.dateparse import parse_date

        if isinstance(fecha_corte, str):
            parsed = parse_date(fecha_corte)
            if parsed:
                fecha_corte = parsed
            else:
                fecha_corte = date.today()
        elif isinstance(fecha_corte, datetime):
            fecha_corte = fecha_corte.date()

        # Validar que el empleado tenga al menos una nomina (Devengo) activa (no anulada)
        if not Devengo.objects.filter(contrato=contrato, empresa_id=contrato.empresa_id, anulado=False).exists():
            raise ValidationError(
                "No es posible liquidar a un empleado que no tiene nominas activas registradas en el sistema."
            )

        # Si el contrato es PRESTACION, forzar a cero inmediatamente
        if contrato.tipo == 'PRESTACION':
            return {
                'dias_primas': 0,
                'dias_cesantias': 0,
                'dias_intereses': 0,
                'dias_vacaciones': 0,
                'valor_primas': Decimal('0.00'),
                'valor_cesantias': Decimal('0.00'),
                'valor_intereses': Decimal('0.00'),
                'valor_vacaciones': Decimal('0.00'),
                'total_prestaciones': Decimal('0.00'),
                'dias_salario_pendiente': 0,
                'salario_pendiente': Decimal('0.00'),
                'indemnizacion': Decimal('0.00'),
                'prestamos_deducidos': Decimal('0.00'),
                'total_neto': Decimal('0.00'),
                'fecha_inicio_contrato': contrato.fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_corte': fecha_corte.strftime('%Y-%m-%d'),
                'fecha_inicio_primas': contrato.fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_inicio_cesantias': contrato.fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_inicio_vacaciones': contrato.fecha_inicio.strftime('%Y-%m-%d'),
            }

        # Calcular dias de primas
        # Primas se liquidan por semestre comercial
        if fecha_corte.month <= 6:
            inicio_sem = date(fecha_corte.year, 1, 1)
        else:
            inicio_sem = date(fecha_corte.year, 7, 1)

        start_primas = max(contrato.fecha_inicio, inicio_sem)
        dias_primas = NominaCalculationService.calcular_dias_360(start_primas, fecha_corte)

        # Calcular dias de cesantias, intereses y vacaciones
        # Cesantias se liquidan por ano calendario
        inicio_ano = date(fecha_corte.year, 1, 1)
        start_cesantias = max(contrato.fecha_inicio, inicio_ano)
        dias_cesantias = NominaCalculationService.calcular_dias_360(start_cesantias, fecha_corte)

        dias_intereses = dias_cesantias

        if tipo_liquidacion == 'LIQUIDACION_DEFINITIVA':
            start_vacaciones = contrato.fecha_inicio
            dias_vacaciones = NominaCalculationService.calcular_dias_360(start_vacaciones, fecha_corte)
        else:
            start_vacaciones = start_cesantias
            dias_vacaciones = dias_cesantias

        # Salario Base para Prestaciones: Salario + Auxilio de Transporte
        salario_base_liq = Decimal(str(contrato.salario_mensual)) + Decimal(str(contrato.auxilio_transporte))
        salario_basico = Decimal(str(contrato.salario_mensual))

        # Formulas legales colombianas
        valor_primas = (salario_base_liq * Decimal(str(dias_primas))) / Decimal('360')
        valor_cesantias = (salario_base_liq * Decimal(str(dias_cesantias))) / Decimal('360')
        
        # Intereses de cesantias = (Cesantias * dias * 0.12) / 360
        valor_intereses = (valor_cesantias * Decimal(str(dias_intereses)) * Decimal('0.12')) / Decimal('360')
        
        # Vacaciones = (Salario Basico * dias) / 720
        valor_vacaciones = (salario_basico * Decimal(str(dias_vacaciones))) / Decimal('720')

        total_prestaciones = valor_primas + valor_cesantias + valor_intereses + valor_vacaciones

        # Definir salario pendiente
        dias_sal_pend = _to_decimal(dias_salario_pendiente)
        salario_pendiente = dias_sal_pend * (salario_basico / Decimal('30'))

        # Definir indemnizacion
        val_indemnizacion = _to_decimal(indemnizacion)

        # Prestamos deducidos
        if tipo_liquidacion == 'LIQUIDACION_DEFINITIVA':
            prestamos_deducidos = Decimal(str(contrato.prestamos_empresa or '0.00'))
        else:
            prestamos_deducidos = Decimal('0.00')

        total_neto = total_prestaciones + salario_pendiente + val_indemnizacion - prestamos_deducidos

        return {
            'dias_primas': dias_primas,
            'dias_cesantias': dias_cesantias,
            'dias_intereses': dias_intereses,
            'dias_vacaciones': dias_vacaciones,
            'valor_primas': valor_primas.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'valor_cesantias': valor_cesantias.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'valor_intereses': valor_intereses.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'valor_vacaciones': valor_vacaciones.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'total_prestaciones': total_prestaciones.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'dias_salario_pendiente': int(dias_sal_pend),
            'salario_pendiente': salario_pendiente.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'indemnizacion': val_indemnizacion.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'prestamos_deducidos': prestamos_deducidos.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'total_neto': total_neto.quantize(MONEY_Q, rounding=ROUND_HALF_UP),
            'fecha_inicio_contrato': contrato.fecha_inicio.strftime('%Y-%m-%d'),
            'fecha_corte': fecha_corte.strftime('%Y-%m-%d'),
            'fecha_inicio_primas': start_primas.strftime('%Y-%m-%d'),
            'fecha_inicio_cesantias': start_cesantias.strftime('%Y-%m-%d'),
            'fecha_inicio_vacaciones': start_vacaciones.strftime('%Y-%m-%d'),
        }


