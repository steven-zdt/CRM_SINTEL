"""
Materialización de asientos contables desde transacciones de gastos.

Este módulo expone la función principal para convertir DocumentoSoporte + Gasto
en TransaccionEconomica DTO, que luego el Contabilizador materializa como asiento.

Usage:
    from apps.tenant.gastos.models import Gasto
    from apps.tenant.contabilidad.services.asientos_service import materializar_asiento_desde_gasto

    gasto = Gasto.objects.get(id=1)
    asiento = materializar_asiento_desde_gasto(gasto)
"""

from decimal import Decimal

from apps.tenant.contabilidad.integracion.contabilizador import Contabilizador
from apps.tenant.contabilidad.integracion.dtos import (
    DocumentoOrigen,
    ImpuestoLinea,
    LineaTransaccion,
    TerceroSnapshot,
    TipoTercero,
    TipoTransaccion,
    TransaccionEconomica,
)


def materializar_asiento_desde_gasto(gasto):
    """
    Materializa un Gasto (Documento Soporte + clasificación) en asiento contable.

    Construye TransaccionEconomica DTO y lo pasa al Contabilizador para
    materialización atómica como AsientoContable + MovimientoContable.

    Estructura de asiento (cuadrado):
        DEBE 51xxxx Gasto                    [subtotal]
        HABER 236540 Retefuente              [retefuente] (si > 0)
        HABER 236801 ReteICA                 [reteica] (si > 0)
        HABER 233595 CXP Proveedor           [total = subtotal - retenciones]
        ─────────────────────────────────────────────
        DEBE total = HABER total = subtotal ✓

    Args:
        gasto: Gasto instance con documento_soporte relacionado

    Returns:
        Newly created AsientoContable instance

    Raises:
        AsientoYaExisteError: Si ya existe asiento para este documento
        PeriodoCerradoError: Si período contable está cerrado
        ReglaContableNoDefinidaError: Si no hay ReglaContable para gastos
        AsientoNoCuadradoError: Si los débitos no igualan créditos
    """
    ds = gasto.documento_soporte

    # Build impuestos (retenciones) — always on HABER side
    impuestos_lineas = []

    if ds.retefuente and ds.retefuente > 0:
        impuestos_lineas.append(
            ImpuestoLinea(
                tipo='RETEFUENTE',
                base=ds.subtotal,
                porcentaje=Decimal(ds.retefuente_porcentaje) * 100,
                valor=ds.retefuente,
                lado='HABER',  # Retenciones are credit/liability
            )
        )

    if ds.reteica and ds.reteica > 0:
        impuestos_lineas.append(
            ImpuestoLinea(
                tipo='RETEICA',
                base=ds.subtotal,
                porcentaje=Decimal(ds.reteica_porcentaje) * 100,
                valor=ds.reteica,
                lado='HABER',  # Retenciones are credit/liability
            )
        )

    # Build lineas: gasto (DEBE) + impuestos (HABER) + CXP (HABER)
    lineas = [
        # Principal gasto line — DEBE (debit side)
        LineaTransaccion(
            concepto='GASTO_OPERATIVO',
            monto=ds.subtotal,
            lado='DEBE',  # Gastos go to debit
            cuenta_hint=gasto.codigo_contable or None,  # Use NIIF code if configured
            impuestos=impuestos_lineas,
            # centro_costo is a CharField label (e.g. 'OPERATIVO'), not a numeric ID
            # LineaTransaccion.centro_costo_id expects Optional[int] — omit for now
        ),
        # Payable line — HABER (credit side)
        LineaTransaccion(
            concepto='CXP_PROVEEDOR',
            monto=ds.total,  # total = subtotal - retenciones
            lado='HABER',  # Payables are credit
        ),
    ]

    # Build DTO
    transaccion = TransaccionEconomica(
        tipo=TipoTransaccion.COMPRA_GASTO,
        fecha=ds.fecha,
        descripcion=f"Gasto {ds.numero_documento} — {ds.vendedor_nombre}",
        tercero=TerceroSnapshot(
            tipo=TipoTercero.PROVEEDOR,
            id_origen=ds.id,
            nit=ds.vendedor_nit,
            razon_social=ds.vendedor_nombre,
        ),
        lineas=lineas,
        documento_origen=DocumentoOrigen(
            app_label='tenant_gastos',
            modelo='DocumentoSoporte',
            id=ds.id,
            numero=ds.numero_documento,
        ),
        observaciones=gasto.observaciones or '',
    )

    # Materialize via Contabilizador
    contabilizador = Contabilizador(empresa_id=gasto.empresa_id)
    asiento = contabilizador.contabilizar(transaccion)

    return asiento
