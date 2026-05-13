"""
Modelos de empleados, contratos y nóminas (por tenant).

WARNING: v2.40: Arquitectura Tabulator Factory - Modelos Anemic (solo datos).

Principios:
- Cero Signals: Toda la lógica está en la capa de servicios (services.py)
- Tenant Isolation: Cada tenant tiene sus propios datos (django-tenants)
- Service Layer: Lógica de negocio en services.py (qs_empleados_list, gestionar_contrato_service, etc.)
- Annotations: Campos calculados (tiene_contrato_activo, tiene_nominas_registradas) en services.py
- LIST_FIELDS: Campos mínimos para Tabulator definidos en services.py
- SSoT: Empresa es la única FK externa (Single Source of Truth)

WARNING: FLUJO SECUENCIAL (Máquina de Estados):
1. Empleado (creación inicial)
2. Contrato (requiere Empleado, habilita botón "Registrar Nómina")
3. Devengo/Nómina (requiere Contrato ACTIVO, habilita botón "Historial")
"""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa

from .choices import AFP_CHOICES, ARL_CHOICES, EPS_CHOICES, RIESGO_ARL_CHOICES


class Empleado(SintelTenantBaseModel):
    """
    Modelo de empleado (v2.95: Flujo Secuencial).
    
    WARNING: ANEMIC MODEL: Solo define estructura de datos.
    - Lógica de negocio en services.py (qs_empleados_list, etc.)
    - Anotaciones para UI reactiva en services.py (tiene_contrato_activo, tiene_nominas_registradas)
    - LIST_FIELDS definido en services.py para optimización de queries
    
    WARNING: SSoT: Solo FK a Empresa (Single Source of Truth).
    WARNING: TENANT ISOLATION: django-tenants maneja aislamiento por esquema automáticamente.
    """
    TIPO_DOC = [('CC', 'Cédula de Ciudadanía'), ('CE', 'Cédula de Extranjería'), ('PA', 'Pasaporte'), ('PPT', 'PPT')]
    ESTADOS = [('ACTIVO', 'Activo'), ('RETIRADO', 'Retirado')]

    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # WARNING: SSoT: FK a Empresa (única FK externa)
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

    # Mapeo Contable (v3.5.0)
    cuenta_contable_uuid = models.UUIDField(
        null=True, 
        blank=True, 
        help_text="Cuenta PUC nivel 6 (Salarios/Prestaciones por pagar)"
    )

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

class Contrato(SintelTenantBaseModel):
    """
    Contrato de trabajo (v2.60: Máquina de Estados Estricta + SSoT).
    
    WARNING: FLUJO SECUENCIAL: Requiere Empleado, habilita creación de Nómina.
    WARNING: MÁQUINA DE ESTADOS: Solo UN contrato ACTIVO por empleado (garantizado en constraint).
    WARNING: VALIDACIÓN: Lógica de integridad en clean() (no es lógica de negocio).
    WARNING: SSoT: FK directa a Empresa (requerido v2.60).
    
    Estados:
    - ACTIVO: Contrato vigente, permite crear nóminas
    - INACTIVO: Contrato finalizado, no permite crear nóminas
    - HISTORICO: Contrato archivado (legacy)
    """
    TIPOS = [
        ('FIJO', 'Término Fijo'),
        ('INDEF', 'Indefinido'),
        ('OBRA', 'Obra o Labor'),
        ('PRESTACION', 'Prestación de Servicios')  # WARNING: Nuevo: Independiente
    ]
    ESTADOS = [('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo'), ('HISTORICO', 'Histórico')]
    
    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # WARNING: SSoT: FK directa a Empresa (requerido v2.60)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='contratos',
        help_text='SSoT Empresa'
    )

    # WARNING: FK a Empleado (sin limit_choices_to para permitir contratos históricos)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='contratos')
    
    # Tipo y fechas
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    
    # Valores económicos (WARNING: v2.95: Todos los valores en COP - Pesos Colombianos)
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
    
    # WARNING: MÁQUINA DE ESTADOS: estado es la fuente de verdad
    estado = models.CharField(
        max_length=12, 
        choices=ESTADOS, 
        default='ACTIVO', 
        help_text="Estado del contrato: ACTIVO, INACTIVO o HISTORICO"
    )
    # WARNING: LEGACY: Campo activo se sincroniza con estado en save()
    activo = models.BooleanField(
        default=True, 
        help_text="Campo legacy - usar estado='ACTIVO' en su lugar"
    )
    
    class Meta:
        verbose_name = _('Contrato')
        verbose_name_plural = _('Contratos')
        indexes = [
            models.Index(fields=['empresa', 'estado']),  # WARNING: v2.60: Índice SSoT
            models.Index(fields=['empleado', 'estado']),
            models.Index(fields=['empleado', 'activo']),
        ]
        constraints = [
            # WARNING: v2.60: Garantizar solo un contrato ACTIVO por empleado a nivel de DB
            models.UniqueConstraint(
                fields=['empleado'],
                condition=Q(estado='ACTIVO'),
                name='uniq_contrato_activo_per_empleado'
            )
        ]

    def clean(self):
        """Validación adicional para máquina de estados."""
        # Si el estado es NULL (datos existentes), establecer como INACTIVO
        if not self.estado:
            self.estado = 'INACTIVO'
            self.activo = False

    def __str__(self):
        return f"Contrato {self.tipo} - {self.empleado.nombre_completo}"

