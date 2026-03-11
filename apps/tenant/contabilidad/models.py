"""
Modelos de contabilidad por tenant.

⚠️ IMPORTANTE: Estos modelos están en TENANT_APPS, por lo que:
- Cada tenant tiene su propia contabilidad
- NO usar foreign keys al esquema público (excepto User si es necesario)
- django-tenants maneja automáticamente el aislamiento por esquema
- No es necesario filtrar manualmente por tenant_id
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal
from apps.tenant.empresa.models import Empresa  # SSoT empresa (singleton por tenant)


class CatalogoMaestroNIIF(models.Model):
    """
    Catálogo Maestro de Cuentas NIIF para Colombia (SSoT).
    
    ⚠️ POLÍTICA:
    - Este es el catálogo oficial NIIF Colombia (Single Source of Truth)
    - NO pertenece a ningún tenant específico (es compartido)
    - Las cuentas de los tenants (CuentaContable) pueden referenciar este catálogo
    - Se puebla desde apps/tenant/contabilidad/choices/choices.py
    
    ⚠️ IMPORTANTE:
    - Este modelo está en TENANT_APPS pero actúa como referencia estática
    - Cada tenant tiene su propia copia del catálogo maestro
    - Permite que cada tenant personalice su plan de cuentas anclado al estándar NIIF
    
    ⚠️ AUTO-SETEO:
    - Solo se requiere el campo 'codigo' al crear una instancia
    - Los campos nombre, nivel y naturaleza se auto-completan desde CATALOGO_NIIF_COLOMBIA
    - Estos campos son editable=False para garantizar integridad del catálogo
    """
    NATURALEZA_CHOICES = [
        ('D', _('Débito/Deudora')),
        ('C', _('Crédito/Acreedora')),
    ]
    
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Código NIIF'),
        help_text=_('Código oficial de la cuenta según NIIF Colombia')
    )
    nombre = models.CharField(
        max_length=200,
        editable=False,
        verbose_name=_('Nombre Oficial'),
        help_text=_('Nombre oficial de la cuenta según NIIF Colombia (auto-seteado desde catálogo)')
    )
    nivel = models.IntegerField(
        editable=False,
        verbose_name=_('Nivel'),
        help_text=_('Nivel de la cuenta: 1 (Clase), 2 (Grupo), 4 (Cuenta), 6 (Subcuenta) (auto-seteado desde catálogo)')
    )
    naturaleza = models.CharField(
        max_length=1,
        choices=NATURALEZA_CHOICES,
        editable=False,
        verbose_name=_('Naturaleza'),
        help_text=_('Naturaleza de la cuenta: D (Débito/Deudora), C (Crédito/Acreedora) (auto-seteado desde catálogo)')
    )
    activa = models.BooleanField(
        default=True,
        verbose_name=_('Activa'),
        help_text=_('Indica si la cuenta está activa en el catálogo')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    class Meta:
        verbose_name = _('Catálogo Maestro NIIF')
        verbose_name_plural = _('Catálogo Maestro NIIF')
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['nivel']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para auto-setear nombre, nivel y naturaleza desde CATALOGO_NIIF_COLOMBIA.
        
        ⚠️ POLÍTICA DE AUTO-SETEO:
        - Busca self.codigo en CATALOGO_NIIF_COLOMBIA
        - Asigna automáticamente nombre, nivel y naturaleza
        - Si el código no existe en el catálogo, lanza ValueError
        - Garantiza integridad del catálogo oficial
        
        Raises:
            ValueError: Si el código no existe en CATALOGO_NIIF_COLOMBIA
        """
        from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA
        
        # Buscar el código en el catálogo oficial
        cuenta_catalogo = None
        for codigo, nombre, nivel, naturaleza in CATALOGO_NIIF_COLOMBIA:
            if codigo == self.codigo:
                cuenta_catalogo = (codigo, nombre, nivel, naturaleza)
                break
        
        # Validar que el código existe en el catálogo
        if not cuenta_catalogo:
            raise ValueError(
                f"El código '{self.codigo}' no existe en CATALOGO_NIIF_COLOMBIA. "
                f"Solo se pueden crear cuentas que existan en el catálogo oficial."
            )
        
        # Auto-setear los campos desde el catálogo
        self.nombre = cuenta_catalogo[1]
        self.nivel = cuenta_catalogo[2]
        self.naturaleza = cuenta_catalogo[3]
        
        # Guardar la instancia
        super().save(*args, **kwargs)
    
    def get_tipo_cuenta(self):
        """
        Determina el tipo de cuenta basado en el primer dígito del código.
        
        Returns:
            str: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO, COSTO
        """
        if not self.codigo:
            return None
        
        primer_digito = self.codigo[0]
        tipos = {
            '1': 'ACTIVO',
            '2': 'PASIVO',
            '3': 'PATRIMONIO',
            '4': 'INGRESO',
            '5': 'GASTO',
            '6': 'COSTO',
        }
        return tipos.get(primer_digito, None)


