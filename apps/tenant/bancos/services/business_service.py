import re
import datetime
import logging
from decimal import Decimal
import pandas as pd
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.tenant.bancos.models import ExtractoBancario, TransaccionBancaria
from apps.tenant.bancos.services.crud_service import TransaccionBancariaCRUDService

logger = logging.getLogger(__name__)

def parse_decimal(val) -> Decimal:
    """Helper to convert float, int, or formatted strings to Decimal."""
    if pd.isna(val) or val == "":
        return Decimal("0.00")
    if isinstance(val, (int, float)):
        return Decimal(f"{val:.2f}")
    
    # Remove commas and clean whitespace
    val_str = str(val).strip().replace(",", "")
    try:
        return Decimal(val_str)
    except Exception:
        logger.warning(f"[BancosBusiness] Failed parsing decimal from raw value: {val}")
        return Decimal("0.00")

class ExtractoBancarioBusinessService:
    """Business logic for processing bank statements."""

    @staticmethod
    @transaction.atomic
    def procesar_archivo_extracto(extracto: ExtractoBancario) -> int:
        """
        Parses the uploaded bank statement Excel file and ingests transactions.
        Ensures idempotency by deleting any previously processed transactions for this extract.
        """
        if not extracto.archivo_s3:
            raise ValidationError("El extracto no tiene un archivo adjunto.")

        # Open and load the excel file using pandas
        extracto.archivo_s3.open("rb")
        try:
            df = pd.read_excel(extracto.archivo_s3, header=None)
        except Exception as e:
            logger.error(f"[BancosBusiness] Error loading Excel file: {str(e)}")
            raise ValidationError(f"Error al leer el archivo Excel: {str(e)}")
        finally:
            extracto.archivo_s3.close()

        # Basic structure validation
        if df.shape[1] < 6:
            raise ValidationError(
                "Estructura de archivo invalida. Se requieren al menos 6 columnas (FECHA, DESCRIPCION, SUCURSAL, DCTO., VALOR, SALDO)."
            )

        # Regex to detect transaction rows (e.g. '1/04', '15/04')
        date_pattern = re.compile(r"^\d{1,2}/\d{1,2}$")
        transacciones_data = []

        for index, row in df.iterrows():
            col_0 = str(row[0]).strip() if pd.notna(row[0]) else ""

            if date_pattern.match(col_0):
                # Valid transaction row found
                fecha_str = col_0
                descripcion = str(row[1]).strip() if pd.notna(row[1]) else ""
                sucursal = str(row[2]).strip() if pd.notna(row[2]) else ""
                dcto = str(row[3]).strip() if pd.notna(row[3]) else ""
                valor_raw = row[4]
                saldo_raw = row[5]

                # Convert amounts safely
                valor = parse_decimal(valor_raw)
                saldo = parse_decimal(saldo_raw)

                # Parse date parts
                parts = fecha_str.split("/")
                day = int(parts[0])
                month = int(parts[1])

                # Determine correct year handling month transitions (e.g., Dec to Jan)
                extracto_mes = extracto.mes
                extracto_anio = extracto.anio

                if abs(month - extracto_mes) > 6:
                    if month > extracto_mes:
                        year = extracto_anio - 1
                    else:
                        year = extracto_anio + 1
                else:
                    year = extracto_anio

                fecha = datetime.date(year, month, day)

                transacciones_data.append({
                    "fecha": fecha,
                    "descripcion": descripcion,
                    "sucursal": sucursal,
                    "dcto": dcto,
                    "valor": valor,
                    "saldo": saldo
                })

        if not transacciones_data:
            raise ValidationError("No se encontraron transacciones validas en el archivo.")

        # Clean existing transactions for this statement (idempotency guarantee)
        # DSV: empresa_id anclado para evitar borrado cross-tenant si extracto fuera manipulado
        TransaccionBancaria.objects.filter(extracto=extracto, empresa_id=extracto.empresa_id).delete()

        # Ingest new transactions in bulk
        TransaccionBancariaCRUDService.crear_transacciones_bulk(
            transacciones_data, extracto, extracto.empresa
        )

        # Mark as processed
        extracto.procesado = True
        extracto.save(update_fields=["procesado"])

        logger.info(
            f"[BancosBusiness] Ingestadas {len(transacciones_data)} transacciones para extracto ID={extracto.id}"
        )
        return len(transacciones_data)
