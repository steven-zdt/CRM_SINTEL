"""
Modelos para el catálogo de impuestos de la DIAN (Colombia).
Esta biblioteca legal está disponible para todos los tenants en el esquema public.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class TipoImpuesto(models.Model):
    """
    Tipos de impuestos según la DIAN (IVA, Retención, etc.)
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Código único del tipo de impuesto'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_vigencia = models.DateField(
        verbose_name='Fecha de Vigencia'
    )
    fecha_fin_vigencia = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha Fin de Vigencia'
    )

    class Meta:
        verbose_name = 'Tipo de Impuesto'
        verbose_name_plural = 'Tipos de Impuestos'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class TarifaIVA(models.Model):
    """
    Tarifas de IVA según la normativa DIAN.
    """
    TIPO_TARIFA_CHOICES = [
        ('general', 'General'),
        ('reducida', 'Reducida'),
        ('excluido', 'Excluido'),
        ('exento', 'Exento'),
    ]

    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Código de la tarifa según DIAN'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje (%)',
        help_text='Porcentaje de IVA (ej: 19.00 para 19%)'
    )
    tipo_tarifa = models.CharField(
        max_length=20,
        choices=TIPO_TARIFA_CHOICES,
        default='general',
        verbose_name='Tipo de Tarifa'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_vigencia = models.DateField(
        verbose_name='Fecha de Vigencia'
    )
    fecha_fin_vigencia = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha Fin de Vigencia'
    )

    class Meta:
        verbose_name = 'Tarifa de IVA'
        verbose_name_plural = 'Tarifas de IVA'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.porcentaje}%)"


