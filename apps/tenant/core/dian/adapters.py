"""
DIANAdapter -- implementacion REAL (SOAP/WCF) de ElectronicDocumentTransportPort
contra el webservice de la DIAN (Colombia).

################################################################################
# ADVERTENCIA CRITICA -- NO VERIFICADO CONTRA EL AMBIENTE REAL DE LA DIAN     #
################################################################################
Escrito con el conocimiento publico general del Anexo Tecnico de Factura
Electronica de la DIAN (servicio WcfDianCustomerServices, operacion
SendBillSync, documento enviado como ZIP+base64) -- NO fue validado contra
el WSDL real ni contra el ambiente de habilitacion de la DIAN. Bloqueado por
falta de WSDL/credenciales verificables en este entorno, ver
docs/fiscal/DIAN_TRANSPORT_AUDIT.md §6 y docs/fiscal/FISCAL_05_DIAN_ADAPTER.md.

Riesgos reales conocidos, sin resolver:
  - El endpoint exacto (URL de habilitacion/produccion) puede haber cambiado
    desde el ultimo conocimiento publico disponible -- DIAN ha modificado
    estas URLs en actualizaciones normativas pasadas.
  - El mecanismo de autenticacion WS-Security (UsernameToken vs certificado
    X.509 en el header SOAP) NO esta implementado aqui -- ver `_client()`.
    Una llamada real fallaria en autenticacion tal como esta escrito hoy.
  - El nombre exacto de la operacion (`SendBillSync`) y sus parametros
    (`fileName`, `contentFile`) puede diferir de la version vigente del
    WSDL real -- solo se puede confirmar leyendo el WSDL real.
  - `_parsear_respuesta()` accede a los campos de la respuesta de forma
    defensiva (getattr con default) precisamente porque no esta confirmado
    el shape exacto del objeto que zeep deserializaria desde la respuesta
    SOAP real.

NO USAR EN PRODUCCION sin, en este orden:
  1. Obtener el WSDL real vigente (habilitacion y produccion) y las
     credenciales de habilitacion de un tenant real.
  2. Implementar la autenticacion WS-Security real en `_client()`.
  3. Validar `send()` end-to-end contra el ambiente de pruebas DIAN real,
     incluyendo el shape real de una respuesta ACEPTADA y una RECHAZADA.
  4. Revisar cada nombre de operacion/campo contra el Anexo Tecnico vigente
     a la fecha de implementacion (los anexos tecnicos de la DIAN cambian
     con resoluciones nuevas).

Settings requeridos (ninguno configurado hoy en ningun entorno, ver
docs/fiscal/DIAN_TRANSPORT_AUDIT.md §3):
  DIAN_WSDL_URL_HABILITACION  -- URL del WSDL en ambiente de pruebas
  DIAN_WSDL_URL_PRODUCCION    -- URL del WSDL en ambiente de produccion
  DIAN_TIP_AMB                -- "2" pruebas (default) | "1" produccion,
                                  mismo setting ya usado por CufeService
"""
import base64
import io
import logging
import zipfile

from apps.tenant.core.dian.transport import ElectronicDocument, TransmissionResult

logger = logging.getLogger(__name__)


