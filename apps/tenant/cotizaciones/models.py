"""
Modelos de Cotizaciones v2.62.0 - SINTEL FSD
"""
import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # [v2.61.4] Herencia SSoT
from apps.tenant.empresa.models import Empresa


def _cotizacion_anexo_upload_path(instance, filename):
    return f"cotizaciones/anexos/{filename}"


def _hoy():
    """Default explicito para Cotizacion.fecha_emision -- mismo fallback
    que CotizacionService._build_header_fields() ya usa cuando el payload
    no trae una fecha (ver models.py, hallazgo real auditoria REL
    Cotizaciones, 2026-08-26)."""
    return timezone.now().date()

class Producto(SintelTenantBaseModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    codigo = models.CharField(max_length=50, blank=True)
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    unidad = models.CharField(max_length=20, default='UND')
    precio_venta = models.DecimalField(max_digits=15, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenant_cotizaciones_producto'
        constraints = [
            # Antes solo se validaba en ProductoBusinessService.registrar()
            # (query + ValueError, sin select_for_update) -- condicion de
            # carrera real entre el check y el create() (hallazgo real,
            # auditoria REL Cotizaciones FASE 2, 2026-08-26). codigo es
            # blank=True (no null) -- la condicion excluye vacios para no
            # romper productos sin codigo, mismo criterio que la validacion
            # de aplicacion existente (`if codigo:`).
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                condition=models.Q(codigo__gt=''),
                name='uniq_producto_codigo_por_empresa',
            ),
        ]

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
    # NO auto_now_add: CotizacionService._build_header_fields() siempre
    # calcula y pasa fecha_emision explicitamente (payload o
    # timezone.now().date() por defecto) -- con auto_now_add=True, Django
    # ignoraba ese valor en el INSERT y usaba timezone.now() sin importar
    # lo que el service calculara (bug real encontrado en auditoria REL
    # Cotizaciones, FASE 0/6, 2026-08-26). default= (no auto_now_add) deja
    # el campo escribible explicitamente mientras conserva un valor
    # implicito para callers que no lo pasan (ORM directo, tests, etc.) --
    # mismo calculo de fallback que _build_header_fields() ya usaba.
    fecha_emision = models.DateField(default=_hoy)
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

    # Sede — vinculacion para indicadores y KPIs por sede (DT-SEDE-04)
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotizaciones',
        verbose_name=_('Sede'),
        help_text=_('Sede de la empresa que emite la cotizacion. '
                    'Opcional — si no se asigna aplica a toda la empresa.'),
        db_index=True,
    )

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
