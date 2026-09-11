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

from apps.tenant.empleados.models import Contrato, Devengo, Empleado, LiquidacionPrestacion, PeriodoNomina
from apps.tenant.empleados.services.crud_service import (
    ContratoCRUDService,
    DevengoCRUDService,
    EmpleadoCRUDService,
    PeriodoNominaCRUDService,
)
from apps.tenant.empleados.services.selectors import ContratoSelector, EmpleadoSelector

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
    @transaction.atomic
    def actualizar_empleado(empleado: Empleado, data: dict) -> Empleado:
        """
        Orquesta la actualizacion de un empleado.

        WARNING [mision auditoria nomina FASE 22, 2026-09-10]: si `estado`
        transiciona ACTIVO->RETIRADO, delega SIEMPRE a retirar_empleado()
        -- ya no basta con cambiar el campo `estado` (esa era exactamente
        la brecha detectada: "no permitir que simplemente se cambie
        estado=RETIRADO sin ejecutar las validaciones correspondientes").
        Este es el unico punto de entrada tanto para el PATCH generico del
        ViewSet como para cualquier otro caller futuro.
        """
        nuevo_estado = data.get('estado', empleado.estado)
        estado_anterior = empleado.estado

        if estado_anterior != 'RETIRADO' and nuevo_estado == 'RETIRADO':
            motivo_retiro = data.pop('motivo_retiro', None)
            fecha_retiro = data.pop('fecha_retiro', None)
            data.pop('estado', None)
            # Aplicar el resto de campos editados en el mismo request (ej.
            # telefono, email) antes de ejecutar el flujo de retiro.
            if data:
                empleado = EmpleadoCRUDService.actualizar_empleado(empleado, data)
            resultado = EmpleadoBusinessService.retirar_empleado(
                empleado=empleado,
                motivo_retiro=motivo_retiro,
                fecha_retiro=fecha_retiro,
                empresa_id=empleado.empresa_id,
            )
            return resultado['empleado']

        return EmpleadoCRUDService.actualizar_empleado(empleado, data)

    @staticmethod
    @transaction.atomic
    def retirar_empleado(
        empleado: Empleado,
        motivo_retiro: str,
        fecha_retiro,
        empresa_id: int,
        dias_salario_pendiente: int = 0,
    ) -> dict:
        """
        Flujo controlado de retiro (mision auditoria nomina FASE 21/22,
        2026-09-10): Empleado ACTIVO -> registrar retiro (fecha + motivo) ->
        cerrar contrato -> calcular indemnizacion si aplica -> generar
        liquidacion definitiva -> Empleado RETIRADO.

        Reutiliza NominaCalculationService.calcular_liquidacion_prestaciones()
        (motor ya probado, sin duplicar formulas) para prima/cesantias/
        intereses/vacaciones/salario pendiente; solo la indemnizacion es
        nueva (calcular_indemnizacion_despido()).

        SUPUESTO DOCUMENTADO: si el empleado no tiene contrato activo o no
        tiene ningun Devengo registrado, el retiro procede igual (el
        empleado queda RETIRADO) pero NO se genera LiquidacionPrestacion
        automatica -- no hay base de calculo real que liquidar. Se reporta
        en el resultado ('liquidacion': None), no se falla silenciosamente.
        """
        if empresa_id is not None and empleado.empresa_id != empresa_id:
            raise ValidationError({'empleado': 'El empleado no pertenece a la empresa activa.'})

        if empleado.estado == 'RETIRADO':
            raise ValidationError({'estado': 'El empleado ya esta retirado.'})

        motivos_validos = {c[0] for c in Empleado._meta.get_field('motivo_retiro').choices}
        if not motivo_retiro or motivo_retiro not in motivos_validos:
            raise ValidationError({
                'motivo_retiro': f'Motivo de retiro requerido. Valores validos: {sorted(motivos_validos)}.'
            })

        if not fecha_retiro:
            raise ValidationError({'fecha_retiro': 'La fecha de retiro es requerida para retirar un empleado.'})
        if isinstance(fecha_retiro, str):
            from django.utils.dateparse import parse_date
            parsed = parse_date(fecha_retiro)
            if not parsed:
                raise ValidationError({'fecha_retiro': 'Formato de fecha invalido.'})
            fecha_retiro = parsed
        if fecha_retiro < empleado.fecha_ingreso:
            raise ValidationError({'fecha_retiro': 'La fecha de retiro no puede ser anterior a la fecha de ingreso.'})

        contrato = ContratoSelector.get_activo_for_empleado(empresa_id, empleado.id)

        indemnizacion_info = None
        if contrato:
            indemnizacion_info = NominaCalculationService.calcular_indemnizacion_despido(
                contrato=contrato, fecha_retiro=fecha_retiro, motivo_retiro=motivo_retiro,
            )

        empleado = EmpleadoCRUDService.actualizar_empleado(empleado, {
            'estado': 'RETIRADO',
            'fecha_retiro': fecha_retiro,
            'motivo_retiro': motivo_retiro,
        })

        contrato_cancelado = False
        if contrato:
            Contrato.objects.filter(pk=contrato.pk).update(
                estado='INACTIVO', activo=False, fecha_fin=fecha_retiro,
            )
            contrato_cancelado = True
            logger.info(
                f"[EmpleadoBusiness] Empleado {empleado.id} retirado (motivo={motivo_retiro}, "
                f"fecha={fecha_retiro}). Contrato {contrato.id} cerrado con fecha_fin={fecha_retiro}."
            )
        else:
            logger.info(f"[EmpleadoBusiness] Empleado {empleado.id} retirado (motivo={motivo_retiro}) sin contrato activo.")

        liquidacion = None
        if contrato:
            try:
                valor_indemnizacion = indemnizacion_info['valor'] if indemnizacion_info else Decimal('0.00')
                resultado_calc = NominaCalculationService.calcular_liquidacion_prestaciones(
                    contrato=contrato,
                    tipo_liquidacion='LIQUIDACION_DEFINITIVA',
                    fecha_corte=fecha_retiro,
                    dias_salario_pendiente=dias_salario_pendiente,
                    indemnizacion=valor_indemnizacion,
                )
                # JSONField sin encoder Decimal-safe (igual que el patron ya
                # usado en LiquidacionPrestacionViewSet.create()) -- stringificar
                # todo Decimal antes de guardar o falla con TypeError en save().
                desglose = {
                    k: (str(v) if isinstance(v, Decimal) else v)
                    for k, v in resultado_calc.items()
                }
                desglose['indemnizacion_detalle'] = {
                    k: (str(v) if isinstance(v, Decimal) else v)
                    for k, v in (indemnizacion_info or {}).items()
                }
                liquidacion = LiquidacionPrestacion.objects.create(
                    empresa_id=empresa_id,
                    empleado=empleado,
                    contrato=contrato,
                    tipo_liquidacion='LIQUIDACION_DEFINITIVA',
                    fecha_corte=fecha_retiro,
                    dias_base_calculo=resultado_calc['dias_cesantias'],
                    base_salarial=Decimal(str(contrato.salario_mensual)) + Decimal(str(contrato.auxilio_transporte)),
                    valor_total=resultado_calc['total_neto'],
                    estado='PROYECTADO',
                    desglose_conceptos=desglose,
                    observaciones=f'Generada automaticamente por retiro (motivo: {motivo_retiro}).',
                )
            except ValidationError as exc:
                logger.warning(
                    f"[EmpleadoBusiness] No se genero liquidacion definitiva automatica para "
                    f"empleado {empleado.id}: {exc}"
                )

        return {
            'empleado': empleado,
            'contrato_cancelado': contrato_cancelado,
            'indemnizacion': indemnizacion_info,
            'liquidacion': liquidacion,
        }

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


