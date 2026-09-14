import datetime
import logging
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.bancos.models import (
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)
from apps.tenant.bancos.services.crud_service import TransaccionBancariaCRUDService
from apps.tenant.bancos.services.importers import get_importer_for
from apps.tenant.bancos.services.importers.base import (
    StatementBalanceError,
    StatementParsingError,
    UnsupportedFormatError,
)
from apps.tenant.bancos.services.parsing.money import parse_money

logger = logging.getLogger(__name__)

TOLERANCIA_BALANCE = Decimal("0.01")


def parse_decimal(val) -> Decimal:
    """Alias retro-compatible -- codigo/tests previos importan este nombre.
    Delega en el parser monetario robusto real (Fase 3)."""
    return parse_money(val)


def _resolver_anio(dia: int, mes: int, extracto_mes: int, extracto_anio: int) -> int:
    """Mismo criterio de rollover de año ya validado en produccion: si el
    mes de la fila esta a mas de 6 meses del mes del periodo del extracto,
    se asume que cruza el limite de año (extractos que arrancan a fin de
    mes y terminan a inicio del siguiente)."""
    if abs(mes - extracto_mes) > 6:
        return extracto_anio - 1 if mes > extracto_mes else extracto_anio + 1
    return extracto_anio


def _validar_balance(transacciones_data: list, saldo_inicial_hint=None):
    """Fase 1 -- validacion obligatoria, format-agnostica: se deriva
    exclusivamente de las propias filas de movimientos (no depende de que
    el formato origen exponga un bloque 'Resumen'). Nunca marca
    procesado=True si esta validacion falla."""
    if not transacciones_data:
        return

    primero = transacciones_data[0]
    ultimo = transacciones_data[-1]

    saldo_inicial_calculado = primero["saldo"] - primero["valor"]
    saldo_final_calculado = ultimo["saldo"]
    total_creditos = sum((t["valor"] for t in transacciones_data if t["valor"] >= 0), Decimal("0.00"))
    total_debitos = sum((-t["valor"] for t in transacciones_data if t["valor"] < 0), Decimal("0.00"))

    saldo_inicial = saldo_inicial_hint if saldo_inicial_hint is not None else saldo_inicial_calculado
    saldo_final_esperado = saldo_inicial + total_creditos - total_debitos

    diferencia = abs(saldo_final_esperado - saldo_final_calculado)
    if diferencia > TOLERANCIA_BALANCE:
        raise StatementBalanceError(
            f"Inconsistencia de saldos detectada: saldo_inicial ({saldo_inicial}) + "
            f"creditos ({total_creditos}) - debitos ({total_debitos}) = {saldo_final_esperado}, "
            f"pero el saldo final segun el ultimo movimiento es {saldo_final_calculado} "
            f"(diferencia de {diferencia}, tolerancia {TOLERANCIA_BALANCE}).",
            saldo_inicial=saldo_inicial, total_creditos=total_creditos,
            total_debitos=total_debitos, saldo_final_declarado=saldo_final_esperado,
            saldo_final_calculado=saldo_final_calculado,
        )

    return {
        "saldo_inicial": saldo_inicial_calculado,
        "saldo_final": saldo_final_calculado,
        "total_creditos": total_creditos,
        "total_debitos": total_debitos,
    }


