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
import datetime
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel
from apps.tenant.empresa.models import Empresa

from .choices import AFP_CHOICES, ARL_CHOICES, EPS_CHOICES, MOTIVO_RETIRO_CHOICES, RIESGO_ARL_CHOICES


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
    
    # Foto de perfil
    foto = models.ImageField(
        _('Foto'),
        upload_to='empleados/fotos/',
        null=True,
        blank=True,
        help_text=_('Foto de perfil del empleado (opcional)')
    )

    # Estado y fechas
    estado = models.CharField(max_length=12, choices=ESTADOS, default='ACTIVO')
    fecha_ingreso = models.DateField()
    fecha_retiro = models.DateField(null=True, blank=True)
    # mision auditoria nomina FASE 21/22 (2026-09-10): catalogo controlado de
    # causal de retiro -- requerido por EmpleadoBusinessService.retirar_empleado()
    # al transicionar ACTIVO->RETIRADO. Determina si aplica indemnizacion por
    # despido sin justa causa (CST art. 64).
    motivo_retiro = models.CharField(
        max_length=30, choices=MOTIVO_RETIRO_CHOICES, null=True, blank=True,
        verbose_name=_('Motivo de Retiro'),
    )

    # Sede y Area (FASE 1: Capa de Datos)
    sede = models.ForeignKey(
        'empresa.Sede',
        on_delete=models.SET_NULL,
        related_name='empleados',
        null=True,
        blank=True,
        verbose_name=_('Sede'),
    )
    area = models.ForeignKey(
        'empresa.Area',
        on_delete=models.SET_NULL,
        related_name='empleados',
        null=True,
        blank=True,
        verbose_name=_('Area'),
    )

    # Resolución DIAN para nómina electrónica (DSPNE)
    # SET_NULL para no bloquear eliminación de resoluciones históricas
    resolucion_dian = models.ForeignKey(
        'ResolucionDIAN',
        on_delete=models.SET_NULL,
        related_name='empleados_asignados',
        null=True,
        blank=True,
        verbose_name=_('Resolución DIAN Nómina Electrónica'),
        help_text=_('Resolución DIAN asignada para generar documentos de nómina electrónica (DSPNE).'),
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
        ('PRESTACION', 'Prestación de Servicios')
    ]
    ESTADOS = [('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo'), ('HISTORICO', 'Histórico')]
    HORAS_SEMANALES_CHOICES = [
        (36, '36 h/semana'),
        (40, '40 h/semana'),
        (42, '42 h/semana — Estándar Colombia 2026 (Ley 2101/2021)'),
        (44, '44 h/semana'),
        (48, '48 h/semana'),
    ]
    
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
    
    # Jornada laboral (Ley 2101/2021 — reduccion progresiva, 42h en 2026)
    horas_semanales = models.PositiveSmallIntegerField(
        default=42,
        choices=HORAS_SEMANALES_CHOICES,
        help_text="Horas laborales semanales pactadas. Referencia para calculo de H.E. y recargos."
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
    periodo_mes  = models.CharField(max_length=7, help_text="Formato: YYYY-MM")
    fecha_inicio = models.DateField(null=True, blank=True, help_text="Primer dia del periodo laborado")
    fecha_fin    = models.DateField(null=True, blank=True, help_text="Ultimo dia del periodo laborado")
    fecha_pago   = models.DateField()
    
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

    # Horas extras y recargos (Decreto 2663/1950 - normativa vigente Colombia)
    horas_extras_diurnas   = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="H.E. diurnas Lun-Sab 6am-9pm (+25%)")
    horas_extras_nocturnas = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="H.E. nocturnas 9pm-6am (+75%)")
    recargo_nocturno_horas = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Horas nocturnas ordinarias (+35%)")
    recargo_festivo_horas  = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Horas dominicales/festivas (+75%)")
    valor_horas_extras     = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False, help_text="Valor calculado de H.E. y recargos en COP")

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

    # WARNING: mision Access Context nomina 2026-08-21 -- FK opcional al periodo de
    # nomina que orquesto su creacion en lote (ver PeriodoNomina abajo). Nullable:
    # los Devengo historicos anteriores a esta migracion no pertenecen a ningun
    # periodo, y procesar_devengo() sigue funcionando igual sin periodo (creacion
    # individual). Devengo NO se convierte en periodo/lote -- sigue siendo la
    # entidad de calculo individual e inmutable; PeriodoNomina es el contenedor.
    periodo = models.ForeignKey(
        'PeriodoNomina',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='devengos',
        help_text='Periodo de nomina al que pertenece (nullable por compatibilidad historica)',
    )

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