class PeriodoNominaBusinessService:
    """
    Orquestacion del ciclo de vida de un PeriodoNomina (mision nomina
    2026-08-21). NO calcula montos por si mismo -- delega siempre a
    DevengoBusinessService.procesar_devengo() (el mismo motor ya existente
    y probado), una vez por empleado elegible. Devengo sigue siendo la
    unica fuente de verdad del calculo individual.

    Ver docs/nomina/NOMINA_FLUJO_EMPRESARIAL.md para el detalle completo
    de cada transicion y las suposiciones documentadas donde no habia
    evidencia normativa (Regla Critica de la mision: documentar, no inventar).
    """

    # Mapa de transiciones legales -- una sola fuente de verdad para toda
    # validacion de estado (FASE 3/FASE 27: "nomina aprobada -> no modificar
    # libremente").
    TRANSICIONES_VALIDAS = {
        'ABIERTO':      {'PRELIQUIDADO', 'ANULADO', 'BLOQUEADO'},
        'PRELIQUIDADO': {'EN_REVISION', 'ABIERTO', 'ANULADO', 'BLOQUEADO'},
        'EN_REVISION':  {'APROBADO', 'PRELIQUIDADO', 'ANULADO', 'BLOQUEADO'},
        'APROBADO':     {'PAGADO', 'ANULADO', 'BLOQUEADO'},
        'PAGADO':       {'CERRADO'},
        'CERRADO':      set(),
        'ANULADO':      set(),
        'BLOQUEADO':    set(),  # se desbloquea con desbloquear_periodo(), no con transicionar()
    }

    @staticmethod
    def _validar_transicion(periodo: PeriodoNomina, estado_destino: str):
        permitidos = PeriodoNominaBusinessService.TRANSICIONES_VALIDAS.get(periodo.estado, set())
        if estado_destino not in permitidos:
            raise ValidationError({
                'estado': f'No se puede pasar de {periodo.estado} a {estado_destino}. '
                          f'Transiciones validas desde {periodo.estado}: {sorted(permitidos) or "ninguna"}.'
            })

    @staticmethod
    @transaction.atomic
    def crear_periodo(data: dict, empresa, creado_por=None) -> PeriodoNomina:
        """Crea un periodo en ABIERTO. La unicidad empresa+periodo_mes (entre
        periodos no ANULADOS) la garantiza el constraint de base de datos --
        aqui solo se traduce a un error legible."""
        try:
            return PeriodoNominaCRUDService.crear_periodo(data, empresa, creado_por)
        except Exception as exc:
            if 'uniq_periodo_nomina_activo_per_empresa_mes' in str(exc):
                raise ValidationError({
                    'periodo_mes': f"Ya existe un periodo de nomina activo para {data.get('periodo_mes')} en esta empresa."
                })
            raise

    @staticmethod
    @transaction.atomic
    def preliquidar_periodo(periodo: PeriodoNomina, empresa_id: int) -> dict:
        """
        FASE 7 de la mision: periodo -> empleados elegibles -> contratos ->
        NominaCalculationService (via procesar_devengo) -> Devengos.

        SUPUESTO DOCUMENTADO (sin evidencia normativa de un flujo de
        "novedades" separado -- ver NOMINA_BASELINE.md bloqueador #2): al no
        existir hoy un modelo Novedad, la preliquidacion genera el devengo
        BASE de cada empleado elegible (salario/auxilio/deducciones de ley,
        30 dias, sin horas extras/prestamos/descuentos) usando el mismo
        procesar_devengo() que ya usa la creacion individual. Si un empleado
        especifico necesita horas extras/descuentos reales, se corrige
        despues con el patron ya existente (anular ese devengo puntual +
        crear uno nuevo con los valores correctos vinculado al mismo
        periodo) -- consistente con la Regla de Inmutabilidad (FASE 11), sin
        inventar edicion de devengos ya creados.

        Cada empleado se procesa en su propia unidad atomica (no todo o
        nada): un fallo puntual (ej. limite de dias, sin resolucion DIAN
        vigente) no bloquea al resto de la nomina de la empresa -- se
        reporta en 'fallidos', no se descarta silenciosamente.

        WARNING [mision "correccion arquitectonica" nomina, 2026-09-10]: esto
        sigue siendo una BASE de 30 dias identica para todos -- util como
        punto de partida rapido, NUNCA como sustituto de la liquidacion real
        de cada empleado. Para dias_laborados individuales (8, 15, 5...) use
        la liquidacion individual: POST /devengos/ con el campo `periodo`
        (ver DevengoSerializer.periodo) -- ese es el flujo correcto y
        recomendado; preliquidar_periodo() no debe ser la unica via para
        cerrar un periodo con datos reales.
        """
        PeriodoNominaBusinessService._validar_transicion(periodo, 'PRELIQUIDADO')

        empleados = EmpleadoSelector.get_disponibles_para_periodo(
            empresa_id=empresa_id,
            fecha_inicio=periodo.fecha_inicio,
            fecha_fin=periodo.fecha_fin,
        )

        creados, fallidos = [], []
        for empleado in empleados:
            contrato = ContratoSelector.get_activo_for_empleado(empresa_id, empleado.id)
            if not contrato:
                fallidos.append({'empleado_uuid': str(empleado.uuid), 'error': 'Sin contrato activo.'})
                continue
            try:
                with transaction.atomic():
                    devengo = DevengoBusinessService.procesar_devengo(
                        empleado=empleado,
                        contrato=contrato,
                        data={
                            'contrato': contrato,
                            'dias_laborados': Decimal('30'),
                            'periodo_mes': periodo.periodo_mes,
                            'fecha_inicio': periodo.fecha_inicio,
                            'fecha_fin': periodo.fecha_fin,
                            'fecha_pago': periodo.fecha_pago,
                        },
                        empresa_id=empresa_id,
                    )
                    devengo.periodo = periodo
                    devengo.save(update_fields=['periodo'])
                creados.append({'empleado_uuid': str(empleado.uuid), 'devengo_uuid': str(devengo.uuid)})
            except ValidationError as exc:
                fallidos.append({'empleado_uuid': str(empleado.uuid), 'error': str(exc.detail if hasattr(exc, 'detail') else exc)})

        if not creados:
            raise ValidationError({
                'periodo': 'Ningun empleado elegible pudo preliquidarse. Revise los errores en "fallidos".',
                'fallidos': fallidos,
            })

        PeriodoNominaCRUDService.actualizar_estado(periodo, 'PRELIQUIDADO')
        logger.info(
            "[PeriodoNominaBusiness] Periodo ID=%s preliquidado: %s creados, %s fallidos",
            periodo.id, len(creados), len(fallidos)
        )
        return {'creados': creados, 'fallidos': fallidos}

    @staticmethod
    @transaction.atomic
    def enviar_a_revision(periodo: PeriodoNomina) -> PeriodoNomina:
        PeriodoNominaBusinessService._validar_transicion(periodo, 'EN_REVISION')
        if not periodo.devengos.filter(anulado=False).exists():
            raise ValidationError({'periodo': 'No hay devengos activos para revisar en este periodo.'})
        return PeriodoNominaCRUDService.actualizar_estado(periodo, 'EN_REVISION')

    @staticmethod
    @transaction.atomic
    def rechazar_revision(periodo: PeriodoNomina) -> PeriodoNomina:
        """Devuelve el periodo a PRELIQUIDADO para permitir corregir devengos
        puntuales (anular + recrear) antes de re-enviar a revision."""
        PeriodoNominaBusinessService._validar_transicion(periodo, 'PRELIQUIDADO')
        return PeriodoNominaCRUDService.actualizar_estado(periodo, 'PRELIQUIDADO')

    @staticmethod
    @transaction.atomic
    def aprobar_periodo(periodo: PeriodoNomina, aprobado_por) -> PeriodoNomina:
        """
        FASE 10 de la mision: separar calcular de aprobar. Backend valida
        SIEMPRE (no confia solo en la UI) -- el ViewSet debe restringir esta
        accion con permission_classes de solo-ADMIN ademas de esta validacion
        de estado.
        """
        PeriodoNominaBusinessService._validar_transicion(periodo, 'APROBADO')
        return PeriodoNominaCRUDService.actualizar_estado(
            periodo, 'APROBADO', aprobado_por=aprobado_por, fecha_aprobacion=timezone.now(),
        )

    @staticmethod
    @transaction.atomic
    def marcar_pagado(periodo: PeriodoNomina, pagado_por, fecha_pago_real=None) -> PeriodoNomina:
        """
        SUPUESTO DOCUMENTADO (NOMINA_BASELINE.md §4): no existe integracion
        real con Bancos para nomina hoy. Este metodo es un registro MANUAL
        del hecho "se pago" -- no ejecuta ninguna transferencia ni valida
        contra un saldo bancario real. Ver FASE 12/13 de la mision para el
        trabajo pendiente de integracion real, documentado como gap, no
        fabricado aqui.
        """
        PeriodoNominaBusinessService._validar_transicion(periodo, 'PAGADO')
        return PeriodoNominaCRUDService.actualizar_estado(
            periodo, 'PAGADO',
            pagado_por=pagado_por,
            fecha_pago_real=fecha_pago_real or timezone.now().date(),
        )

    @staticmethod
    @transaction.atomic
    def cerrar_periodo(periodo: PeriodoNomina) -> PeriodoNomina:
        """
        mision auditoria nomina FASE 15 (2026-09-10): "No permitir CERRAR si
        hay empleados pendientes." Antes de esta correccion, cerrar_periodo()
        solo validaba la transicion de estado (PAGADO->CERRADO) -- un periodo
        con empleados elegibles que nunca llegaron a tener un Devengo (por
        fallidos en la preliquidacion, o por altas posteriores a esa
        preliquidacion) podia cerrarse igual, congelandolo sin que jamas se
        les pagara. enviar_a_revision()/aprobar()/marcar_pagado() se dejan
        SIN este bloqueo -- ese comportamiento (avanzar con preliquidacion
        parcial) fue una decision de diseño ya documentada y justificada en
        NOMINA_FLUJO_EMPRESARIAL.md §3; el conteo de 'pendientes' ya es
        visible en esas pantallas via PeriodoNominaSelector.get_resumen()
        para revision humana, sin bloquear las transiciones intermedias.
        """
        PeriodoNominaBusinessService._validar_transicion(periodo, 'CERRADO')

        pendientes = EmpleadoSelector.get_empleados_pendientes_para_periodo(periodo)
        if pendientes.exists():
            nombres = [f"{e.nombre_completo} ({e.numero_documento})" for e in pendientes[:10]]
            raise ValidationError({
                'periodo': (
                    f"No se puede cerrar el periodo: {pendientes.count()} empleado(s) "
                    f"elegible(s) todavia no tienen nomina liquidada en este periodo. "
                    f"Preliquide o registre su nomina, o retirelos, antes de cerrar."
                ),
                'pendientes': nombres,
            })

        return PeriodoNominaCRUDService.actualizar_estado(periodo, 'CERRADO')

    @staticmethod
    @transaction.atomic
    def anular_periodo(periodo: PeriodoNomina, empresa_id: int) -> PeriodoNomina:
        """Anula el periodo Y, en cascada, todos sus devengos activos (misma
        semantica de anulacion ya usada por DevengoBusinessService.anular_devengo
        -- nunca hard-delete, mismo principio de inmutabilidad/trazabilidad)."""
        PeriodoNominaBusinessService._validar_transicion(periodo, 'ANULADO')
        for devengo in periodo.devengos.filter(anulado=False):
            DevengoBusinessService.anular_devengo(devengo, empresa_id)
        return PeriodoNominaCRUDService.actualizar_estado(periodo, 'ANULADO')

    @staticmethod
    @transaction.atomic
    def bloquear_periodo(periodo: PeriodoNomina) -> PeriodoNomina:
        """Pausa reversible -- guarda el estado previo en observaciones para
        que desbloquear_periodo() pueda restaurarlo sin exigir que el
        llamador lo recuerde (sin agregar un campo nuevo solo para esto)."""
        PeriodoNominaBusinessService._validar_transicion(periodo, 'BLOQUEADO')
        estado_previo = periodo.estado
        periodo.observaciones = (periodo.observaciones or '') + f'\n[BLOQUEADO desde {estado_previo} en {timezone.now().isoformat()}]'
        periodo.save(update_fields=['observaciones'])
        return PeriodoNominaCRUDService.actualizar_estado(periodo, 'BLOQUEADO')

    @staticmethod
    @transaction.atomic
    def desbloquear_periodo(periodo: PeriodoNomina, estado_destino: str) -> PeriodoNomina:
        if periodo.estado != 'BLOQUEADO':
            raise ValidationError({'estado': 'El periodo no esta bloqueado.'})
        if estado_destino not in {'ABIERTO', 'PRELIQUIDADO', 'EN_REVISION', 'APROBADO'}:
            raise ValidationError({'estado_destino': f'Destino de desbloqueo invalido: {estado_destino}.'})
        return PeriodoNominaCRUDService.actualizar_estado(periodo, estado_destino)


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

    # Motivos que NO generan indemnizacion por despido (CST art. 64): la ley
    # solo indemniza la terminacion UNILATERAL del empleador SIN justa causa.
    MOTIVOS_SIN_INDEMNIZACION_DESPIDO = {
        'RENUNCIA', 'MUTUO_ACUERDO', 'VENCIMIENTO_TERMINO',
        'TERMINACION_OBRA', 'JUSTA_CAUSA', 'MUERTE', 'OTRO',
    }

    @staticmethod
    def calcular_indemnizacion_despido(contrato: Contrato, fecha_retiro, motivo_retiro: str) -> dict:
        """
        Indemnizacion por terminacion unilateral del contrato SIN JUSTA CAUSA
        por parte del empleador (CST art. 64, modificado por Ley 789/2002
        art. 28). Mision auditoria nomina FASE 21 (2026-09-10): "no asumir
        automaticamente indemnizacion. Determinarla segun tipo contrato,
        motivo, causal, regla legal aplicable. Mostrar la explicacion del
        calculo" -- de ahi que el dict de retorno siempre incluya
        'aplica' y 'explicacion', no solo el monto.

        SUPUESTOS DOCUMENTADOS (Regla Critica de la mision: no inventar sin
        evidencia normativa):
        - Solo motivo_retiro == 'SIN_JUSTA_CAUSA' genera esta indemnizacion.
          Los demas motivos (renuncia, mutuo acuerdo, vencimiento normal del
          plazo, terminacion normal de obra, justa causa, muerte) retornan
          monto 0 con la explicacion de por que no aplica.
        - Base salarial: solo salario_mensual del contrato (SIN auxilio de
          transporte -- jurisprudencia mayoritaria lo excluye de esta base
          por no ser factor salarial permanente).
        - "Años de servicio" se cuenta con calcular_dias_360() (misma
          convencion comercial 30/360 que el resto del motor de nomina,
          NO 365) para mantener una sola definicion de "año" en toda la app.
        - SMLMV: lee settings.SMLMV_VIGENTE (ver config/settings.py) -- un
          valor desactualizado sesga el umbral legal de 10 SMLMV.
        - PRESTACION: no aplica (es un contrato civil, no laboral bajo CST).
        - OBRA sin fecha_fin pactada: no es posible calcular "tiempo que
          falte para terminar la obra" sin un dato inventado -- retorna 0
          con explicacion pidiendo fecha_fin o ajuste manual.
        """
        from django.conf import settings as dj_settings

        base = {
            'aplica': False,
            'dias': 0,
            'valor': Decimal('0.00'),
            'base_legal': 'CST art. 64 (modificado por Ley 789/2002 art. 28)',
            'explicacion': '',
        }

        if motivo_retiro in NominaCalculationService.MOTIVOS_SIN_INDEMNIZACION_DESPIDO:
            base['explicacion'] = (
                f"Motivo de retiro '{motivo_retiro}' no genera indemnizacion por "
                f"despido: el CST art. 64 solo indemniza la terminacion unilateral "
                f"del contrato SIN JUSTA CAUSA por parte del empleador."
            )
            return base

        if motivo_retiro != 'SIN_JUSTA_CAUSA':
            base['explicacion'] = f"Motivo de retiro '{motivo_retiro}' no reconocido para calculo de indemnizacion."
            return base

        if contrato.tipo == 'PRESTACION':
            base['explicacion'] = (
                'Contrato de Prestacion de Servicios: no es un contrato laboral '
                'bajo el CST, no genera indemnizacion por despido.'
            )
            return base

        salario_basico = _to_decimal(contrato.salario_mensual)
        salario_diario = salario_basico / _DIAS_MENSUALES

        if contrato.tipo == 'FIJO':
            if not contrato.fecha_fin or contrato.fecha_fin <= fecha_retiro:
                base['explicacion'] = (
                    'Contrato a Termino Fijo sin fecha_fin vigente posterior al '
                    'retiro: no hay tiempo restante que indemnizar.'
                )
                return base
            dias = NominaCalculationService.calcular_dias_360(fecha_retiro, contrato.fecha_fin)
            valor = (dias * salario_diario).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
            return {
                'aplica': True,
                'dias': dias,
                'valor': valor,
                'base_legal': base['base_legal'],
                'explicacion': (
                    f"Contrato a Termino Fijo, despido sin justa causa: se indemniza "
                    f"el tiempo que falta para el vencimiento pactado ({dias} dias "
                    f"hasta {contrato.fecha_fin}) a razon de salario diario "
                    f"({salario_diario.quantize(MONEY_Q)}) = {valor} COP."
                ),
            }

        if contrato.tipo == 'OBRA':
            if not contrato.fecha_fin:
                base['explicacion'] = (
                    'Contrato de Obra o Labor sin fecha_fin pactada: no es posible '
                    'determinar el "tiempo que falte para terminar la obra" sin ese '
                    'dato. Ajuste manual requerido (ver desglose_conceptos).'
                )
                return base
            dias = max(NominaCalculationService.calcular_dias_360(fecha_retiro, contrato.fecha_fin), 15)
            valor = (dias * salario_diario).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
            return {
                'aplica': True,
                'dias': dias,
                'valor': valor,
                'base_legal': base['base_legal'],
                'explicacion': (
                    f"Contrato de Obra o Labor, despido sin justa causa: se indemniza "
                    f"el tiempo que falta para terminar la obra (minimo legal 15 dias), "
                    f"{dias} dias a razon de salario diario "
                    f"({salario_diario.quantize(MONEY_Q)}) = {valor} COP."
                ),
            }

        # INDEF -- escala de Ley 789/2002 art. 28 segun umbral de 10 SMLMV.
        smlmv = _to_decimal(dj_settings.SMLMV_VIGENTE)
        umbral = smlmv * Decimal('10')
        dias_servicio = NominaCalculationService.calcular_dias_360(contrato.fecha_inicio, fecha_retiro)

        if salario_basico < umbral:
            dias_base, dias_adicional_por_anio = Decimal('30'), Decimal('20')
        else:
            dias_base, dias_adicional_por_anio = Decimal('20'), Decimal('15')

        if dias_servicio <= 360:
            dias = dias_base
        else:
            anios_adicionales = (Decimal(dias_servicio) - Decimal('360')) / Decimal('360')
            dias = dias_base + (anios_adicionales * dias_adicional_por_anio)

        valor = (dias * salario_diario).quantize(MONEY_Q, rounding=ROUND_HALF_UP)
        return {
            'aplica': True,
            'dias': float(dias.quantize(Decimal('0.01'))),
            'valor': valor,
            'base_legal': base['base_legal'],
            'explicacion': (
                f"Contrato a Termino Indefinido, despido sin justa causa. Salario "
                f"({salario_basico}) {'menor' if salario_basico < umbral else 'mayor o igual'} "
                f"a 10 SMLMV ({umbral}, SMLMV={smlmv}). {dias_servicio} dias de servicio "
                f"({dias_servicio / 360:.2f} años). Formula: {dias_base} dias primer año + "
                f"{dias_adicional_por_anio} dias/año adicional (prorrateado) = "
                f"{dias:.2f} dias x salario diario ({salario_diario.quantize(MONEY_Q)}) = {valor} COP."
            ),
        }


