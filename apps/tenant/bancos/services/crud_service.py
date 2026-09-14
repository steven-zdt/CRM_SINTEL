import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)

logger = logging.getLogger(__name__)

TOLERANCIA_APLICACION = Decimal("0.01")

class CuentaBancariaCRUDService:
    """Pure CRUD operations for CuentaBancaria."""

    @staticmethod
    @transaction.atomic
    def crear_cuenta(data: dict, empresa) -> CuentaBancaria:
        """Create a new bank account."""
        numero = data.get("numero")
        if CuentaBancaria.objects.filter(empresa=empresa, numero=numero).exists():
            raise ValidationError(
                f"Ya existe una cuenta bancaria con el numero {numero} para esta empresa."
            )
        cuenta = CuentaBancaria(empresa=empresa, **data)
        cuenta.full_clean()
        cuenta.save()
        logger.info(f"[CuentaBancariaCRUD] Creada cuenta ID={cuenta.id}")
        return cuenta

    @staticmethod
    @transaction.atomic
    def editar_cuenta(cuenta: CuentaBancaria, data: dict) -> CuentaBancaria:
        """Edit an existing bank account."""
        for field, value in data.items():
            setattr(cuenta, field, value)
        cuenta.full_clean()
        cuenta.save()
        logger.info(f"[CuentaBancariaCRUD] Editada cuenta ID={cuenta.id}")
        return cuenta

    @staticmethod
    @transaction.atomic
    def eliminar_cuenta(cuenta: CuentaBancaria) -> None:
        """Delete a bank account if no statements are linked."""
        if cuenta.extractos.exists():
            raise ValidationError(
                "No se puede eliminar la cuenta bancaria porque tiene extractos asociados."
            )
        cuenta_id = cuenta.id
        cuenta.delete()
        logger.info(f"[CuentaBancariaCRUD] Eliminada cuenta ID={cuenta_id}")

class ExtractoBancarioCRUDService:
    """Pure CRUD operations for ExtractoBancario."""

    @staticmethod
    @transaction.atomic
    def crear_extracto(data: dict, empresa) -> ExtractoBancario:
        """Create a bank statement record."""
        cuenta = data.get("cuenta")
        mes = data.get("mes")
        anio = data.get("anio")

        # DSV: verify cuenta belongs to empresa — last line of defense against FK injection
        if cuenta is not None and cuenta.empresa_id != empresa.id:
            raise ValidationError(
                "La cuenta bancaria seleccionada no existe o no pertenece a esta empresa."
            )

        if ExtractoBancario.objects.filter(
            empresa=empresa, cuenta=cuenta, mes=mes, anio=anio
        ).exists():
            raise ValidationError(
                f"Ya existe un extracto registrado para el periodo {anio}/{mes:02d} en esta cuenta."
            )

        extracto = ExtractoBancario(empresa=empresa, **data)
        extracto.full_clean()
        extracto.save()
        logger.info(f"[ExtractoBancarioCRUD] Creado extracto ID={extracto.id}")
        return extracto

    @staticmethod
    @transaction.atomic
    def editar_extracto(extracto: ExtractoBancario, data: dict) -> ExtractoBancario:
        """Edit a bank statement record."""
        for field, value in data.items():
            setattr(extracto, field, value)
        extracto.full_clean()
        extracto.save()
        logger.info(f"[ExtractoBancarioCRUD] Editado extracto ID={extracto.id}")
        return extracto

    @staticmethod
    @transaction.atomic
    def eliminar_extracto(extracto: ExtractoBancario) -> None:
        """Delete a bank statement and all its transactions."""
        extracto_id = extracto.id
        extracto.delete()  # CASCADE deletes related TransaccionBancaria records
        logger.info(f"[ExtractoBancarioCRUD] Eliminado extracto ID={extracto_id}")