class ResolucionDIAN(SintelTenantBaseModel):
    """
    Resolucion DIAN para Nomina Electronica.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='resoluciones_dian_empleados')

    numero_resolucion = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='Numero Resolucion DIAN'
    )
    rango_desde = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Rango Desde'
    )
    rango_hasta = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Rango Hasta'
    )
    fecha_resolucion = models.DateField(
        verbose_name='Fecha de Emision',
        help_text='Fecha en la que la DIAN emitio la resolucion'
    )
    fecha_inicio = models.DateField(
        verbose_name='Fecha Inicio Aplicacion',
        help_text='Fecha desde la cual se empezara a usar en el sistema',
        default=datetime.date.today
    )
    fecha_fin = models.DateField(
        verbose_name='Fecha Final Aplicacion',
        help_text='Fecha de vencimiento de la resolucion'
    )
    clave_tecnica = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    vigente = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Vigente (Prestablecida)',
        help_text='Solo una resolucion puede estar vigente para ser usada por defecto.'
    )
    prefijo = models.CharField(max_length=10, verbose_name='Prefijo')
    consecutivo = models.IntegerField(
        db_index=True,
        editable=False,
        verbose_name='Siguiente Consecutivo',
        default=1,
        help_text='Se inicializa automaticamente desde rango_desde al crear la resolucion.'
    )

    def formar_consecutivo(self, numero):
        """Une prefijo y numero para formar el identificador del documento."""
        return f"{self.prefijo}-{numero}"

    class Meta:
        verbose_name = 'Resolucion DIAN'
        verbose_name_plural = 'Resoluciones DIAN'
        ordering = ['-vigente', '-fecha_resolucion']
        indexes = [
            models.Index(fields=['empresa', 'vigente']),
        ]

    def save(self, *args, **kwargs):
        # Al crear, inicializar consecutivo en rango_desde para que los numeros
        # de documento queden dentro del rango autorizado por la DIAN.
        if not self.pk and (self.consecutivo is None or self.consecutivo < self.rango_desde):
            self.consecutivo = self.rango_desde
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
                if parsed:
                    fecha_referencia = parsed
                else:
                    return False
            except Exception:
                return False
        return self.fecha_inicio <= fecha_referencia <= self.fecha_fin


class TransmisionNominaDIAN(SintelTenantBaseModel):
    """
    Transmision de Nomina Electronica a la DIAN.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('ACEPTADO', 'Aceptado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='transmisiones_nomina')

    devengo = models.OneToOneField(Devengo, on_delete=models.CASCADE, related_name='transmision')
    resolucion = models.ForeignKey(ResolucionDIAN, on_delete=models.PROTECT, related_name='transmisiones')

    numero_documento = models.CharField(max_length=64, db_index=True)
    cune = models.CharField(max_length=128, db_index=True, blank=True, null=True)
    estado_dian = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')

    xml_enviado = models.TextField(blank=True, null=True)
    xml_respuesta = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Transmision Nomina DIAN'
        verbose_name_plural = 'Transmisiones Nomina DIAN'


class LiquidacionPrestacion(SintelTenantBaseModel):
    """
    Liquidacion de prestaciones sociales (Primas, Cesantias, Vacaciones, Liquidacion Definitiva).
    """
    TIPOS = [
        ('PRIMA_SERVICIOS', 'Prima de Servicios'),
        ('CESANTIAS', 'Cesantias'),
        ('VACACIONES', 'Vacaciones'),
        ('LIQUIDACION_DEFINITIVA', 'Liquidacion Definitiva'),
    ]
    ESTADOS = [
        ('PROYECTADO', 'Proyectado'),
        ('PAGADO', 'Pagado'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='liquidaciones_prestaciones')

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='liquidaciones')
    contrato = models.ForeignKey(Contrato, on_delete=models.PROTECT, related_name='liquidaciones')

    tipo_liquidacion = models.CharField(max_length=30, choices=TIPOS)
    fecha_corte = models.DateField()
    dias_base_calculo = models.IntegerField()
    base_salarial = models.DecimalField(max_digits=14, decimal_places=2)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROYECTADO')
    desglose_conceptos = models.JSONField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Liquidacion de Prestacion'
        verbose_name_plural = 'Liquidaciones de Prestaciones'
        indexes = [
            models.Index(fields=['empresa', 'empleado']),
        ]


class PeriodoNomina(SintelTenantBaseModel):
    """
    Periodo de nomina: agrupa los Devengo de todos los empleados de un mismo
    ciclo de pago y orquesta su flujo de aprobacion en lote.

    WARNING [mision nomina 2026-08-21, docs/nomina/NOMINA_BASELINE.md]: NO
    reemplaza a Devengo. Devengo sigue siendo la entidad de calculo
    individual, inmutable (update/partial_update -> 405). PeriodoNomina es
    el CONTENEDOR/PROCESO que orquesta la creacion en lote (llamando al
    mismo procesar_devengo() ya existente, una vez por empleado elegible) y
    el flujo de aprobacion sobre ese conjunto de Devengo -- nunca calcula ni
    persiste montos por si mismo.

    Maquina de estados (ver docs/nomina/NOMINA_FLUJO_EMPRESARIAL.md para el
    detalle completo de cada transicion):

        ABIERTO -> PRELIQUIDADO -> EN_REVISION -> APROBADO -> PAGADO -> CERRADO

    Excepciones: ANULADO (desde cualquier estado antes de PAGADO -- anula en
    cascada los Devengo del periodo), BLOQUEADO (pausa reversible, no
    transiciona automaticamente a ningun otro estado).

    WARNING: Pago -- no existe integracion real con Bancos para nomina hoy
    (ver NOMINA_BASELINE.md §2/§4). fecha_pago_real/pagado_por son un
    registro MANUAL minimo, no una integracion automatica -- documentado
    como gap conocido, no fabricado como si ya existiera.
    """
    ESTADOS = [
        ('ABIERTO', 'Abierto'),
        ('PRELIQUIDADO', 'Preliquidado'),
        ('EN_REVISION', 'En revisión'),
        ('APROBADO', 'Aprobado'),
        ('PAGADO', 'Pagado'),
        ('CERRADO', 'Cerrado'),
        ('ANULADO', 'Anulado'),
        ('BLOQUEADO', 'Bloqueado'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='periodos_nomina')

    periodo_mes = models.CharField(max_length=7, help_text="Formato: YYYY-MM")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_pago = models.DateField(help_text="Fecha de pago planeada para el periodo")

    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABIERTO', db_index=True)

    # WARNING: FK a perfil.TenantProfile (nunca directo al modelo de usuario global, AGENTS.md).
    # SET_NULL: conserva el registro historico del periodo aunque el perfil que
    # lo creo/aprobo/pago sea eliminado despues -- se pierde la atribucion
    # puntual, no el periodo en si (decision documentada, no verificada con
    # normativa contable real -- ver NOMINA_BASELINE.md bloqueador #2).
    creado_por = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodos_nomina_creados',
    )
    aprobado_por = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodos_nomina_aprobados',
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    fecha_pago_real = models.DateField(null=True, blank=True, help_text="Fecha en que se marcó como pagado (registro manual)")
    pagado_por = models.ForeignKey(
        'perfil.TenantProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='periodos_nomina_pagados',
    )

    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Periodo de Nómina'
        verbose_name_plural = 'Periodos de Nómina'
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['periodo_mes']),
        ]
        constraints = [
            # Un solo periodo "vivo" por empresa+mes -- permite recrear el
            # periodo del mismo mes si el anterior fue ANULADO.
            models.UniqueConstraint(
                fields=['empresa', 'periodo_mes'],
                condition=~Q(estado='ANULADO'),
                name='uniq_periodo_nomina_activo_per_empresa_mes',
            )
        ]

    def __str__(self):
        return f"Período {self.periodo_mes} ({self.get_estado_display()})"