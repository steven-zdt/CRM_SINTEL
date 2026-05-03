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

    v3.0: Integración centralizada — trazabilidad a documento origen + soporte reversales
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
        verbose_name=_('Número de Asiento'),
        help_text=_('Número único del asiento (auto-generado)')
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

    # v3.0: Trazabilidad a documento origen (idempotencia)
    documento_origen_app = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name=_('App de Origen'),
        help_text=_('App que generó el asiento: facturas, gastos, empleados, inventario')
    )
    documento_origen_modelo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Modelo de Origen'),
        help_text=_('Modelo que generó el asiento: Factura, DocumentoSoporte, Devengo')
    )
    documento_origen_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('ID del Documento Origen'),
        help_text=_('PK en la app de origen')
    )
    documento_origen_numero = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Número del Documento Origen'),
        help_text=_('Número visible del documento origen (factura, recibo, etc.)')
    )
    documento_origen_reversado = models.BooleanField(
        default=False,
        verbose_name=_('Es Reversal'),
        help_text=_('Indica si este asiento es reversal de otro')
    )
    asiento_reversado = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reversales',
        verbose_name=_('Asiento Reversado'),
        help_text=_('Asiento original que fue reversado por este')
    )
    periodo_contable = models.ForeignKey(
        'PeriodoContable',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='asientos',
        verbose_name=_('Periodo Contable'),
        help_text=_('Período contable al que pertenece el asiento')
    )

    # Totales (deben cuadrar: debe = haber) - WARNING: NORMATIVA: Partida Doble Estricta
    debe_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Débito')
    )
    haber_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Crédito')
    )

    # Legado: mantener compatibilidad
    total_debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Débito (legado)'),
        editable=False
    )
    total_haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Crédito (legado)'),
        editable=False
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
            models.Index(fields=['documento_origen_app', 'documento_origen_modelo', 'documento_origen_id']),  # v3.0: Idempotencia
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'documento_origen_app', 'documento_origen_modelo', 'documento_origen_id'],
                condition=models.Q(documento_origen_reversado=False),
                name='%(class)s_unique_documento_origen',
                violation_error_message=_('Ya existe asiento para este documento origen')
            )
        ]

    def __str__(self):
        return f"{self.numero} - {self.fecha}"

    def save(self, *args, **kwargs):
        """Sync debe_total/haber_total with new fields for compatibility."""
        self.total_debe = self.debe_total
        self.total_haber = self.haber_total
        super().save(*args, **kwargs)


class MovimientoContable(SintelTenantBaseModel):
    """
    Movimiento contable (partida de un asiento) (por tenant).

    Cada asiento tiene múltiples movimientos (partidas).

    v3.0: Integración centralizada — soporte para centro_costo_id + cuenta_codigo directo
    """
    asiento = models.ForeignKey(
        AsientoContable,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name=_('Asiento')
    )
    # v3.0: Direct cuenta_codigo lookup (para resolver cuentas sin FK)
    cuenta_codigo = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Código de Cuenta'),
        help_text=_('Código PUC de la cuenta (ej: 130505). Si se completa, se usa en lugar de FK.')
    )
    # Legado: FK a CuentaContable
    cuenta = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_('Cuenta Contable'),
        help_text=_('Cuenta contable (debe ser de nivel 6 según normativa). Legado si cuenta_codigo está presente.')
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
    # v3.0: Centro de costo para análisis por proyecto (sin FK — referencia desacoplada)
    centro_costo_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('ID del Centro de Costo'),
        help_text=_('ID del proyecto/centro de costo (sin FK — referencia desacoplada)')
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
            models.Index(fields=['cuenta_codigo']),  # v3.0: índice para resolución directa
            models.Index(fields=['tipo_tercero', 'tercero_id']),
            models.Index(fields=['tercero_nit']),
            models.Index(fields=['centro_costo_id']),  # v3.0: índice para reportes por proyecto
        ]

    def __str__(self):
        cuenta_str = self.cuenta_codigo or (self.cuenta.codigo if self.cuenta else '?')
        return f"{self.asiento.numero} - {cuenta_str} - {self.tercero_razon_social or 'Sin tercero'}"

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


# ============================================================================
# v3.0: INTEGRACIÓN CENTRALIZADA - Configuración Contable
# ============================================================================