class TransaccionBancariaCRUDService:
    """Pure CRUD operations for TransaccionBancaria."""

    @staticmethod
    @transaction.atomic
    def crear_transaccion(data: dict, empresa) -> TransaccionBancaria:
        """Create a single bank transaction."""
        transaccion = TransaccionBancaria(empresa=empresa, **data)
        transaccion.full_clean()
        transaccion.save()
        return transaccion

    @staticmethod
    @transaction.atomic
    def crear_transacciones_bulk(transacciones_list: list, extracto: ExtractoBancario, empresa) -> list:
        """Bulk create transactions for a specific statement."""
        to_create = []
        for tx_data in transacciones_list:
            tx = TransaccionBancaria(
                empresa=empresa,
                extracto=extracto,
                **tx_data
            )
            to_create.append(tx)

        created = TransaccionBancaria.objects.bulk_create(to_create)
        logger.info(f"[TransaccionBancariaCRUD] Creadas {len(created)} transacciones bulk para extracto ID={extracto.id}")
        return created

    @staticmethod
    @transaction.atomic
    def conciliar_transaccion(transaccion: TransaccionBancaria, data: dict) -> TransaccionBancaria:
        """Vincula una transaccion con factura_uuid, proveedor_uuid y/o cliente_uuid."""
        CAMPOS_CONCILIACION = ("factura_uuid", "proveedor_uuid", "cliente_uuid", "conciliado", "notas_conciliacion")

        # REM P1-04 (docs/remediation/REM-P1-04.md): sin validacion previa,
        # se podia vincular una transaccion bancaria (pago) con una factura
        # emitida DESPUES de la fecha del pago -- un pago no puede ocurrir
        # antes de que exista el documento que paga. Solo se valida cuando
        # se esta vinculando/cambiando factura_uuid (no proveedor_uuid/
        # cliente_uuid, que enlazan a un tercero completo, no a un documento
        # con fecha propia). Si la factura no resuelve (soft-reference sin
        # match), no se bloquea -- mismo criterio ya usado en todo el
        # proyecto para soft-references (Kardex, Retenciones): un dato
        # incompleto no bloquea la operacion, solo un dato claramente
        # inconsistente lo hace.
        nueva_factura_uuid = data.get("factura_uuid")
        if nueva_factura_uuid and nueva_factura_uuid != transaccion.factura_uuid:
            from apps.tenant.facturas.services.business_service import FacturaInterAppAPI
            factura = FacturaInterAppAPI.get_by_id(factura_uuid=nueva_factura_uuid)
            if factura is not None and factura.fecha_emision is not None:
                fecha_pago = data.get("fecha", transaccion.fecha)
                fecha_doc = factura.fecha_emision
                if hasattr(fecha_doc, 'date'):
                    fecha_doc = fecha_doc.date()
                if fecha_pago < fecha_doc:
                    raise ValidationError({
                        "factura_uuid": (
                            f"La fecha de la transaccion ({fecha_pago}) es anterior a la "
                            f"fecha de emision de la factura ({fecha_doc}). Un pago no "
                            f"puede ocurrir antes del documento que paga."
                        )
                    })

        # DEUDA-C03 "Clientes + Cartera" (decision del usuario, 2026-09-11):
        # capturado ANTES de aplicar los cambios, para saber si `conciliado`
        # esta transicionando False/None -> True AHORA (evita disparar un
        # segundo abono en Cartera si se re-guarda una conciliacion ya
        # existente sin cambiar el flag, ej. solo se edita notas_conciliacion).
        conciliado_previo = transaccion.conciliado

        campos_a_guardar = []
        for field in CAMPOS_CONCILIACION:
            if field in data:
                setattr(transaccion, field, data[field])
                campos_a_guardar.append(field)

        if not campos_a_guardar:
            return transaccion

        transaccion.save(update_fields=campos_a_guardar)
        logger.info(
            "[TransaccionBancariaCRUD] Conciliada uuid=%s | factura=%s | proveedor=%s | cliente=%s | conciliado=%s",
            transaccion.uuid,
            transaccion.factura_uuid,
            transaccion.proveedor_uuid,
            transaccion.cliente_uuid,
            transaccion.conciliado,
        )

        # Disparador cross-app: recalcular estado_pago de la factura.
        # Pull Model: Bancos notifica a Facturas sin FK directa.
        # Solo se dispara si hay factura_uuid vinculada.
        if transaccion.factura_uuid:
            try:
                from apps.tenant.facturas.services.business_service import FacturaInterAppAPI
                FacturaInterAppAPI.recalcular_estado_pago_automatico(transaccion.factura_uuid)
            except Exception as exc:
                # No bloquear la conciliacion por fallo en el recalculo
                logger.warning(
                    "[TransaccionBancariaCRUD] recalcular_estado_pago fallido para factura_uuid=%s: %s",
                    transaccion.factura_uuid, exc
                )

            # DEUDA-C03 "Clientes + Cartera" (decision del usuario,
            # 2026-09-11): Cartera es la UNICA SSoT real de pagos -- al
            # conciliar una transaccion contra una Factura de VENTA, Bancos
            # dispara automaticamente un abono en la Cartera asociada (la
            # crea si no existia todavia, mismo patron get_or_create que ya
            # usa CarteraViewSet.render_offcanvas_abono_factura()). Solo se
            # dispara en la transicion real no-conciliada -> conciliada
            # (evita doble abono si se re-guarda sin cambiar el flag).
            # LIMITACION CONOCIDA, documentada, no resuelta aqui:
            # des-conciliar una transaccion (True -> False) NO revierte el
            # abono ya aplicado -- Cartera no tiene hoy un mecanismo de
            # reverso de abonos (ver mision seccion 74, "no improvisar un
            # DELETE"); si esto se necesita, es una mision aparte.
            if transaccion.conciliado and not conciliado_previo:
                try:
                    from apps.tenant.clientes.services.business_service import (
                        CarteraBusinessService,
                    )
                    CarteraBusinessService.registrar_abono_desde_conciliacion_bancaria(
                        empresa_id=transaccion.empresa_id,
                        factura_uuid=transaccion.factura_uuid,
                        monto=abs(transaccion.valor),
                        fecha=transaccion.fecha,
                    )
                except Exception as exc:
                    logger.warning(
                        "[TransaccionBancariaCRUD] No se pudo sincronizar abono en Cartera para factura_uuid=%s: %s",
                        transaccion.factura_uuid, exc
                    )

        return transaccion


