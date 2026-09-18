"""BAN-12 (.agent/AUDITORIA_FLUJO_COMPLETO.md §10): exportar el reporte de
conciliacion de un extracto (periodo = cuenta + mes/anio) a CSV.

Solo lectura -- reutiliza los selectores ya existentes (TransaccionBancariaSelector,
TerceroDisplaySelector) en vez de reimplementar el resuelto de nombres."""
import csv
import io

from apps.tenant.bancos.services.selectors import TerceroDisplaySelector, TransaccionBancariaSelector


class ExtractoBancarioExportService:
    """Genera el reporte de conciliacion de un extracto en formato CSV."""

    @staticmethod
    def generar_csv_conciliacion(empresa_id: int, extracto) -> str:
        transacciones = list(
            TransaccionBancariaSelector.get_list(empresa_id=empresa_id, extracto_uuid=str(extracto.uuid))
        )
        display_map = TerceroDisplaySelector.resolver(
            empresa_id,
            factura_uuids={t.factura_uuid for t in transacciones if t.factura_uuid},
            proveedor_uuids={t.proveedor_uuid for t in transacciones if t.proveedor_uuid},
            cliente_uuids={t.cliente_uuid for t in transacciones if t.cliente_uuid},
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Fecha", "Descripcion", "Documento", "Tipo", "Valor", "Saldo",
            "Conciliado", "Vinculo", "Notas",
        ])
        for t in transacciones:
            vinculo = ""
            if t.factura_uuid:
                vinculo = display_map.get(str(t.factura_uuid)) or f"Factura {t.factura_uuid}"
            elif t.proveedor_uuid:
                vinculo = display_map.get(str(t.proveedor_uuid)) or f"Proveedor {t.proveedor_uuid}"
            elif t.cliente_uuid:
                vinculo = display_map.get(str(t.cliente_uuid)) or f"Cliente {t.cliente_uuid}"

            writer.writerow([
                t.fecha.strftime("%Y-%m-%d"),
                t.descripcion,
                t.dcto or "",
                t.tipo_movimiento,
                str(t.valor),
                str(t.saldo),
                "Si" if t.conciliado else "No",
                vinculo,
                t.notas_conciliacion or "",
            ])
        return buffer.getvalue()
