"""
Generador XML NominaIndividual DIAN (Nomina Electronica / DSPNE - Colombia).

################################################################################
# ADVERTENCIA -- ESTRUCTURA NO VERIFICADA CONTRA EL XSD OFICIAL              #
################################################################################
Mismo criterio de honestidad que `apps/tenant/core/dian/adapters.py`
(DIANAdapter) y `apps/tenant/empleados/services/dian/cune_service.py`: la
forma general de este documento (namespaces, bloques
InformacionGeneral/Empleador/Trabajador/Pago/Devengados/Deducciones) esta
construida con conocimiento publico general del "Anexo Tecnico Documento
Soporte de Pago de Nomina Electronica" (DIAN, Resolucion 000013 de 2021,
v1.0), pero NO fue validada contra el XSD oficial ni contra el ambiente de
habilitacion DIAN. Antes de transmitir a produccion, confirmar cada tag y
namespace contra el Anexo Tecnico vigente.

Reutiliza el mismo mecanismo de extension UBL que Factura Electronica
(`apps.tenant.core.dian.XadesSignerService`/`AttachedDocumentService`):
dos `ext:UBLExtension`, la primera con los datos de control DIAN, la
segunda vacia como marcador para que `XadesSignerService.sign()` inserte
`ds:Signature` sin duplicar esa logica (ver docs/nomina/NOMINA_DIAN_AUDIT.md
§2, "puede invocarse sin modificar una sola linea, siempre que el XML de
nomina deje el mismo placeholder vacio").
"""
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Namespaces -- ver advertencia del modulo (no confirmados contra el XSD real)
# ---------------------------------------------------------------------------
NS = {
    "nomina": "dian:gov:co:facturaelectronica:NominaIndividual",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sts": "dian:gov:co:facturaelectronica:Structures-2-1",
}

for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


def _tag(ns_key: str, local: str) -> str:
    return "{%s}%s" % (NS[ns_key], local)


def _sub(parent, ns_key: str, local: str, text: str = None, attribs: dict = None):
    el = ET.SubElement(parent, _tag(ns_key, local), attrib=attribs or {})
    if text is not None:
        el.text = str(text)
    return el