class ConceptoRetencion(models.Model):
    """
    Conceptos de retención según la DIAN (ICA, IVA, Renta, etc.)
    """
    TIPO_RETENCION_CHOICES = [
        ('ica', 'ICA - Impuesto de Industria y Comercio'),
        ('iva', 'IVA - Impuesto al Valor Agregado'),
        ('renta', 'Renta'),
        ('cree', 'CREE - Impuesto sobre la Renta para la Equidad'),
        ('otro', 'Otro'),
    ]

    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Código del concepto según DIAN'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre'
    )
    tipo_retencion = models.CharField(
        max_length=20,
        choices=TIPO_RETENCION_CHOICES,
        verbose_name='Tipo de Retención'
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True,
        null=True,
        verbose_name='Porcentaje (%)',
        help_text='Porcentaje de retención (puede variar según actividad)'
    )
    base_minima = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Base Mínima',
        help_text='Valor mínimo sobre el cual se aplica la retención'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_vigencia = models.DateField(
        verbose_name='Fecha de Vigencia'
    )
    fecha_fin_vigencia = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha Fin de Vigencia'
    )

    class Meta:
        verbose_name = 'Concepto de Retención'
        verbose_name_plural = 'Conceptos de Retención'
        ordering = ['tipo_retencion', 'codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.get_tipo_retencion_display()})"


class CodigoTributario(models.Model):
    """
    Códigos tributarios según la DIAN (Responsabilidades, Regímenes, etc.)
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Código tributario según DIAN'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre'
    )
    tipo = models.CharField(
        max_length=50,
        verbose_name='Tipo',
        help_text='Tipo de código (Responsabilidad, Régimen, etc.)'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_vigencia = models.DateField(
        verbose_name='Fecha de Vigencia'
    )
    fecha_fin_vigencia = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha Fin de Vigencia'
    )

    class Meta:
        verbose_name = 'Código Tributario'
        verbose_name_plural = 'Códigos Tributarios'
        ordering = ['tipo', 'codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ActividadEconomica(models.Model):
    """
    Actividades económicas según CIIU (Clasificación Industrial Internacional Uniforme).
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código CIIU',
        help_text='Código de la actividad económica'
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    class Meta:
        verbose_name = 'Actividad Económica'
        verbose_name_plural = 'Actividades Económicas'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class DocumentoFuente(models.Model):
    """
    Documento fuente para ingesta de información tributaria.
    
    Permite recibir documentos desde archivo o URL para procesamiento posterior.
    """
    TIPO = (
        ("PDF", "PDF"),
        ("HTML", "HTML"),
        ("XML", "XML"),
        ("XLS", "XLS/XLSX"),
        ("CSV", "CSV"),
        ("OTRO", "OTRO"),
    )
    ESTADO = (
        ("RECIBIDO", "RECIBIDO"),
        ("EN_PROCESO", "EN_PROCESO"),
        ("PROCESADO", "PROCESADO"),
        ("ERROR", "ERROR"),
    )
    
    archivo = models.FileField(
        upload_to="impuestos/ingesta/%Y/%m/%d",
        null=True,
        blank=True,
        verbose_name="Archivo",
        help_text="Archivo subido para procesamiento"
    )
    url_origen = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL Origen",
        help_text="URL del documento a descargar"
    )
    fuente = models.CharField(
        max_length=100,
        verbose_name="Fuente",
        help_text="Fuente del documento (DIAN/DOF/SUIN/DiarioOficial/...)"
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO,
        default="OTRO",
        db_index=True,
        verbose_name="Tipo"
    )
    # Metadatos del archivo
    content_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Content Type",
        help_text="Tipo MIME del archivo"
    )
    extension = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="Extensión",
        help_text="Extensión del archivo (ej: .pdf, .xlsx)"
    )
    size_bytes = models.BigIntegerField(
        default=0,
        verbose_name="Tamaño (bytes)",
        help_text="Tamaño del archivo en bytes"
    )
    hash_sha256 = models.CharField(
        max_length=64,
        db_index=True,
        blank=True,
        verbose_name="Hash SHA256",
        help_text="Hash SHA256 del documento para deduplicación"
    )
    fecha_publicacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Publicación"
    )
    estado = models.CharField(
        max_length=12,
        choices=ESTADO,
        default="RECIBIDO",
        verbose_name="Estado"
    )
    
    # Cumplimiento/ética crawling
    user_agent = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="User Agent",
        help_text="User agent usado para el crawling"
    )
    robots_observado = models.BooleanField(
        default=False,
        verbose_name="Robots.txt Observado",
        help_text="Indica si se respetó robots.txt"
    )
    crawl_delay_s = models.PositiveIntegerField(
        default=0,
        verbose_name="Crawl Delay (segundos)",
        help_text="Delay configurado en robots.txt"
    )
    
    # Auditoría
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    
    class Meta:
        verbose_name = "Documento Fuente"
        verbose_name_plural = "Documentos Fuente"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estado", "created_at"]),
            models.Index(fields=["hash_sha256"]),
        ]
    
    def __str__(self):
        return f"{self.fuente} - {self.tipo} ({self.estado})"


class IngestaLog(models.Model):
    """
    Logs de ingesta para rastrear el procesamiento de documentos.
    """
    NIVEL_CHOICES = [
        ("INFO", "INFO"),
        ("WARN", "WARN"),
        ("ERROR", "ERROR"),
    ]
    
    documento = models.ForeignKey(
        DocumentoFuente,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="Documento"
    )
    etapa = models.CharField(
        max_length=50,
        verbose_name="Etapa",
        help_text="Etapa del procesamiento (descarga, parseo, normalizacion, indexado)"
    )
    nivel = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        default="INFO",
        verbose_name="Nivel"
    )
    mensaje = models.TextField(
        verbose_name="Mensaje"
    )
    payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Payload",
        help_text="Datos adicionales en formato JSON"
    )
    ts = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )
    
    class Meta:
        verbose_name = "Log de Ingesta"
        verbose_name_plural = "Logs de Ingesta"
        ordering = ["-ts"]
        indexes = [
            models.Index(fields=["documento", "etapa", "ts"]),
        ]
    
    def __str__(self):
        return f"{self.documento} - {self.etapa} [{self.nivel}]"


