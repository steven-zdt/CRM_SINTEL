"""
Capa de importacion de extractos bancarios, desacoplada del formato de
archivo (Fase 2, mision Bancos v3.0).

    BankStatementImporter          (ABC)
        XLSXBankStatementImporter
        CSVBankStatementImporter
        XMLBankStatementImporter   (adapter contract -- UNSUPPORTED_FORMAT)

Uso:
    from apps.tenant.bancos.services.importers import get_importer_for
    importer = get_importer_for(nombre_archivo)
    resultado = importer.importar(archivo_abierto, nombre_archivo)
"""
from apps.tenant.bancos.services.importers.base import (
    BankStatementImporter,
    UnsupportedFormatError,
)
from apps.tenant.bancos.services.importers.csv_importer import CSVBankStatementImporter
from apps.tenant.bancos.services.importers.xlsx_importer import XLSXBankStatementImporter
from apps.tenant.bancos.services.importers.xml_importer import XMLBankStatementImporter

# Orden de deteccion: el primero cuyo puede_procesar() devuelva True gana.
_IMPORTERS = [
    XLSXBankStatementImporter(),
    CSVBankStatementImporter(),
    XMLBankStatementImporter(),
]


def get_importer_for(nombre_archivo: str) -> BankStatementImporter:
    """Devuelve el importador que declara soportar la extension del archivo.

    Lanza UnsupportedFormatError si ninguno la reconoce (nunca ImportError
    ni excepcion generica -- el caller decide como reportarlo al usuario).
    """
    nombre_archivo = nombre_archivo or ""
    for importer in _IMPORTERS:
        if importer.puede_procesar(nombre_archivo):
            return importer
    raise UnsupportedFormatError(
        f"Formato de archivo no soportado: '{nombre_archivo}'. "
        f"Formatos soportados: XLSX, CSV. XML disponible solo para bancos con "
        f"adapter configurado."
    )


__all__ = [
    "BankStatementImporter",
    "UnsupportedFormatError",
    "XLSXBankStatementImporter",
    "CSVBankStatementImporter",
    "XMLBankStatementImporter",
    "get_importer_for",
]
