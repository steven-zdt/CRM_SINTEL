import datetime
import uuid as uuid_module
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel


class ResolucionFacturacion(SintelTenantBaseModel):
    """
    Resolucion de Facturacion DIAN para la emision de Ventas.
    Controla el rango de consecutivos autorizado por la DIAN para cada tipo de documento.
    """

    class TipoDocumento(models.TextChoices):
        ELECTRONICA = "FE", _("Electronica")
        POS = "POS", _("Punto de Venta POS")
        PAPEL = "PAPEL", _("Papel")

    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    numero_resolucion = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Numero de Resolucion DIAN"),
    )

    prefijo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Prefijo"),
        help_text=_("Ej: SETP, FE, PV. Dejar vacio si no aplica."),
    )

    tipo = models.CharField(
        max_length=10,
        choices=TipoDocumento.choices,
        default=TipoDocumento.ELECTRONICA,
        db_index=True,
        verbose_name=_("Tipo de Documento"),
    )

    fecha_resolucion = models.DateField(
        verbose_name=_("Fecha de Emision DIAN"),
        help_text=_("Fecha en la que la DIAN emitio la resolucion"),
    )

    fecha_desde = models.DateField(
        verbose_name=_("Vigencia Desde"),
        help_text=_("Fecha de inicio de vigencia"),
        default=datetime.date.today,
    )

    fecha_hasta = models.DateField(
        verbose_name=_("Vigencia Hasta"),
        help_text=_("Fecha de vencimiento de la resolucion"),
    )

    rango_desde = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Rango Desde"),
    )

    rango_hasta = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Rango Hasta"),
    )

    consecutivo_actual = models.IntegerField(
        default=1,
        db_index=True,
        verbose_name=_("Consecutivo Actual"),
        help_text=_("Proximo numero a asignar. Se incrementa automaticamente."),
    )

    vigente = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Vigente (Activa)"),
        help_text=_("Solo una resolucion por tipo puede estar marcada como vigente."),
    )

    def formar_numero(self):
        """Retorna el numero de factura completo: prefijo + consecutivo_actual."""
        if self.prefijo:
            return f"{self.prefijo}{self.consecutivo_actual}"
        return str(self.consecutivo_actual)

    def esta_en_rango(self):
        """Verifica que el consecutivo_actual no haya superado el rango_hasta."""
        return self.consecutivo_actual <= self.rango_hasta

    def esta_vigente_en_fecha(self, fecha_ref=None):
        """Verifica vigencia de fechas."""
        if fecha_ref is None:
            fecha_ref = datetime.date.today()
        return self.fecha_desde <= fecha_ref <= self.fecha_hasta

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.rango_desde and self.rango_hasta and self.rango_desde > self.rango_hasta:
            raise ValidationError(
                {"rango_hasta": _("El rango_hasta debe ser mayor o igual a rango_desde.")}
            )

    class Meta:
        verbose_name = _("Resolucion de Facturacion")
        verbose_name_plural = _("Resoluciones de Facturacion")
        ordering = ["-vigente", "-fecha_resolucion"]
        indexes = [
            models.Index(fields=["empresa", "vigente"]),
            models.Index(fields=["empresa", "tipo"]),
        ]

    def __str__(self):
        return f"{self.prefijo or 'SIN-PREFIJO'} {self.rango_desde}-{self.rango_hasta} ({self.numero_resolucion})"


class Venta(SintelTenantBaseModel):
    """
    Master Record comercial del tenant antes y despues de la emision DIAN.

    Estados:
    - BORRADOR: venta registrada, factura aun no emitida.
    - FACTURADA_DIAN: factura electronica generada y vinculada.
    - ANULADA: venta cancelada (la factura asociada permanece para auditoria).
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", _("Borrador")
        FACTURADA_DIAN = "FACTURADA_DIAN", _("Facturada DIAN")
        ANULADA = "ANULADA", _("Anulada")

    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    cliente = models.ForeignKey(
        "tenant_clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name=_("Cliente"),
    )

    proyecto = models.ForeignKey(
        "tenant_proyectos.Proyecto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas",
        verbose_name=_("Proyecto"),
    )

    resolucion = models.ForeignKey(
        ResolucionFacturacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventas_asociadas",
        verbose_name=_("Resolucion de Facturacion"),
    )

    factura_asociada = models.OneToOneField(
        "facturas.Factura",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="venta_origen",
        verbose_name=_("Factura electronica DIAN"),
    )

    fecha_emision = models.DateField(verbose_name=_("Fecha de emision"))
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name=_("Fecha de vencimiento"))

    estado = models.CharField(
        max_length=16,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
    )

    numero_factura = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Numero de Factura"),
        help_text=_("Numero asignado por la resolucion. Ej: FE1001"),
    )

    observaciones = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    impuestos = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    total_neto = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = _("Venta")
        verbose_name_plural = _("Ventas")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "-created_at"]),
            models.Index(fields=["empresa", "resolucion"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=Decimal("0.00")),
                name="ventas_venta_subtotal_gte_cero",
            ),
            models.CheckConstraint(
                check=models.Q(total_neto__gte=Decimal("0.00")),
                name="ventas_venta_total_neto_gte_cero",
            ),
        ]

    def __str__(self):
        return f"Venta {self.uuid} - {self.estado}"


class ItemVenta(SintelTenantBaseModel):
    """
    Linea de una Venta. Referencia a Producto o Servicio del catalogo de inventario.
    """

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Venta"),
    )

    producto = models.ForeignKey(
        "tenant_inventario.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_venta",
        verbose_name=_("Producto"),
    )

    servicio = models.ForeignKey(
        "tenant_inventario.Servicio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_venta",
        verbose_name=_("Servicio"),
    )

    descripcion = models.CharField(max_length=500)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("1.0000"))
    precio_unitario = models.DecimalField(max_digits=16, decimal_places=2)
    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["empresa", "venta"]),
        ]

    def save(self, *args, **kwargs):
        cant = self.cantidad or Decimal("0")
        pu = self.precio_unitario or Decimal("0")
        self.subtotal = cant * pu
        if not self.empresa_id and self.venta_id:
            eid = (
                Venta.objects.filter(id=self.venta_id)
                .values_list("empresa_id", flat=True)
                .first()
            )
            if eid:
                self.empresa_id = eid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"
