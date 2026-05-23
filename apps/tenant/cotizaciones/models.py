"""
Modelos de Cotizaciones v2.62.0 - SINTEL FSD
"""
import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT
from apps.tenant.empresa.models import Empresa


def _cotizacion_anexo_upload_path(instance, filename):
    return f"cotizaciones/anexos/{filename}"

class Producto(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    codigo = models.CharField(max_length=50, blank=True)
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    unidad = models.CharField(max_length=20, default='UND')
    precio_venta = models.DecimalField(max_digits=15, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta: db_table = 'tenant_cotizaciones_producto'

class Servicio(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
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
    numero_cotizacion = models.CharField(max_length=50) 
    
    codigo_unico = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        verbose_name=_('Codigo Unico'),
        help_text=_('Codigo unico generado automaticamente desde el perfil de configuracion (ej: "STS. 0422-2026")')
    )
    
    # empresa field inherited from SintelTenantBaseModel
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
    
    # Tiempos del Proyecto (v2.62.0)
    dias_totales = models.PositiveIntegerField(default=1)
    dias_infraestructura = models.PositiveIntegerField(default=0)
    dias_instalacion = models.PositiveIntegerField(default=0)
    dias_configuracion = models.PositiveIntegerField(default=0)
    dias_pruebas = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.numero_cotizacion} - {self.cliente or 'Sin cliente'}"

    class Meta:
        db_table = 'tenant_cotizaciones_documento'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'configuracion', 'numero_cotizacion'],
                name='unique_numero_cotizacion_por_perfil'
            )
        ]

class CotizacionItem(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    class TipoItem(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Equipo')
        MATERIAL = 'MATERIAL', _('Material')
        SERVICIO = 'SERVICIO', _('Servicio')

    cotizacion = models.ForeignKey(Cotizacion, related_name='items', on_delete=models.CASCADE)
    tipo_item = models.CharField(max_length=20, choices=TipoItem.choices)
    
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        default=""
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

    class Meta: 
        db_table = 'tenant_cotizaciones_item'
        ordering = ['orden']