class NormaTributaria(models.Model):
    """
    Norma tributaria tokenizada y normalizada.
    
    Almacena artículos, temas, impuestos y vigencias extraídos de documentos fuente.
    """
    documento_fuente = models.ForeignKey(
        DocumentoFuente,
        on_delete=models.CASCADE,
        related_name="normas",
        verbose_name="Documento Fuente",
        help_text="Documento del cual se extrajo esta norma"
    )
    articulo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Artículo",
        help_text="Número o referencia del artículo (ej: 'Artículo 1', 'Art. 2.1')"
    )
    tema = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Tema",
        help_text="Tema o categoría de la norma"
    )
    impuesto = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Impuesto",
        help_text="Tipo de impuesto relacionado (IVA, Retención, ICA, etc.)"
    )
    vigencia_desde = models.DateField(
        null=True,
        blank=True,
        verbose_name="Vigencia Desde",
        help_text="Fecha de inicio de vigencia"
    )
    vigencia_hasta = models.DateField(
        null=True,
        blank=True,
        verbose_name="Vigencia Hasta",
        help_text="Fecha de fin de vigencia (null si vigente indefinidamente)"
    )
    texto_html = models.TextField(
        blank=True,
        null=True,
        verbose_name="Texto HTML",
        help_text="Texto de la norma en formato HTML"
    )
    texto_plano = models.TextField(
        verbose_name="Texto Plano",
        help_text="Texto de la norma en formato plano"
    )
    referencias = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Referencias",
        help_text="Lista de referencias a otras normas/artículos"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    
    class Meta:
        verbose_name = "Norma Tributaria"
        verbose_name_plural = "Normas Tributarias"
        ordering = ["documento_fuente", "articulo", "vigencia_desde"]
        indexes = [
            models.Index(fields=["articulo", "impuesto"]),
            models.Index(fields=["vigencia_desde", "vigencia_hasta"]),
            models.Index(fields=["documento_fuente"]),
        ]
        # Constraint para evitar duplicados exactos
        constraints = [
            models.UniqueConstraint(
                fields=["documento_fuente", "articulo", "tema", "impuesto"],
                name="unique_norma_por_documento",
                condition=models.Q(articulo__isnull=False),
            ),
        ]
    
    def __str__(self):
        articulo_str = self.articulo or "Sin artículo"
        return f"{articulo_str} - {self.tema or 'Sin tema'}"


# ============================================================================
# apps\public\impuestos\api 
# ============================================================================
# ⚠️ POLÍTICA SSoT: Estos modelos son la ÚNICA fuente de verdad para
# normativa DIAN. Todas las TENANT_APPS deben consumirlos vía API.
# ============================================================================

