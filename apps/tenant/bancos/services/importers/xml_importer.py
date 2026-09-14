"""
Adapter XML (Fase 2 y Fase 27, mision Bancos v3.0).

No existe hoy un esquema XML bancario de referencia real disponible para
este proyecto (a diferencia del XLSX, no se recibio ningun fixture XML
real) -- por eso este importador es CONTRATO/ADAPTER, no un parser
funcional todavia. Declara la interfaz esperada (mismo
BankStatementImporter.importar() -> NormalizedBankStatement que XLSX/CSV)
para que agregar un banco con XML propietario en el futuro sea
`class BBVAXMLImporter(XMLBankStatementImporter): ...` sin tocar el resto
del sistema (Fase 27 -- por adapter, sin bancos hardcodeados).

Cuando el XML no tiene un mapping configurado, importar() lanza
UnsupportedFormatError -- el caller (business_service) lo traduce a un
mensaje accionable, nunca un 500 (Fase 26).
"""
from apps.tenant.bancos.services.importers.base import (
    BankStatementImporter,
    NormalizedBankStatement,
    UnsupportedFormatError,
)


class XMLBankStatementImporter(BankStatementImporter):
    formato = "XML"
    extensiones = (".xml",)

    # Fase 27: mapping por banco (ej. {"bancolombia": BancolombiaXMLAdapter}).
    # Vacio a proposito -- ningun banco tiene un esquema XML confirmado hoy.
    ADAPTERS_POR_BANCO: dict = {}

    def importar(self, archivo, nombre_archivo: str) -> NormalizedBankStatement:
        raise UnsupportedFormatError(
            "STATUS = UNSUPPORTED_FORMAT: no hay un adapter XML configurado todavia. "
            "La arquitectura esta preparada (BankStatementImporter.importar() -> "
            "NormalizedBankStatement, igual que XLSX/CSV) pero requiere el esquema "
            "XML real del banco antes de implementar el parseo -- usa XLSX o CSV "
            "mientras tanto."
        )
