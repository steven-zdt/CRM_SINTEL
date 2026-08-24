"""
Puerto de transporte de documentos electronicos DIAN (FISCAL-02).

Separa "que" se envia (facturas/empleados construyen el documento) de
"como" se transmite (SOAP/REST/proveedor tecnologico) -- ninguna app de
dominio debe importar requests/zeep/httpx directamente para hablar con la
DIAN. Ver docs/fiscal/DIAN_TRANSPORT_AUDIT.md.

Escenario C confirmado por FISCAL-01: no existe hoy ningun adaptador real
verificado (DIANAdapter sigue siendo SKELETON_NO_VERIFICADO, ver
docs/fiscal/FISCAL_05_DIAN_ADAPTER.md) -- requiere WSDL/credenciales de
habilitacion verificables, no disponibles en este entorno. Por decision
explicita del usuario (FISCAL-02A), el trabajo activo se hace contra
`MockTransportAdapter` (apps/tenant/core/dian/adapters.py): infraestructura
completa, probada de punta a punta, sin ninguna conexion externa -- cuando
existan credenciales reales, solo se reemplaza el adaptador inyectado en
`ElectronicInvoiceApplicationService`, sin tocar Factura/Venta/Inventario/
Bancos/Contabilidad/UI/estados de negocio.

`get_status()` (FISCAL-02A): agregado al contrato para soportar
reconciliacion real de una transmision `AMBIGUA` (ver
docs/fiscal/FISCAL_04_IDEMPOTENCIA_TRANSMISION.md §3, dejado fuera de
alcance en su momento por falta de un adaptador contra el cual probarlo --
MockTransportAdapter ahora lo hace posible sin conexion real).
"""
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from django.utils import timezone


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
    submitted_at: "object | None" = None  # datetime del intento -- lo fija el adaptador o el orquestador


@runtime_checkable
class ElectronicDocumentTransportPort(Protocol):
    """
    Contrato de transporte. La app de dominio solo conoce "enviar
    documento" / "consultar estado" -- nunca como funciona HTTP/SOAP, como
    autentica la DIAN, ni como responde el proveedor especifico detras del
    adaptador.
    """

    def send(self, document: ElectronicDocument) -> TransmissionResult:
        ...

    def get_status(self, tracking_key: str) -> TransmissionResult:
        """
        Consulta el estado de una transmision previa por su `tracking_key`
        (CUFE/CUNE). Existe para reconciliar una transmision `AMBIGUA`
        (FISCAL-04 §2) -- un adaptador que no soporte consulta real puede
        retornar `status="ERROR_TRANSMISION"` con `errors=["not_supported"]`
        en vez de fingir una respuesta.
        """
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
            submitted_at=timezone.now(),
        )

    def get_status(self, tracking_key: str) -> TransmissionResult:
        return TransmissionResult(
            success=False,
            status="ERROR_TRANSMISION",
            response_message="No hay un adaptador de transporte DIAN real configurado.",
            errors=["transport_not_configured"],
        )


class MockTransportAdapter:
    """
    Adaptador de simulacion controlada (FISCAL-02A) -- CERO conexion
    externa, siempre. Permite probar de punta a punta toda la logica de
    `ElectronicInvoiceApplicationService` (idempotencia, maquina de
    estados FISCAL-03, manejo de excepciones FISCAL-04) contra escenarios
    deterministas, sin depender de un WSDL/credenciales DIAN reales -- ver
    docs/fiscal/FISCAL_02A_MOCK_TRANSPORT.md.

    Escenarios soportados (`scenario` del constructor, o override por
    documento via `scenario_por_tracking_key={cufe: escenario}`):
      TEST_ACCEPTED         -- send() retorna ACEPTADO (roundtrip exitoso)
      TEST_REJECTED         -- send() retorna RECHAZADO (roundtrip exitoso,
                                rechazo de negocio)
      TEST_PENDING          -- send() retorna un status sin mapeo a estado
                                terminal -- la Factura queda en ENVIADA,
                                igual que un caso real "aun sin resolver"
      TEST_TIMEOUT          -- send() lanza TimeoutError (simula falta de
                                respuesta real -- el orquestador lo trata
                                como transmision AMBIGUA, igual que un
                                timeout real)
      TEST_CONNECTION_ERROR -- send() lanza ConnectionError (mismo
                                tratamiento que TEST_TIMEOUT)
    """

    _ESCENARIOS_QUE_LANZAN = {
        "TEST_TIMEOUT": TimeoutError,
        "TEST_CONNECTION_ERROR": ConnectionError,
    }

    def __init__(self, scenario: str = "TEST_ACCEPTED", scenario_por_tracking_key: dict | None = None):
        self.scenario = scenario
        self.scenario_por_tracking_key = scenario_por_tracking_key or {}
        self._historial: dict[str, TransmissionResult] = {}
        self._contador_intentos: dict[str, int] = {}

    def _resolver_escenario(self, document: ElectronicDocument) -> str:
        return self.scenario_por_tracking_key.get(document.tracking_key, self.scenario)

    def send(self, document: ElectronicDocument) -> TransmissionResult:
        escenario = self._resolver_escenario(document)
        self._contador_intentos[document.tracking_key] = self._contador_intentos.get(document.tracking_key, 0) + 1

        excepcion_cls = self._ESCENARIOS_QUE_LANZAN.get(escenario)
        if excepcion_cls:
            raise excepcion_cls(f"[MockTransportAdapter] {escenario} simulado para tracking_key={document.tracking_key}")

        track_id = f"MOCK-{(document.tracking_key or 'sin-cufe')[:12]}"
        ahora = timezone.now()

        if escenario == "TEST_ACCEPTED":
            resultado = TransmissionResult(
                success=True, status="ACEPTADO", track_id=track_id, response_code="00",
                response_message="[SIMULADO] Documento aceptado.",
                submitted_at=ahora, raw_response="[MOCK] IsValid=True",
            )
        elif escenario == "TEST_REJECTED":
            resultado = TransmissionResult(
                success=True, status="RECHAZADO", track_id=track_id, response_code="99",
                response_message="[SIMULADO] Documento rechazado.",
                errors=["[SIMULADO] XML invalido"],
                submitted_at=ahora, raw_response="[MOCK] IsValid=False",
            )
        elif escenario == "TEST_PENDING":
            resultado = TransmissionResult(
                success=True, status="PENDIENTE", track_id=track_id,
                response_message="[SIMULADO] Aun sin resolver -- consultar mas tarde con get_status().",
                submitted_at=ahora, raw_response="[MOCK] pending",
            )
        else:
            raise ValueError(f"[MockTransportAdapter] escenario desconocido: {escenario!r}")

        self._historial[document.tracking_key] = resultado
        return resultado

    def get_status(self, tracking_key: str) -> TransmissionResult:
        if tracking_key not in self._historial:
            return TransmissionResult(
                success=False, status="ERROR_TRANSMISION",
                response_message=f"[SIMULADO] No hay transmision registrada para tracking_key={tracking_key}.",
                errors=["not_found"],
            )
        return self._historial[tracking_key]

    def intentos(self, tracking_key: str) -> int:
        """Cuantas veces se llamo send() para este tracking_key -- para tests de idempotencia/reintento."""
        return self._contador_intentos.get(tracking_key, 0)
