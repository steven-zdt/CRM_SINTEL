"""
Modelos de Ventas (Ordenes de Venta) por tenant.

Arquitectura:
- OrdenVenta: cabecera del pedido, vinculada a Cliente y opcionalmente a Factura.
- ItemOrdenVenta: lineas del pedido con referencias a Producto o Servicio de Inventario.
- NO se almacenan cuentas contables aqui (Pull Model de Contabilidad extrae desde Facturas).
"""
import uuid
from decimal import Decimal

from django.db import models

from apps.tenant.core.models import SintelTenantBaseModel


class OrdenVenta(SintelTenantBaseModel):
    """Pedido/Orden de venta emitida por la empresa a un cliente."""

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        FACTURADA = "FACTURADA", "Facturada"
        ANULADA = "ANULADA", "Anulada"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    cliente = models.ForeignKey(
        "tenant_clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="ordenes_venta",
        verbose_name="Cliente",
    )
    factura = models.ForeignKey(
        "facturas.Factura",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_venta",
        verbose_name="Factura generada",
    )
    fecha_emision = models.DateField(verbose_name="Fecha de emision")
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento",
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
    )
    observaciones = models.TextField(blank=True)
    subtotal = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    impuestos = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        verbose_name = "Orden de Venta"
        verbose_name_plural = "Ordenes de Venta"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=Decimal("0.00")),
                name="ventas_orden_subtotal_positivo",
            ),
            models.CheckConstraint(
                check=models.Q(total__gte=Decimal("0.00")),
                name="ventas_orden_total_positivo",
            ),
        ]

    def __str__(self):
        return f"OV-{str(self.uuid).replace('-', '').upper()[:8]} | {self.estado}"


class ItemOrdenVenta(SintelTenantBaseModel):
    """Linea de producto o servicio dentro de una OrdenVenta."""

    orden = models.ForeignKey(
        OrdenVenta,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Orden de venta",
    )
    producto = models.ForeignKey(
        "tenant_inventario.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_orden_venta",
        verbose_name="Producto",
    )
    servicio = models.ForeignKey(
        "tenant_inventario.Servicio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_orden_venta",
        verbose_name="Servicio",
    )
    descripcion = models.CharField(max_length=255, verbose_name="Descripcion")
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("1.0000"),
        verbose_name="Cantidad",
    )
    precio_unitario = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        verbose_name="Precio unitario",
    )
    tasa_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Tasa IVA (%)",
    )
    subtotal = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Subtotal linea",
    )

    class Meta:
        verbose_name = "Item de Orden de Venta"
        verbose_name_plural = "Items de Orden de Venta"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["empresa", "orden"]),
        ]

    def save(self, *args, **kwargs):
        if not self.empresa_id and self.orden_id:
            self.empresa_id = (
                OrdenVenta.objects.filter(id=self.orden_id)
                .values_list("empresa_id", flat=True)
                .first()
            )
        self.subtotal = (self.cantidad or Decimal("0.00")) * (
            self.precio_unitario or Decimal("0.00")
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Item #{self.pk} | {self.descripcion[:50]}"
