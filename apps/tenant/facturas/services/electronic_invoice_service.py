"""
ElectronicInvoiceApplicationService (FISCAL-04, extendido en FISCAL-02A) --
orquesta el envio de una Factura de VENTA a la DIAN a traves de
ElectronicDocumentTransportPort (FISCAL-02), aplicando la maquina de
estados real (FISCAL-03) como mecanismo de idempotencia -- no un flag/
tabla nueva, el propio `Factura.estado` ya persistido es el ancla.

Patron de 2 fases, deliberado (no es solo estetica): la transicion a
ENVIADA se confirma en su PROPIA transaccion, ANTES de llamar
transport.send(). Si send() lanza (timeout, conexion caida -- exactamente
el escenario que el plan describe: "Factura #123 -> enviada -> timeout ->
¿se envio realmente?"), esa escritura ya esta comprometida: la Factura
queda en ENVIADA (no vuelve a BORRADOR), y un reintento inmediato de
transmitir() es rechazado por validar_transicion_automatica() (ENVIADA no
tiene a ENVIADA en sus transiciones validas) -- el sistema nunca reenvia
a ciegas un documento cuyo resultado real se desconoce.

FISCAL-02A agrega persistencia completa de CADA intento en
`TransmisionFactura` (historial, no solo el ultimo estado) -- permite
reconstruir cuantos intentos hubo, cuando, y con que respuesta cruda,
sin depender de que `Factura.estado` (que solo guarda el ultimo valor)
alcance. La reconciliacion de un `AMBIGUO` via `transport.get_status()`
es posible ahora que `MockTransportAdapter` la implementa -- ver
`reconciliar()` mas abajo.
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.tenant.core.dian import (
    ElectronicDocument,
    ElectronicDocumentTransportPort,
    NullTransportAdapter,
    TransmissionResult,
)
from apps.tenant.core.dian.attached_document import AttachedDocumentService
from apps.tenant.facturas.models import Factura, TransmisionFactura
from apps.tenant.facturas.services.business_service import FacturaBusinessService

logger = logging.getLogger(__name__)

# TransmissionResult.status -> Factura.Estado (FISCAL-03). "ENVIADO" no
# mapea a un estado propio -- ya es el estado en el que la Factura queda
# ANTES de llamar send() (fase 1), no un resultado de fase 2. "PENDIENTE"
# tampoco mapea a proposito -- la Factura queda en ENVIADA (aun sin
# resolver), igual que un caso AMBIGUO real.
_STATUS_A_ESTADO = {
    "ACEPTADO": Factura.Estado.ACEPTADA,
    "RECHAZADO": Factura.Estado.RECHAZADA,
    "ERROR_TRANSMISION": Factura.Estado.ERROR_TRANSMISION,
}

# TransmissionResult.status -> TransmisionFactura.Status (vocabularios
# hermanos, no identicos: TransmisionFactura agrega AMBIGUO, que no es un
# status que un adaptador retorne -- lo asigna este servicio cuando
# transport.send() lanza una excepcion).
_STATUS_A_TRANSMISION_STATUS = {
    "ACEPTADO": TransmisionFactura.Status.ACEPTADO,
    "RECHAZADO": TransmisionFactura.Status.RECHAZADO,
    "ERROR_TRANSMISION": TransmisionFactura.Status.ERROR_TRANSMISION,
    "PENDIENTE": TransmisionFactura.Status.PENDIENTE,
}

_AMBIENTE_A_ENVIRONMENT = {
    "pruebas": TransmisionFactura.Environment.TEST,
    "produccion": TransmisionFactura.Environment.PRODUCTION,
}


class ElectronicInvoiceApplicationService:
    """Unico punto de entrada para transmitir una Factura a la DIAN."""

    @staticmethod
    def _construir_documento(factura: Factura) -> ElectronicDocument:
        ubl_xml = getattr(getattr(factura, "anexos", None), "ubl_xml", None) or factura.xml_content
        if not ubl_xml:
            raise ValueError(
                f"Factura {factura.numero} no tiene XML UBL firmado (FacturaAnexos.ubl_xml vacio) -- "
                "no se puede transmitir un documento que nunca se genero."
            )
        signed_xml = ubl_xml.encode("utf-8")

        dto_minimo = {
            "num_fac": factura.numero,
            "emisor": {"nit": factura.emisor_nit, "dv": ""},
            "receptor": {"tipo_documento": "31", "nit": factura.receptor_nit},
        }
        attached_document = AttachedDocumentService.build(
            signed_xml, dto_minimo, factura.cufe or "", document_type="Invoice",
        )

        return ElectronicDocument(
            document_type="Invoice",
            numero=factura.numero,
            tracking_key=factura.cufe or "",
            signed_xml=signed_xml,
            attached_document=attached_document,
            ambiente="produccion" if factura.estado != Factura.Estado.BORRADOR else "pruebas",
            empresa_nit=factura.emisor_nit or "",
        )

    @staticmethod
    def _actualizar_transmision(transmision: TransmisionFactura, resultado: TransmissionResult, status: str) -> None:
        transmision.status = status
        transmision.responded_at = timezone.now()
        transmision.track_id = resultado.track_id
        transmision.response_code = resultado.response_code
        transmision.response_message = resultado.response_message
        transmision.raw_response = resultado.raw_response
        transmision.save(update_fields=[
            "status", "responded_at", "track_id", "response_code", "response_message", "raw_response",
        ])

    @staticmethod
    def transmitir(
        factura: Factura, transport: "ElectronicDocumentTransportPort | None" = None,
    ) -> dict:
        """
        Transmite `factura` (debe ser naturaleza=VENTA -- no transmitimos
        facturas de compra, las emite el proveedor) a traves de `transport`
        (por defecto `NullTransportAdapter`, honesto: no hay adaptador real
        configurado, ver FISCAL-01/02; usar `MockTransportAdapter` para
        desarrollo/tests, FISCAL-02A).

        Retorna {"factura": Factura, "resultado": TransmissionResult,
        "transmision": TransmisionFactura}. Lanza DRFValidationError (via
        validar_transicion_automatica) si el estado actual de la Factura no
        permite transmitir ahora -- esta ES la proteccion de idempotencia
        real, sin flag ni tabla nueva; `TransmisionFactura` es la traza de
        auditoria de cada intento, no un segundo guardian.
        """
        if factura.naturaleza != Factura.Naturaleza.VENTA:
            raise ValueError("Solo se transmiten facturas de naturaleza VENTA (emitidas por el tenant).")

        transport = transport or NullTransportAdapter()

        # -- Fase 1: idempotencia + marcar ENVIADA + registrar el intento --
        # todo en la MISMA transaccion, confirmada ANTES de llamar
        # transport.send(). Si send() falla o nunca retorna (timeout), este
        # commit ya ocurrio: la Factura nunca vuelve a BORRADOR, y queda un
        # registro PENDIENTE del intento aunque nunca se resuelva.
        with transaction.atomic():
            factura.refresh_from_db(fields=["estado"])
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)
            documento = ElectronicInvoiceApplicationService._construir_documento(factura)
            factura.estado = Factura.Estado.ENVIADA
            factura.save(update_fields=["estado"])
            transmision = TransmisionFactura.objects.create(
                empresa_id=factura.empresa_id, factura=factura,
                environment=_AMBIENTE_A_ENVIRONMENT.get(documento.ambiente, TransmisionFactura.Environment.TEST),
                status=TransmisionFactura.Status.PENDIENTE,
            )

        # -- Fuera de la transaccion: la llamada de red real --
        try:
            resultado = transport.send(documento)
        except Exception as exc:
            # Ambiguo por diseño: no sabemos si la DIAN recibio el documento.
            # La Factura QUEDA en ENVIADA (fase 1 ya comprometida) -- no se
            # inventa un ERROR_TRANSMISION que invitaria a un reintento
            # automatico inseguro.
            logger.error(
                "[ElectronicInvoiceApplicationService] transport.send() lanzo excepcion para "
                "factura id=%s numero=%s -- estado queda en ENVIADA (ambiguo, no reintentar "
                "automaticamente): %s", factura.id, factura.numero, exc, exc_info=True,
            )
            resultado_ambiguo = TransmissionResult(
                success=False,
                status="ENVIADA_AMBIGUA",
                response_message=(
                    "La transmision no obtuvo respuesta (timeout/error de red). "
                    "El documento pudo o no haber llegado a la DIAN -- usar reconciliar() "
                    "antes de reintentar."
                ),
                errors=[str(exc)],
            )
            ElectronicInvoiceApplicationService._actualizar_transmision(
                transmision, resultado_ambiguo, TransmisionFactura.Status.AMBIGUO,
            )
            return {"factura": factura, "resultado": resultado_ambiguo, "transmision": transmision}

        # -- Fase 2: aplicar el resultado real + cerrar el registro del intento --
        transmision_status = _STATUS_A_TRANSMISION_STATUS.get(resultado.status, TransmisionFactura.Status.ERROR_TRANSMISION)
        estado_destino = _STATUS_A_ESTADO.get(resultado.status)
        with transaction.atomic():
            if estado_destino is not None:
                factura.refresh_from_db(fields=["estado"])
                FacturaBusinessService.validar_transicion_automatica(factura, estado_destino)
                factura.estado = estado_destino
                factura.save(update_fields=["estado"])
                if resultado.raw_response and hasattr(factura, "anexos"):
                    factura.anexos.application_response_xml = resultado.raw_response
                    factura.anexos.save(update_fields=["application_response_xml"])
            ElectronicInvoiceApplicationService._actualizar_transmision(transmision, resultado, transmision_status)

        return {"factura": factura, "resultado": resultado, "transmision": transmision}

    @staticmethod
    def reconciliar(
        factura: Factura, transport: "ElectronicDocumentTransportPort | None" = None,
    ) -> dict:
        """
        Consulta el estado real de la ULTIMA transmision de `factura` via
        `transport.get_status()` -- pensado para resolver un `AMBIGUO`
        (timeout/error de red sin confirmar, ver `transmitir()`). No crea
        un intento nuevo; actualiza el registro `TransmisionFactura`
        existente y aplica la transicion de `Factura.estado` si la
        consulta trae una respuesta definitiva.

        Retorna {"factura": Factura, "resultado": TransmissionResult,
        "transmision": TransmisionFactura | None} -- `transmision` es
        `None` si nunca hubo un intento previo para esta Factura.
        """
        transport = transport or NullTransportAdapter()
        transmision = factura.transmisiones.order_by("-submitted_at").first()
        if transmision is None:
            raise ValueError(f"Factura {factura.numero} no tiene ningun intento de transmision registrado.")

        resultado = transport.get_status(factura.cufe or "")

        transmision_status = _STATUS_A_TRANSMISION_STATUS.get(resultado.status)
        estado_destino = _STATUS_A_ESTADO.get(resultado.status)
        with transaction.atomic():
            if estado_destino is not None:
                factura.refresh_from_db(fields=["estado"])
                FacturaBusinessService.validar_transicion_automatica(factura, estado_destino)
                factura.estado = estado_destino
                factura.save(update_fields=["estado"])
            if transmision_status is not None:
                ElectronicInvoiceApplicationService._actualizar_transmision(transmision, resultado, transmision_status)

        return {"factura": factura, "resultado": resultado, "transmision": transmision}
