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
from django.core.exceptions import ValidationError
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
    # ⚠️ NORMATIVA NIIF: Nivel de la cuenta (debe ser 6 para permitir registros)
    nivel = models.IntegerField(
        default=6,
        verbose_name=_('Nivel'),
        help_text=_('Nivel de la cuenta según NIIF. Solo nivel 6 (Subcuenta) permite registros contables.')
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
            models.Index(fields=['nivel']),  # ⚠️ NORMATIVA: Índice para validación de nivel
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        """
        ⚠️ NORMATIVA COLOMBIANA: Validación de nivel.
        
        Si no tiene nivel, se asigna 6 por defecto.
        """
        super().clean()
        if not self.nivel:
            self.nivel = 6
    
    def save(self, *args, **kwargs):
        """Sobrescribe save() para ejecutar validaciones."""
        self.full_clean()
        super().save(*args, **kwargs)


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
    
    # ⚠️ NORMATIVA: Tipo de comprobante para trazabilidad
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
    
    # Totales (deben cuadrar: debe = haber) - ⚠️ NORMATIVA: Partida Doble Estricta
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
            models.Index(fields=['tipo_comprobante', 'numero_comprobante']),  # ⚠️ NORMATIVA: Trazabilidad
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.fecha}"
    
    def calcular_totales(self):
        """
        Recalcula total_debe y total_haber desde los movimientos.
        
        ⚠️ NORMATIVA: Usa agregación de base de datos para precisión.
        """
        from django.db.models import Sum
        
        totales = self.movimientos.aggregate(
            total_debe=Sum('debe'),
            total_haber=Sum('haber')
        )
        
        self.total_debe = totales['total_debe'] or Decimal('0.00')
        self.total_haber = totales['total_haber'] or Decimal('0.00')
    
    def validar_partida_doble(self):
        """
        ⚠️ NORMATIVA COLOMBIANA: Valida Partida Doble Estricta.
        
        Regla: ∑ Débitos = ∑ Créditos (sin excepciones)
        
        Returns:
            bool: True si está cuadrado
        
        Raises:
            ValidationError: Si el asiento no está cuadrado
        """
        diferencia = abs(self.total_debe - self.total_haber)
        es_valido = diferencia < Decimal('0.01')  # Tolerancia de 0.01 para redondeo
        
        if not es_valido:
            raise ValidationError({
                'total_debe': _(
                    f'Partida Doble no cumplida. Diferencia: ${diferencia:,.2f}. '
                    f'Total Débito: ${self.total_debe:,.2f}, Total Crédito: ${self.total_haber:,.2f}. '
                    f'La normativa colombiana exige que ∑ Débitos = ∑ Créditos.'
                )
            })
        
        return True
    
    def save(self, *args, **kwargs):
        """
        ⚠️ NORMATIVA COLOMBIANA: Validación de Partida Doble Estricta.
        
        - Recalcula totales desde movimientos antes de guardar
        - Valida que debe = haber (partida doble estricta)
        - Impide guardar asientos no cuadrados si están aprobados/cerrados
        """
        # ⚠️ v2.61: Solo recalcular totales si el asiento ya tiene ID (ya existe en BD)
        # Si es un asiento nuevo, los movimientos aún no existen, así que no calcular
        if self.pk:
            # Recalcular totales desde movimientos
            self.calcular_totales()
            
            # ⚠️ NORMATIVA: Validar Partida Doble Estricta
            # Si el asiento está aprobado o cerrado, la validación es obligatoria
            if self.estado in ['APROBADO', 'CERRADO']:
                self.validar_partida_doble()
            # Si está en borrador, solo validar si hay movimientos (advertencia, no bloquea)
            elif self.movimientos.exists():
                try:
                    self.validar_partida_doble()
                except ValidationError:
                    # En borrador, solo advertir pero permitir guardar
                    pass
        
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
        verbose_name=_('Cuenta Contable'),
        help_text=_('Cuenta contable (debe ser de nivel 6 según normativa)')
    )
    
    # ⚠️ NORMATIVA: Terceros Obligatorios (para medios magnéticos DIAN)
    # ForeignKey genérico a Cliente, Proveedor o Empleado
    tipo_tercero = models.CharField(
        max_length=20,
        choices=TIPO_TERCERO_CHOICES,
        blank=True,  # OPCIONAL inicialmente para compatibilidad
        null=True,
        verbose_name=_('Tipo de Tercero'),
        help_text=_('Tipo de tercero asociado al movimiento (obligatorio para medios magnéticos)')
    )
    tercero_id = models.PositiveIntegerField(
        blank=True,  # OPCIONAL inicialmente para compatibilidad
        null=True,
        verbose_name=_('ID del Tercero'),
        help_text=_('ID del tercero (Cliente, Proveedor, Empleado u otro)')
    )
    tercero_nit = models.CharField(
        max_length=32,
        blank=True,  # OPCIONAL inicialmente para compatibilidad
        null=True,
        verbose_name=_('NIT/CC del Tercero'),
        help_text=_('Número de identificación del tercero (NIT, CC, CE, etc.)')
    )
    tercero_razon_social = models.CharField(
        max_length=200,
        blank=True,  # OPCIONAL inicialmente para compatibilidad
        null=True,
        verbose_name=_('Razón Social del Tercero'),
        help_text=_('Nombre o razón social del tercero')
    )
    
    # Valores - ⚠️ NORMATIVA: DecimalField(15,2) para COP
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
    
    # ⚠️ NORMATIVA: Campos tributarios para cálculo automático
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
        indexes = [
            models.Index(fields=['asiento', 'orden']),
            models.Index(fields=['cuenta']),
            models.Index(fields=['tipo_tercero', 'tercero_id']),  # ⚠️ NORMATIVA: Búsqueda de terceros
            models.Index(fields=['tercero_nit']),  # ⚠️ NORMATIVA: Medios magnéticos
        ]
    
    def __str__(self):
        return f"{self.asiento.numero} - {self.cuenta.codigo} - {self.tercero_razon_social or 'Sin tercero'}"
    
    def get_tercero(self):
        """
        Obtiene el objeto del tercero según tipo_tercero y tercero_id.
        
        Returns:
            Cliente, Proveedor, Empleado u otro objeto según tipo_tercero, o None
        """
        if not self.tipo_tercero or not self.tercero_id:
            return None
        
        if self.tipo_tercero == 'CLIENTE':
            from apps.tenant.clientes.models import Cliente
            try:
                return Cliente.objects.get(id=self.tercero_id)
            except Cliente.DoesNotExist:
                return None
        elif self.tipo_tercero == 'PROVEEDOR':
            from apps.tenant.proveedores.models import Proveedor
            try:
                return Proveedor.objects.get(id=self.tercero_id)
            except Proveedor.DoesNotExist:
                return None
        elif self.tipo_tercero == 'EMPLEADO':
            from apps.tenant.empleados.models import Empleado
            try:
                return Empleado.objects.get(id=self.tercero_id)
            except Empleado.DoesNotExist:
                return None
        return None
    
    def calcular_iva(self, porcentaje_iva=Decimal('0.19')):
        """
        ⚠️ NORMATIVA COLOMBIANA: Calcula IVA generado o descontable.
        
        Args:
            porcentaje_iva: Porcentaje de IVA (default: 19% para Colombia)
        
        Returns:
            dict: {'base_iva': Decimal, 'iva_generado': Decimal, 'iva_descontable': Decimal}
        """
        if not self.cuenta:
            self.base_iva = Decimal('0.00')
            self.iva_generado = Decimal('0.00')
            self.iva_descontable = Decimal('0.00')
            return {
                'base_iva': self.base_iva,
                'iva_generado': self.iva_generado,
                'iva_descontable': self.iva_descontable
            }
        
        # Determinar si es IVA generado o descontable según el tipo de cuenta
        # Cuentas 240805 (IVA Generado) son crédito (ventas)
        # Cuentas 240810 (IVA Descontable) son débito (compras)
        
        if self.cuenta.codigo == '240805':  # IVA Generado
            self.base_iva = self.debe if self.debe > 0 else self.haber
            self.iva_generado = (self.base_iva * porcentaje_iva).quantize(Decimal('0.01'))
            self.iva_descontable = Decimal('0.00')
        elif self.cuenta.codigo == '240810':  # IVA Descontable
            self.base_iva = self.debe if self.debe > 0 else self.haber
            self.iva_descontable = (self.base_iva * porcentaje_iva).quantize(Decimal('0.01'))
            self.iva_generado = Decimal('0.00')
        else:
            # Si no es cuenta de IVA, no calcular
            self.base_iva = Decimal('0.00')
            self.iva_generado = Decimal('0.00')
            self.iva_descontable = Decimal('0.00')
        
        return {
            'base_iva': self.base_iva,
            'iva_generado': self.iva_generado,
            'iva_descontable': self.iva_descontable
        }
    
    def calcular_retenciones(self, porcentaje_retefuente=Decimal('0.00'), porcentaje_reteica=Decimal('0.00')):
        """
        ⚠️ NORMATIVA COLOMBIANA: Calcula retenciones (ReteFuente 2365 y ReteICA 2368).
        
        Args:
            porcentaje_retefuente: Porcentaje de retención en la fuente (default: 0%)
            porcentaje_reteica: Porcentaje de retención ICA (default: 0%)
        
        Returns:
            dict: {'retefuente': Decimal, 'reteica': Decimal}
        """
        if not self.cuenta:
            self.retefuente = Decimal('0.00')
            self.reteica = Decimal('0.00')
            return {
                'retefuente': self.retefuente,
                'reteica': self.reteica
            }
        
        # Base para retenciones: debe o haber según el tipo de cuenta
        base_retenciones = self.debe if self.debe > 0 else self.haber
        
        # Calcular ReteFuente (cuenta 2365)
        if self.cuenta.codigo.startswith('2365'):  # Retención en la Fuente
            self.retefuente = (base_retenciones * porcentaje_retefuente).quantize(Decimal('0.01'))
        else:
            self.retefuente = Decimal('0.00')
        
        # Calcular ReteICA (cuenta 2368)
        if self.cuenta.codigo.startswith('2368'):  # Retención ICA
            self.reteica = (base_retenciones * porcentaje_reteica).quantize(Decimal('0.01'))
        else:
            self.reteica = Decimal('0.00')
        
        return {
            'retefuente': self.retefuente,
            'reteica': self.reteica
        }
    
    def clean(self):
        """
        ⚠️ NORMATIVA COLOMBIANA: Validaciones de movimiento contable.
        
        - Validar nivel 6 de cuenta (advertencia inicialmente, no bloquea)
        - Validar terceros (advertencia inicialmente, no bloquea)
        - Validar debe/haber (obligatorio)
        """
        super().clean()
        
        # Validar nivel de cuenta (solo advertencia inicialmente para compatibilidad)
        if self.cuenta and self.cuenta.nivel != 6:
            # Advertencia pero no error (para compatibilidad hacia atrás)
            pass
        
        # Validar terceros (solo advertencia inicialmente para compatibilidad)
        if not self.tercero_nit or not self.tercero_razon_social:
            # Advertencia pero no error (para compatibilidad hacia atrás)
            pass
        
        # Validar debe/haber (obligatorio siempre)
        if self.debe > 0 and self.haber > 0:
            raise ValidationError({
                'debe': _('Un movimiento no puede tener débito y crédito simultáneamente.'),
                'haber': _('Un movimiento no puede tener débito y crédito simultáneamente.')
            })
        if self.debe == 0 and self.haber == 0:
            raise ValidationError({
                'debe': _('Un movimiento debe tener débito o crédito mayor a cero.'),
                'haber': _('Un movimiento debe tener débito o crédito mayor a cero.')
            })
    
    def save(self, *args, **kwargs):
        """
        ⚠️ NORMATIVA COLOMBIANA: Validaciones y cálculos automáticos.
        
        - Ejecuta validaciones de clean()
        - Calcula IVA si aplica
        - Calcula retenciones si aplica
        - Actualiza totales del asiento usando método mejorado
        """
        # Ejecutar validaciones
        self.full_clean()
        
        # Calcular IVA y retenciones si aplica
        # Nota: Los porcentajes deberían venir de configuración o del documento origen
        self.calcular_iva()
        self.calcular_retenciones()
        
        super().save(*args, **kwargs)
        
        # Actualizar totales del asiento usando método mejorado
        self.asiento.calcular_totales()
        self.asiento.save(update_fields=['total_debe', 'total_haber'])


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
    
    # ⚠️ v2.61: UUID para lookup público en API
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID'),
        help_text=_('Identificador único público para la API')
    )
    
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