class ContribuyenteTipo(models.Model):
    """
    Tipos de contribuyentes según la DIAN (Persona Natural, Persona Jurídica).
    
    ⚠️ POLÍTICA SSoT: Este modelo es la única fuente de verdad para tipos de contribuyentes.
    Base legal: Resolución 000013 de 2020 (DIAN) y normativa vigente.
    """
    CLASE_PN, CLASE_PJ = "PN", "PJ"
    CLASE_CHOICES = (
        (CLASE_PN, "Persona Natural"),
        (CLASE_PJ, "Persona Jurídica")
    )

    SEG_GRAN, SEG_MED_ALTO, SEG_MED, SEG_PEQ, SEG_MICRO, SEG_OTRO = (
        "GRAN_CONTRIBUYENTE", "MEDIANO_ALTO", "MEDIANO", "PEQUENO", "MICRO", "OTRO"
    )
    SEGMENTO_CHOICES = (
        (SEG_GRAN, "Gran contribuyente"),
        (SEG_MED_ALTO, "Contribuyente mediano alto"),
        (SEG_MED, "Contribuyente mediano"),
        (SEG_PEQ, "Contribuyente pequeño"),
        (SEG_MICRO, "Contribuyente micro"),
        (SEG_OTRO, "Otro / No aplica"),
    )

    nombre = models.CharField(
        max_length=120,
        unique=True,
        verbose_name='Nombre',
        help_text='Nombre del tipo de contribuyente'
    )
    clase = models.CharField(
        max_length=2,
        choices=CLASE_CHOICES,
        verbose_name='Clase',
        help_text='Clase de contribuyente (Persona Natural o Persona Jurídica)'
    )
    segmento_dian = models.CharField(
        max_length=32,
        choices=SEGMENTO_CHOICES,
        default=SEG_OTRO,
        verbose_name='Segmento DIAN',
        help_text='Segmento según clasificación DIAN'
    )
    base_legal = models.TextField(
        blank=True,
        verbose_name='Base Legal',
        help_text='Referencia a la normativa legal que establece este tipo'
    )
    vigente_desde = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Desde',
        help_text='Fecha desde la cual este tipo está vigente'
    )
    vigente_hasta = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Hasta',
        help_text='Fecha hasta la cual este tipo está vigente (null si vigente indefinidamente)'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si este tipo está activo'
    )

    class Meta:
        ordering = ("clase", "segmento_dian", "nombre")
        verbose_name = "Tipo de Contribuyente"
        verbose_name_plural = "Tipos de Contribuyente"
        indexes = [
            models.Index(fields=["clase", "activo"]),
            models.Index(fields=["segmento_dian", "activo"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_clase_display()})"


class RegimenRenta(models.Model):
    """
    Regímenes de renta según la DIAN (Ordinario, RTE, SIMPLE).
    
    ⚠️ POLÍTICA SSoT: Este modelo es la única fuente de verdad para regímenes de renta.
    Base legal: Ley 1819 de 2016 (Régimen Simple de Tributación), Ley 1943 de 2018 (RTE).
    """
    ORD, RTE, SIMPLE = "ORDINARIO", "ESPECIAL", "SIMPLE"
    COD_CHOICES = (
        (ORD, "Régimen Ordinario"),
        (RTE, "Régimen Tributario Especial (RTE)"),
        (SIMPLE, "Régimen Simple de Tributación (SIMPLE)")
    )
    
    codigo = models.CharField(
        max_length=20,
        choices=COD_CHOICES,
        unique=True,
        verbose_name='Código',
        help_text='Código del régimen según DIAN'
    )
    nombre = models.CharField(
        max_length=120,
        verbose_name='Nombre',
        help_text='Nombre del régimen'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Descripción detallada del régimen'
    )
    tarifa_base_pj = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Tarifa Base PJ (%)',
        help_text='Tarifa base para personas jurídicas (porcentaje)'
    )
    requiere_facturacion_electronica = models.BooleanField(
        default=True,
        verbose_name='Requiere Facturación Electrónica',
        help_text='Indica si este régimen requiere facturación electrónica'
    )
    aplica_retenciones = models.BooleanField(
        default=True,
        verbose_name='Aplica Retenciones',
        help_text='Indica si este régimen aplica retenciones'
    )
    base_legal = models.TextField(
        blank=True,
        verbose_name='Base Legal',
        help_text='Referencia a la normativa legal que establece este régimen'
    )
    vigente_desde = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Desde',
        help_text='Fecha desde la cual este régimen está vigente'
    )
    vigente_hasta = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Hasta',
        help_text='Fecha hasta la cual este régimen está vigente (null si vigente indefinidamente)'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si este régimen está activo'
    )

    class Meta:
        ordering = ("codigo",)
        verbose_name = "Régimen de Renta"
        verbose_name_plural = "Regímenes de Renta"
        indexes = [
            models.Index(fields=["codigo", "activo"]),
        ]

    def __str__(self):
        return f"{self.get_codigo_display()}"


