"""
DTOs de importacion y contrato base (Fase 2, mision Bancos v3.0).

NormalizedBankStatement / NormalizedBankTransaction son el formato interno
unico que consume el resto del sistema (validacion de balance,
bulk_create de TransaccionBancaria) -- ningun consumidor debe conocer si
el origen fue XLSX, CSV o XML.
"""
import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


class UnsupportedFormatError(Exception):
    """El archivo tiene una extension/estructura no soportada todavia.

    No es un error fatal del sistema -- el caller lo traduce a un mensaje
    accionable para el usuario (Fase 26: nunca un 500).
    """


class StatementParsingError(Exception):
    """El archivo tiene la extension correcta pero su contenido no pudo
    interpretarse (estructura inesperada, columnas faltantes, etc.)."""


class StatementBalanceError(Exception):
    """saldo_inicial + creditos - debitos != saldo_final (tolerancia 0.01).

    Fase 1 de la mision: el importador NUNCA marca procesado=True en
    silencio si esta validacion falla.
    """

    def __init__(self, mensaje, saldo_inicial=None, total_creditos=None,
                 total_debitos=None, saldo_final_declarado=None, saldo_final_calculado=None):
        super().__init__(mensaje)
        self.saldo_inicial = saldo_inicial
        self.total_creditos = total_creditos
        self.total_debitos = total_debitos
        self.saldo_final_declarado = saldo_final_declarado
        self.saldo_final_calculado = saldo_final_calculado


@dataclass
class NormalizedBankTransaction:
    """Una linea de movimiento, ya normalizada, independiente del formato origen."""

    fecha: date | None
    descripcion: str
    valor: Decimal
    saldo: Decimal
    sucursal: str | None = None
    dcto: str | None = None

    # Algunos extractos (ej. Bancolombia) solo traen dia/mes sin año en la
    # columna FECHA -- cuando fecha es None, el caller (que conoce el
    # periodo mes/anio del ExtractoBancario) debe resolver el año real con
    # dia_sin_anio/mes_sin_anio (ver ExtractoBancarioBusinessService).
    dia_sin_anio: int | None = None
    mes_sin_anio: int | None = None

    # Metadata de origen (Fase 2) -- trazabilidad, no se persiste como
    # columnas nuevas en TransaccionBancaria en esta fase (evita migrar un
    # modelo ya usado en produccion solo por metadata de auditoria); se usa
    # para fingerprint y deduplicacion (Fase 25).
    source_row_number: int | None = None

    @property
    def tipo_movimiento(self) -> str:
        return "DEBITO" if self.valor < Decimal("0") else "CREDITO"

    def fingerprint(self, currency: str, source_file_hash: str) -> str:
        """Fase 25: fingerprint de deduplicacion. No depende solo de
        fecha+valor (pueden existir movimientos legitimos iguales) -- combina
        fecha, valor, saldo, descripcion, dcto y numero de fila de origen."""
        base = "|".join([
            str(self.fecha), str(self.valor), str(self.saldo),
            (self.descripcion or "").strip().upper(),
            (self.dcto or "").strip().upper(),
            str(self.source_row_number or ""),
            currency, source_file_hash,
        ])
        return hashlib.sha256(base.encode("utf-8")).hexdigest()


@dataclass
class NormalizedBankStatement:
    """Resultado normalizado completo de un archivo de extracto."""

    transactions: list = field(default_factory=list)  # list[NormalizedBankTransaction]

    # Metadata del encabezado del archivo (best-effort -- no todos los
    # formatos/bancos la exponen; None cuando no se pudo extraer).
    saldo_inicial_declarado: Decimal | None = None
    saldo_final_declarado: Decimal | None = None
    total_creditos_declarado: Decimal | None = None
    total_debitos_declarado: Decimal | None = None

    source_format: str = ""          # "XLSX" | "CSV" | "XML"
    source_file_name: str = ""
    source_file_hash: str = ""
    currency: str = "COP"

    filas_leidas: int = 0
    filas_importadas: int = 0
    filas_omitidas: int = 0
    errores: list = field(default_factory=list)      # list[str]
    advertencias: list = field(default_factory=list)  # list[str]

    def resumen(self) -> dict:
        return {
            "filas_leidas": self.filas_leidas,
            "filas_importadas": self.filas_importadas,
            "filas_omitidas": self.filas_omitidas,
            "errores": self.errores,
            "advertencias": self.advertencias,
        }


class BankStatementImporter:
    """Contrato base -- Fase 2 y Fase 27 (adapter por banco, no hardcoded)."""

    formato: str = "GENERICO"
    extensiones: tuple = ()

    def puede_procesar(self, nombre_archivo: str) -> bool:
        nombre = (nombre_archivo or "").lower()
        return any(nombre.endswith(ext) for ext in self.extensiones)

    def importar(self, archivo, nombre_archivo: str) -> NormalizedBankStatement:
        raise NotImplementedError