class MovimientoBancarioAplicacionCRUDService:
    """Fase 5-7 (mision Bancos v3.0): CRUD de aplicaciones multiples por
    movimiento. Deliberadamente NO dispara ningun efecto lateral cross-app
    (Cartera, estado_pago) -- ese automatismo sigue siendo exclusivo del
    vinculo legado 1:1 (TransaccionBancariaCRUDService.conciliar_transaccion),
    documentado en AUDITORIA_FLUJO_COMPLETO.md v3.0 §5. Esta capa solo
    clasifica/aplica y sincroniza el flag `conciliado` hacia arriba (nunca
    lo revierte a False -- evita pisar un vinculo legado ya completo)."""

    @staticmethod
    def _validar_no_sobreaplicar(transaccion: TransaccionBancaria, monto_nuevo: Decimal, excluir_uuid=None):
        monto_movimiento = abs(transaccion.valor)
        qs = MovimientoBancarioAplicacion.objects.filter(
            transaccion=transaccion, empresa_id=transaccion.empresa_id
        )
        if excluir_uuid:
            qs = qs.exclude(uuid=excluir_uuid)
        monto_existente = sum((a.monto_aplicado for a in qs), Decimal("0.00"))
        total = monto_existente + monto_nuevo
        if total - monto_movimiento > TOLERANCIA_APLICACION:
            raise ValidationError({
                "monto_aplicado": (
                    f"El monto aplicado total ({total}) excederia el valor del movimiento "
                    f"({monto_movimiento}). Ya hay {monto_existente} aplicado; el maximo "
                    f"disponible para esta aplicacion es {monto_movimiento - monto_existente}."
                )
            })
        return monto_existente

    @staticmethod
    def _sincronizar_conciliado(transaccion: TransaccionBancaria):
        """Solo ASCIENDE conciliado a True cuando el 100% del movimiento
        esta aplicado -- nunca lo revierte a False (ver docstring de clase)."""
        if transaccion.conciliado:
            return
        monto_movimiento = abs(transaccion.valor)
        total_aplicado = sum(
            (a.monto_aplicado for a in MovimientoBancarioAplicacion.objects.filter(
                transaccion=transaccion, empresa_id=transaccion.empresa_id
            )),
            Decimal("0.00"),
        )
        if monto_movimiento - total_aplicado <= TOLERANCIA_APLICACION:
            transaccion.conciliado = True
            transaccion.save(update_fields=["conciliado"])

    @staticmethod
    @transaction.atomic
    def crear_aplicacion(transaccion: TransaccionBancaria, data: dict, empresa) -> MovimientoBancarioAplicacion:
        # select_for_update: serializa aplicaciones concurrentes sobre el
        # mismo movimiento para que el guard de sobreaplicacion sea real
        # (Fase 6).
        transaccion = TransaccionBancaria.objects.select_for_update().get(pk=transaccion.pk)

        monto_aplicado = data["monto_aplicado"]
        MovimientoBancarioAplicacionCRUDService._validar_no_sobreaplicar(transaccion, monto_aplicado)

        aplicacion = MovimientoBancarioAplicacion(
            empresa=empresa,
            transaccion=transaccion,
            tipo_referencia=data["tipo_referencia"],
            referencia_uuid=data.get("referencia_uuid"),
            tercero_tipo=data.get("tercero_tipo"),
            tercero_uuid=data.get("tercero_uuid"),
            monto_aplicado=monto_aplicado,
            fecha_aplicacion=data.get("fecha_aplicacion") or timezone.localdate(),
            notas=data.get("notas"),
            origen_matching=data.get("origen_matching", "MANUAL"),
            confianza=data.get("confianza"),
        )
        aplicacion.full_clean()
        aplicacion.save()

        MovimientoBancarioAplicacionCRUDService._sincronizar_conciliado(transaccion)

        logger.info(
            "[MovimientoBancarioAplicacionCRUD] Creada aplicacion uuid=%s tipo=%s monto=%s tx=%s",
            aplicacion.uuid, aplicacion.tipo_referencia, aplicacion.monto_aplicado, transaccion.uuid,
        )
        return aplicacion

    @staticmethod
    @transaction.atomic
    def editar_aplicacion(aplicacion: MovimientoBancarioAplicacion, data: dict) -> MovimientoBancarioAplicacion:
        transaccion = TransaccionBancaria.objects.select_for_update().get(pk=aplicacion.transaccion_id)

        if "monto_aplicado" in data:
            MovimientoBancarioAplicacionCRUDService._validar_no_sobreaplicar(
                transaccion, data["monto_aplicado"], excluir_uuid=aplicacion.uuid
            )

        for field in ("tipo_referencia", "referencia_uuid", "tercero_tipo", "tercero_uuid",
                      "monto_aplicado", "fecha_aplicacion", "notas"):
            if field in data:
                setattr(aplicacion, field, data[field])
        aplicacion.full_clean()
        aplicacion.save()

        MovimientoBancarioAplicacionCRUDService._sincronizar_conciliado(transaccion)
        return aplicacion

    @staticmethod
    @transaction.atomic
    def eliminar_aplicacion(aplicacion: MovimientoBancarioAplicacion) -> None:
        aplicacion_uuid = aplicacion.uuid
        transaccion_id = aplicacion.transaccion_id
        aplicacion.delete()
        logger.info(
            "[MovimientoBancarioAplicacionCRUD] Eliminada aplicacion uuid=%s tx_id=%s",
            aplicacion_uuid, transaccion_id,
        )
        # Eliminar SI puede bajar el total aplicado por debajo del 100%, pero
        # nunca revertimos `conciliado` automaticamente (ver docstring de
        # clase) -- el usuario decide si quitar el vinculo legado tambien.