class CuentaContable(models.Model):
    """
    Plan de cuentas contables (por tenant).
    
    Cada tenant tiene su propio plan de cuentas.
    """
    TIPO_CUENTA_CHOICES = [
        ('ACTIVO', _('Activo')),
        ('PASIVO', _('Pasivo')),
        ('PATRIMONIO', _('Patrimonio')),
        ('INGRESO', _('Ingreso')),
        ('GASTO', _('Gasto')),
    ]
    
    # ⚠️ v2.37: UUID para lookup público (no expone PK interno)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador único público para la API')
    )
    
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Código'),
        help_text=_('Código único de la cuenta contable')
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name=_('Nombre'),
        help_text=_('Nombre de la cuenta contable')
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CUENTA_CHOICES,
        verbose_name=_('Tipo de Cuenta')
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripción')
    )
    cuenta_padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='cuentas_hijas',
        verbose_name=_('Cuenta Padre'),
        help_text=_('Cuenta contable padre (para jerarquía)')
    )
    # ⚠️ ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='cuentas_contables',
        verbose_name=_('Empresa'),
        help_text=_('Empresa propietaria de la cuenta contable (SSoT por tenant).')
    )
    # ⚠️ v2.61: Vinculación con Catálogo Maestro NIIF
    catalogo_referencia = models.ForeignKey(
        CatalogoMaestroNIIF,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cuentas_vinculadas',
        verbose_name=_('Referencia Catálogo NIIF'),
        help_text=_('Cuenta oficial del catálogo NIIF Colombia a la que está anclada esta cuenta personalizada')
    )
    activa = models.BooleanField(
        default=True,
        verbose_name=_('Activa')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    class Meta:
        verbose_name = _('Cuenta Contable')
        verbose_name_plural = _('Cuentas Contables')
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['empresa']),  # ⚠️ v2.40: Índice para FK a Empresa
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class AsientoContable(models.Model):
    """
    Asiento contable (por tenant).
    
    Cada tenant tiene sus propios asientos contables.
    """
    ESTADO_CHOICES = [
        ('BORRADOR', _('Borrador')),
        ('APROBADO', _('Aprobado')),
        ('CERRADO', _('Cerrado')),
    ]
    
    # ⚠️ v2.37: UUID para lookup público (no expone PK interno)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador único público para la API')
    )
    
    numero = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Número de Asiento')
    )
    fecha = models.DateField(
        verbose_name=_('Fecha del Asiento')
    )
    descripcion = models.TextField(
        verbose_name=_('Descripción'),
        help_text=_('Descripción del asiento contable')
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='BORRADOR',
        verbose_name=_('Estado')
    )
    
    # Totales (deben cuadrar: debe = haber)
    total_debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Débito')
    )
    total_haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Crédito')
    )
    
    # ⚠️ ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='asientos_contables',
        verbose_name=_('Empresa'),
        help_text=_('Empresa propietaria del asiento contable (SSoT por tenant).')
    )
    # Relación con factura (opcional)
    factura = models.ForeignKey(
        'facturas.Factura',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='asientos',
        verbose_name=_('Factura Relacionada'),
        help_text=_('Factura relacionada con este asiento (opcional)')
    )
    
    # Metadatos
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Asiento Contable')
        verbose_name_plural = _('Asientos Contables')
        ordering = ['-fecha', '-numero']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['empresa']),  # ⚠️ v2.40: Índice para FK a Empresa
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.fecha}"
    
    def save(self, *args, **kwargs):
        # Validar que debe = haber si el asiento está aprobado
        if self.estado == 'APROBADO' and self.total_debe != self.total_haber:
            raise ValueError(_('Un asiento aprobado debe tener débito igual a crédito'))
        super().save(*args, **kwargs)


