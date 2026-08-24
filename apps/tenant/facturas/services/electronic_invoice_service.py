"""
ElectronicInvoiceApplicationService (FISCAL-04) -- orquesta el envio de una
Factura de VENTA a la DIAN a traves de ElectronicDocumentTransportPort
(FISCAL-02), aplicando la maquina de estados real (FISCAL-03) como
mecanismo de idempotencia -- no un flag/tabla nueva, el propio
`Factura.estado` ya persistido es el ancla.

Patron de 2 fases, deliberado (no es solo estetica): la transicion a
ENVIADA se confirma en su PROPIA transaccion, ANTES de llamar
transport.send(). Si send() lanza (timeout, conexion caida -- exactamente
el escenario que el plan describe: "Factura #123 -> enviada -> timeout ->
¿se envio realmente?"), esa escritura ya esta comprometida: la Factura
queda en ENVIADA (no vuelve a BORRADOR), y un reintento inmediato de
transmitir() es rechazado por validar_transicion_automatica() (ENVIADA no
tiene a ENVIADA en sus transiciones validas) -- el sistema nunca reenvia
a ciegas un documento cuyo resultado real se desconoce. Reconciliar un
ENVIADA ambiguo requiere una consulta de estado real contra el proveedor
(fuera de alcance de FISCAL-04 -- ElectronicDocumentTransportPort.send()
no incluye una operacion de consulta; agregarla sin un adaptador real que
la implemente seria infraestructura especulativa, ver
docs/fiscal/DIAN_TRANSPORT_AUDIT.md §6).
"""
import logging

from django.db import transaction

from apps.tenant.core.dian import (
    ElectronicDocument,
    ElectronicDocumentTransportPort,
    NullTransportAdapter,
    TransmissionResult,
)
from apps.tenant.core.dian.attached_document import AttachedDocumentService
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.business_service import FacturaBusinessService

logger = logging.getLogger(__name__)

# TransmissionResult.status -> Factura.Estado (FISCAL-03). "ENVIADO" no
# mapea a un estado propio -- ya es el estado en el que la Factura queda
# ANTES de llamar send() (fase 1), no un resultado de fase 2.
_STATUS_A_ESTADO = {
    "ACEPTADO": Factura.Estado.ACEPTADA,
    "RECHAZADO": Factura.Estado.RECHAZADA,
    "ERROR_TRANSMISION": Factura.Estado.ERROR_TRANSMISION,
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
    def transmitir(
        factura: Factura, transport: "ElectronicDocumentTransportPort | None" = None,
    ) -> dict:
        """
        Transmite `factura` (debe ser naturaleza=VENTA -- no transmitimos
        facturas de compra, las emite el proveedor) a traves de `transport`
        (por defecto `NullTransportAdapter`, honesto: no hay adaptador real
        configurado, ver FISCAL-01/02).

        Retorna {"factura": Factura, "resultado": TransmissionResult}.
        Lanza DRFValidationError (via validar_transicion_automatica) si el
        estado actual de la Factura no permite transmitir ahora -- esta
        ES la proteccion de idempotencia real, sin flag ni tabla nueva.
        """
        if factura.naturaleza != Factura.Naturaleza.VENTA:
            raise ValueError("Solo se transmiten facturas de naturaleza VENTA (emitidas por el tenant).")

        transport = transport or NullTransportAdapter()

        # -- Fase 1: idempotencia + marcar ENVIADA, transaccion propia --
        # confirmada ANTES de llamar transport.send(). Si send() falla o
        # nunca retorna (timeout), este commit ya ocurrio: la Factura
        # nunca vuelve a BORRADOR por una falla de red.
        with transaction.atomic():
            factura.refresh_from_db(fields=["estado"])
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)
            documento = ElectronicInvoiceApplicationService._construir_documento(factura)
            factura.estado = Factura.Estado.ENVIADA
            factura.save(update_fields=["estado"])

        # -- Fuera de la transaccion: la llamada de red real --
        try:
            resultado = transport.send(documento)
        except Exception as exc:
            # Ambiguo por diseño: no sabemos si la DIAN recibio el documento.
            # La Factura QUEDA en ENVIADA (fase 1 ya comprometida) -- no se
            # inventa un ERROR_TRANSMISION que invitaria a un reintento
            # automatico inseguro. Requiere reconciliacion manual/consulta
            # real (fuera de alcance, ver docstring del modulo).
            logger.error(
                "[ElectronicInvoiceApplicationService] transport.send() lanzo excepcion para "
                "factura id=%s numero=%s -- estado queda en ENVIADA (ambiguo, no reintentar "
                "automaticamente): %s", factura.id, factura.numero, exc, exc_info=True,
            )
            return {
                "factura": factura,
                "resultado": TransmissionResult(
                    success=False,
                    status="ENVIADA_AMBIGUA",
                    response_message=(
                        "La transmision no obtuvo respuesta (timeout/error de red). "
                        "El documento pudo o no haber llegado a la DIAN -- requiere "
                        "verificacion manual antes de reintentar."
                    ),
                    errors=[str(exc)],
                ),
            }

        # -- Fase 2: aplicar el resultado real, transaccion propia --
        estado_destino = _STATUS_A_ESTADO.get(resultado.status)
        if estado_destino is not None:
            with transaction.atomic():
                factura.refresh_from_db(fields=["estado"])
                FacturaBusinessService.validar_transicion_automatica(factura, estado_destino)
                factura.estado = estado_destino
                factura.save(update_fields=["estado"])
                if resultado.raw_response and hasattr(factura, "anexos"):
                    factura.anexos.application_response_xml = resultado.raw_response
                    factura.anexos.save(update_fields=["application_response_xml"])

        return {"factura": factura, "resultado": resultado}
