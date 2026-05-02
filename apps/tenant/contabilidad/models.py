"""
Modelos de contabilidad por tenant.

WARNING: IMPORTANTE: Estos modelos están en TENANT_APPS, por lo que:
- Cada tenant tiene su propia contabilidad
- NO usar foreign keys al esquema público (excepto User si es necesario)
- django-tenants maneja automáticamente el aislamiento por esquema
- No es necesario filtrar manualmente por tenant_id
"""
import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa  # SSoT empresa (singleton por tenant)

# ============================================================================
# CHOICES - Normativa Colombiana (NIIF PYMES)
# ============================================================================

TIPO_COMPROBANTE_CHOICES = [
    ('FVE', _('Factura de Venta Electrónica')),
    ('CE', _('Comprobante de Egreso')),
    ('RC', _('Recibo de Caja')),
    ('GN', _('Nota General')),
    ('ND', _('Nota Débito')),
    ('NC', _('Nota Crédito')),
]

TIPO_TERCERO_CHOICES = [
    ('CLIENTE', _('Cliente')),
    ('PROVEEDOR', _('Proveedor')),
    ('EMPLEADO', _('Empleado')),
    ('OTRO', _('Otro Tercero')),
]


class CatalogoMaestroNIIF(SintelTenantBaseModel):
    """
    Catálogo Maestro de Cuentas NIIF para Colombia (SSoT).
    
    WARNING: POLÍTICA:
    - Este es el catálogo oficial NIIF Colombia (Single Source of Truth)
    - NO pertenece a ningún tenant específico (es compartido)
    - Las cuentas de los tenants (CuentaContable) pueden referenciar este catálogo
    - Se puebla desde apps/tenant/contabilidad/choices/choices.py
    
    WARNING: IMPORTANTE:
    - Este modelo está en TENANT_APPS pero actúa como referencia estática
    - Cada tenant tiene su propia copia del catálogo maestro
    - Permite que cada tenant personalice su plan de cuentas anclado al estándar NIIF
    
    WARNING: AUTO-SETEO:
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
    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Catálogo Maestro NIIF')
        verbose_name_plural = _('Catálogo Maestro NIIF')
        ordering = ['codigo']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['codigo']),
            models.Index(fields=['nivel']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    
    
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
        return tipos.get(primer_digito)


class CuentaContable(SintelTenantBaseModel):
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
    
    # WARNING: v2.37: UUID para lookup público (no expone PK interno)
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
    nivel = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('Nivel'),
        help_text=_('Nivel jerárquico de la cuenta (1-6)')
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
    catalogo_referencia = models.ForeignKey(
        'CatalogoMaestroNIIF',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='cuentas_vinculadas',
        verbose_name=_('Referencia Catálogo NIIF'),
        help_text=_('Vínculo con el catálogo maestro oficial NIIF')
    )
    activa = models.BooleanField(
        default=True,
        verbose_name=_('Activa'),
        help_text=_('Indica si la cuenta está habilitada para registros')
    )
    # WARNING: ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    
    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Cuenta Contable')
        verbose_name_plural = _('Cuentas Contables')
        ordering = ['codigo']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['nivel']),  # WARNING: NORMATIVA: Índice para validación de nivel
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class AsientoContable(SintelTenantBaseModel):
    """
    Asiento contable (por tenant).
    
    Cada tenant tiene sus propios asientos contables.
    """
    ESTADO_CHOICES = [
        ('BORRADOR', _('Borrador')),
        ('APROBADO', _('Aprobado')),
        ('CERRADO', _('Cerrado')),
    ]
    
    # WARNING: v2.37: UUID para lookup público (no expone PK interno)
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
    
    # WARNING: NORMATIVA: Tipo de comprobante para trazabilidad
    tipo_comprobante = models.CharField(
        max_length=5,
        choices=TIPO_COMPROBANTE_CHOICES,
        blank=True,
        null=True,
        verbose_name=_('Tipo de Comprobante'),
        help_text=_('Tipo de documento que originó el asiento (FVE, CE, RC, GN, ND, NC)')
    )
    numero_comprobante = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Número de Comprobante'),
        help_text=_('Número del comprobante que originó el asiento')
    )
    
    # Totales (deben cuadrar: debe = haber) - WARNING: NORMATIVA: Partida Doble Estricta
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
    
    # WARNING: ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    
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
    
    
    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Asiento Contable')
        verbose_name_plural = _('Asientos Contables')
        ordering = ['-fecha', '-numero']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['tipo_comprobante', 'numero_comprobante']),  # WARNING: NORMATIVA: Trazabilidad
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.fecha}"


class MovimientoContable(SintelTenantBaseModel):
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
        verbose_name=_('Cuenta Contable'),
        help_text=_('Cuenta contable (debe ser de nivel 6 según normativa)')
    )
    tipo_tercero = models.CharField(
        max_length=20,
        choices=TIPO_TERCERO_CHOICES,
        blank=True,
        null=True,
        verbose_name=_('Tipo de Tercero'),
        help_text=_('Tipo de tercero asociado al movimiento (obligatorio para medios magnéticos)')
    )
    tercero_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('ID del Tercero'),
        help_text=_('ID del tercero (Cliente, Proveedor, Empleado u otro)')
    )
    tercero_nit = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name=_('NIT/CC del Tercero'),
        help_text=_('Número de identificación del tercero (NIT, CC, CE, etc.)')
    )
    tercero_razon_social = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Razón Social del Tercero'),
        help_text=_('Nombre o razón social del tercero')
    )
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
    base_iva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Base IVA'),
        help_text=_('Base gravable para cálculo de IVA')
    )
    iva_generado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('IVA Generado'),
        help_text=_('IVA generado (cuenta 240805)')
    )
    iva_descontable = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('IVA Descontable'),
        help_text=_('IVA descontable (cuenta 240810)')
    )
    retefuente = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Retención en la Fuente'),
        help_text=_('Retención en la fuente (cuenta 2365)')
    )
    reteica = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Retención ICA'),
        help_text=_('Retención ICA (cuenta 2368)')
    )
    orden = models.IntegerField(
        default=1,
        verbose_name=_('Orden'),
        help_text=_('Orden del movimiento en el asiento')
    )

    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Movimiento Contable')
        verbose_name_plural = _('Movimientos Contables')
        ordering = ['asiento', 'orden']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['asiento', 'orden']),
            models.Index(fields=['cuenta']),
            models.Index(fields=['tipo_tercero', 'tercero_id']),
            models.Index(fields=['tercero_nit']),
        ]

    def __str__(self):
        return f"{self.asiento.numero} - {self.cuenta.codigo} - {self.tercero_razon_social or 'Sin tercero'}"

class PeriodoContable(SintelTenantBaseModel):
    """
    Periodo contable cerrado (por tenant).
    
    WARNING: v2.60 Fase 3: Inmutabilidad de Periodos Cerrados
    - Una vez cerrado un periodo, no se pueden editar/anular documentos en ese rango de fechas
    - Bloquea edición/anulación de Facturas y Gastos en periodos cerrados
    """
    ESTADO_CHOICES = [
        ('ABIERTO', _('Abierto')),
        ('CERRADO', _('Cerrado')),
    ]
    
    # WARNING: v2.61: UUID para lookup público en API
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador único público para la API')
    )
    
    # WARNING: ENFORCED MODE v2.40: FK NO NULA a Empresa (SSoT)
    
    
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
    
    
    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Periodo Contable')
        verbose_name_plural = _('Periodos Contables')
        ordering = ['-periodo']
        unique_together = [['empresa', 'periodo']]
        indexes = SintelTenantBaseModel.Meta.indexes + [
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