class ResponsabilidadRUT(models.Model):
    """
    Responsabilidades RUT según la DIAN (códigos de responsabilidades tributarias).
    
    ⚠️ POLÍTICA SSoT: Este modelo es la única fuente de verdad para responsabilidades RUT.
    Base legal: Resolución 000013 de 2020 (DIAN) y normativa vigente.
    
    Códigos comunes:
    - 48: Responsable de IVA
    - 49: No responsable de IVA
    - 47: Responsable de IVA como agente de retención
    - 52: Gran contribuyente
    - 13: Facturador electrónico
    """
    codigo = models.CharField(
        max_length=3,
        unique=True,
        verbose_name='Código',
        help_text='Código de responsabilidad según DIAN (ej: 48, 49, 47, 52, 13)'
    )
    nombre = models.CharField(
        max_length=160,
        verbose_name='Nombre',
        help_text='Nombre de la responsabilidad'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Descripción detallada de la responsabilidad'
    )
    es_responsable_iva = models.BooleanField(
        default=False,
        verbose_name='Es Responsable de IVA',
        help_text='Indica si esta responsabilidad implica ser responsable de IVA'
    )
    es_no_responsable_iva = models.BooleanField(
        default=False,
        verbose_name='Es No Responsable de IVA',
        help_text='Indica si esta responsabilidad implica NO ser responsable de IVA'
    )
    es_simple = models.BooleanField(
        default=False,
        verbose_name='Es SIMPLE',
        help_text='Indica si esta responsabilidad está relacionada con el régimen SIMPLE'
    )
    es_facturador_electronico = models.BooleanField(
        default=False,
        verbose_name='Es Facturador Electrónico',
        help_text='Indica si esta responsabilidad implica ser facturador electrónico'
    )
    es_gran_contribuyente = models.BooleanField(
        default=False,
        verbose_name='Es Gran Contribuyente',
        help_text='Indica si esta responsabilidad implica ser gran contribuyente'
    )
    base_legal = models.TextField(
        blank=True,
        verbose_name='Base Legal',
        help_text='Referencia a la normativa legal que establece esta responsabilidad'
    )
    vigente_desde = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Desde',
        help_text='Fecha desde la cual esta responsabilidad está vigente'
    )
    vigente_hasta = models.DateField(
        null=True,
        blank=True,
        verbose_name='Vigente Hasta',
        help_text='Fecha hasta la cual esta responsabilidad está vigente (null si vigente indefinidamente)'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si esta responsabilidad está activa'
    )

    class Meta:
        ordering = ("codigo",)
        verbose_name = "Responsabilidad RUT (DIAN)"
        verbose_name_plural = "Responsabilidades RUT (DIAN)"
        indexes = [
            models.Index(fields=["codigo", "activo"]),
            models.Index(fields=["es_responsable_iva", "activo"]),
            models.Index(fields=["es_facturador_electronico", "activo"]),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class PerfilTributario(models.Model):
    """
    Perfiles tributarios que combinan tipo de contribuyente, régimen de renta y responsabilidades RUT.
    
    ⚠️ POLÍTICA SSoT: Este modelo es la única fuente de verdad para perfiles tributarios.
    Permite definir combinaciones recomendadas de características tributarias.
    """
    nombre = models.CharField(
        max_length=160,
        unique=True,
        verbose_name='Nombre',
        help_text='Nombre del perfil tributario'
    )
    tipo_contribuyente = models.ForeignKey(
        ContribuyenteTipo,
        on_delete=models.PROTECT,
        related_name="perfiles",
        verbose_name='Tipo de Contribuyente',
        help_text='Tipo de contribuyente asociado a este perfil'
    )
    regimen_renta = models.ForeignKey(
        RegimenRenta,
        on_delete=models.PROTECT,
        related_name="perfiles",
        verbose_name='Régimen de Renta',
        help_text='Régimen de renta asociado a este perfil'
    )
    responsabilidades = models.ManyToManyField(
        ResponsabilidadRUT,
        blank=True,
        related_name="perfiles",
        verbose_name='Responsabilidades RUT',
        help_text='Responsabilidades RUT asociadas a este perfil'
    )
    recomendado_desde = models.DateField(
        null=True,
        blank=True,
        verbose_name='Recomendado Desde',
        help_text='Fecha desde la cual este perfil es recomendado'
    )
    recomendado_hasta = models.DateField(
        null=True,
        blank=True,
        verbose_name='Recomendado Hasta',
        help_text='Fecha hasta la cual este perfil es recomendado (null si vigente indefinidamente)'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si este perfil está activo'
    )

    class Meta:
        ordering = ("nombre",)
        verbose_name = "Perfil Tributario (público)"
        verbose_name_plural = "Perfiles Tributarios (público)"
        indexes = [
            models.Index(fields=["nombre", "activo"]),
            models.Index(fields=["tipo_contribuyente", "activo"]),
            models.Index(fields=["regimen_renta", "activo"]),
        ]

    def __str__(self):
        return self.nombre