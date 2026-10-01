"""
ProcurementBudgetControlService -- control financiero unico
Cotizacion -> Requisiciones -> OrdenCompra.

PLAN_CENTRO_APROBACIONES_DASHBOARD_COMPRAS.md #17-25: "una regla, una
implementacion, muchos consumidores" (#20) -- ningun otro servicio debe
reimplementar estas sumas. Fases 1-4 de esa mision: el servicio existe y lo
consume `OrdenCompraBusinessService.crear_orden_compra()` (unico consumidor
real por ahora); el enganche en la aprobacion de Requisicion
(`validar_requisicion_contra_cotizacion`, necesario para bloquear en el
Centro de Aprobaciones) es Fase 5, DEFERRED explicito -- el metodo ya existe
y esta listo para ese enganche, pero nada lo llama todavia.

Todos los metodos son `@staticmethod`, sin estado propio -- reciben las
instancias ya resueltas (DSV) por el caller, nunca resuelven UUIDs por su
cuenta (esa responsabilidad es del Business Service que orquesta el DSV real
del dominio, mismo criterio que el resto del proyecto).
"""

from decimal import Decimal
from typing import Any

from django.db.models import Sum

# Estados de RequisicionCompra que representan compromiso presupuestal real
# (#19 del plan, verificado contra el codigo real -- no es una hipotesis sin
# validar: son exactamente los estados no-terminales-negativos de
# RequisicionCompraBusinessService.TRANSICIONES_VALIDAS).
ESTADOS_REQUISICION_ACTIVA = (
    "PENDIENTE_APROBACION",
    "APROBADA",
    "EN_PROCESO_COMPRA",
    "PARCIALMENTE_ATENDIDA",
    "ATENDIDA",
)

# Estados de OrdenCompra que representan consumo real de saldo -- todos
# menos 'ANULADA' (unico estado terminal negativo real, ver
# OrdenCompra.ESTADO_CHOICES en apps/tenant/compras/models.py).
ESTADOS_ORDEN_ACTIVA = ("BORRADOR", "PENDIENTE", "APROBADA", "PARCIAL", "RECIBIDA")


class ProcurementBudgetControlService:
    @staticmethod
    def obtener_saldo_cotizacion(cotizacion) -> Decimal:
        """total_con_impuestos de la Cotizacion menos la suma de
        total_estimado de sus Requisiciones activas (tipo_relacion='ORIGEN'
        -- la cotizacion de origen obligatoria, nunca vinculos adicionales
        de contexto)."""
        from apps.tenant.compras.requisiciones.models import RequisicionCotizacion

        total_requisiciones = RequisicionCotizacion.objects.filter(
            empresa_id=cotizacion.empresa_id,
            cotizacion_id=cotizacion.id,
            tipo_relacion="ORIGEN",
            requisicion__estado__in=ESTADOS_REQUISICION_ACTIVA,
        ).aggregate(total=Sum("requisicion__total_estimado"))["total"] or Decimal("0.00")

        return (cotizacion.total_con_impuestos or Decimal("0.00")) - total_requisiciones

    @staticmethod
    def obtener_saldo_requisicion(requisicion) -> Decimal:
        """total_estimado de la Requisicion menos la suma de monto_asignado
        de sus OrdenCompraRequisicion activas."""
        from apps.tenant.compras.models import OrdenCompraRequisicion

        total_asignado = OrdenCompraRequisicion.objects.filter(
            empresa_id=requisicion.empresa_id,
            requisicion_id=requisicion.id,
            orden_compra__estado__in=ESTADOS_ORDEN_ACTIVA,
        ).aggregate(total=Sum("monto_asignado"))["total"] or Decimal("0.00")

        return (requisicion.total_estimado or Decimal("0.00")) - total_asignado

    @staticmethod
    def validar_requisicion_contra_cotizacion(requisicion, cotizacion) -> tuple[bool, str]:
        """Bloquea si la SUMA de requisiciones activas de la Cotizacion
        (incluyendo `requisicion`, que puede o no estar ya contada segun el
        punto del flujo en que se llame) supera `cotizacion.total_con_impuestos`
        (#17). Enganche real (llamar esto antes de aprobar una Requisicion)
        es Fase 5 -- este metodo queda listo, sin caller todavia."""
        saldo = ProcurementBudgetControlService.obtener_saldo_cotizacion(cotizacion)
        if saldo < Decimal("0.00"):
            exceso = -saldo
            return False, (
                f"Las requisiciones activas de la cotizacion {cotizacion.numero_cotizacion} "
                f"superan en ${exceso:,.2f} el valor autorizado (${cotizacion.total_con_impuestos:,.2f})."
            )
        return True, ""

    @staticmethod
    def validar_consolidacion_oc(requisicion_montos: dict[Any, Decimal]) -> tuple[bool, str]:
        """Por cada (requisicion, monto) en `requisicion_montos`: el monto
        asignado nunca puede exceder el saldo disponible de esa requisicion
        (#23/#24 -- nunca consumo negativo ni doble consumo). No persiste
        nada; el caller (crear_orden_compra, dentro de su propia
        transaction.atomic + select_for_update) es responsable de la
        escritura atomica."""
        for requisicion, monto in requisicion_montos.items():
            if monto < Decimal("0.00"):
                return (
                    False,
                    f"El monto asignado a la requisicion {requisicion.numero_documento} no puede ser negativo.",
                )
            saldo = ProcurementBudgetControlService.obtener_saldo_requisicion(requisicion)
            if monto > saldo:
                return False, (
                    f"La requisicion {requisicion.numero_documento} tiene un saldo disponible de "
                    f"${saldo:,.2f}, pero se le esta asignando ${monto:,.2f}."
                )
        return True, ""

    @staticmethod
    def repartir_monto_proporcional(
        requisiciones: list, total_orden: Decimal
    ) -> dict[Any, Decimal]:
        """Reparte `total_orden` entre `requisiciones` proporcional al
        `total_estimado` de cada una. Decision explicita (el plan no fija el
        criterio de reparto, solo exige que la suma nunca exceda el saldo,
        ver validar_consolidacion_oc) -- usado cuando el caller no especifica
        montos explicitos por requisicion."""
        total_estimado_acumulado = sum((r.total_estimado or Decimal("0.00")) for r in requisiciones)
        if total_estimado_acumulado <= Decimal("0.00"):
            # Sin base para prorratear (ej. todas en $0) -- reparto igualitario.
            monto_igual = (total_orden / len(requisiciones)).quantize(Decimal("0.01"))
            return {r: monto_igual for r in requisiciones}

        montos = {}
        acumulado = Decimal("0.00")
        for i, requisicion in enumerate(requisiciones):
            if i == len(requisiciones) - 1:
                # Ultima: recibe el remanente exacto, evita error de redondeo.
                montos[requisicion] = total_orden - acumulado
            else:
                proporcion = (
                    requisicion.total_estimado or Decimal("0.00")
                ) / total_estimado_acumulado
                monto = (total_orden * proporcion).quantize(Decimal("0.01"))
                montos[requisicion] = monto
                acumulado += monto
        return montos