class DIANAdapter:
    """
    Adaptador real (no verificado, ver advertencia del modulo) para
    ElectronicDocumentTransportPort. Construido para inyeccion de
    dependencias en tests: `_client_factory` reemplaza la construccion real
    de `zeep.Client` sin requerir un WSDL real disponible.
    """

    def __init__(self, wsdl_url: str | None = None, tip_amb: str | None = None, _client_factory=None):
        from django.conf import settings

        self.tip_amb = tip_amb or getattr(settings, "DIAN_TIP_AMB", "2")
        if wsdl_url:
            self.wsdl_url = wsdl_url
        elif self.tip_amb == "1":
            self.wsdl_url = getattr(settings, "DIAN_WSDL_URL_PRODUCCION", "")
        else:
            self.wsdl_url = getattr(settings, "DIAN_WSDL_URL_HABILITACION", "")
        self._client_factory = _client_factory

    def _client(self):
        """
        Construye el cliente SOAP real.

        # WARNING: NO IMPLEMENTADO -- WS-Security. El WSDL real de la DIAN
        # requiere autenticacion (mecanismo exacto no confirmado, ver
        # advertencia del modulo). Esta implementacion construye un cliente
        # zeep "desnudo" -- una llamada real fallaria en autenticacion.
        """
        if self._client_factory is not None:
            return self._client_factory(self.wsdl_url)

        import zeep  # import perezoso -- zeep es dependencia opcional hasta que este adaptador se use de verdad

        return zeep.Client(wsdl=self.wsdl_url)

    @staticmethod
    def _empaquetar_documento(document: ElectronicDocument) -> str:
        """
        Empaqueta `attached_document` en un ZIP en memoria + base64, tal
        como el Anexo Tecnico FE describe para `SendBillSync` (no
        confirmado contra el WSDL real -- ver advertencia del modulo).
        """
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{document.numero}.xml", document.attached_document)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _parsear_respuesta(respuesta) -> TransmissionResult:
        """
        Traduce la respuesta cruda de zeep a TransmissionResult. Acceso
        defensivo (getattr con default) porque el shape exacto de la
        respuesta real NO esta confirmado -- ver advertencia del modulo.
        """
        es_valido = getattr(respuesta, "IsValid", None)
        status_code = getattr(respuesta, "StatusCode", None)
        status_desc = getattr(respuesta, "StatusDescription", "") or ""
        track_id = getattr(respuesta, "XmlDocumentKey", None) or getattr(respuesta, "TrackId", None)
        raw = str(respuesta)

        if es_valido is True:
            return TransmissionResult(
                success=True, status="ACEPTADO", track_id=track_id,
                response_code=str(status_code) if status_code is not None else None,
                response_message=status_desc, raw_response=raw,
            )
        if es_valido is False:
            return TransmissionResult(
                success=True, status="RECHAZADO", track_id=track_id,
                response_code=str(status_code) if status_code is not None else None,
                response_message=status_desc,
                errors=[status_desc] if status_desc else [],
                raw_response=raw,
            )
        # es_valido is None -- la respuesta no trae el campo esperado. No se
        # inventa ACEPTADO/RECHAZADO sobre un shape no reconocido.
        return TransmissionResult(
            success=False, status="ERROR_TRANSMISION",
            response_message="Respuesta de la DIAN con formato no reconocido -- revisar contra el WSDL real.",
            errors=["unrecognized_response_shape"], raw_response=raw,
        )

    def send(self, document: ElectronicDocument) -> TransmissionResult:
        if not self.wsdl_url:
            return TransmissionResult(
                success=False, status="ERROR_TRANSMISION",
                response_message=(
                    "DIAN_WSDL_URL_HABILITACION/DIAN_WSDL_URL_PRODUCCION no configurado. "
                    "Ver docs/fiscal/DIAN_TRANSPORT_AUDIT.md §3."
                ),
                errors=["wsdl_not_configured"],
            )

        try:
            cliente = self._client()
        except ImportError:
            return TransmissionResult(
                success=False, status="ERROR_TRANSMISION",
                response_message="Dependencia 'zeep' no instalada.",
                errors=["zeep_not_installed"],
            )

        contenido_b64 = self._empaquetar_documento(document)

        # Sin catch generico aqui a proposito: una excepcion de red/timeout
        # en esta llamada debe propagarse -- ElectronicInvoiceApplicationService
        # (FISCAL-04) la captura y la trata como transmision AMBIGUA (no se
        # sabe si la DIAN recibio el documento), nunca como un resultado
        # inventado. Ver docs/fiscal/FISCAL_04_IDEMPOTENCIA_TRANSMISION.md §2.
        respuesta = cliente.service.SendBillSync(
            fileName=f"{document.numero}.zip",
            contentFile=contenido_b64,
        )
        return self._parsear_respuesta(respuesta)

    def get_status(self, tracking_key: str) -> TransmissionResult:
        """
        # WARNING: NO IMPLEMENTADO. La operacion real de consulta de estado
        # DIAN (nombre/parametros exactos no confirmados -- posiblemente
        # `GetStatus`/`GetStatusZip` segun el Anexo Tecnico, sin verificar)
        # no se implemento para no inventar una segunda operacion SOAP sin
        # WSDL real contra el cual validarla. Retorna un resultado honesto
        # de "no soportado" en vez de fingir una consulta real.
        """
        return TransmissionResult(
            success=False, status="ERROR_TRANSMISION",
            response_message=(
                "DIANAdapter.get_status() no esta implementado -- operacion real de "
                "la DIAN no confirmada. Ver docs/fiscal/FISCAL_05_DIAN_ADAPTER.md."
            ),
            errors=["not_supported"],
        )
