"""
Modelos de gastos (TENANT_APP).

v2.62: FLEXIBILIDAD OPERATIVA - Reglas de Inmutabilidad deshabilitadas.
- DocumentoSoporte: Evidencia legal de gasto (Edicion permitida segun requerimiento).
- Gasto: Clasificacion contable (centro de costos/categoria)

NOTA: La integridad legal debe ser gestionada por procesos administrativos, el sistema permite modificaciones.
El formato del documento debe cumplir con la normativa DIAN colombiana.
"""
import datetime
import uuid as uuid_module
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa  # SSoT empresa (singleton por tenant)

from .choices.categoria_contable import CATEGORIA_CONTABLE_CHOICES


class ResolucionDIAN(SintelTenantBaseModel):
    """
    Resolucion DIAN para Documentos Soporte.
    """
    # UUID Lookup Field (AGENTS.md §25)
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    numero_resolucion = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_('Numero Resolucion DIAN')
    )
    
    
    rango_desde = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Desde')
    )
    rango_hasta = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Hasta')
    )
    
    fecha_resolucion = models.DateField(
        verbose_name=_('Fecha de Emision'),
        help_text=_('Fecha en la que la DIAN emitio la resolucion')
    )
    fecha_inicio = models.DateField(
        verbose_name=_('Fecha Inicio Aplicacion'),
        help_text=_('Fecha desde la cual se empezara a usar en el sistema'),
        default=datetime.date.today
    )
    fecha_fin = models.DateField(
        verbose_name=_('Fecha Final Aplicacion'),
        help_text=_('Fecha de vencimiento de la resolucion')
    )
    
    clave_tecnica = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    vigente = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('Vigente (Prestablecida)'),
        help_text=_('Solo una resolucion puede estar vigente para ser usada por defecto.')
    )

    prefijo = models.CharField(max_length=10, verbose_name=_('Prefijo'))
    consecutivo = models.IntegerField(db_index=True, editable=False, verbose_name=_('Siguiente Consecutivo'), default=1)

    def formar_consecutivo(self, numero):
        """Une prefijo y numero para formar el identificador del documento."""
        return f"{self.prefijo} {numero}"

    class Meta:
        verbose_name = _('Resolucion DIAN')
        verbose_name_plural = _('Resoluciones DIAN')
        ordering = ['-vigente', '-fecha_resolucion']
        indexes = [
            models.Index(fields=['empresa', 'vigente']),
        ]

    def save(self, *args, **kwargs):
        """Guardado con validacion basica. Regla de inmutabilidad deshabilitada."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prefijo} {self.rango_desde}-{self.rango_hasta} (Vence: {self.fecha_fin})"

    def esta_dentro_de_fecha(self, fecha_referencia=None):
        if fecha_referencia is None:
            fecha_referencia = datetime.date.today()
        if isinstance(fecha_referencia, str):
            try:
                from django.utils.dateparse import parse_date
                parsed = parse_date(fecha_referencia)
                if parsed: fecha_referencia = parsed
                else: return False
            except Exception: return False
        return self.fecha_inicio <= fecha_referencia <= self.fecha_fin


class DocumentoSoporte(SintelTenantBaseModel):
    """
    Documento Soporte - Evidencia legal de gasto.
    v2.62: Inmutabilidad deshabilitada para permitir ajustes operativos.
    """
    # UUID Lookup Field (AGENTS.md §25)
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    # [FIELDS FIRST]
    resolucion_dian = models.ForeignKey(
        ResolucionDIAN,
        on_delete=models.PROTECT,
        related_name='documentos_soporte',
        verbose_name=_('Resolucion DIAN')
    )
    
    consecutivo = models.IntegerField(db_index=True, editable=False, verbose_name=_('Consecutivo'))
    
    categoria_contable = models.CharField(
        max_length=50,
        choices=CATEGORIA_CONTABLE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Categoría Contable"
    )
   
    fecha = models.DateField(verbose_name=_('Fecha del Documento'))
    
    proveedor = models.ForeignKey(
        'tenant_proveedores.Proveedor',
        on_delete=models.CASCADE,
        related_name='documentos_soporte',
        verbose_name=_('Proveedor'),
        db_index=True,
        help_text=_('Cuando se elimina el proveedor, se eliminan en cascada todos sus documentos soporte')
    )
    
    numero_documento_proveedor = models.CharField(
        max_length=100, 
        db_index=True, 
        blank=True, 
        null=True,
        verbose_name=_('Número Documento Proveedor'),
        help_text=_('Número de la factura o documento de referencia del proveedor')
    )
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    RETEFUENTE_CHOICES = [
        ('0.00', '0% - Sin Retefuente'),
        ('0', '0% - Sin Retefuente'),
        ('0.0', '0% - Sin Retefuente'),
        ('0.04', '4% - Servicios (Declarantes)'),
        ('0.06', '6% - Servicios (No Declarantes)'),
        ('0.10', '10% - Honorarios y Consultoria (No declarante)'),
        ('0.11', '11% - Honorarios y Consultoria (Declarante)'),
    ]
    
    retefuente_porcentaje = models.CharField(max_length=10, choices=RETEFUENTE_CHOICES, default='0.00', verbose_name=_('% Retefuente [DEPRECATED v3.7.1]'), editable=False)
    retefuente = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Monto Retefuente [DEPRECATED v3.7.1]'), editable=False)
    
    RETEICA_CHOICES = [
        ('0.00', '0% - Exento'),
        ('0', '0% - Exento'),
        ('0.0', '0% - Exento'),
        ('0.0069', '0.69%'),
        ('0.00966', '0.966%'),
        ('0.01104', '1.104%'),
    ]
    
    reteica_porcentaje = models.CharField(max_length=10, choices=RETEICA_CHOICES, default='0.00', verbose_name=_('% ReteICA [DEPRECATED v3.7.1]'), editable=False)
    reteica = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Monto ReteICA [DEPRECATED v3.7.1]'), editable=False)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
  
    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripcion"
    )
    observaciones = models.TextField(blank=True)

    # Integracion Contable (SSoT UUID - mapeados por app contabilidad)
    # WARNING: v3.7.1 - Solo cuenta de gasto. Contrapartida orquestada por app contabilidad
    cuenta_gasto_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Cuenta de Gasto/Egreso (UUID)",
        help_text="UUID de la CuentaContable de resultado (ej. 5105 Gastos). Contabilidad determina la contrapartida segun tipo de transaccion."
    )
    
    adjunto = models.FileField(upload_to='documentos_soporte/%Y/%m/', blank=True, null=True)
    activo = models.BooleanField(default=True, db_index=True)
    anulado = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(null=True, blank=True)
    usuario_anulacion = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='documentos_anulados_gastos'
    )
    
    class Meta:
        verbose_name = _('Documento Soporte')
        verbose_name_plural = _('Documentos Soporte')
        ordering = ['-fecha', '-consecutivo']
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['resolucion_dian', 'consecutivo']),
            models.Index(fields=['proveedor', 'numero_documento_proveedor']),
            models.Index(fields=['categoria_contable']),
            models.Index(fields=['fecha'], condition=models.Q(activo=True, anulado=False), name='idx_gastos_activos'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['resolucion_dian', 'consecutivo'], name='unique_ds_resolucion_consecutivo'),
            models.UniqueConstraint(fields=['empresa', 'proveedor', 'numero_documento_proveedor'], name='unique_ds_vendedor_documento', condition=models.Q(anulado=False)),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        if self.resolucion_dian and self.consecutivo:
            if not (self.resolucion_dian.rango_desde <= self.consecutivo <= self.resolucion_dian.rango_hasta):
                raise ValidationError({'consecutivo': f'El consecutivo {self.consecutivo} esta fuera de rango.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_documento} - {self.proveedor.razon_social} - {self.categoria_contable or 'Sin categoria'}"

    @property
    def prefijo(self):
        """Retorna el prefijo de la resolucion asociada."""
        return self.resolucion_dian.prefijo

    @property
    def numero_documento(self): 
        """Retorna el numero completo usando la funcion de la resolucion."""
        return self.resolucion_dian.formar_consecutivo(self.consecutivo)

    @property
    def total_retefuente(self) -> Decimal:
        """Lee RETEFUENTE desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return self.retefuente or Decimal('0.00')
        try:
            from apps.tenant.contabilidad.models import Retencion
            total = Retencion.objects.filter(
                tipo='RETEFUENTE',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            return self.retefuente or Decimal('0.00')

    @property
    def total_reteica(self) -> Decimal:
        """Lee RETEICA desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return self.reteica or Decimal('0.00')
        try:
            from apps.tenant.contabilidad.models import Retencion
            total = Retencion.objects.filter(
                tipo='RETEICA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            return self.reteica or Decimal('0.00')

    @property
    def total_reteiva(self) -> Decimal:
        """Lee RETEIVA desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            from apps.tenant.contabilidad.models import Retencion
            total = Retencion.objects.filter(
                tipo='RETEIVA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            return Decimal('0.00')
    @property
    def vendedor_nombre(self): return self.proveedor.razon_social
    @property
    def vendedor_nit(self): return self.proveedor.numero_documento
    @property
    def vendedor_direccion(self): return self.proveedor.direccion
    @property
    def vendedor_telefono(self): return self.proveedor.telefono_contacto

    @property
    def total_cop(self): return f"${self.total:,.0f}".replace(',', '.') if self.total else "$0"

    @property
    def total_retenciones(self) -> Decimal:
        """Suma total de todas las retenciones asociadas en Contabilidad."""
        if not self.pk: return Decimal('0.00')
        try:
            from django.apps import apps
            Retencion = apps.get_model('contabilidad', 'Retencion')
            total = Retencion.objects.filter(
                empresa=self.empresa,
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            return Decimal('0.00')

    @property
    def retefuente_calculada(self) -> Decimal:
        """Retorna el monto de Retefuente desde Contabilidad."""
        if not self.pk: return self.retefuente or Decimal('0.00')
        try:
            from django.apps import apps
            Retencion = apps.get_model('contabilidad', 'Retencion')
            monto = Retencion.objects.filter(
                tipo='RETEFUENTE',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(monto))
        except Exception:
            return self.retefuente or Decimal('0.00')

    @property
    def reteica_calculada(self) -> Decimal:
        """Retorna el monto de ReteICA desde Contabilidad."""
        if not self.pk: return self.reteica or Decimal('0.00')
        try:
            from django.apps import apps
            Retencion = apps.get_model('contabilidad', 'Retencion')
            monto = Retencion.objects.filter(
                tipo='RETEICA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(monto))
        except Exception:
            return self.reteica or Decimal('0.00')

    @property
    def subtotal_cop(self): return f"${self.subtotal:,.0f}".replace(',', '.') if self.subtotal else "$0"
    
    @property
    def retefuente_cop(self): 
        val = self.retefuente_calculada
        return f"${val:,.0f}".replace(',', '.') if val else "$0"
    
    @property
    def reteica_cop(self): 
        val = self.reteica_calculada
        return f"${val:,.0f}".replace(',', '.') if val else "$0"
    
    @property
    def total_retenciones_cop(self):
        val = self.total_retenciones
        return f"${val:,.0f}".replace(',', '.') if val else "$0"

    @property
    def cuenta_gasto_label(self):
        """Resuelve el label de la cuenta contable de gasto (SSoT v3.5.0)."""
        if not self.cuenta_gasto_uuid:
            return None
        from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
        return CuentaContableSelector.get_label_by_uuid(
            empresa_id=self.empresa_id,
            uuid=self.cuenta_gasto_uuid
        )


