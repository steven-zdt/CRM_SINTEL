import logging
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria

logger = logging.getLogger(__name__)

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

        return transaccion
