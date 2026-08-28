import uuid as uuid_module
from decimal import Decimal
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
