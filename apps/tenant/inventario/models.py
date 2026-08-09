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
        # TRASLADOS ENTRE SEDES (F21) — distintos de TRASLADO_MANTENIMIENTO/
        # RETORNO_MANTENIMIENTO (esos son transiciones de estado de ActivoFijo,
        # no movimiento de stock de Producto entre sedes).
        TRASLADO_SALIDA = "TRASLADO_SALIDA", _("Traslado - Salida de Sede")
        TRASLADO_ENTRADA = "TRASLADO_ENTRADA", _("Traslado - Entrada a Sede")
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

    # Sede — vinculacion para indicadores y KPIs por sede (DT-SEDE-05)
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        verbose_name=_('Sede'),
        help_text=_('Sede de la empresa donde ocurre el movimiento de inventario. '
                    'Opcional — si no se asigna aplica a toda la empresa.'),
        db_index=True,
    )

    # Trazabilidad a documento origen (F21) — mismo patron de idempotencia que
    # AsientoContable (apps/tenant/contabilidad/models.py): soft reference,
    # sin FK cross-app real. app='compras', modelo='RecepcionCompraItem' para
    # entradas por compra; app='inventario', modelo='TrasladoInventario' para
    # traslados entre sedes.
    documento_origen_app = models.CharField(
        max_length=30, null=True, blank=True,
        help_text="App que origino el movimiento: compras, inventario.",
    )
    documento_origen_modelo = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Modelo que origino el movimiento: RecepcionCompraItem, TrasladoInventario.",
    )
    documento_origen_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="PK en la app de origen.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Movimiento Inventario"
        verbose_name_plural = "Movimientos Inventario"
        indexes = [
            models.Index(fields=["empresa", "created_at"]),
            models.Index(fields=["producto", "created_at"]),
            models.Index(fields=["activo_fijo", "created_at"]),
            models.Index(fields=["empresa", "sede", "producto"]),
            models.Index(
                fields=["documento_origen_app", "documento_origen_modelo", "documento_origen_id"]
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(producto__isnull=False, activo_fijo__isnull=True) |
                    models.Q(producto__isnull=True, activo_fijo__isnull=False)
                ),
                name="exactly_one_product_or_asset"
            ),
            # Idempotencia: un mismo documento origen no puede generar dos
            # movimientos del mismo tipo. Incluye 'tipo' (a diferencia del
            # UniqueConstraint de AsientoContable) porque un TrasladoInventario
            # es UN documento origen que legitimamente genera DOS movimientos
            # (TRASLADO_SALIDA + TRASLADO_ENTRADA).
            models.UniqueConstraint(
                fields=[
                    "empresa", "documento_origen_app", "documento_origen_modelo",
                    "documento_origen_id", "tipo",
                ],
                condition=models.Q(documento_origen_id__isnull=False),
                name="uniq_movimiento_documento_origen_tipo",
            ),
        ]

    def __str__(self):
        item_code = self.producto.codigo if self.producto else (self.activo_fijo.codigo if self.activo_fijo else "N/A")
        return f"{self.tipo} | {item_code}"


# ==============================================================================
# 5-BIS. TRASLADO ENTRE SEDES (F21)
# ==============================================================================
class TrasladoInventario(TimeStampedModel):
    """
    Traslado de stock de un Producto entre dos Sede de la misma Empresa.

    [ALCANCE F21] Un traslado = un producto, una cantidad. No modela un
    "carrito" de multiples productos por traslado (TrasladoInventarioItem) —
    reduccion de alcance documentada en documentacion/F21_TRASLADOS_SEDES.md;
    el dominio real (ejemplo del prompt maestro) es 1 producto por operacion.

    No modifica MovimientoInventario.sede directamente: el flujo real crea DOS
    movimientos append-only (TRASLADO_SALIDA al enviar, TRASLADO_ENTRADA al
    recibir) via KardexService.registrar_movimiento(), igual patron que
    Recepcion de Compras.
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", _("Borrador")
        SOLICITADO = "SOLICITADO", _("Solicitado")
        APROBADO = "APROBADO", _("Aprobado")
        EN_TRANSITO = "EN_TRANSITO", _("En Transito")
        RECIBIDO = "RECIBIDO", _("Recibido")
        CANCELADO = "CANCELADO", _("Cancelado")

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="traslados_inventario",
        help_text="Empresa propietaria del traslado.",
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="traslados",
        help_text="Producto trasladado.",
    )
    cantidad = models.DecimalField(max_digits=14, decimal_places=3)

    sede_origen = models.ForeignKey(
        'empresa.Sede', on_delete=models.PROTECT, related_name='traslados_salida',
        verbose_name=_('Sede Origen'),
    )
    sede_destino = models.ForeignKey(
        'empresa.Sede', on_delete=models.PROTECT, related_name='traslados_entrada',
        verbose_name=_('Sede Destino'),
    )
    area_origen = models.ForeignKey(
        'empresa.Area', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='traslados_salida', verbose_name=_('Area Origen'),
    )
    area_destino = models.ForeignKey(
        'empresa.Area', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='traslados_entrada', verbose_name=_('Area Destino'),
    )

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    motivo = models.TextField(blank=True)

    usuario_solicita = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.PROTECT, related_name='traslados_solicitados',
    )
    usuario_aprueba = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.PROTECT, null=True, blank=True,
        related_name='traslados_aprobados',
    )
    usuario_recibe = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.PROTECT, null=True, blank=True,
        related_name='traslados_recibidos',
    )

    fecha_solicitud = models.DateTimeField(null=True, blank=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Traslado de Inventario"
        verbose_name_plural = "Traslados de Inventario"
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "producto"]),
            models.Index(fields=["sede_origen", "estado"]),
            models.Index(fields=["sede_destino", "estado"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(sede_origen=models.F('sede_destino')),
                name="traslado_sede_origen_distinta_destino",
            ),
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="traslado_cantidad_positiva",
            ),
        ]

    def __str__(self):
        return f"Traslado {self.producto.codigo if self.producto_id else '?'} {self.sede_origen_id}->{self.sede_destino_id} ({self.estado})"


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

    # VINCULACION PROYECTO (Soft Reference - patron factura_uuid/numero)
    proyecto_uuid = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="UUID snapshot del proyecto vinculado (Soft Reference)."
    )
    proyecto_nombre = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Nombre snapshot del proyecto vinculado."
    )

    class Meta:
        ordering = ["-fecha_registro"]
        verbose_name = "Historial Servicio"
        verbose_name_plural = "Historial Servicios"
        indexes = [models.Index(fields=["empresa", "fecha_registro"])]

    def __str__(self):
        return f"{self.servicio.nombre} -> {self.cliente_referencia}"
