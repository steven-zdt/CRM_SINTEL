"""
Puerto de transporte de documentos electronicos DIAN (FISCAL-02).

Separa "que" se envia (facturas/empleados construyen el documento) de
"como" se transmite (SOAP/REST/proveedor tecnologico) -- ninguna app de
dominio debe importar requests/zeep/httpx directamente para hablar con la
DIAN. Ver docs/fiscal/DIAN_TRANSPORT_AUDIT.md.

Escenario C confirmado por FISCAL-01: no existe hoy ningun adaptador real
(DIANAdapter/ProviderAdapter) -- requiere WSDL/credenciales de
habilitacion verificables, no disponibles en este entorno (mismo criterio
ya aplicado en NOMINA-03 para el transporte SOAP). Esta fase define
UNICAMENTE el contrato + un adaptador nulo honesto (NullTransportAdapter),
para que el resto del pipeline pueda depender de la interfaz ya, sin
bloquear en la implementacion real ni fingir una transmision que no
ocurrio.
"""
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ElectronicDocument:
    """
    Documento electronico ya construido y firmado, listo para transmitir.

    Lo construye la app de dominio (facturas hoy; empleados/nomina cuando
    exista su propio pipeline) usando UBL21BuilderService/CufeService +
    XadesSignerService + AttachedDocumentService -- el transporte no
    construye ni firma nada, solo envia bytes ya terminados.
    """
    document_type: str          # "Invoice" | "NominaIndividual" | ...
    numero: str                 # numero/consecutivo del documento
    tracking_key: str           # CUFE o CUNE, segun document_type
    signed_xml: bytes           # XML UBL firmado (XAdES)
    attached_document: bytes    # AttachedDocument que envuelve signed_xml
    ambiente: str = "pruebas"   # "pruebas" | "produccion"
    empresa_nit: str = ""       # NIT del emisor -- resuelve credenciales/certificado por tenant


@dataclass(frozen=True)
class TransmissionResult:
    """
    Resultado uniforme de un intento de transmision, sin importar el
    adaptador real detras -- ningun campo especifico de un proveedor.

    `status` es el estado FISCAL real reportado por la DIAN/proveedor
    (ENVIADO/ACEPTADO/RECHAZADO/ERROR_TRANSMISION, ver FISCAL-03) -- no
    debe confundirse con `success`, que solo indica si la llamada de
    transporte en si misma se completo sin excepcion.
    """
    success: bool
    status: str
    track_id: str | None = None
    response_code: str | None = None
    response_message: str = ""
    errors: list[str] = field(default_factory=list)
    raw_response: str = ""       # cuerpo crudo de la respuesta, para auditoria -- nunca secretos


@runtime_checkable
class ElectronicDocumentTransportPort(Protocol):
    """
    Contrato de transporte. La app de dominio solo conoce "enviar
    documento" -- nunca como funciona HTTP/SOAP, como autentica la DIAN,
    ni como responde el proveedor especifico detras del adaptador.
    """

    def send(self, document: ElectronicDocument) -> TransmissionResult:
        ...


class NullTransportAdapter:
    """
    Adaptador por defecto, honesto: no transmite nada, nunca finge exito.

    Mismo criterio que `XadesSignerService.sign()` ya aplica cuando no hay
    certificado configurado (retorna el XML sin firmar en vez de fallar
    silenciosamente con una firma invalida) -- aqui, sin un adaptador real
    configurado (`DIANAdapter`/`ProviderAdapter`, bloqueados por
    FISCAL-01 §6 hasta tener WSDL/credenciales verificables), `send()`
    retorna un resultado explicito de "no configurado". Nunca inventa un
    ACEPTADO ni un RECHAZADO -- la ausencia de transporte real es un
    hecho que debe ser visible, no ocultado detras de un resultado
    plausible.
    """

    def send(self, document: ElectronicDocument) -> TransmissionResult:
        return TransmissionResult(
            success=False,
            status="ERROR_TRANSMISION",
            response_message=(
                "No hay un adaptador de transporte DIAN real configurado. "
                "Ver docs/fiscal/DIAN_TRANSPORT_AUDIT.md §6."
            ),
            errors=["transport_not_configured"],
        )
