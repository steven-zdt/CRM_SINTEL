from django.db.models import Count, Q
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario, TransaccionBancaria

CUENTA_LIST_FIELDS = (
    "id", "uuid", "nombre", "banco", "tipo", "numero", "empresa_id"
)
CUENTA_DETAIL_FIELDS = (
    "id", "uuid", "nombre", "banco", "tipo", "numero", "empresa_id", "created_at", "updated_at"
)

EXTRACTO_LIST_FIELDS = (
    "id", "uuid", "cuenta_id", "cuenta__uuid", "cuenta__nombre", "cuenta__numero",
    "mes", "anio", "archivo_s3", "procesado", "saldo_inicial", "saldo_final",
    "empresa_id",
)
EXTRACTO_DETAIL_FIELDS = (
    "id", "uuid", "cuenta_id", "cuenta__uuid", "cuenta__nombre", "cuenta__numero",
    "mes", "anio", "archivo_s3", "procesado", "saldo_inicial", "saldo_final",
    "empresa_id", "created_at", "updated_at",
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
            .select_related("cuenta")
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
        qs = ExtractoBancario.objects.filter(empresa_id=empresa_id).select_related("cuenta").only(*EXTRACTO_DETAIL_FIELDS)
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
        qs = TransaccionBancaria.objects.filter(empresa_id=empresa_id).select_related("extracto").only(*TRANSACCION_LIST_FIELDS)
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
