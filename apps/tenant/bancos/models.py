import uuid as uuid_module
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel

MES_CHOICES = [
    (1, _('Enero')), (2, _('Febrero')), (3, _('Marzo')), (4, _('Abril')),
    (5, _('Mayo')), (6, _('Junio')), (7, _('Julio')), (8, _('Agosto')),
    (9, _('Septiembre')), (10, _('Octubre')), (11, _('Noviembre')), (12, _('Diciembre')),
]

class CuentaBancaria(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    nombre = models.CharField(max_length=100, verbose_name=_("Nombre"))
    banco = models.CharField(max_length=100, verbose_name=_("Banco"))
    tipo = models.CharField(max_length=50, verbose_name=_("Tipo de Cuenta"))
    numero = models.CharField(max_length=50, verbose_name=_("Numero de Cuenta"))

    class Meta:
        db_table = "bancos_cuenta_bancaria"
        verbose_name = _("Cuenta Bancaria")
        verbose_name_plural = _("Cuentas Bancarias")
        indexes = [
            models.Index(fields=["empresa", "numero"]),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.numero}"

class ExtractoBancario(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    cuenta = models.ForeignKey(CuentaBancaria, on_delete=models.CASCADE, related_name="extractos", verbose_name=_("Cuenta Bancaria"))
    mes = models.IntegerField(choices=MES_CHOICES, verbose_name=_("Mes"))
    anio = models.IntegerField(verbose_name=_("Anio"))
    archivo_s3 = models.FileField(upload_to="extractos/", null=True, blank=True, verbose_name=_("Archivo de Extracto"))
    procesado = models.BooleanField(default=False, verbose_name=_("Procesado"))
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name=_("Saldo Inicial"))
    saldo_final = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name=_("Saldo Final"))

    class Meta:
        db_table = "bancos_extracto_bancario"
        verbose_name = _("Extracto Bancario")
        verbose_name_plural = _("Extractos Bancarios")
        indexes = [
            models.Index(fields=["empresa", "cuenta", "anio", "mes"]),
        ]
        constraints = [
            # REM P1-03 (docs/remediation/REM-P1-03.md): la clave natural ya
            # la usaba ExtractoBancarioCRUDService.crear_extracto() como
            # chequeo de aplicacion (.exists() antes de crear, con ventana
            # TOCTOU real bajo doble-submit concurrente) -- se agrega el
            # backstop real de BD con la misma clave, sin inventar una nueva.
            models.UniqueConstraint(
                fields=["empresa", "cuenta", "anio", "mes"],
                name="uniq_extracto_bancario_empresa_cuenta_periodo",
            ),
        ]

    def __str__(self):
        return f"{self.cuenta.nombre} - {self.anio}/{self.mes:02d}"

class TransaccionBancaria(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    extracto = models.ForeignKey(ExtractoBancario, on_delete=models.CASCADE, related_name="transacciones", verbose_name=_("Extracto Bancario"))
    fecha = models.DateField(verbose_name=_("Fecha"))
    descripcion = models.TextField(verbose_name=_("Descripcion"))
    sucursal = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Sucursal"))
    dcto = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Documento"))
    valor = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("Valor"))
    saldo = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("Saldo"))

    # Conciliacion bancaria: soft references, no FK directa cross-app.
    factura_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_("UUID Factura"),
        help_text=_("Referencia soft a Factura asociada a esta transaccion."),
    )
    proveedor_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_("UUID Proveedor"),
        help_text=_("Referencia soft a Proveedor asociado a esta transaccion."),
    )
    cliente_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_("UUID Cliente"),
        help_text=_("Referencia soft a Cliente asociado a esta transaccion."),
    )
    conciliado = models.BooleanField(
        default=False,
        verbose_name=_("Conciliado"),
        help_text=_("True cuando la transaccion fue vinculada manualmente con un documento."),
    )
    notas_conciliacion = models.TextField(
        null=True, blank=True,
        verbose_name=_("Notas de Conciliacion"),
        help_text=_("Observaciones o comentarios sobre la conciliacion de esta transaccion."),
    )

    @property
    def tipo_movimiento(self):
        """DEBITO si valor < 0, CREDITO si valor >= 0."""
        return 'DEBITO' if self.valor < Decimal('0') else 'CREDITO'

    @property
    def monto(self):
        """Valor absoluto de la transaccion."""
        return abs(self.valor)

    class Meta:
        db_table = "bancos_transaccion_bancaria"
        verbose_name = _("Transaccion Bancaria")
        verbose_name_plural = _("Transacciones Bancarias")
        ordering = ["-fecha", "-created_at"]
        indexes = [
            models.Index(fields=["empresa", "extracto"]),
            models.Index(fields=["empresa", "fecha"]),
        ]

    def __str__(self):
        return f"{self.fecha} - {self.descripcion[:30]} - {self.valor}"


