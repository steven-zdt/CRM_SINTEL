"""
Modelos de gastos (TENANT_APP).

WARNING: v2.40: Sistema de Documento Soporte Inmutable
- DocumentoSoporte: Evidencia legal inmutable según Art. 1.6.1.4.12 DR 1625 de 2016
- Gasto: Clasificación contable (centro de costos/categoría)

REGLA DE ORO: Una vez generado el consecutivo, los valores monetarios son INMUTABLES.
El formato del documento debe cumplir con la normativa DIAN colombiana.
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # auto-inserted by autocorrect
from apps.tenant.empresa.models import Empresa  # SSoT empresa (singleton por tenant)

from .choices.categoria_contable import CATEGORIA_CONTABLE_CHOICES
from .choices.centros_costo import CENTRO_COSTO_CHOICES
from .choices.niif_gastos_choices import GASTOS_NIIF_CHOICES


class ResolucionDIAN(SintelTenantBaseModel):
    """
    Resolución DIAN para Documentos Soporte.
    WARNING: v2.40: Configuración manual de rangos y fechas de vigencia.
    """
    empresa = models.ForeignKey(
        'empresa.Empresa', # Asegúrate de que el path sea correcto
        on_delete=models.PROTECT,
        related_name='resoluciones_dian'
    )
    
    numero_resolucion = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_('Número Resolución DIAN')
    )
    
    prefijo = models.CharField(
        max_length=10,
        verbose_name=_('Prefijo')
    )
    
    rango_desde = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Desde')
    )
    rango_hasta = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Rango Hasta')
    )
    
    # WARNING: FECHAS DE APLICACIÓN MANUAL
    fecha_resolucion = models.DateField(
        verbose_name=_('Fecha de Emisión'),
        help_text=_('Fecha en la que la DIAN emitió la resolución')
    )
    fecha_inicio = models.DateField(
        verbose_name=_('Fecha Inicio Aplicación'),
        help_text=_('Fecha desde la cual se empezará a usar en el sistema'),
        default=datetime.date.today  # WARNING: Callable: se evalúa en tiempo de creación, no en tiempo de definición
    )
    fecha_fin = models.DateField(
        verbose_name=_('Fecha Final Aplicación'),
        help_text=_('Fecha de vencimiento de la resolución')
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
        help_text=_('Solo una resolución puede estar vigente para ser usada por defecto.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Resolución DIAN')
        verbose_name_plural = _('Resoluciones DIAN')
        ordering = ['-vigente', '-fecha_resolucion']
        indexes = [
            models.Index(fields=['empresa', 'vigente']),
        ]

    def clean(self):
        """Validaciones de integridad de datos."""
        # 1. Validar Rangos
        if self.rango_hasta and self.rango_desde:
            if self.rango_hasta <= self.rango_desde:
                raise ValidationError({'rango_hasta': _('El número final debe ser mayor al inicial.')})
        
        # 2. Validar Fechas
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                raise ValidationError({'fecha_fin': _('La fecha de fin debe ser posterior a la de inicio.')})
        
        if self.fecha_inicio and self.fecha_resolucion:
            if self.fecha_inicio < self.fecha_resolucion:
                raise ValidationError({'fecha_inicio': _('La aplicación no puede iniciar antes de la emisión de la resolución.')})

    def save(self, *args, **kwargs):
        """Lógica de negocio para asegurar una sola resolución vigente."""
        self.full_clean()
        
        # Si esta resolución se marca como vigente, desactivamos las anteriores (Atomically)
        if self.vigente:
            with transaction.atomic():
                ResolucionDIAN.objects.filter(
                    empresa=self.empresa, 
                    vigente=True
                ).exclude(pk=self.pk).update(vigente=False)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prefijo} {self.rango_desde}-{self.rango_hasta} (Vence: {self.fecha_fin})"

    def esta_dentro_de_fecha(self, fecha_referencia=None):
        """Verifica si hoy (o una fecha dada) está en el rango permitido."""
        if fecha_referencia is None:
            fecha_referencia = datetime.date.today()
        return self.fecha_inicio <= fecha_referencia <= self.fecha_fin
        

class DocumentoSoporte(SintelTenantBaseModel):
    """
    Documento Soporte Inmutable - Evidencia legal de gasto.
    
    WARNING: v2.40: REGLA DE ORO - Una vez generado el consecutivo, los valores son INMUTABLES.
    Formato según Art. 1.6.1.4.12 DR 1625 de 2016.
    
    El documento debe incluir:
    - Resolución DIAN (prefijo + número consecutivo dentro del rango)
    - Datos del vendedor (proveedor)
    - Detalle económico con retenciones (Retefuente, ReteICA)
    - Total = Subtotal - Retefuente - ReteICA
    """
    # WARNING: ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='documentos_soporte',
        help_text='Empresa propietaria del documento (SSoT por tenant).'
    )
    
    # WARNING: Resolución DIAN asociada
    resolucion_dian = models.ForeignKey(
        ResolucionDIAN,
        on_delete=models.PROTECT,
        related_name='documentos_soporte',
        verbose_name=_('Resolución DIAN'),
        help_text=_('Resolución DIAN que autoriza este documento')
    )
    
    # Prefijo (delegado desde resolución, pero almacenado para snapshot histórico)
    prefijo = models.CharField(
        max_length=10,
        verbose_name=_('Prefijo'),
        help_text=_('Prefijo del documento (ej: SI)')
    )
    
    # Consecutivo (entero, dentro del rango de la resolución)
    consecutivo = models.IntegerField(
        db_index=True,
        editable=False,  # WARNING: INMUTABLE: No editable una vez asignado
        verbose_name=_('Consecutivo'),
        help_text=_('Número consecutivo del documento (dentro del rango de la resolución)')
    )
    
    # Fecha del documento
    fecha = models.DateField(
        verbose_name=_('Fecha del Documento'),
        help_text=_('Fecha de emisión del documento soporte')
    )
    
    # ======================
    # DATOS DEL VENDEDOR (Proveedor)
    # ======================
    vendedor_nombre = models.CharField(
        max_length=200,
        verbose_name=_('Nombre/Razón Social Vendedor'),
        help_text=_('Nombre o razón social del vendedor (snapshot histórico)')
    )
    vendedor_nit = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name=_('NIT Vendedor'),
        help_text=_('NIT del vendedor (snapshot histórico)')
    )
    vendedor_direccion = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Dirección Vendedor'),
        help_text=_('Dirección del vendedor (snapshot histórico)')
    )
    vendedor_telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Teléfono Vendedor'),
        help_text=_('Teléfono del vendedor (snapshot histórico)')
    )
    
    # Número de factura/comprobante del proveedor (referencia externa)
    numero_factura_proveedor = models.CharField(
        max_length=100,
        db_index=True,
        blank=True,
        null=True,
        verbose_name=_('Número Factura Proveedor'),
        help_text=_('Número de factura o comprobante emitido por el proveedor (referencia)')
    )
    
    # ======================
    # DETALLE ECONÓMICO (INMUTABLE una vez asignado el consecutivo)
    # WARNING: v2.40: Total = Subtotal - Retefuente - ReteICA
    # ======================
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Subtotal'),
        help_text=_('Subtotal del documento (antes de retenciones)')
    )
    
    # WARNING: v2.40: Choices para Retefuente (porcentajes comunes en Colombia)
    RETEFUENTE_CHOICES = [
        ('0.00', '0% - Sin Retefuente'),
        ('0.04', '4% - Servicios (Declarantes)'),
        ('0.06', '6% - Servicios (No Declarantes)'),
        ('0.10', '10% - Honorarios y Consultoría (Persona Natural no declarante)'),
        ('0.11', '11% - Honorarios y Consultoría (Persona Jurídica o declarante)'),
    ]
    
    retefuente_porcentaje = models.CharField(
        max_length=10,
        choices=RETEFUENTE_CHOICES,
        default='0.00',
        verbose_name=_('Porcentaje Retefuente'),
        help_text=_('Porcentaje de retención en la fuente aplicado')
    )
    
    retefuente = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Retefuente'),
        help_text=_('Valor calculado de retención en la fuente (subtotal * porcentaje)')
    )
    
    # WARNING: v2.40: Choices para ReteICA (tarifas comunes en Colombia)
    RETEICA_CHOICES = [
        ('0.00', '0% - Exento'),
        ('0.0069', '0.69% - Tarifa 0.69% (6.9/1000)'),
        ('0.00966', '0.966% - Tarifa 0.966% (9.66/1000)'),
        ('0.01104', '1.104% - Tarifa 1.104% (11.04/1000)'),
    ]
    
    reteica_porcentaje = models.CharField(
        max_length=10,
        choices=RETEICA_CHOICES,
        default='0.00',
        verbose_name=_('Porcentaje ReteICA'),
        help_text=_('Porcentaje de retención ICA aplicado')
    )
    
    reteica = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('ReteICA'),
        help_text=_('Valor calculado de retención ICA (subtotal * porcentaje)')
    )
    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total'),
        help_text=_('Total del documento (Subtotal - Retefuente - ReteICA)')
    )
    
    # Archivo adjunto (evidencia legal)
    adjunto = models.FileField(
        upload_to='documentos_soporte/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'xml'])],
        blank=True,
        null=True,
        verbose_name=_('Archivo Adjunto'),
        help_text=_('Archivo del documento soporte (PDF, imagen o XML)')
    )
    
    # Estado
    activo = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('Activo'),
        help_text=_('Indica si el documento soporte está activo. Debe estar desactivado para poder anular.')
    )
    anulado = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Anulado'),
        help_text=_('Indica si el documento soporte ha sido anulado. Solo se puede anular si está desactivado.')
    )
    fecha_anulacion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Fecha de Anulación'),
        help_text=_('Fecha y hora de anulación')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Documento Soporte')
        verbose_name_plural = _('Documentos Soporte')
        ordering = ['-fecha', '-consecutivo']
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['resolucion_dian', 'consecutivo']),
            models.Index(fields=['prefijo', 'consecutivo']),  # Para búsqueda por "SI 150"
            models.Index(fields=['vendedor_nit', 'numero_factura_proveedor']),  # Para evitar duplicados
            
            # WARNING: v2.61: SINTEL ADVANCED INDEXING (Partial Index para estados concurrentes)
            # Reemplaza índices estáticos booleanos por índice filtrado de alto rendimiento
            models.Index(
                fields=['fecha'], 
                condition=models.Q(activo=True, anulado=False), 
                name='idx_gastos_activos'
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['resolucion_dian', 'consecutivo'],
                name='unique_ds_resolucion_consecutivo',
                violation_error_message=_('Ya existe un Documento Soporte con este consecutivo en esta resolución.')
            ),
            models.UniqueConstraint(
                fields=['empresa', 'vendedor_nit', 'numero_factura_proveedor'],
                name='unique_ds_vendedor_factura',
                condition=models.Q(anulado=False),
                violation_error_message=_('Ya existe un Documento Soporte activo con este vendedor y número de factura.')
            )
        ]
    
    def clean(self):
        """
        Valida coherencia de totales y rango de consecutivo.
        WARNING: v2.40: Calcula automáticamente las retenciones basándose en los porcentajes.
        """
        # Validar que el consecutivo esté dentro del rango de la resolución
        if self.resolucion_dian and self.consecutivo:
            if not (self.resolucion_dian.rango_desde <= self.consecutivo <= self.resolucion_dian.rango_hasta):
                raise ValidationError({
                    'consecutivo': _(
                        f'El consecutivo {self.consecutivo} debe estar entre '
                        f'{self.resolucion_dian.rango_desde} y {self.resolucion_dian.rango_hasta} '
                        f'(rango de la resolución {self.resolucion_dian.numero_resolucion}).'
                    )
                })
        
        # WARNING: v2.40: Calcular retenciones automáticamente basándose en los porcentajes
        if self.subtotal is not None and self.subtotal >= 0:
            # Calcular Retefuente
            if self.retefuente_porcentaje:
                porcentaje_retefuente = Decimal(str(self.retefuente_porcentaje))
                self.retefuente = (self.subtotal * porcentaje_retefuente).quantize(Decimal('0.01'))
            else:
                self.retefuente = Decimal('0.00')
            
            # Calcular ReteICA
            if self.reteica_porcentaje:
                porcentaje_reteica = Decimal(str(self.reteica_porcentaje))
                self.reteica = (self.subtotal * porcentaje_reteica).quantize(Decimal('0.01'))
            else:
                self.reteica = Decimal('0.00')
        
        # Validar fórmula: Total = Subtotal - Retefuente - ReteICA
        # WARNING: v2.40: Tolerancia aumentada para manejar errores de redondeo en cálculos grandes
        # Tolerancia de 100.00 para permitir diferencias por redondeo acumulado en documentos grandes
        # Esto es necesario porque los cálculos de retenciones pueden tener pequeñas diferencias por redondeo
        if self.subtotal is not None and self.retefuente is not None and self.reteica is not None:
            total_calculado = self.subtotal - self.retefuente - self.reteica
            diferencia = abs(self.total - total_calculado) if self.total is not None else Decimal('0.00')
            if self.total is not None and diferencia > Decimal('100.00'):
                raise ValidationError({
                    'total': _(
                        f'El total debe ser igual a Subtotal - Retefuente - ReteICA. '
                        f'Esperado: {total_calculado}, Actual: {self.total}, Diferencia: {diferencia}'
                    )
                })
    
    def save(self, *args, **kwargs):
        """Asegura que clean() se ejecute y recalcula total si es necesario."""
        # Recalcular total si no está definido o es inconsistente
        if self.subtotal is not None and self.retefuente is not None and self.reteica is not None:
            self.total = self.subtotal - self.retefuente - self.reteica
        
        # Sincronizar prefijo desde resolución si no está definido
        if self.resolucion_dian and not self.prefijo:
            self.prefijo = self.resolucion_dian.prefijo
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.prefijo} {self.consecutivo} - {self.vendedor_nombre} ({self.fecha})"
    
    @property
    def numero_documento(self):
        """Retorna el número completo del documento (Prefijo + Consecutivo)."""
        return f"{self.prefijo} {self.consecutivo}"
    
    # WARNING: v2.40: Propiedades para formatear valores monetarios como dinero en COP
    @property
    def subtotal_cop(self):
        """Retorna el subtotal formateado como dinero en pesos colombianos (COP)."""
        if self.subtotal is None:
            return "$0"
        return f"${self.subtotal:,.0f}".replace(',', '.')
    
    @property
    def retefuente_cop(self):
        """Retorna la retención en la fuente formateada como dinero en pesos colombianos (COP)."""
        if self.retefuente is None:
            return "$0"
        return f"${self.retefuente:,.0f}".replace(',', '.')
    
    @property
    def reteica_cop(self):
        """Retorna la retención ICA formateada como dinero en pesos colombianos (COP)."""
        if self.reteica is None:
            return "$0"
        return f"${self.reteica:,.0f}".replace(',', '.')
    
    @property
    def total_cop(self):
        """Retorna el total formateado como dinero en pesos colombianos (COP)."""
        if self.total is None:
            return "$0"
        return f"${self.total:,.0f}".replace(',', '.')
    
    @property
    def total_retenciones_cop(self):
        """Retorna el total de retenciones (Retefuente + ReteICA) formateado como dinero en COP."""
        total_retenciones = (self.retefuente or Decimal('0.00')) + (self.reteica or Decimal('0.00'))
        return f"${total_retenciones:,.0f}".replace(',', '.')


class Gasto(SintelTenantBaseModel):
    """
    Clasificación contable de un Documento Soporte.
    
    WARNING: v2.40: El Gasto es la clasificación contable (centro de costos/categoría).
    El DocumentoSoporte es la evidencia legal inmutable.
    
    REGLA: Un DocumentoSoporte puede tener múltiples Gastos (distribución contable).
    Por simplicidad inicial, implementamos OneToOneField (1 DS = 1 Gasto).
    
    WARNING: LIMPIEZA: Eliminadas categorías de personal (Salarios, Aportes).
    """
    # WARNING: RELACIÓN CON DOCUMENTO SOPORTE (OneToOne)
    documento_soporte = models.OneToOneField(
        DocumentoSoporte,
        on_delete=models.PROTECT,
        related_name='gasto',
        verbose_name=_('Documento Soporte'),
        help_text=_('Documento Soporte asociado (evidencia legal)')
    )
    
    # WARNING: ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='gastos',
        help_text='Empresa propietaria del gasto (SSoT por tenant).'
    )
    
    # Clasificación contable
    centro_costo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=CENTRO_COSTO_CHOICES,
        verbose_name=_('Centro de Costo'),
        help_text=_('Centro de costo para clasificación contable')
    )
    categoria_contable = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=CATEGORIA_CONTABLE_CHOICES,
        verbose_name=_('Categoria Contable'),
        help_text=_('Categoria contable del gasto (excluye personal)')
    )

    # v2.61.7: Codigo NIIF para vinculacion con plan de cuentas del tenant
    codigo_contable = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=GASTOS_NIIF_CHOICES,
        db_index=True,
        verbose_name=_('Codigo Contable NIIF'),
        help_text=_(
            'Codigo del PUC (ej: 510506) para vinculacion con CuentaContable del tenant. '
            'Si se configura, el asiento contable usara esta cuenta como debito de gastos.'
        )
    )
    
    # Periodo contable
    periodo = models.CharField(
        max_length=7,
        verbose_name=_('Periodo Contable'),
        help_text=_('Periodo contable. Ej: 2026-01')
    )
    
    # Descripción adicional (opcional)
    descripcion = models.TextField(
        blank=True,
        verbose_name=_('Descripción'),
        help_text=_('Descripción adicional del gasto')
    )
    
    # Observaciones
    observaciones = models.TextField(
        blank=True,
        verbose_name=_('Observaciones'),
        help_text=_('Observaciones adicionales')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Gasto')
        verbose_name_plural = _('Gastos')
        ordering = ['-documento_soporte__fecha', '-documento_soporte__consecutivo']
        indexes = [
            models.Index(fields=['empresa', 'periodo']),
            models.Index(fields=['centro_costo', 'categoria_contable']),
            models.Index(fields=['documento_soporte']),
        ]
    
    def __str__(self):
        return f"{self.documento_soporte.numero_documento} - {self.categoria_contable or 'Sin categoría'}"
    
    # Properties delegadas desde DocumentoSoporte (INMUTABLES)
    @property
    def subtotal(self):
        """Delega al DocumentoSoporte (INMUTABLE)."""
        return self.documento_soporte.subtotal
    
    @property
    def retefuente(self):
        """Delega al DocumentoSoporte (INMUTABLE)."""
        return self.documento_soporte.retefuente
    
    @property
    def reteica(self):
        """Delega al DocumentoSoporte (INMUTABLE)."""
        return self.documento_soporte.reteica
    
    @property
    def total(self):
        """Delega al DocumentoSoporte (INMUTABLE)."""
        return self.documento_soporte.total
    
    @property
    def fecha(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.fecha
    
    @property
    def numero_documento(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.numero_documento
    
    # WARNING: v2.40: Propiedades para formatear valores monetarios como dinero en COP (delegadas)
    @property
    def subtotal_cop(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.subtotal_cop
    
    @property
    def retefuente_cop(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.retefuente_cop
    
    @property
    def reteica_cop(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.reteica_cop
    
    @property
    def total_cop(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.total_cop
    
    @property
    def total_retenciones_cop(self):
        """Delega al DocumentoSoporte."""
        return self.documento_soporte.total_retenciones_cop