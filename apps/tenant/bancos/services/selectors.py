from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)

CUENTA_LIST_FIELDS = (
    "id", "uuid", "nombre", "banco", "tipo", "numero", "empresa_id"
)
CUENTA_DETAIL_FIELDS = (
    "id", "uuid", "nombre", "banco", "tipo", "numero", "empresa_id", "created_at", "updated_at"
)

EXTRACTO_LIST_FIELDS = (
    "id", "uuid", "cuenta_id", "cuenta__uuid", "cuenta__nombre", "cuenta__numero",
    "mes", "anio", "archivo_s3", "procesado", "saldo_inicial", "saldo_final",
    "empresa_id", "sede_id", "sede__nombre",  # BAN-11 (DT-SEDE-01)
)
EXTRACTO_DETAIL_FIELDS = (
    "id", "uuid", "cuenta_id", "cuenta__uuid", "cuenta__nombre", "cuenta__numero",
    "mes", "anio", "archivo_s3", "procesado", "saldo_inicial", "saldo_final",
    "empresa_id", "created_at", "updated_at", "sede_id", "sede__nombre",  # BAN-11
)

TRANSACCION_LIST_FIELDS = (
    "id", "uuid", "extracto_id", "extracto__uuid", "fecha", "descripcion", "sucursal",
    "dcto", "valor", "saldo", "factura_uuid", "proveedor_uuid", "cliente_uuid",
    "conciliado", "notas_conciliacion", "empresa_id",
)
TRANSACCION_DETAIL_FIELDS = (
    "id", "uuid", "extracto_id", "extracto__uuid", "fecha", "descripcion", "sucursal",
    "dcto", "valor", "saldo", "factura_uuid", "proveedor_uuid", "cliente_uuid",
    "conciliado", "notas_conciliacion", "empresa_id", "created_at", "updated_at",
)