class MovimientoContable(models.Model):
    """
    Movimiento contable (partida de un asiento) (por tenant).
    
    Cada asiento tiene múltiples movimientos (partidas).
    """
    asiento = models.ForeignKey(
        AsientoContable,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name=_('Asiento')
    )
    cuenta = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        verbose_name=_('Cuenta Contable')
    )
    
    # Valores
    debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Débito')
    )
    haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Crédito')
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripción'),
        help_text=_('Descripción del movimiento')
    )
    
    # Orden
    orden = models.IntegerField(
        default=1,
        verbose_name=_('Orden'),
        help_text=_('Orden del movimiento en el asiento')
    )
    
    class Meta:
        verbose_name = _('Movimiento Contable')
        verbose_name_plural = _('Movimientos Contables')
        ordering = ['asiento', 'orden']
    
    def __str__(self):
        return f"{self.asiento.numero} - {self.cuenta.codigo}"
    
    def save(self, *args, **kwargs):
        # Validar que debe o haber sea mayor a 0, pero no ambos
        if self.debe > 0 and self.haber > 0:
            raise ValueError(_('Un movimiento no puede tener débito y crédito simultáneamente'))
        if self.debe == 0 and self.haber == 0:
            raise ValueError(_('Un movimiento debe tener débito o crédito mayor a cero'))
        
        super().save(*args, **kwargs)
        
        # Actualizar totales del asiento
        self.asiento.total_debe = sum(m.debe for m in self.asiento.movimientos.all())
        self.asiento.total_haber = sum(m.haber for m in self.asiento.movimientos.all())
        self.asiento.save()


class PeriodoContable(models.Model):
    """
    Periodo contable cerrado (por tenant).
    
    ⚠️ v2.60 Fase 3: Inmutabilidad de Periodos Cerrados
    - Una vez cerrado un periodo, no se pueden editar/anular documentos en ese rango de fechas
    - Bloquea edición/anulación de Facturas y Gastos en periodos cerrados
    """
    ESTADO_CHOICES = [
        ('ABIERTO', _('Abierto')),
        ('CERRADO', _('Cerrado')),
    ]
    
    # ⚠️ ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='periodos_contables',
        verbose_name=_('Empresa'),
        help_text=_('Empresa propietaria del periodo contable (SSoT por tenant).')
    )
    
    periodo = models.CharField(
        max_length=7,
        verbose_name=_('Periodo (YYYY-MM)'),
        help_text=_('Formato: YYYY-MM (ej: 2024-01)')
    )
    
    fecha_inicio = models.DateField(
        verbose_name=_('Fecha Inicio'),
        help_text=_('Primer día del periodo')
    )
    
    fecha_fin = models.DateField(
        verbose_name=_('Fecha Fin'),
        help_text=_('Último día del periodo')
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='ABIERTO',
        verbose_name=_('Estado'),
        help_text=_('ABIERTO: Permite ediciones. CERRADO: Bloquea ediciones/anulaciones.')
    )
    
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Cierre'),
        help_text=_('Fecha y hora en que se cerró el periodo')
    )
    
    cerrado_por = models.ForeignKey(
        'perfil.TenantProfile',  # Usuario del tenant (perfil específico del tenant)
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='periodos_cerrados',
        verbose_name=_('Cerrado Por'),
        help_text=_('Usuario del tenant que cerró el periodo')
    )
    
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Observaciones'),
        help_text=_('Notas sobre el cierre del periodo')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Periodo Contable')
        verbose_name_plural = _('Periodos Contables')
        ordering = ['-periodo']
        unique_together = [['empresa', 'periodo']]
        indexes = [
            models.Index(fields=['empresa', 'periodo']),
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]
    
    def __str__(self):
        return f"{self.periodo} - {self.get_estado_display()}"
    
    def esta_cerrado(self):
        """Verifica si el periodo está cerrado."""
        return self.estado == 'CERRADO'
    
    def contiene_fecha(self, fecha):
        """
        Verifica si una fecha está dentro del rango del periodo.
        
        Args:
            fecha: datetime.date o datetime.datetime
        
        Returns:
            bool
        """
        if hasattr(fecha, 'date'):
            fecha = fecha.date()
        return self.fecha_inicio <= fecha <= self.fecha_fin