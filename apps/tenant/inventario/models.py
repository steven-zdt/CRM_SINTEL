import uuid

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # auto-inserted by autocorrect

# Referencia a Empresa (SSoT singleton por tenant)
from apps.tenant.empresa.models import Empresa


class TimeStampedModel(SintelTenantBaseModel):
    """Modelo base abstracto para auditoría de tiempos."""
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ==============================================================================
# 1. CATEGORÍAS (Agrupación Comercial)
# ==============================================================================
class CategoriaItem(TimeStampedModel):
    class Aplicacion(models.TextChoices):
        TODO = "TODO", _("Todos")
        PRODUCTO = "PRODUCTO", _("Solo Productos")
        SERVICIO = "SERVICIO", _("Solo Servicios")
        ACTIVO = "ACTIVO", _("Activos Fijos")

    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="categorias_inventario",
        help_text="Empresa propietaria de esta categoría."
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    nombre = models.CharField(max_length=100, db_index=True)
    descripcion = models.TextField(blank=True, null=True)
    aplicacion = models.CharField(
        max_length=16, 
        choices=Aplicacion.choices, 
        default=Aplicacion.TODO,
        help_text="Define si esta categoría agrupa productos, servicios o activos."
    )
    imagen = models.ImageField(upload_to='inventario/categorias/', null=True, blank=True)
    activo = models.BooleanField(default=True)
    
    # Mapeo Contable Base (Heredado por los items si no tienen uno propio)
    cuenta_inventario_uuid = models.UUIDField(
        null=True, blank=True, help_text="Cuenta PUC nivel 6 (Inventario/Activo)"
    )
    cuenta_costo_uuid = models.UUIDField(
        null=True, blank=True, help_text="Cuenta PUC nivel 6 (Costo de Ventas/Depreciación)"
    )
    cuenta_ingreso_uuid = models.UUIDField(
        null=True, blank=True, help_text="Cuenta PUC nivel 6 (Ingreso por Ventas)"
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        indexes = [models.Index(fields=["empresa", "nombre"])]
        constraints = [
            models.UniqueConstraint(
                Lower('nombre'),
                'empresa',
                name='unique_categoria_nombre_per_empresa'
            )
        ]

    def __str__(self):
        return self.nombre


# ==============================================================================
# 2. ACTIVOS FIJOS (Uso Interno)
# ==============================================================================
class ActivoFijo(TimeStampedModel):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", _("Activo / En Uso")
        MANTENIMIENTO = "MANTENIMIENTO", _("En Mantenimiento")
        BAJA = "BAJA", _("De Baja / Desechado")
        VENDIDO = "VENDIDO", _("Vendido")

    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="activos_fijos"
    )
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]},
        related_name="activos"
    )
    codigo = models.CharField(max_length=64, help_text="Placa, Serial o Identificador unico.")
    nombre = models.CharField(max_length=200, db_index=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='inventario/activos/', null=True, blank=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    costo_adquisicion = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    cuenta_activo_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Control Activo)"
    )
    cuenta_depreciacion_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Depreciación Acumulada/Gasto)"
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Activo Fijo"
        verbose_name_plural = "Activos Fijos"
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["empresa"])
        ]
        constraints = [
            models.UniqueConstraint(
                Lower('codigo'),
                'empresa',
                name='unique_activo_codigo_per_empresa'
            )
        ]

    def __str__(self):
        return f"[{self.codigo}] {self.nombre}"


# ==============================================================================
# 3. PRODUCTOS (Catálogo de Venta Tangible)
# ==============================================================================
class Producto(TimeStampedModel):
    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="productos_venta",
        help_text="Empresa propietaria del producto."
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    codigo = models.CharField(max_length=64, help_text="SKU unico")
    nombre = models.CharField(max_length=200, db_index=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.SET_NULL,
        related_name="productos",
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.PRODUCTO, CategoriaItem.Aplicacion.TODO]},
        help_text="Categoria del producto. Puede quedar sin categoria si se elimina la categoria asociada."
    )
    descripcion = models.TextField(blank=True, null=True)
    unidad = models.CharField(max_length=16, default="UND")
    imagen = models.ImageField(upload_to='inventario/productos/', null=True, blank=True)
    
    # Precios
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    costo_promedio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Stock
    stock_actual = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    stock_minimo = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    
    activo = models.BooleanField(default=True)
    cuenta_inventario_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Activo de Inventario)"
    )
    cuenta_costo_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Costo de Ventas)"
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["empresa", "nombre"]),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower('codigo'),
                'empresa',
                name='unique_producto_codigo_per_empresa'
            )
        ]

    def __str__(self):
        return f"{self.nombre} (Disp: {self.stock_actual})"


