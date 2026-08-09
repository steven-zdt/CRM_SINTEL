import uuid as uuid_module
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SedeAwareModel, SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa


class PlantillaOrdenCompra(SintelTenantBaseModel):
    """
    Plantilla de numeracion para Ordenes de Compra en el esquema Tenant.
    """
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Plantilla')
    )
    prefijo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Prefijo'),
        help_text=_('Ej: OC, COM. Dejar vacio si no aplica.')
    )
    rango_desde = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Desde')
    )
    rango_hasta = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Hasta')
    )
    consecutivo_actual = models.IntegerField(
        default=1,
        db_index=True,
        verbose_name=_('Consecutivo Actual'),
        help_text=_('Proximo numero a asignar. Se incrementa automaticamente.')
    )
    vigente = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('Vigente (Activa)')
    )

    def formar_numero(self):
        """Retorna el numero de orden completo: prefijo-consecutivo_actual."""
        if self.prefijo:
            return f"{self.prefijo}-{self.consecutivo_actual}"
        return str(self.consecutivo_actual)

    def esta_en_rango(self):
        """Verifica que el consecutivo_actual no haya superado el rango_hasta."""
        return self.consecutivo_actual <= self.rango_hasta

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.rango_desde and self.rango_hasta and self.rango_desde > self.rango_hasta:
            raise ValidationError(
                {"rango_hasta": _("El rango_hasta debe ser mayor o igual a rango_desde.")}
            )

    class Meta:
        verbose_name = _('Plantilla de Orden de Compra')
        verbose_name_plural = _('Plantillas de Orden de Compra')
        ordering = ['-vigente', '-created_at']
        indexes = [
            models.Index(fields=['empresa', 'vigente']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rango_hasta__gte=models.F('rango_desde')),
                name='plantilla_oc_rango_hasta_gte_rango_desde',
            ),
            models.CheckConstraint(
                check=models.Q(consecutivo_actual__gte=models.F('rango_desde')),
                name='plantilla_oc_consecutivo_gte_rango_desde',
            ),
        ]

    def __str__(self):
        return f"{self.prefijo or 'SIN-PREFIJO'} {self.rango_desde}-{self.rango_hasta} ({self.nombre})"


class OrdenCompra(SedeAwareModel):
    """
    Orden de Compra en el esquema Tenant.
    Gestiona la cabecera del documento transaccional de compras.

    Piloto del Contexto Organizacional (docs/ADR-003-contexto-organizacional-
    sede-area.md): hereda SedeAwareModel en vez de SintelTenantBaseModel, por
    lo que gana `sede` (Sede emisora de la orden, obligatoria para ordenes
    nuevas) y `area` (Area solicitante, opcional).
    """
    ESTADO_CHOICES = [
        ('BORRADOR', _('Borrador')),
        ('PENDIENTE', _('Pendiente por Aprobar')),
        ('APROBADA', _('Aprobada')),
        ('PARCIAL', _('Recepcion Parcial')),
        ('RECIBIDA', _('Recibida/Completada')),
        ('ANULADA', _('Anulada')),
    ]

    # Endurece SedeAwareModel.sede (nullable por defecto, pensada como punto
    # de partida para la migracion controlada de un futuro adoptante) a
    # obligatoria: la migracion 0006 (backfill) + 0007 (harden NOT NULL a
    # nivel de BD) de este app ya garantizan que toda fila tiene sede_id.
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name=_('Sede'),
        help_text=_('Sede propietaria del registro (Contexto Organizacional). Obligatoria para nuevos registros.'),
        null=False,
        blank=False,
        db_index=True,
    )

    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        db_index=True,
        editable=False
    )

    plantilla = models.ForeignKey(
        PlantillaOrdenCompra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ordenes_compra",
        verbose_name=_('Plantilla de Orden de Compra')
    )

    consecutivo = models.IntegerField(
        db_index=True,
        verbose_name=_('Consecutivo')
    )

    numero_documento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Numero de Documento')
    )

    proveedor = models.ForeignKey(
        'tenant_proveedores.Proveedor',
        on_delete=models.PROTECT,
        related_name='ordenes_compra',
        verbose_name=_('Proveedor')
    )

    proyecto = models.ForeignKey(
        'tenant_proyectos.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra',
        verbose_name=_('Proyecto')
    )

    documento_soporte = models.ForeignKey(
        'tenant_gastos.DocumentoSoporte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra',
        verbose_name=_('Documento Soporte / Gasto')
    )

    fecha = models.DateField(
        verbose_name=_('Fecha de Emision')
    )

    fecha_entrega = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Entrega Pactada')
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='BORRADOR',
        db_index=True,
        verbose_name=_('Estado')
    )

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    impuestos = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    observaciones = models.TextField(
        blank=True,
        verbose_name=_('Observaciones')
    )

    class Meta:
        verbose_name = _('Orden de Compra')
        verbose_name_plural = _('Ordenes de Compra')
        ordering = ['-fecha', '-consecutivo']
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['empresa', 'estado']),
            # [ADR-003] Meta.indexes de un Meta propio NO se fusiona con el de
            # una clase base abstracta (SedeAwareModel/SintelTenantBaseModel) -
            # verificado empiricamente: OrdenCompra._meta.indexes solo traia
            # estos dos hasta agregar esta linea. Repetir explicitamente el
            # indice compuesto empresa+sede aqui (y en cualquier otro modelo
            # que adopte SedeAwareModel y tambien declare su propio Meta.indexes).
            models.Index(fields=['empresa', 'sede']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'numero_documento'],
                name='unique_orden_compra_numero_documento'
            ),
            models.CheckConstraint(
                check=models.Q(fecha_entrega__isnull=True) | models.Q(fecha_entrega__gte=models.F('fecha')),
                name='orden_compra_fecha_entrega_gte_fecha',
            ),
        ]

    def __str__(self):
        if self.numero_documento:
            return f"{self.numero_documento} ({self.proveedor})"
        return f"OC-{self.consecutivo} ({self.proveedor})"


