"""
Modelos de empleados, contratos y nóminas (por tenant).

⚠️ v2.40: Arquitectura Tabulator Factory - Modelos Anemic (solo datos).

Principios:
- Cero Signals: Toda la lógica está en la capa de servicios (services.py)
- Tenant Isolation: Cada tenant tiene sus propios datos (django-tenants)
- Service Layer: Lógica de negocio en services.py (qs_empleados_list, gestionar_contrato_service, etc.)
- Annotations: Campos calculados (tiene_contrato_activo, tiene_nominas_registradas) en services.py
- LIST_FIELDS: Campos mínimos para Tabulator definidos en services.py
- SSoT: Empresa es la única FK externa (Single Source of Truth)

⚠️ FLUJO SECUENCIAL (Máquina de Estados):
1. Empleado (creación inicial)
2. Contrato (requiere Empleado, habilita botón "Registrar Nómina")
3. Devengo/Nómina (requiere Contrato ACTIVO, habilita botón "Historial")
"""
from django.db import models, transaction
from django.db.models import Q
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.tenant.empresa.models import Empresa
from decimal import Decimal
from .choices import EPS_CHOICES, AFP_CHOICES, ARL_CHOICES, RIESGO_ARL_CHOICES


class Empleado(models.Model):
    """
    Modelo de empleado (v2.95: Flujo Secuencial).
    
    ⚠️ ANEMIC MODEL: Solo define estructura de datos.
    - Lógica de negocio en services.py (qs_empleados_list, etc.)
    - Anotaciones para UI reactiva en services.py (tiene_contrato_activo, tiene_nominas_registradas)
    - LIST_FIELDS definido en services.py para optimización de queries
    
    ⚠️ SSoT: Solo FK a Empresa (Single Source of Truth).
    ⚠️ TENANT ISOLATION: django-tenants maneja aislamiento por esquema automáticamente.
    """
    TIPO_DOC = [('CC', 'Cédula de Ciudadanía'), ('CE', 'Cédula de Extranjería'), ('PA', 'Pasaporte'), ('PPT', 'PPT')]
    ESTADOS = [('ACTIVO', 'Activo'), ('RETIRADO', 'Retirado')]

    # ⚠️ SSoT: FK a Empresa (única FK externa)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='empleados')
    
    # Identificación y Datos Personales
    tipo_documento = models.CharField(max_length=5, choices=TIPO_DOC)
    numero_documento = models.CharField(max_length=32, db_index=True)
    primer_nombre = models.CharField(max_length=80)
    segundo_nombre = models.CharField(max_length=80, blank=True)
    primer_apellido = models.CharField(max_length=80)
    segundo_apellido = models.CharField(max_length=80, blank=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=32, blank=True)
    
    # Seguridad Social (Campos v2.95)
    eps = models.CharField(max_length=10, choices=EPS_CHOICES, verbose_name=_('EPS'))
    afp = models.CharField(max_length=10, choices=AFP_CHOICES, verbose_name=_('Fondo de Pensión'))
    arl = models.CharField(max_length=10, choices=ARL_CHOICES, verbose_name=_('ARL Contratada'))
    nivel_riesgo_arl = models.CharField(max_length=5, choices=RIESGO_ARL_CHOICES, default='I')
    
    # Estado y fechas
    estado = models.CharField(max_length=12, choices=ESTADOS, default='ACTIVO')
    fecha_ingreso = models.DateField()
    fecha_retiro = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _('Empleado')
        verbose_name_plural = _('Empleados')
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'tipo_documento', 'numero_documento'], 
                name='uniq_empleado_per_tenant'
            )
        ]
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['numero_documento']),
        ]

    @property
    def nombre_completo(self):
        return f"{self.primer_nombre} {self.primer_apellido}"

    def __str__(self):
        return f"{self.nombre_completo} ({self.numero_documento})"