class ExtractoBancarioBusinessService:
    """Business logic for processing bank statements (Fase 1-3-24, mision Bancos v3.0)."""

    @staticmethod
    @transaction.atomic
    def procesar_archivo_extracto(extracto: ExtractoBancario, forzar: bool = False) -> dict:
        """
        Importa (multiformato: XLSX/CSV, XML preparado) -> normaliza -> valida
        balance -> ingesta transacciones.

        REM P1-03: select_for_update() sobre el propio extracto evita que 2
        llamadas concurrentes intercalen su delete()+insert() (idempotencia).

        Fase 24 (Importacion no destructiva): si el extracto ya tiene
        transacciones conciliadas o con aplicaciones registradas, bloquea el
        reprocesamiento salvo forzar=True explicito -- evita borrar en
        silencio clasificaciones ya hechas por el usuario.

        Devuelve un dict con filas_leidas/importadas/omitidas/errores/
        advertencias y los totales de balance (Fase 26 -- nunca un 500 por
        una fila mala, nunca procesado=True si el balance no cuadra).
        """
        extracto = ExtractoBancario.objects.select_for_update().get(pk=extracto.pk)

        if not extracto.archivo_s3:
            raise ValidationError("El extracto no tiene un archivo adjunto.")

        if not forzar:
            existentes = TransaccionBancaria.objects.filter(extracto=extracto, empresa_id=extracto.empresa_id)
            n_conciliadas = existentes.filter(conciliado=True).count()
            n_aplicaciones = MovimientoBancarioAplicacion.objects.filter(
                transaccion__extracto=extracto, empresa_id=extracto.empresa_id
            ).count()
            if n_conciliadas or n_aplicaciones:
                raise ValidationError(
                    f"Este extracto ya tiene {n_conciliadas} transaccion(es) conciliada(s) y {n_aplicaciones} "
                    "aplicacion(es) registrada(s). Reprocesar borraria esas transacciones y "
                    "sus vinculos. Si estas seguro, reintenta con forzar=true."
                )

        nombre_archivo = getattr(extracto.archivo_s3, "name", "") or ""
        try:
            importer = get_importer_for(nombre_archivo)
        except UnsupportedFormatError as exc:
            raise ValidationError(str(exc)) from exc

        extracto.archivo_s3.open("rb")
        try:
            estado_normalizado = importer.importar(extracto.archivo_s3, nombre_archivo)
        except (StatementParsingError, UnsupportedFormatError) as exc:
            raise ValidationError(str(exc)) from exc
        finally:
            extracto.archivo_s3.close()

        transacciones_data = []
        for tx in estado_normalizado.transactions:
            fecha = tx.fecha
            if fecha is None and tx.dia_sin_anio and tx.mes_sin_anio:
                anio = _resolver_anio(tx.dia_sin_anio, tx.mes_sin_anio, extracto.mes, extracto.anio)
                try:
                    fecha = datetime.date(anio, tx.mes_sin_anio, tx.dia_sin_anio)
                except ValueError as exc:
                    estado_normalizado.filas_omitidas += 1
                    estado_normalizado.filas_importadas -= 1
                    estado_normalizado.errores.append(f"Fila {tx.source_row_number}: fecha invalida ({exc})")
                    continue
            if fecha is None:
                estado_normalizado.filas_omitidas += 1
                estado_normalizado.filas_importadas -= 1
                estado_normalizado.errores.append(f"Fila {tx.source_row_number}: sin fecha valida")
                continue

            transacciones_data.append({
                "fecha": fecha,
                "descripcion": tx.descripcion or "",
                "sucursal": tx.sucursal,
                "dcto": tx.dcto,
                "valor": tx.valor,
                "saldo": tx.saldo,
            })

        if not transacciones_data:
            raise ValidationError("No se encontraron transacciones validas en el archivo.")

        saldo_inicial_hint = (
            extracto.saldo_inicial
            if extracto.saldo_inicial and extracto.saldo_inicial != Decimal("0.00")
            else estado_normalizado.saldo_inicial_declarado
        )
        try:
            balance = _validar_balance(transacciones_data, saldo_inicial_hint=saldo_inicial_hint)
        except StatementBalanceError as exc:
            # Fase 1: nunca marcar procesado=True en silencio si el balance no cuadra.
            raise ValidationError(str(exc)) from exc

        # Idempotencia (delete + bulk_create), DSV: empresa_id anclado.
        TransaccionBancaria.objects.filter(extracto=extracto, empresa_id=extracto.empresa_id).delete()

        TransaccionBancariaCRUDService.crear_transacciones_bulk(
            transacciones_data, extracto, extracto.empresa
        )

        extracto.saldo_inicial = balance["saldo_inicial"]
        extracto.saldo_final = balance["saldo_final"]
        extracto.procesado = True
        extracto.save(update_fields=["procesado", "saldo_inicial", "saldo_final"])

        logger.info(
            "[BancosBusiness] Ingestadas %s transacciones para extracto ID=%s (formato=%s, "
            "creditos=%s, debitos=%s, saldo_inicial=%s, saldo_final=%s)",
            len(transacciones_data), extracto.id, estado_normalizado.source_format,
            balance["total_creditos"], balance["total_debitos"],
            balance["saldo_inicial"], balance["saldo_final"],
        )

        return {
            "transacciones_importadas": len(transacciones_data),
            "filas_leidas": estado_normalizado.filas_leidas,
            "filas_importadas": estado_normalizado.filas_importadas,
            "filas_omitidas": estado_normalizado.filas_omitidas,
            "errores": estado_normalizado.errores,
            "advertencias": estado_normalizado.advertencias,
            "formato": estado_normalizado.source_format,
            "saldo_inicial": str(balance["saldo_inicial"]),
            "saldo_final": str(balance["saldo_final"]),
            "total_creditos": str(balance["total_creditos"]),
            "total_debitos": str(balance["total_debitos"]),
        }