class ItemOrdenCompra(SintelTenantBaseModel):
    """
    Detalle de items de una Orden de Compra.
    """
    uuid = models.UUIDField(
        default=uuid_module.uuid4,
        unique=True,
        db_index=True,
        editable=False
    )

    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Orden de Compra')
    )

    descripcion = models.CharField(
        max_length=255,
        verbose_name=_('Descripcion')
    )

    item_inventario_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Soft reference a Producto o Servicio del catalogo de inventario')
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Cantidad')
    )

    valor_unitario = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Valor Unitario')
    )

    porcentaje_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Porcentaje IVA')
    )

    valor_iva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Valor IVA')
    )

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Subtotal')
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total')
    )

    cantidad_recibida = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Cantidad Recibida'),
        help_text=_(
            'Acumulado de recepciones CONFIRMADA para este item (F21). '
            'cantidad_recibida <= cantidad siempre; actualizado transaccionalmente '
            'por RecepcionCompraBusinessService bajo select_for_update, mismo '
            'patron que Producto.stock_actual en KardexService.'
        ),
    )

    class Meta:
        verbose_name = _('Item Orden de Compra')
        verbose_name_plural = _('Items Orden de Compra')
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_recibida__lte=models.F('cantidad')),
                name='item_orden_compra_recibida_lte_cantidad',
            ),
        ]

    @property
    def cantidad_pendiente(self):
        return self.cantidad - self.cantidad_recibida

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"


class RecepcionCompra(SedeAwareModel):
    """
    Evento de recepcion fisica de mercancia contra una OrdenCompra (F21).

    OrdenCompra != Recepcion: una orden puede recibirse en varios eventos
    parciales (RecepcionCompra #1, #2, ...) que se acumulan sobre
    ItemOrdenCompra.cantidad_recibida hasta completar la cantidad ordenada.
    Solo CONFIRMADA genera MovimientoInventario (via RecepcionCompraBusinessService
    + KardexService.registrar_movimiento) — BORRADOR es editable/sin efecto en
    stock, y una vez CONFIRMADA es inmutable (no se reversa automaticamente:
    ver documentacion/F21_RECEPCION_INVENTARIO.md sobre este limite de alcance).
    """

    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        CONFIRMADA = 'CONFIRMADA', _('Confirmada')
        ANULADA = 'ANULADA', _('Anulada')

    # Tabla nueva sin datos historicos: se endurece sede a NOT NULL desde el
    # inicio (a diferencia de OrdenCompra, que necesito nullable->backfill->
    # harden por tener filas preexistentes). Por defecto toma la sede de la
    # orden de compra (ver RecepcionCompraBusinessService.crear_recepcion).
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name=_('Sede'),
        help_text=_('Sede que recibe la mercancia. Por defecto, la sede de la orden de compra.'),
        null=False,
        blank=False,
        db_index=True,
    )

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.PROTECT,
        related_name='recepciones',
        verbose_name=_('Orden de Compra'),
    )

    fecha = models.DateField(verbose_name=_('Fecha de Recepcion'))

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
        verbose_name=_('Estado'),
    )

    usuario = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.PROTECT,
        related_name='recepciones_compra',
        verbose_name=_('Usuario que Recibe'),
    )

    observaciones = models.TextField(blank=True, verbose_name=_('Observaciones'))

    class Meta:
        verbose_name = _('Recepcion de Compra')
        verbose_name_plural = _('Recepciones de Compra')
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(fields=['empresa', 'orden_compra']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'sede']),
        ]

    def __str__(self):
        return f"Recepcion #{self.pk} - OC {self.orden_compra_id} ({self.estado})"


class RecepcionCompraItem(SintelTenantBaseModel):
    """Linea de recepcion: cuanto se recibio de un ItemOrdenCompra en este evento."""

    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    recepcion = models.ForeignKey(
        RecepcionCompra,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Recepcion'),
    )

    item_orden_compra = models.ForeignKey(
        ItemOrdenCompra,
        on_delete=models.PROTECT,
        related_name='recepciones_item',
        verbose_name=_('Item de Orden de Compra'),
    )

    cantidad_recibida = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Cantidad Recibida en este Evento'),
    )

    observaciones = models.TextField(blank=True, verbose_name=_('Observaciones'))

    class Meta:
        verbose_name = _('Item de Recepcion de Compra')
        verbose_name_plural = _('Items de Recepcion de Compra')
        ordering = ['id']
        indexes = [
            models.Index(fields=['empresa', 'item_orden_compra']),
        ]

    def __str__(self):
        return f"{self.item_orden_compra_id}: +{self.cantidad_recibida}"
