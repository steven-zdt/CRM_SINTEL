import io
from decimal import Decimal
from apps.tenant.bancos.services.importers import get_importer_for
from apps.tenant.bancos.services.importers.xml_importer import XMLBankStatementImporter
from apps.tenant.bancos.services.importers.base import UnsupportedFormatError

csv_texto = (
    "FECHA;DESCRIPCION;VALOR;SALDO\n"
    "01/08/2026;ABONO INTERESES;4,05;986834,90\n"
    "04/08/2026;PAGO CLIENTE ACME;1400000,00;2386834,90\n"
    "04/08/2026;PAGO PROVEEDOR XYZ;-1431900,00;954936,20\n"
)
archivo = io.BytesIO(csv_texto.encode("utf-8-sig"))
importer = get_importer_for("extracto.csv")
resultado = importer.importar(archivo, "extracto.csv")
print("formato:", resultado.source_format)
print("filas_leidas:", resultado.filas_leidas, "importadas:", resultado.filas_importadas, "omitidas:", resultado.filas_omitidas)
for t in resultado.transactions:
    print(t.fecha, t.descripcion, t.valor, t.saldo)

print("\n--- CSV con separador coma y BOM, decimales americanos ---")
csv2 = "FECHA,DESCRIPCION,VALOR,SALDO\n2026-08-01,Test,1000.50,5000.00\n"
archivo2 = io.BytesIO(csv2.encode("utf-8"))
resultado2 = get_importer_for("mov.csv").importar(archivo2, "mov.csv")
print("filas_importadas:", resultado2.filas_importadas)
for t in resultado2.transactions:
    print(t.fecha, t.descripcion, t.valor, t.saldo)

print("\n--- XML sin adapter -> UnsupportedFormatError, no rompe el sistema ---")
try:
    get_importer_for("extracto.xml").importar(io.BytesIO(b"<xml/>"), "extracto.xml")
    print("FAIL: deberia haber lanzado UnsupportedFormatError")
except UnsupportedFormatError as e:
    print("OK:", str(e)[:80])

print("\n--- Extension desconocida -> UnsupportedFormatError desde get_importer_for ---")
try:
    get_importer_for("archivo.pdf")
    print("FAIL")
except UnsupportedFormatError as e:
    print("OK:", str(e)[:80])
