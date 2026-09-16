"""
Modelos de gastos (TENANT_APP).

v2.62: FLEXIBILIDAD OPERATIVA - Reglas de Inmutabilidad deshabilitadas.
- DocumentoSoporte: Evidencia legal de gasto (Edicion permitida segun requerimiento).
- Gasto: Clasificacion contable (centro de costos/categoria)

NOTA: La integridad legal debe ser gestionada por procesos administrativos, el sistema permite modificaciones.
El formato del documento debe cumplir con la normativa DIAN colombiana.
"""
import datetime
import logging
import uuid as uuid_module
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa  # SSoT empresa (singleton por tenant)

from .choices.categoria_contable import CATEGORIA_CONTABLE_CHOICES

logger = logging.getLogger(__name__)


class ResolucionDIAN(SintelTenantBaseModel):
    """
    Resolucion DIAN para Documentos Soporte.
    """
    # UUID Lookup Field (AGENTS.md ?25)
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
    # UUID Lookup Field (AGENTS.md ?25)
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
        verbose_name="Categoria Contable"
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
        verbose_name=_('Numero Documento Proveedor'),
        help_text=_('Numero de la factura o documento de referencia del proveedor')
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
    
    RETEICA_CHOICES = [
        ('0.00', '0% - Exento'),
        ('0', '0% - Exento'),
        ('0.0', '0% - Exento'),
        ('0.0069', '0.69%'),
        ('0.00966', '0.966%'),
        ('0.01104', '1.104%'),
    ]
    
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
  
    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripcion"
    )
    observaciones = models.TextField(blank=True)

    # Integracion Contable (SSoT UUID - mapeados por app contabilidad)
    # WARNING: v3.7.1 - Solo cuenta de gasto. Contrapartida orquestada por app contabilidad

    # Sede — vinculacion para indicadores y KPIs por sede (DT-SEDE-01)
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gastos',
        verbose_name=_('Sede'),
        help_text=_('Sede de la empresa donde se origina el gasto. '
                    'Opcional — si no se asigna aplica a toda la empresa.'),
        db_index=True,
    )

    # Integration with Inventario Kardex (Pull Model via UUID)
    movimiento_inventario_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Vinculacion transaccional al Kardex de Inventario"
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

    def _get_retencion_model(self):
        """Retorna de forma perezosa el modelo Retencion de contabilidad para evitar importacion circular."""
        from django.apps import apps
        return apps.get_model('contabilidad', 'Retencion')

    @property
    def total_retefuente(self) -> Decimal:
        """Lee RETEFUENTE desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            total = Retencion.objects.filter(
                tipo='RETEFUENTE',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            # Hallazgo GASTOS-02 (mision UI/UX): un fallo real de la consulta
            # cross-schema era indistinguible de "sin retencion" -- ahora queda
            # en logs (ERROR REAL -> ERROR EXPLICITO, nunca $0 silencioso).
            logger.exception("total_retefuente: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
            return Decimal('0.00')

    @property
    def total_reteica(self) -> Decimal:
        """Lee RETEICA desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            total = Retencion.objects.filter(
                tipo='RETEICA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            logger.exception("total_reteica: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
            return Decimal('0.00')

    @property
    def total_reteiva(self) -> Decimal:
        """Lee RETEIVA desde Contabilidad.Retencion (v3.7.1 Pull Model)."""
        if not self.pk:
            return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            total = Retencion.objects.filter(
                tipo='RETEIVA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            logger.exception("total_reteiva: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
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
    def movimiento_referencia(self):
        """
        Retorna detalles clave del movimiento de inventario asociado (Pull Model).
        Evita dependencias circulares importando localmente el selector.
        """
        if not self.movimiento_inventario_uuid:
            return None
        try:
            from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
            mov = MovimientoInventarioSelector.get_detail(
                empresa_id=self.empresa_id,
                movimiento_uuid=self.movimiento_inventario_uuid
            )
            item_nombre = ""
            item_codigo = ""
            item_tipo = ""
            if mov.producto:
                item_nombre = mov.producto.nombre
                item_codigo = mov.producto.codigo
                item_tipo = "PRODUCTO"
            elif mov.activo_fijo:
                item_nombre = mov.activo_fijo.nombre
                item_codigo = mov.activo_fijo.codigo
                item_tipo = "ACTIVO_FIJO"
            return {
                'tipo': mov.tipo,
                'tipo_display': mov.get_tipo_display(),
                'item_tipo': item_tipo,
                'item_nombre': item_nombre,
                'item_codigo': item_codigo,
                'cantidad': float(mov.cantidad or 0),
            }
        except Exception:
            return None

    @property
    def total_cop(self): return f"${self.total:,.0f}".replace(',', '.') if self.total else "$0"

    @property
    def total_retenciones(self) -> Decimal:
        """Suma total de todas las retenciones asociadas en Contabilidad."""
        if not self.pk: return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            total = Retencion.objects.filter(
                empresa=self.empresa,
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(total))
        except Exception:
            logger.exception("total_retenciones: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
            return Decimal('0.00')

    @property
    def retefuente_calculada(self) -> Decimal:
        """Retorna el monto de Retefuente desde Contabilidad."""
        if not self.pk: return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            monto = Retencion.objects.filter(
                tipo='RETEFUENTE',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(monto))
        except Exception:
            logger.exception("retefuente_calculada: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
            return Decimal('0.00')

    @property
    def reteica_calculada(self) -> Decimal:
        """Retorna el monto de ReteICA desde Contabilidad."""
        if not self.pk: return Decimal('0.00')
        try:
            Retencion = self._get_retencion_model()
            monto = Retencion.objects.filter(
                tipo='RETEICA',
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=self.id,
                reversada=False
            ).aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
            return Decimal(str(monto))
        except Exception:
            logger.exception("reteica_calculada: fallo leyendo Retencion (documento_soporte_id=%s)", self.id)
            return Decimal('0.00')

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