class ReglaContable(SintelTenantBaseModel):
    """
    Regla de contabilización: mapea (tipo_transaccion + concepto) a cuenta PUC.

    Reemplaza el MAPEO_CUENTAS hardcoded. Permite customización por tenant.

    Ejemplo:
        tipo_transaccion='VENTA_FACTURA'
        concepto='INGRESO_PRINCIPAL'
        cuenta_codigo='413501'  # Ingresos por venta

    v3.0: Nueva en integración centralizada
    """
    tipo_transaccion = models.CharField(
        max_length=50,
        verbose_name=_('Tipo de Transacción'),
        help_text=_('Tipo de transacción (VENTA_FACTURA, COMPRA_GASTO, NOMINA_LIQUIDACION, etc.)')
    )
    concepto = models.CharField(
        max_length=50,
        verbose_name=_('Concepto Económico'),
        help_text=_('Concepto económico (INGRESO_PRINCIPAL, AUXILIO_TRANSPORTE, etc.)')
    )
    cuenta_codigo = models.CharField(
        max_length=20,
        verbose_name=_('Código de Cuenta PUC'),
        help_text=_('Código PUC de 6 dígitos (ej: 130505)')
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripción'),
        help_text=_('Descripción de la regla (para auditoría)')
    )
    activo = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Indica si esta regla es vigente')
    )

    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Regla Contable')
        verbose_name_plural = _('Reglas Contables')
        ordering = ['tipo_transaccion', 'concepto']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['tipo_transaccion', 'concepto', 'activo']),
            models.Index(fields=['cuenta_codigo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'tipo_transaccion', 'concepto'],
                condition=models.Q(activo=True),
                name='%(class)s_unique_tipo_concepto_activo',
                violation_error_message=_('Ya existe regla activa para este tipo + concepto')
            )
        ]

    def __str__(self):
        return f"{self.tipo_transaccion} + {self.concepto} → {self.cuenta_codigo}"


class TarifaImpuesto(SintelTenantBaseModel):
    """
    Tarifa de impuesto/deducción con vigencia por fecha y exoneración.

    Reemplaza tasas hardcodeadas (IVA 19%, Retefuente 2.5%, etc.)
    Permite cambios retrospectivos (ej: IVA subió de 19% a 21% en fecha X)

    Exoneración (exonerado=True) se aplica cuando:
    - El salario < base_minima_uvt * SMMLV_vigente (art. 114-1 ET para parafiscales)
    - El tercero está en lista de exonerados

    v3.0: Nueva en integración centralizada
    """
    TIPO_CHOICES = [
        ('IVA', _('IVA')),
        ('RETEFUENTE', _('Retención en la Fuente')),
        ('RETEICA', _('Retención ICA')),
        ('RETEIVA', _('Retención IVA')),
        ('SALUD_EMPLEADO', _('Aporte Salud Empleado')),
        ('PENSION_EMPLEADO', _('Aporte Pensión Empleado')),
        ('SALUD_PATRONAL', _('Aporte Salud Patronal')),
        ('PENSION_PATRONAL', _('Aporte Pensión Patronal')),
        ('ARL', _('Seguro ARL')),
        ('CAJA', _('Caja de Compensación')),
        ('ICBF', _('ICBF')),
        ('SENA', _('SENA')),
        ('CESANTIAS', _('Cesantías')),
        ('PRIMA_SERVICIOS', _('Prima de Servicios')),
        ('VACACIONES', _('Vacaciones')),
        ('INTERESES_CESANTIAS', _('Intereses sobre Cesantías')),
    ]

    tipo = models.CharField(
        max_length=50,
        choices=TIPO_CHOICES,
        verbose_name=_('Tipo de Impuesto/Deducción'),
        help_text=_('Clasificación del impuesto o deducción')
    )
    valor_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_('Valor %'),
        help_text=_('Tasa en porcentaje (ej: 19.00 para 19% IVA)')
    )
    fecha_inicio = models.DateField(
        verbose_name=_('Fecha Inicio Vigencia'),
        help_text=_('Desde cuándo rige esta tarifa')
    )
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Fecha Fin Vigencia'),
        help_text=_('Hasta cuándo rige. NULL = abierta (vigente indefinidamente)')
    )
    vigente = models.BooleanField(
        default=True,
        verbose_name=_('Vigente'),
        help_text=_('Indica si esta tarifa está activa')
    )
    exonerado = models.BooleanField(
        default=False,
        verbose_name=_('Puede ser Exonerado'),
        help_text=_('Si aplica art. 114-1 ET (parafiscales <10 SMMLV)')
    )
    base_minima_uvt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_('Base Mínima en UVT'),
        help_text=_('Umbral UVT para exoneración (ej: 10 para <10 SMMLV). 0 = no aplica exoneración.')
    )

    class Meta(SintelTenantBaseModel.Meta):
        verbose_name = _('Tarifa de Impuesto')
        verbose_name_plural = _('Tarifas de Impuesto')
        ordering = ['tipo', '-fecha_inicio']
        indexes = SintelTenantBaseModel.Meta.indexes + [
            models.Index(fields=['tipo', 'fecha_inicio', 'vigente']),
            models.Index(fields=['tipo', 'fecha_inicio', 'fecha_fin']),
        ]

    def __str__(self):
        fecha_str = f"{self.fecha_inicio}"
        if self.fecha_fin:
            fecha_str += f" — {self.fecha_fin}"
        else:
            fecha_str += " — ∞"
        return f"{self.tipo} {self.valor_porcentaje}% ({fecha_str})"

    @property
    def vigente_en(self, fecha):
        """Verifica si la tarifa está vigente en una fecha específica."""
        if not self.vigente:
            return False
        if fecha < self.fecha_inicio:
            return False
        if self.fecha_fin and fecha > self.fecha_fin:
            return False
        return True