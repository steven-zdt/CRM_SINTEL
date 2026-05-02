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
    
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]},
        related_name="activos"
    )
    codigo = models.CharField(max_length=64, unique=True, help_text="Placa, Serial o Identificador único.")
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

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Activo Fijo"
        verbose_name_plural = "Activos Fijos"
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["empresa"])
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

    codigo = models.CharField(max_length=64, unique=True, help_text="SKU único")
    nombre = models.CharField(max_length=200, db_index=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.PROTECT,
        related_name="productos",
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.PRODUCTO, CategoriaItem.Aplicacion.TODO]},
        help_text="Categoría del producto. Puede quedar sin categoría si se elimina la categoría asociada."
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

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["empresa", "nombre"]),
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

    codigo = models.CharField(max_length=64, unique=True)
    nombre = models.CharField(max_length=200, db_index=True)
    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.PROTECT,
        related_name="servicios",
        null=True,
        blank=True,
        limit_choices_to={'aplicacion__in': [CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]},
        help_text="Categoría del servicio. Puede quedar sin categoría si se elimina la categoría asociada."
    )
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='inventario/servicios/', null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        indexes = [models.Index(fields=["empresa", "nombre"])]

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
        ENTRADA_DEVOLUCION = "ENTRADA_DEVOLUCION", _("Devolución Cliente")
        # SALIDAS
        SALIDA_VENTA = "SALIDA_VENTA", _("Venta")
        SALIDA_BAJA = "SALIDA_BAJA", _("Baja / Deterioro")
        SALIDA_CONSUMO = "SALIDA_CONSUMO", _("Consumo Interno")

    # VINCULACIÓN EMPRESA (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
        help_text="Empresa a la que pertenece el movimiento."
    )

    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE, 
        related_name="movimientos",
        help_text="Producto del movimiento. Si se elimina el producto, se eliminan todos sus movimientos."
    )
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
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
        ]

    def __str__(self):
        return f"{self.tipo} | {self.producto.codigo}"


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
