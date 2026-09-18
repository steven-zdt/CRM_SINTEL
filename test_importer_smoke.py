import io
from decimal import Decimal

from apps.tenant.bancos.services.parsing.money import parse_money

CASOS = [
    ("1,400,000.00", Decimal("1400000.00")),
    ("-1,431,900.00", Decimal("-1431900.00")),
    (".97", Decimal("0.97")),
    ("1.00", Decimal("1.00")),
    ("-100,000.00", Decimal("-100000.00")),
    ("1.400.000,00", Decimal("1400000.00")),
    ("-1.431.900,00", Decimal("-1431900.00")),
]
for texto, esperado in CASOS:
    resultado = parse_money(texto)
    ok = "OK" if resultado == esperado else "FAIL"
    print(f"{ok}  parse_money({texto!r}) = {resultado}  (esperado {esperado})")

print("\n--- XLSX importer contra el fixture real ---")
from apps.tenant.bancos.services.importers import get_importer_for

with open("media/extractos/10800014844_AGO2026.xlsx", "rb") as f:
    importer = get_importer_for("10800014844_AGO2026.xlsx")
    resultado = importer.importar(f, "10800014844_AGO2026.xlsx")

print("filas_leidas:", resultado.filas_leidas)
print("filas_importadas:", resultado.filas_importadas)
print("filas_omitidas:", resultado.filas_omitidas)
print("errores:", resultado.errores)
print("n_transactions:", len(resultado.transactions))
print("resumen extraido:", resultado.saldo_inicial_declarado, resultado.total_creditos_declarado,
      resultado.total_debitos_declarado, resultado.saldo_final_declarado)

creditos = sum((t.valor for t in resultado.transactions if t.valor >= 0), Decimal("0"))
debitos = sum((-t.valor for t in resultado.transactions if t.valor < 0), Decimal("0"))
n_creditos = sum(1 for t in resultado.transactions if t.valor >= 0)
n_debitos = sum(1 for t in resultado.transactions if t.valor < 0)
print(f"creditos={creditos} (n={n_creditos})  debitos={debitos} (n={n_debitos})")

primero = resultado.transactions[0]
ultimo = resultado.transactions[-1]
print("primero:", primero.dia_sin_anio, primero.mes_sin_anio, primero.descripcion, primero.valor, primero.saldo)
print("ultimo:", ultimo.dia_sin_anio, ultimo.mes_sin_anio, ultimo.descripcion, ultimo.valor, ultimo.saldo)

saldo_inicial_derivado = primero.saldo - primero.valor
saldo_final_derivado = ultimo.saldo
print("saldo_inicial_derivado:", saldo_inicial_derivado)
print("saldo_final_derivado:", saldo_final_derivado)
print("check balance:", saldo_inicial_derivado + creditos - debitos, "== ", saldo_final_derivado)

print("\n--- Resolucion de fecha con anio (simulando extracto mes=8, anio=2026) ---")
import datetime
def resolver_anio(dia, mes, extracto_mes, extracto_anio):
    if abs(mes - extracto_mes) > 6:
        return extracto_anio - 1 if mes > extracto_mes else extracto_anio + 1
    return extracto_anio

for t in resultado.transactions[:3] + resultado.transactions[-3:]:
    anio = resolver_anio(t.dia_sin_anio, t.mes_sin_anio, 8, 2026)
    fecha = datetime.date(anio, t.mes_sin_anio, t.dia_sin_anio)
    print(fecha, t.descripcion[:30], t.valor)