class Contrato(models.Model):
    """
    Contrato de trabajo (v2.60: Máquina de Estados Estricta + SSoT).
    
    ⚠️ FLUJO SECUENCIAL: Requiere Empleado, habilita creación de Nómina.
    ⚠️ MÁQUINA DE ESTADOS: Solo UN contrato ACTIVO por empleado (garantizado en constraint).
    ⚠️ VALIDACIÓN: Lógica de integridad en save() y clean() (no es lógica de negocio).
    ⚠️ SSoT: FK directa a Empresa (requerido v2.60).
    
    Estados:
    - ACTIVO: Contrato vigente, permite crear nóminas
    - INACTIVO: Contrato finalizado, no permite crear nóminas
    - HISTORICO: Contrato archivado (legacy)
    """
    TIPOS = [
        ('FIJO', 'Término Fijo'),
        ('INDEF', 'Indefinido'),
        ('OBRA', 'Obra o Labor'),
        ('PRESTACION', 'Prestación de Servicios')  # ⚠️ Nuevo: Independiente
    ]
    ESTADOS = [('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo'), ('HISTORICO', 'Histórico')]
    
    # ⚠️ SSoT: FK directa a Empresa (requerido v2.60)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT, 
        related_name='contratos',
        help_text='SSoT Empresa'
    )
    
    # ⚠️ FK a Empleado (sin limit_choices_to para permitir contratos históricos)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='contratos')
    
    # Tipo y fechas
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    
    # Valores económicos (⚠️ v2.95: Todos los valores en COP - Pesos Colombianos)
    salario_mensual = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Salario mensual en COP (Pesos Colombianos)"
    )
    auxilio_transporte = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Auxilio de transporte mensual pactado en COP"
    )
    prestamos_empresa = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Préstamos o deudas que la empresa tiene con el empleado en COP (puede ser 0)"
    )
    
    # Información adicional
    cargo = models.CharField(max_length=120)
    archivo_pdf = models.FileField(
        upload_to='empleados/contratos/', 
        null=True, 
        blank=True, 
        help_text="Copia digital del contrato firmado (PDF)"
    )
    
    # ⚠️ MÁQUINA DE ESTADOS: estado es la fuente de verdad
    estado = models.CharField(
        max_length=12, 
        choices=ESTADOS, 
        default='ACTIVO', 
        help_text="Estado del contrato: ACTIVO, INACTIVO o HISTORICO"
    )
    # ⚠️ LEGACY: Campo activo se sincroniza con estado en save()
    activo = models.BooleanField(
        default=True, 
        help_text="Campo legacy - usar estado='ACTIVO' en su lugar"
    )
    
    class Meta:
        verbose_name = _('Contrato')
        verbose_name_plural = _('Contratos')
        indexes = [
            models.Index(fields=['empresa', 'estado']),  # ⚠️ v2.60: Índice SSoT
            models.Index(fields=['empleado', 'estado']),
            models.Index(fields=['empleado', 'activo']),
        ]
        constraints = [
            # ⚠️ v2.60: Garantizar solo un contrato ACTIVO por empleado a nivel de DB
            models.UniqueConstraint(
                fields=['empleado'],
                condition=Q(estado='ACTIVO'),
                name='uniq_contrato_activo_per_empleado'
            )
        ]

    @transaction.atomic
    def save(self, *args, **kwargs):
        # ⚠️ v2.60: SSoT - Sincronizar empresa desde empleado si no está establecida
        if not self.empresa_id and self.empleado_id:
            if hasattr(self.empleado, 'empresa_id'):
                self.empresa_id = self.empleado.empresa_id
        
        # ⚠️ v2.40: Sincronizar activo con estado para compatibilidad
        self.activo = (self.estado == 'ACTIVO')
        
        # ⚠️ v2.40: Máquina de Estados Estricta - Solo UN contrato ACTIVO por empleado
        # ⚠️ NOTA: El constraint UniqueConstraint garantiza esto a nivel de DB, pero mantenemos
        # la lógica aquí para desactivar contratos previos antes de que el constraint falle
        if self.estado == 'ACTIVO':
            # Desactivar contratos previos del mismo empleado para mantener unicidad
            Contrato.objects.filter(
                empleado=self.empleado, 
                estado='ACTIVO'
            ).exclude(pk=self.pk).update(estado='INACTIVO', activo=False)
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validación adicional para máquina de estados."""
        # Si el estado es NULL (datos existentes), establecer como INACTIVO
        if not self.estado:
            self.estado = 'INACTIVO'
            self.activo = False

    def __str__(self):
        return f"Contrato {self.tipo} - {self.empleado.nombre_completo}"

class Devengo(models.Model):
    """
    Nómina/Pago de nómina (v2.60: Inmutable, vinculado a Contrato ACTIVO + SSoT).
    
    ⚠️ FLUJO SECUENCIAL: Requiere Contrato ACTIVO, habilita botón "Historial".
    ⚠️ INMUTABLE: Una vez creada, solo se puede anular (no editar).
    ⚠️ SSoT: neto_pagar se calcula en save() como fuente de verdad.
    ⚠️ SSoT: FK directa a Empresa (requerido v2.60).
    ⚠️ PROPORCIONAL: Valores calculados según días_laborados (1-30).
    
    Cálculo:
    - Devengos = salario_base + auxilio_transporte + otros_devengos
    - Deducciones = salud_empleado + pension_empleado + prestamos + descuentos_operativos
    - neto_pagar = Devengos - Deducciones (calculado en save())
    """
    # ⚠️ SSoT: FK directa a Empresa (requerido v2.60)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.PROTECT, 
        related_name='nominas',
        help_text='SSoT Empresa'
    )
    
    # FKs
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="nominas")
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name="pagos_nomina")
    
    # Periodo y fecha
    periodo_mes = models.CharField(max_length=7, help_text="Formato: YYYY-MM")
    fecha_pago = models.DateField()
    
    # ⚠️ Días laborados para cálculo proporcional (0.5-30 días)
    # ⚠️ v2.95: Permite decimales para soportar medio día (0.5) y cálculo por horas
    dias_laborados = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30, 
        validators=[MinValueValidator(Decimal('0.5'))], 
        help_text="Días laborados en el periodo (0.5-30, permite decimales para medio día)"
    )
    
    # ⚠️ DEVENGOS (valores proporcionales calculados en COP)
    salario_base = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        help_text="Salario base proporcional calculado en COP (según días laborados)"
    )
    auxilio_transporte = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Auxilio de transporte proporcional calculado en COP"
    )
    otros_devengos = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Otros devengos adicionales del periodo en COP (valor fijo, no proporcional)"
    )
    
    # ⚠️ DEDUCCIONES (porcentajes legales + descuentos en COP)
    salud_empleado = models.DecimalField(max_digits=12, decimal_places=2, help_text="4% Ley - Deducción en COP")
    pension_empleado = models.DecimalField(max_digits=12, decimal_places=2, help_text="4% Ley - Deducción en COP")
    # otro descuento que se pueda agregar
    prestamos = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Préstamos descontados en COP")
    descuentos_operativos = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Descuentos operativos varios en COP"
    )
    
    # Información adicional
    observaciones = models.TextField(blank=True, help_text="Observaciones sobre la nómina")
    
    # ⚠️ SSoT: neto_pagar se calcula automáticamente en save() (en COP)
    neto_pagar = models.DecimalField(max_digits=12, decimal_places=2, editable=False, help_text="Neto a pagar en COP")
    anulado = models.BooleanField(default=False, help_text="Nómina anulada (no se puede editar)")
    
    class Meta:
        verbose_name = _('Nómina')
        verbose_name_plural = _('Nóminas')
        indexes = [
            models.Index(fields=['empresa', 'fecha_pago']),  # ⚠️ v2.60: Índice SSoT
            models.Index(fields=['empleado', 'fecha_pago']),
            models.Index(fields=['empleado', 'anulado']),
            models.Index(fields=['contrato']),
            models.Index(fields=['periodo_mes']),
        ]
        constraints = [
            # ⚠️ v2.60: Nómina Multitanda - Permitir múltiples registros por mes
            # Unicidad basada en empleado + periodo_mes + fecha_pago (permite semanas/quincenas)
            models.UniqueConstraint(
                fields=['empleado', 'periodo_mes', 'fecha_pago'],
                condition=Q(anulado=False),
                name='uniq_nomina_per_empleado_periodo_fecha'
            )
        ]

    def clean(self):
        # Validar que el contrato pertenezca al empleado y esté activo
        if self.contrato.empleado != self.empleado:
            raise ValidationError("El contrato seleccionado no pertenece al empleado.")
        # ⚠️ v2.40: Máquina de Estados - Bloquear nómina si contrato no está ACTIVO
        if self.contrato.estado != 'ACTIVO' and not self.pk:
            raise ValidationError("No se puede generar nómina: El contrato no está activo.")
        # Compatibilidad: también validar campo activo legacy
        if not self.contrato.activo and not self.pk:
            raise ValidationError("No se puede generar nómina para un contrato inactivo.")

    def save(self, *args, **kwargs):
        # ⚠️ v2.60: SSoT - Sincronizar empresa desde empleado si no está establecida
        if not self.empresa_id and self.empleado_id:
            if hasattr(self.empleado, 'empresa_id'):
                self.empresa_id = self.empleado.empresa_id
        
        self.full_clean()
        
        # ⚠️ v2.40: Validar días laborados (1-30)
        if self.dias_laborados < 1:
            self.dias_laborados = 1
        elif self.dias_laborados > 30:
            self.dias_laborados = 30
        
        # ⚠️ v2.40: El frontend envía valores calculados desde el endpoint de previsualización
        # El service layer se usa solo en el endpoint de previsualización, no en el modelo
        # El modelo solo valida y recalcula neto_pagar como SSoT
        
        # ⚠️ v2.40: Siempre recalcular neto_pagar con los valores actuales (SSoT)
        from decimal import Decimal
        devengos = (self.salario_base or Decimal('0')) + (self.auxilio_transporte or Decimal('0')) + (self.otros_devengos or Decimal('0'))
        deducciones = (self.salud_empleado or Decimal('0')) + (self.pension_empleado or Decimal('0')) + (self.prestamos or Decimal('0')) + (self.descuentos_operativos or Decimal('0'))
        self.neto_pagar = devengos - deducciones
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Nómina {self.periodo_mes} | {self.empleado.nombre_completo}"