# ==============================================================================
# 4. SERVICIOS (Catálogo de Venta Intangible)
# ==============================================================================
class Servicio(TimeStampedModel):
    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="servicios_venta",
        help_text="Empresa que presta el servicio."
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    codigo = models.CharField(max_length=64)
    nombre = models.CharField(max_length=200, db_index=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.SET_NULL,
        related_name="servicios",
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]},
        help_text="Categoria del servicio. Puede quedar sin categoria si se elimina la categoria asociada."
    )
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='inventario/servicios/', null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    cuenta_ingreso_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Ingreso)"
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        indexes = [models.Index(fields=["empresa", "nombre"])]
        constraints = [
            models.UniqueConstraint(
                Lower('codigo'),
                'empresa',
                name='unique_servicio_codigo_per_empresa'
            )
        ]

    def __str__(self):
        return f"[SRV] {self.nombre}"


# ==============================================================================
# 5. MOVIMIENTOS DE INVENTARIO (Kardex - Backend)
# ==============================================================================
class MovimientoInventario(TimeStampedModel):
    class TipoMovimiento(models.TextChoices):
        # ENTRADAS
        ENTRADA_COMPRA = "ENTRADA_COMPRA", _("Compra")
        ENTRADA_AJUSTE = "ENTRADA_AJUSTE", _("Ajuste (+)")
        ENTRADA_DEVOLUCION = "ENTRADA_DEVOLUCION", _("Devolucion Cliente")
        # SALIDAS
        SALIDA_VENTA = "SALIDA_VENTA", _("Venta")
        SALIDA_BAJA = "SALIDA_BAJA", _("Baja / Deterioro")
        SALIDA_CONSUMO = "SALIDA_CONSUMO", _("Consumo Interno")
        # ACTIVOS
        ASIGNACION_RESPONSABLE = "ASIGNACION_RESPONSABLE", _("Asignacion de Responsable")
        TRASLADO_MANTENIMIENTO = "TRASLADO_MANTENIMIENTO", _("Traslado a Mantenimiento")
        RETORNO_MANTENIMIENTO = "RETORNO_MANTENIMIENTO", _("Retorno de Mantenimiento")
        SALIDA_BAJA_ACTIVO = "SALIDA_BAJA_ACTIVO", _("Baja de Activo")

    # VINCULACION EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
        help_text="Empresa a la que pertenece el movimiento."
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name="movimientos",
        null=True,
        blank=True,
        help_text="Producto del movimiento. Si se elimina el producto, se eliminan todos sus movimientos."
    )
    activo_fijo = models.ForeignKey(
        ActivoFijo,
        on_delete=models.CASCADE,
        related_name="movimientos",
        null=True,
        blank=True,
        help_text="Activo fijo del movimiento."
    )
    tipo = models.CharField(max_length=30, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # VINCULACIÓN FACTURA (v3.9.2+) — Soft Reference (no FK)
    factura_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID de la factura asociada. Referencia soft, sin FK."
    )
    factura_numero = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Snapshot del número de factura al momento del movimiento."
    )

    # TRAZABILIDAD EXTERNA
    origen_referencia = models.CharField(max_length=100, blank=True, null=True)
    cliente_referencia = models.CharField(max_length=200, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Movimiento Inventario"
        verbose_name_plural = "Movimientos Inventario"
        indexes = [
            models.Index(fields=["empresa", "created_at"]),
            models.Index(fields=["producto", "created_at"]),
            models.Index(fields=["activo_fijo", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(producto__isnull=False, activo_fijo__isnull=True) |
                    models.Q(producto__isnull=True, activo_fijo__isnull=False)
                ),
                name="exactly_one_product_or_asset"
            )
        ]

    def __str__(self):
        item_code = self.producto.codigo if self.producto else (self.activo_fijo.codigo if self.activo_fijo else "N/A")
        return f"{self.tipo} | {item_code}"


# ==============================================================================
# 6. HISTORIAL DE SERVICIOS (Log de Ventas)
# ==============================================================================
class HistorialServicio(TimeStampedModel):
    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="historial_servicios",
        help_text="Empresa que registra la transacción."
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name="historial_ventas",
        help_text="Servicio del historial. Si se elimina el servicio, se eliminan todos sus historiales."
    )
    fecha_registro = models.DateField(default=timezone.now)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    valor_cobrado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # TRAZABILIDAD EXTERNA
    origen_referencia = models.CharField(max_length=100, blank=True, null=True)
    cliente_referencia = models.CharField(max_length=200, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-fecha_registro"]
        verbose_name = "Historial Servicio"
        verbose_name_plural = "Historial Servicios"
        indexes = [models.Index(fields=["empresa", "fecha_registro"])]

    def __str__(self):
        return f"{self.servicio.nombre} -> {self.cliente_referencia}"
