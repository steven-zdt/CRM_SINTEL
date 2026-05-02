"""
Modelos de Cotizaciones v2.60 - DESACOPLAMIENTO RADICAL
# WARNING: v2.60: Sistema Resiliente. No depende de la disponibilidad de otras apps.
Si un Cliente o Producto es eliminado o falla, la Cotización persiste.
"""
import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT
from apps.tenant.empresa.models import Empresa


def _cotizacion_anexo_upload_path(instance, filename):
    return f"cotizaciones/anexos/{filename}"

# # WARNING: Importación diferida para evitar referencias circulares
# ConfiguracionCotizacion se importa cuando sea necesario

class Producto(SintelTenantBaseModel):
    codigo = models.CharField(max_length=50, blank=True)
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    unidad = models.CharField(max_length=20, default='UND')
    precio_venta = models.DecimalField(max_digits=15, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta: db_table = 'tenant_cotizaciones_producto'

class Servicio(SintelTenantBaseModel):
    # [v2.61.4] empresa FK heredada de SintelTenantBaseModel
    nombre = models.CharField(max_length=255)
    precio_venta = models.DecimalField(max_digits=15, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta: db_table = 'tenant_cotizaciones_servicio'

class Cotizacion(SintelTenantBaseModel):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        ENVIADA = 'ENVIADA', _('Enviada')
        ACEPTADA = 'ACEPTADA', _('Aceptada')
        CANCELADA = 'CANCELADA', _('Cancelada')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    numero_cotizacion = models.CharField(max_length=50)  # # WARNING: v2.60: Removido unique=True, se valida con constraint
    
    # # WARNING: v2.60: Código único generado automáticamente (ej. "STS. 0422-2026")
    # Este campo almacena el código completo generado desde el perfil
    codigo_unico = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        verbose_name=_('Código Único'),
        help_text=_('Código único generado automáticamente desde el perfil de configuración (ej: "STS. 0422-2026")')
    )
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    
    # RELACIÓN OPCIONAL (Resiliencia): 
    # Si la app Clientes falla, la relación puede ser null.
    cliente = models.ForeignKey('tenant_clientes.Cliente', on_delete=models.SET_NULL, null=True, blank=True)

    
    configuracion = models.ForeignKey(
        'tenant_cotizaciones.ConfiguracionCotizacion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cotizaciones'
    )
    tipo_cotizacion = models.CharField(max_length=20, default='MIXTO')
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    
    # DNA Financiero
    porcentaje_aiu_admin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    porcentaje_aiu_imprevistos = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    porcentaje_aiu_utilidad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=19.00)
    total_con_impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.numero_cotizacion} - {self.cliente or 'Sin cliente'}"

    class Meta:
        db_table = 'tenant_cotizaciones_documento'
        constraints = [
            # # WARNING: v2.60: Unicidad de numero_cotizacion por empresa y perfil
            models.UniqueConstraint(
                fields=['empresa', 'configuracion', 'numero_cotizacion'],
                name='unique_numero_cotizacion_por_perfil'
            )
        ]

class CotizacionItem(SintelTenantBaseModel):
    class TipoItem(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Equipo')
        MATERIAL = 'MATERIAL', _('Material')
        SERVICIO = 'SERVICIO', _('Servicio')

    # # WARNING: v2.60: related_name='items' permite crear items desde el serializador anidado de Cotizacion
    # El campo 'cotizacion' es obligatorio en el modelo pero opcional durante la validación del serializer
    # El ID se asigna automáticamente en CotizacionSerializer.create() después de crear la cotización
    cotizacion = models.ForeignKey(Cotizacion, related_name='items', on_delete=models.CASCADE)
    tipo_item = models.CharField(max_length=20, choices=TipoItem.choices)
    
    # REFERENCIAS OPCIONALES (No rompen el código si fallan)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    
    # DATOS REALES (Snapshot): Lo que realmente se imprime y calcula
    # # WARNING: CORRECCIÓN: Permitir campos vacíos y nulos para flexibilidad
    # Aunque no es ideal para el Snapshot Pattern, esto previene errores de validación
    descripcion = models.TextField(
        blank=True,  # Permite formularios con descripción vacía
        null=True,   # Permite nulos en BD
        default=""   # Valor por defecto es cadena vacía
    )
    marca = models.CharField(max_length=100, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    unidad = models.CharField(max_length=20, default='UND')
    
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    costo_unitario = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    porcentaje_utilidad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    precio_unitario_venta = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    subtotal_linea = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    orden = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        """Calcula precios y subtotales automáticamente."""
        factor_utilidad = Decimal('1.00') + (self.porcentaje_utilidad / Decimal('100.00'))
        self.precio_unitario_venta = self.costo_unitario * factor_utilidad
        self.subtotal_linea = self.cantidad * self.precio_unitario_venta
        super().save(*args, **kwargs)

    class Meta: 
        db_table = 'tenant_cotizaciones_item'
        ordering = ['orden']