class TipoReferenciaAplicacion(models.TextChoices):
    """Fase 5 (mision Bancos v3.0): tipos de concepto que puede aplicarse a
    un movimiento bancario. Lista ampliable -- OTRO/OTRO_INGRESO/OTRO_EGRESO
    existen deliberadamente para no bloquear el flujo cuando el concepto
    todavia no tiene un dominio propio integrado."""
    FACTURA_VENTA = "FACTURA_VENTA", _("Factura de Venta")
    FACTURA_COMPRA = "FACTURA_COMPRA", _("Factura de Compra")
    CARTERA = "CARTERA", _("Cartera (Cliente)")
    CUENTA_POR_PAGAR = "CUENTA_POR_PAGAR", _("Cuenta por Pagar (Proveedor)")
    GASTO = "GASTO", _("Gasto")
    NOMINA = "NOMINA", _("Nomina")
    IMPUESTO = "IMPUESTO", _("Impuesto")
    TRANSFERENCIA_INTERNA = "TRANSFERENCIA_INTERNA", _("Transferencia entre Cuentas Propias")
    ANTICIPO = "ANTICIPO", _("Anticipo")
    OTRO_INGRESO = "OTRO_INGRESO", _("Otro Ingreso")
    OTRO_EGRESO = "OTRO_EGRESO", _("Otro Egreso")
    AJUSTE = "AJUSTE", _("Ajuste")
    OTRO = "OTRO", _("Otro / Sin clasificar")


class OrigenMatchingAplicacion(models.TextChoices):
    MANUAL = "MANUAL", _("Manual")
    SUGERIDO = "SUGERIDO", _("Sugerido por el sistema")


class MovimientoBancarioAplicacion(SintelTenantBaseModel):
    """Fase 5 (mision Bancos v3.0): permite aplicar UN movimiento bancario a
    VARIOS conceptos/documentos (split de pagos, pagos combinados, etc.).

    Soft references (UUID) a otros dominios -- Bounded Context §18, igual
    que factura_uuid/proveedor_uuid/cliente_uuid en TransaccionBancaria. NO
    exige que referencia_uuid resuelva a una fila real: permite
    tipo_referencia=OTRO con referencia_uuid=None para clasificar/probar
    manualmente sin bloquear el flujo (Fase 30).

    NO dispara automaticamente el abono en Cartera (a diferencia del
    vinculo legado 1:1 en TransaccionBancaria.conciliar_transaccion(), que
    se mantiene intacto para compatibilidad -- ver AUDITORIA_FLUJO_COMPLETO.md
    v3.0 §5). Ese trigger sigue siendo responsabilidad exclusiva del path
    legado hasta que una fase posterior decida unificarlos.
    """

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    transaccion = models.ForeignKey(
        TransaccionBancaria, on_delete=models.CASCADE, related_name="aplicaciones",
        verbose_name=_("Transaccion Bancaria"),
    )
    tipo_referencia = models.CharField(
        max_length=30, choices=TipoReferenciaAplicacion.choices,
        verbose_name=_("Tipo de Referencia"),
    )
    referencia_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_("UUID Referencia"),
        help_text=_("Soft ref al documento/concepto aplicado (Factura, Gasto, PeriodoNomina, etc.)."),
    )
    tercero_tipo = models.CharField(
        max_length=20, null=True, blank=True,
        verbose_name=_("Tipo de Tercero"),
        help_text=_("CLIENTE | PROVEEDOR | EMPLEADO, cuando aplica."),
    )
    tercero_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name=_("UUID Tercero"),
    )
    monto_aplicado = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Monto Aplicado"),
    )
    fecha_aplicacion = models.DateField(verbose_name=_("Fecha de Aplicacion"))
    notas = models.TextField(null=True, blank=True, verbose_name=_("Notas"))
    origen_matching = models.CharField(
        max_length=20, choices=OrigenMatchingAplicacion.choices,
        default=OrigenMatchingAplicacion.MANUAL, verbose_name=_("Origen"),
    )
    confianza = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True,
        verbose_name=_("Confianza del Matching"),
        help_text=_("Score 0-1 cuando origen_matching=SUGERIDO."),
    )

    class Meta:
        db_table = "bancos_movimiento_aplicacion"
        verbose_name = _("Aplicacion de Movimiento Bancario")
        verbose_name_plural = _("Aplicaciones de Movimientos Bancarios")
        ordering = ["-fecha_aplicacion", "-created_at"]
        indexes = [
            models.Index(fields=["empresa", "transaccion"]),
            models.Index(fields=["empresa", "tipo_referencia", "referencia_uuid"]),
        ]

    def __str__(self):
        return f"{self.tipo_referencia} - {self.monto_aplicado} ({self.transaccion_id})"