def _fmt2(val) -> str:
    return str(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class NominaXMLBuilderService:
    """
    Construye el XML NominaIndividual a partir del DTO canonico.

    Uso:
        xml_bytes = NominaXMLBuilderService.build(dto, cune)
        # Retorna bytes UTF-8 del documento XML sin firmar -- firmar con
        # apps.tenant.core.dian.XadesSignerService.sign() a continuacion.
    """

    @classmethod
    def build(cls, dto: dict, cune: str) -> bytes:
        root = cls._build_root(dto, cune)
        ET.indent(root, space="  ")
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode").encode("utf-8")

    # ------------------------------------------------------------------
    @classmethod
    def _build_root(cls, dto: dict, cune: str) -> ET.Element:
        # No se declaran xmlns:* manualmente -- ET.register_namespace() (arriba)
        # ya hace que el serializador de ElementTree las agregue automaticamente
        # a partir de los tags {uri}local usados en el arbol. Declararlas tambien
        # a mano aqui produce atributos xmlns:* duplicados (XML invalido) porque
        # ET.tostring() las vuelve a emitir por su cuenta -- bug real encontrado
        # al escribir este builder, confirmado presente tambien en
        # UBL21BuilderService (facturas), ver hallazgo reportado por separado.
        root = ET.Element(_tag("nomina", "NominaIndividual"))

        cls._build_extensions(root, dto, cune)

        _sub(root, "cbc", "UBLVersionID", "UBL 2.1")
        _sub(root, "cbc", "CustomizationID", dto.get("tipo_xml", "102"))
        _sub(root, "cbc", "ID", dto["num_nie"])
        _sub(root, "cbc", "UUID", cune, {"schemeName": "CUNE-SHA384"})
        _sub(root, "cbc", "IssueDate", dto["fec_nie"])
        _sub(root, "cbc", "IssueTime", dto["hor_nie"])

        periodo = dto.get("periodo", {})
        periodo_el = _sub(root, "sts", "PeriodoNomina")
        _sub(periodo_el, "cbc", "FechaIngreso", periodo.get("fecha_ingreso", ""))
        _sub(periodo_el, "cbc", "FechaLiquidacionInicio", periodo.get("fecha_liquidacion_inicio", ""))
        _sub(periodo_el, "cbc", "FechaLiquidacionFin", periodo.get("fecha_liquidacion_fin", ""))
        _sub(periodo_el, "cbc", "TiempoLaboradoDias", str(periodo.get("tiempo_laborado_dias", "")))

        cls._build_empleador(root, dto.get("empleador", {}))
        cls._build_trabajador(root, dto.get("trabajador", {}))
        cls._build_pago(root, dto.get("pago", {}))
        cls._build_devengados(root, dto.get("devengados", {}))
        cls._build_deducciones(root, dto.get("deducciones", {}))

        totales = _sub(root, "sts", "ResumenNomina")
        _sub(totales, "cbc", "TotalDevengado", _fmt2(dto.get("devengados", {}).get("total", "0")), {"currencyID": "COP"})
        _sub(totales, "cbc", "TotalDeducciones", _fmt2(dto.get("deducciones", {}).get("total", "0")), {"currencyID": "COP"})
        _sub(totales, "cbc", "ComprobanteTotal", _fmt2(dto.get("total_pago", "0")), {"currencyID": "COP"})

        return root

    # ------------------------------------------------------------------
    @classmethod
    def _build_extensions(cls, root: ET.Element, dto: dict, cune: str):
        """Mismo patron que UBL21BuilderService._build_extensions() -- ver
        apps/tenant/facturas/services/dian/ubl21_builder.py. Dos
        UBLExtension: [0] control DIAN, [1] placeholder vacio para la
        firma que inserta XadesSignerService.sign()."""
        ext_content = _sub(root, "ext", "UBLExtensions")
        ext1 = _sub(ext_content, "ext", "UBLExtension")
        _sub(ext1, "ext", "ExtensionURI", "urn:oasis:names:specification:ubl:dsig:ext:XADES")
        content = _sub(ext1, "ext", "ExtensionContent")

        dian_ext = _sub(content, "sts", "DianExtensions")
        resol = dto.get("resolucion", {})
        inv_ctrl = _sub(dian_ext, "sts", "InvoiceControl")
        _sub(inv_ctrl, "sts", "InvoiceAuthorization", resol.get("numero_autorizacion", "0"))
        auth_period = _sub(inv_ctrl, "sts", "AuthorizationPeriod")
        _sub(auth_period, "cbc", "StartDate", resol.get("fecha_inicio", dto["fec_nie"]))
        _sub(auth_period, "cbc", "EndDate", resol.get("fecha_fin", dto["fec_nie"]))
        auth_range = _sub(inv_ctrl, "sts", "AuthorizedInvoices")
        _sub(auth_range, "sts", "Prefix", resol.get("prefijo", ""))
        _sub(auth_range, "sts", "From", resol.get("desde", "1"))
        _sub(auth_range, "sts", "To", resol.get("hasta", "1"))

        # Placeholder vacio -- XadesSignerService lo reemplaza por ds:Signature
        _sub(ext_content, "ext", "UBLExtension")

    # ------------------------------------------------------------------
    @classmethod
    def _build_empleador(cls, root: ET.Element, empleador: dict):
        el = _sub(root, "sts", "Empleador")
        _sub(el, "cbc", "RegistrationName", empleador.get("razon_social", ""))
        _sub(el, "cbc", "CompanyID", empleador.get("nit", ""),
             {"schemeAgencyID": "195", "schemeAgencyName": "CO, DIAN",
              "schemeID": empleador.get("dv", "0"), "schemeName": "31"})
        addr = _sub(el, "cac", "RegistrationAddress")
        _sub(addr, "cbc", "CityName", empleador.get("ciudad", ""))
        addr_line = _sub(addr, "cac", "AddressLine")
        _sub(addr_line, "cbc", "Line", empleador.get("direccion", ""))

    # ------------------------------------------------------------------
    @classmethod
    def _build_trabajador(cls, root: ET.Element, trabajador: dict):
        el = _sub(root, "sts", "Trabajador")
        _sub(el, "cbc", "TipoDocumento", trabajador.get("tipo_documento", "CC"))
        _sub(el, "cbc", "NumeroDocumento", trabajador.get("numero_documento", ""))
        _sub(el, "cbc", "PrimerApellido", trabajador.get("primer_apellido", ""))
        _sub(el, "cbc", "SegundoApellido", trabajador.get("segundo_apellido", ""))
        _sub(el, "cbc", "PrimerNombre", trabajador.get("primer_nombre", ""))
        _sub(el, "cbc", "OtrosNombres", trabajador.get("segundo_nombre", ""))
        _sub(el, "cbc", "TipoTrabajador", trabajador.get("tipo_trabajador", "01"))
        _sub(el, "cbc", "SubTipoTrabajador", trabajador.get("subtipo_trabajador", "00"))
        _sub(el, "cbc", "TipoContrato", trabajador.get("tipo_contrato", ""))
        _sub(el, "cbc", "Cargo", trabajador.get("cargo", ""))
        _sub(el, "cbc", "SalarioIntegral", "false")
        _sub(el, "cbc", "SueldoTrabajador", _fmt2(trabajador.get("salario", "0")), {"currencyID": "COP"})

    # ------------------------------------------------------------------
    @classmethod
    def _build_pago(cls, root: ET.Element, pago: dict):
        el = _sub(root, "sts", "Pago")
        _sub(el, "cbc", "FormaPago", pago.get("forma", "1"))
        _sub(el, "cbc", "MetodoPago", pago.get("metodo", "42"))
        _sub(el, "cbc", "FechaPago", pago.get("fecha_pago", ""))

    # ------------------------------------------------------------------
    @classmethod
    def _build_devengados(cls, root: ET.Element, devengados: dict):
        el = _sub(root, "sts", "Devengados")
        basico = _sub(el, "sts", "Basico")
        _sub(basico, "cbc", "DiasTrabajados", str(devengados.get("dias_trabajados", "30")))
        _sub(basico, "cbc", "SueldoTrabajado", _fmt2(devengados.get("salario_basico", "0")), {"currencyID": "COP"})

        if Decimal(str(devengados.get("auxilio_transporte", "0"))) > 0:
            transporte = _sub(el, "sts", "Transporte")
            _sub(transporte, "cbc", "AuxilioTransporte", _fmt2(devengados.get("auxilio_transporte", "0")), {"currencyID": "COP"})

        if Decimal(str(devengados.get("horas_extras", "0"))) > 0:
            he = _sub(el, "sts", "HorasExtra")
            _sub(he, "cbc", "Pago", _fmt2(devengados.get("horas_extras", "0")), {"currencyID": "COP"})

        if Decimal(str(devengados.get("otros", "0"))) > 0:
            otros = _sub(el, "sts", "OtrosConceptos")
            _sub(otros, "cbc", "Pago", _fmt2(devengados.get("otros", "0")), {"currencyID": "COP"})

    # ------------------------------------------------------------------
    @classmethod
    def _build_deducciones(cls, root: ET.Element, deducciones: dict):
        el = _sub(root, "sts", "Deducciones")
        salud = _sub(el, "sts", "Salud")
        _sub(salud, "cbc", "Deduccion", _fmt2(deducciones.get("salud", "0")), {"currencyID": "COP"})
        pension = _sub(el, "sts", "FondoPension")
        _sub(pension, "cbc", "Deduccion", _fmt2(deducciones.get("pension", "0")), {"currencyID": "COP"})

        if Decimal(str(deducciones.get("otros", "0"))) > 0:
            otros = _sub(el, "sts", "OtrasDeducciones")
            _sub(otros, "cbc", "Deduccion", _fmt2(deducciones.get("otros", "0")), {"currencyID": "COP"})