class Devengo(SintelTenantBaseModel):
    """
    Nómina/Pago de nómina (v2.60: Inmutable, vinculado a Contrato ACTIVO + SSoT).
    
    WARNING: FLUJO SECUENCIAL: Requiere Contrato ACTIVO, habilita botón "Historial".
    WARNING: INMUTABLE: Una vez creada, solo se puede anular (no editar).
    WARNING: SSoT: neto_pagar se calcula en service layer como fuente de verdad.
    WARNING: SSoT: FK directa a Empresa (requerido v2.60).
    WARNING: PROPORCIONAL: Valores calculados según días_laborados (1-30).
    
    Cálculo:
    - Devengos = salario_base + auxilio_transporte + otros_devengos
    - Deducciones = salud_empleado + pension_empleado + prestamos + descuentos_operativos
    - neto_pagar = Devengos - Deducciones (calculado en service layer)
    """
    # UUID Lookup Field (AGENTS.md §14)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # WARNING: SSoT: FK directa a Empresa (requerido v2.60)
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
    
    # WARNING: Días laborados para cálculo proporcional (0.5-30 días)
    # WARNING: v2.95: Permite decimales para soportar medio día (0.5) y cálculo por horas
    dias_laborados = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30, 
        validators=[MinValueValidator(Decimal('0.5'))], 
        help_text="Días laborados en el periodo (0.5-30, permite decimales para medio día)"
    )
    
    # WARNING: DEVENGOS (valores proporcionales calculados en COP)
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
    
    # WARNING: DEDUCCIONES (porcentajes legales + descuentos en COP)
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
    
    # WARNING: SSoT: neto_pagar se calcula en service layer (en COP)
    neto_pagar = models.DecimalField(max_digits=12, decimal_places=2, editable=False, help_text="Neto a pagar en COP")
    anulado = models.BooleanField(default=False, help_text="Nómina anulada (no se puede editar)")
    
    class Meta:
        verbose_name = _('Nómina')
        verbose_name_plural = _('Nóminas')
        indexes = [
            models.Index(fields=['empresa', 'fecha_pago']),  # WARNING: v2.60: Índice SSoT
            models.Index(fields=['empleado', 'fecha_pago']),
            models.Index(fields=['empleado', 'anulado']),
            models.Index(fields=['contrato']),
            models.Index(fields=['periodo_mes']),
        ]
        constraints = [
            # WARNING: v2.60: Nómina Multitanda - Permitir múltiples registros por mes
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
        # WARNING: v2.40: Máquina de Estados - Bloquear nómina si contrato no está ACTIVO
        if self.contrato.estado != 'ACTIVO' and not self.pk:
            raise ValidationError("No se puede generar nómina: El contrato no está activo.")
        # Compatibilidad: también validar campo activo legacy
        if not self.contrato.activo and not self.pk:
            raise ValidationError("No se puede generar nómina para un contrato inactivo.")

    def __str__(self):
        return f"Nómina {self.periodo_mes} | {self.empleado.nombre_completo}"