class CuentaBancariaSelector:
    """Read-only selectors for CuentaBancaria."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """Get optimized CuentaBancaria queryset for listing."""
        qs = CuentaBancaria.objects.filter(empresa_id=empresa_id).only(*CUENTA_LIST_FIELDS)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(banco__icontains=search) |
                Q(numero__icontains=search)
            )
        return qs.order_by("nombre")

    @staticmethod
    def get_detail(empresa_id: int, uuid=None):
        """Get optimized CuentaBancaria detail or queryset."""
        qs = CuentaBancaria.objects.filter(empresa_id=empresa_id).only(*CUENTA_DETAIL_FIELDS)
        if uuid:
            return qs.filter(uuid=uuid)
        return qs

class ExtractoBancarioSelector:
    """Read-only selectors for ExtractoBancario."""

    @staticmethod
    def get_list(empresa_id: int, cuenta_uuid=None, search: str = None):
        """Get optimized ExtractoBancario list con anotaciones de conciliacion."""
        qs = (
            ExtractoBancario.objects
            .filter(empresa_id=empresa_id)
            .select_related("cuenta", "sede")
            .only(*EXTRACTO_LIST_FIELDS)
            .annotate(
                total_transacciones=Count('transacciones'),
                tx_conciliadas=Count(
                    'transacciones',
                    filter=Q(transacciones__conciliado=True)
                ),
            )
        )
        if cuenta_uuid:
            qs = qs.filter(cuenta__uuid=cuenta_uuid)
        if search:
            qs = qs.filter(
                Q(cuenta__nombre__icontains=search) |
                Q(cuenta__numero__icontains=search)
            )
        return qs.order_by("-anio", "-mes")

    @staticmethod
    def get_detail(empresa_id: int, uuid=None):
        """Get optimized ExtractoBancario detail."""
        qs = ExtractoBancario.objects.filter(empresa_id=empresa_id).select_related("cuenta", "sede").only(*EXTRACTO_DETAIL_FIELDS)
        if uuid:
            return qs.filter(uuid=uuid)
        return qs

class TransaccionBancariaSelector:
    """Read-only selectors for TransaccionBancaria."""

    @staticmethod
    def get_list(
        empresa_id: int,
        extracto_uuid=None,
        search: str = None,
        tipo_movimiento: str = None,
        conciliado: str = None,
    ):
        """Get optimized TransaccionBancaria list."""
        qs = (
            TransaccionBancaria.objects.filter(empresa_id=empresa_id)
            .select_related("extracto")
            .only(*TRANSACCION_LIST_FIELDS)
            .annotate(
                monto_aplicado_total=Coalesce(
                    Sum("aplicaciones__monto_aplicado"), Value(0), output_field=DecimalField()
                )
            )
        )
        if extracto_uuid:
            qs = qs.filter(extracto__uuid=extracto_uuid)
        if search:
            qs = qs.filter(
                Q(descripcion__icontains=search) |
                Q(sucursal__icontains=search) |
                Q(dcto__icontains=search)
            )
        tipo_mov = (tipo_movimiento or "").upper()
        if tipo_mov == "DEBITO":
            qs = qs.filter(valor__lt=0)
        elif tipo_mov == "CREDITO":
            qs = qs.filter(valor__gte=0)

        conc = (conciliado or "").lower()
        if conc in ("true", "1"):
            qs = qs.filter(conciliado=True)
        elif conc in ("false", "0"):
            qs = qs.filter(conciliado=False)
        return qs.order_by("-fecha", "-created_at")

    @staticmethod
    def get_detail(empresa_id: int, uuid=None):
        """Get optimized TransaccionBancaria detail."""
        qs = TransaccionBancaria.objects.filter(empresa_id=empresa_id).select_related("extracto").only(*TRANSACCION_DETAIL_FIELDS)
        if uuid:
            return qs.filter(uuid=uuid)
        return qs


APLICACION_FIELDS = (
    "id", "uuid", "transaccion_id", "transaccion__uuid",
    "tipo_referencia", "referencia_uuid", "tercero_tipo", "tercero_uuid",
    "monto_aplicado", "fecha_aplicacion", "notas",
    "origen_matching", "confianza", "empresa_id", "created_at",
)


class TerceroDisplaySelector:
    """BAN-06/07: resuelve UUIDs de terceros/documentos vinculados a un texto
    legible (numero+nombre / razon social) en una sola query por tipo -- evita
    N+1 llamadas a los endpoints search-* desde el frontend solo para mostrar
    el nombre de un vinculo ya guardado (antes se mostraba el UUID truncado)."""

    @staticmethod
    def resolver(empresa_id: int, factura_uuids=None, proveedor_uuids=None, cliente_uuids=None) -> dict:
        """Retorna {uuid_str: display_str}. Un UUID sin match (registro
        eliminado o soft-ref sin resolver) queda ausente del dict -- el
        llamador debe usar un fallback, mismo criterio de soft references
        ya usado en el resto del modulo (no bloquea)."""
        display = {}

        if factura_uuids:
            from apps.tenant.facturas.models import Factura

            for f in Factura.objects.filter(empresa_id=empresa_id, uuid__in=factura_uuids).only(
                "uuid", "numero", "prefijo", "naturaleza", "receptor_razon_social", "emisor_razon_social"
            ):
                nombre = f.receptor_razon_social if f.naturaleza == "VENTA" else f.emisor_razon_social
                numero = f"{f.prefijo}-{f.numero}" if f.prefijo else (f.numero or "")
                partes = [p for p in (numero, nombre) if p]
                display[str(f.uuid)] = " — ".join(partes) if partes else str(f.uuid)

        if proveedor_uuids:
            from apps.tenant.proveedores.models import Proveedor

            for p in Proveedor.objects.filter(empresa_id=empresa_id, uuid__in=proveedor_uuids).only(
                "uuid", "razon_social", "nombre_comercial"
            ):
                display[str(p.uuid)] = p.nombre_comercial or p.razon_social

        if cliente_uuids:
            from apps.tenant.clientes.models import Cliente

            for c in Cliente.objects.filter(empresa_id=empresa_id, uuid__in=cliente_uuids).only(
                "uuid", "razon_social", "nombre_comercial"
            ):
                display[str(c.uuid)] = c.nombre_comercial or c.razon_social

        return display


class ExtractoBancarioKpiSelector:
    """BAN-09: KPIs agregados de conciliacion a nivel de empresa (no por
    extracto individual -- eso ya existe en render_offcanvas_detalle, Fase 19).
    Se muestra en la cabecera del tab Extractos."""

    @staticmethod
    def get_kpis_empresa(empresa_id: int) -> dict:
        qs = TransaccionBancaria.objects.filter(empresa_id=empresa_id)
        agg = qs.aggregate(
            total=Count("id"),
            conciliadas=Count("id", filter=Q(conciliado=True)),
            # Suma de valores ABSOLUTOS (no el neto -- ingresos/egresos se
            # cancelarian entre si) de las transacciones aun sin conciliar.
            monto_sin_conciliar=Coalesce(
                Sum(
                    Case(When(valor__lt=0, then=-F("valor")), default=F("valor")),
                    filter=Q(conciliado=False),
                    output_field=DecimalField(),
                ),
                Value(0),
                output_field=DecimalField(),
            ),
        )
        total = agg["total"] or 0
        conciliadas = agg["conciliadas"] or 0
        agg["pendientes"] = total - conciliadas
        agg["pct_conciliado"] = round((conciliadas / total) * 100) if total else 0
        return agg


class MovimientoBancarioAplicacionSelector:
    """Read-only selectors for MovimientoBancarioAplicacion (Fase 5/18)."""

    @staticmethod
    def get_list(empresa_id: int, transaccion_uuid=None):
        qs = (
            MovimientoBancarioAplicacion.objects.filter(empresa_id=empresa_id)
            .only(*APLICACION_FIELDS)
        )
        if transaccion_uuid:
            qs = qs.filter(transaccion__uuid=transaccion_uuid)
        return qs.order_by("-fecha_aplicacion", "-created_at")

    @staticmethod
    def get_detail(empresa_id: int, uuid=None):
        qs = MovimientoBancarioAplicacion.objects.filter(empresa_id=empresa_id).only(*APLICACION_FIELDS)
        if uuid:
            return qs.filter(uuid=uuid)
        return qs
