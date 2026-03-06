# apps/tenant/facturas/models.py
"""
Modelos de facturación por tenant.

⚠️ TENANT_APPS: cada tenant tiene sus propias facturas/ítems (aislamiento por esquema).
SSoT histórico: snapshots de emisor/receptor al momento de emisión.
"""

from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class Factura(models.Model):
    class TipoFactura(models.TextChoices):
        FE = 'FE', _('Factura Electrónica')
        NC = 'NC', _('Nota Crédito')
        ND = 'ND', _('Nota Débito')

    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        ENVIADA  = 'ENVIADA',  _('Enviada')
        ACEPTADA = 'ACEPTADA', _('Aceptada')
        RECHAZADA= 'RECHAZADA',_('Rechazada')
        ANULADA  = 'ANULADA',  _('Anulada')

    # Naturaleza frente al tenant (compra/venta)
    class Naturaleza(models.TextChoices):
        VENTA  = 'VENTA',  _('Venta (emitida por el tenant)')
        COMPRA = 'COMPRA', _('Compra (recibida por el tenant)')

    # Clasificación de lo facturado (según ítems)
    class Categoria(models.TextChoices):
        PRODUCTO = 'PRODUCTO', _('Productos')
        SERVICIO = 'SERVICIO', _('Servicios')
        MIXTO    = 'MIXTO',    _('Mixto')

    # ⚠️ v2.40: FK a Empresa (requerido para ENFORCED MODE y auditoría)
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name=_('Empresa'),
        help_text=_('Empresa del tenant (SSoT)')
    )

    # Información básica
    numero = models.CharField(
        max_length=50, unique=True, verbose_name=_('Número de Factura'),
        help_text=_('Ej: FST354')
    )
    prefijo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Prefijo'))
    consecutivo = models.IntegerField(verbose_name=_('Consecutivo'))

    tipo = models.CharField(max_length=2, choices=TipoFactura.choices,
                            default=TipoFactura.FE, verbose_name=_('Tipo'))
    estado = models.CharField(max_length=20, choices=Estado.choices,
                              default=Estado.BORRADOR, verbose_name=_('Estado'))

    # Naturaleza frente al tenant y categoría de la operación
    # ⚠️ v2.60: Se calcula automáticamente comparando NIT del emisor con NIT de la empresa del tenant (SSoT)
    naturaleza = models.CharField(
        max_length=10, choices=Naturaleza.choices, null=True, blank=True,
        verbose_name=_('Naturaleza (venta/compra)'),
        help_text=_('VENTA si el tenant es emisor; COMPRA si el tenant es receptor. Se calcula automáticamente en importación UBL comparando NITs normalizados.')
    )
    categoria = models.CharField(
        max_length=10, choices=Categoria.choices, default=Categoria.SERVICIO,
        verbose_name=_('Categoría (producto/servicio/mixto)')
    )

    # UBL/DIAN metadatos
    ubl_version = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('UBL Version'))
    customization_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('CustomizationID'))
    profile_id = models.CharField(max_length=80, blank=True, null=True, verbose_name=_('ProfileID'))
    profile_execution_id = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('ProfileExecutionID'))
    invoice_type_code = models.CharField(max_length=4, blank=True, null=True, verbose_name=_('InvoiceTypeCode'))

    # Fechas
    fecha_emision = models.DateTimeField(verbose_name=_('Fecha/hora de Emisión'))
    fecha_vencimiento = models.DateField(blank=True, null=True, verbose_name=_('Fecha de Vencimiento'))

    # Snapshot emisor (empresa del tenant al momento de emisión)
    emisor_nit = models.CharField(max_length=20, verbose_name=_('NIT Emisor'))
    emisor_razon_social = models.CharField(max_length=200, verbose_name=_('Razón Social Emisor'))
    emisor_direccion = models.CharField(max_length=300, blank=True, null=True, verbose_name=_('Dirección Emisor'))
    emisor_email = models.CharField(max_length=120, blank=True, null=True, verbose_name=_('Email Emisor'))
    emisor_telefono = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('Teléfono Emisor'))
    emisor_actividad_ciiu = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('CIIU Emisor'))

    # Snapshot receptor
    receptor_nit = models.CharField(max_length=20, verbose_name=_('NIT Receptor'))
    receptor_razon_social = models.CharField(max_length=200, verbose_name=_('Razón Social Receptor'))
    receptor_direccion = models.CharField(max_length=300, blank=True, null=True, verbose_name=_('Dirección Receptor'))
    receptor_email = models.CharField(max_length=120, blank=True, null=True, verbose_name=_('Email Receptor'))
    receptor_telefono = models.CharField(max_length=40, blank=True, null=True, verbose_name=_('Teléfono Receptor'))

    # Totales
    moneda = models.CharField(max_length=3, default='COP', verbose_name=_('Moneda'))
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                   validators=[MinValueValidator(Decimal('0.00'))])
    impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                    validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                validators=[MinValueValidator(Decimal('0.00'))])

    # Formas de pago
    forma_pago = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Forma de pago'))
    medio_pago_codigo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('PaymentMeansCode'))
    payment_due_date = models.DateField(blank=True, null=True, verbose_name=_('Fecha límite de pago'))

    # DIAN / QR / CUFE y autorización
    # ⚠️ v2.60: Índice único para garantizar idempotencia en guardar_factura_desde_dto()
    # Django permite múltiples NULLs en campos únicos, así que esto garantiza unicidad cuando hay valor
    cufe = models.CharField(
        max_length=128, 
        blank=True, 
        null=True, 
        unique=True,  # ⚠️ CRÍTICO: Garantiza idempotencia por CUFE (clave legal de la DIAN)
        db_index=True,  # Índice adicional para búsquedas rápidas
        verbose_name=_('CUFE'), 
        help_text=_('Código Único de Facturación Electrónica (clave legal de la DIAN para idempotencia)')
    )
    qr_code = models.TextField(blank=True, null=True, verbose_name=_('QR raw'), help_text=_('Texto multilínea del código QR'))
    qr_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name=_('URL QR DIAN'), help_text=_('URL del código QR (puede ser muy larga)'))
    autorizacion_numero = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Autorización DIAN'))
    autorizacion_prefijo = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Prefijo autorizado'))
    autorizacion_rango_desde = models.IntegerField(blank=True, null=True, verbose_name=_('Rango desde'))
    autorizacion_rango_hasta = models.IntegerField(blank=True, null=True, verbose_name=_('Rango hasta'))
    autorizacion_vigencia_inicio = models.DateField(blank=True, null=True, verbose_name=_('Vigencia inicio'))
    autorizacion_vigencia_fin = models.DateField(blank=True, null=True, verbose_name=_('Vigencia fin'))

    # Respuesta DIAN (ApplicationResponse) / estado de validación
    dian_validation_code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Código Validación DIAN'))
    dian_validation_desc = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Descripción Validación'))
    dian_validation_fecha = models.DateField(blank=True, null=True, verbose_name=_('Fecha Validación'))
    dian_validation_hora = models.TimeField(blank=True, null=True, verbose_name=_('Hora Validación'))
    dian_response_xml = models.TextField(blank=True, null=True, verbose_name=_('ApplicationResponse XML'))

    # XML (⚠️ DEPRECADO: usar FacturaAnexos.ubl_xml en su lugar)
    # Mantenido por compatibilidad durante migración
    xml_content = models.TextField(blank=True, null=True, verbose_name=_('XML UBL completo (Deprecado)'))
    xml_file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Ruta XML'))

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))

    class Meta:
        verbose_name = _('Factura')
        verbose_name_plural = _('Facturas')
        ordering = ['-fecha_emision', '-consecutivo']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['estado']),
            models.Index(fields=['naturaleza']),  # ⚠️ v2.60: Índice para filtrar por VENTA/COMPRA
            # ⚠️ v2.60: cufe tiene unique=True y db_index=True, no necesita índice adicional aquí
            models.Index(fields=['empresa']),  # ⚠️ v2.40: Índice para FK a Empresa
        ]
        # ⚠️ v2.60: Constraint único por cufe garantiza idempotencia (definido en el campo con unique=True)
        # Django permite múltiples NULLs en campos únicos, así que esto funciona correctamente

    @property
    def tiene_nota_credito(self) -> bool:
        """Verifica si la factura tiene una nota crédito asociada."""
        return hasattr(self, "nota_credito")

    def __str__(self):
        cufe_str = f" | {self.cufe}" if self.cufe else ""
        return f"{self.numero}{cufe_str}"

    def save(self, *args, **kwargs):
        if self.total is None or self.total == Decimal('0.00'):
            self.total = (self.subtotal or Decimal('0.00')) + (self.impuestos or Decimal('0.00'))
        super().save(*args, **kwargs)


class ItemFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items', verbose_name=_('Factura'))
    
    # ⚠️ v2.40: FK a Empresa (requerido para ENFORCED MODE y auditoría)
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='items_factura',
        verbose_name=_('Empresa'),
        help_text=_('Empresa del tenant (SSoT)')
    )
    
    # UBL: ID de línea y codificación estándar si existe
    linea_id = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('ID línea UBL'))
    codigo = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Código del ítem'))
    descripcion = models.CharField(max_length=500, verbose_name=_('Descripción'))

    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'),
                                   validators=[MinValueValidator(Decimal('0.01'))])
    unidad_medida = models.CharField(max_length=10, default='UND', verbose_name=_('Unidad de Medida'),
                                     help_text=_('Ej: UN, ZZ, UND'))
    valor_unitario = models.DecimalField(max_digits=15, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.00'))])

    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])
    valor_iva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                    validators=[MinValueValidator(Decimal('0.00'))])

    subtotal = models.DecimalField(max_digits=15, decimal_places=2,
                                   validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=15, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.00'))])

    # Derivación: servicio vs producto (heurística por unitCode y/o keywords)
    es_servicio = models.BooleanField(default=False, verbose_name=_('¿Es servicio?'))

    orden = models.IntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Ítem de Factura')
        verbose_name_plural = _('Ítems de Factura')
        ordering = ['factura', 'orden']

    def __str__(self):
        return f"{self.factura.numero} - {self.descripcion[:50]}"

    def save(self, *args, **kwargs):
        # ⚠️ v2.40: Auto-asignar empresa desde factura si no está asignada
        if not self.empresa_id and self.factura_id:
            self.empresa = self.factura.empresa
        
        self.subtotal = (self.cantidad or Decimal('0.00')) * (self.valor_unitario or Decimal('0.00'))
        self.valor_iva = (self.subtotal or Decimal('0.00')) * ((self.porcentaje_iva or Decimal('0.00')) / Decimal('100.00'))
        self.total = (self.subtotal or Decimal('0.00')) + (self.valor_iva or Decimal('0.00'))
        # Heurística simple: unitCode 'ZZ' suele usarse en servicios (ajustable por catálogo propio)
        if self.unidad_medida and self.unidad_medida.upper() in {'ZZ'}:
            self.es_servicio = True
        super().save(*args, **kwargs)


# --- DEPRECADO: Configuración de ingesta por correo (por tenant) ---
# ⚠️ DEPRECADO (Fase 5): Este modelo ha sido migrado a apps.tenant.empresa.models.MailInboxConfig
# Se mantiene temporalmente para migración de datos. No usar en código nuevo.
# TODO: Crear migración de datos y eliminar este modelo.
class MailIngestionConfig(models.Model):
    """
    ⚠️ DEPRECADO: Este modelo ha sido migrado a apps.tenant.empresa.models.MailInboxConfig (SSoT).
    
    No usar en código nuevo. Usar apps.tenant.empresa.services.mailbox_provider.get_mailbox_config().
    """
    PROTOCOL_CHOICES = (
        ("imap", "IMAP"),
        ("pop3", "POP3"),
    )
    
    host = models.CharField(max_length=255, verbose_name=_('Servidor'))
    port = models.PositiveIntegerField(default=993, verbose_name=_('Puerto'))
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        default="imap",
        verbose_name=_('Protocolo')
    )
    ssl = models.BooleanField(default=True, verbose_name=_('Usar SSL/TLS'))
    username = models.CharField(max_length=255, verbose_name=_('Usuario'))
    password = models.CharField(max_length=255, verbose_name=_('Contraseña'))
    mailbox = models.CharField(max_length=255, default="INBOX", verbose_name=_('Carpeta'))
    mark_as_seen = models.BooleanField(default=True, verbose_name=_('Marcar como leído'))
    move_processed_to = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Mover procesados a')
    )
    max_attachment_mb = models.PositiveIntegerField(default=50, verbose_name=_('Límite adjuntos (MB)'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        verbose_name = _('Configuración de Ingesta por Correo (DEPRECADO)')
        verbose_name_plural = _('Configuraciones de Ingesta por Correo (DEPRECADO)')
        ordering = ("-updated_at",)
    
    def __str__(self):
        return f"{self.protocol.upper()}://{self.username}@{self.host}:{self.port}/{self.mailbox}"


# --- Tracking de ejecuciones de ingesta por correo (por tenant) ---
class MailIngestionRun(models.Model):
    """
    Registro de ejecución de ingesta de facturas desde correo.
    
    ⚠️ TENANT_APPS: Cada tenant tiene sus propios registros (aislamiento por esquema).
    ⚠️ CERO SIGNALS: La tarea Celery actualiza este modelo directamente (sin signals).
    """
    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("RUNNING", "RUNNING"),
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),  # Cambiar de FAILURE a FAILED para consistencia
        ("CANCEL_REQUESTED", "CANCEL_REQUESTED"),  # ← Clave para cancelación cooperativa
        ("CANCELED", "CANCELED"),
        ("ABORTED", "ABORTED"),  # Mantener por compatibilidad
    ]
    
    started_by = models.ForeignKey(
        'perfil.TenantProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mail_ingestion_runs',
        verbose_name=_('Iniciado por'),
        help_text=_('Operador del tenant que inició la ingesta de correo')
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Iniciado'))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Finalizado'))
    task_id = models.CharField(max_length=128, db_index=True, unique=True, verbose_name=_('ID Tarea Celery'))
    naturaleza = models.CharField(
        max_length=10,
        default="VENTA",
        choices=Factura.Naturaleza.choices,
        verbose_name=_('Naturaleza')
    )
    status = models.CharField(
        max_length=20,  # Aumentar para CANCEL_REQUESTED
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,  # Índice para consultas rápidas de estado
        verbose_name=_('Estado')
    )
    # Conteos resumidos y detalles (ligeros) — JSON-only
    counts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Conteos'),
        help_text=_('Métricas: xml_detected, imported, duplicates, errors')
    )
    summary = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Resumen'),
        help_text=_('Detalles de ejecución (JSON)')
    )
    
    class Meta:
        verbose_name = _('Ejecución de Ingesta por Correo')
        verbose_name_plural = _('Ejecuciones de Ingesta por Correo')
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"MailIngestionRun(task={self.task_id}, status={self.status})"


# --- Estado del buzón para procesamiento incremental (por tenant) ---
class MailInboxState(models.Model):
    """
    Estado del procesamiento IMAP de un buzón de correo.
    
    Rastrea el último UID procesado para permitir procesamiento incremental eficiente.
    
    ⚠️ TENANT_APPS: Cada tenant tiene sus propios estados (aislamiento por esquema).
    ⚠️ SSoT: Relacionado con MailInboxConfig de empresa.
    ⚠️ UID IMAP: Los UIDs son únicos y persistentes por buzón (no cambian al eliminar mensajes).
    
    Reglas:
    - Si last_seen_uid es NULL → primera ejecución (procesar histórico completo desde UID 1).
    - Si existe → solo procesar UIDs mayores a last_seen_uid (incremental).
    """
    mailbox_config = models.ForeignKey(
        'empresa.MailInboxConfig',
        on_delete=models.CASCADE,
        related_name='inbox_states',
        verbose_name=_('Configuración de buzón'),
        help_text=_('Configuración de correo asociada')
    )
    last_seen_uid = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Último UID procesado'),
        help_text=_('Último UID IMAP procesado. NULL = primera ejecución (histórico completo)')
    )
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última ejecución'),
        help_text=_('Fecha/hora de la última ejecución exitosa')
    )
    total_processed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total procesados'),
        help_text=_('Total acumulado de mensajes procesados')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        verbose_name = _('Estado de Buzón IMAP')
        verbose_name_plural = _('Estados de Buzón IMAP')
        unique_together = [['mailbox_config']]  # Un estado por configuración
        indexes = [
            models.Index(fields=['mailbox_config', 'last_seen_uid']),
            models.Index(fields=['last_run_at']),
        ]
    
    def __str__(self):
        uid_str = str(self.last_seen_uid) if self.last_seen_uid else "NULL (histórico)"
        return f"MailInboxState(config={self.mailbox_config_id}, last_uid={uid_str})"


class FacturaAnexos(models.Model):
    """
    Anexos de factura (XMLs grandes separados de la fila principal).
    
    ⚠️ OPTIMIZACIÓN: Evita cargar blobs en listados.
    ⚠️ ONE-TO-ONE: Una factura tiene un único registro de anexos.
    ⚠️ TENANT_APPS: Aislado por esquema (django-tenants).
    """
    factura = models.OneToOneField(
        Factura,
        on_delete=models.CASCADE,
        related_name='anexos',
        verbose_name=_('Factura'),
        help_text=_('Factura asociada')
    )
    
    # UBL principal (invoice)
    ubl_xml = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('XML UBL completo'),
        help_text=_('Contenido completo del XML UBL de la factura')
    )
    
    # ApplicationResponse / AttachedDocument / otros adjuntos DIAN
    application_response_xml = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('ApplicationResponse XML'),
        help_text=_('XML de respuesta de la DIAN (ApplicationResponse)')
    )
    
    # PDF físico (representación gráfica de la factura)
    pdf_file = models.FileField(
        upload_to='facturas/pdfs/',
        null=True,
        blank=True,
        verbose_name=_('Archivo PDF'),
        help_text=_('Archivo PDF de la factura (representación gráfica)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha de Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha de Actualización'))
    
    class Meta:
        verbose_name = _('Anexo de Factura')
        verbose_name_plural = _('Anexos de Factura')
        db_table = 'facturas_factura_anexos'
    
    def __str__(self):
        return f"FacturaAnexos(factura={self.factura.numero})"


class NotaCredito(models.Model):
    """
    Nota Crédito UBL 2.1 (una por factura). Idempotencia por CUDE.
    
    ⚠️ ONE-TO-ONE: Una factura tiene una única nota crédito.
    ⚠️ PROTECT: Evita borrar nota crédito al borrar factura accidentalmente.
    ⚠️ TENANT_APPS: Aislado por esquema (django-tenants).
    ⚠️ INMUTABILIDAD: Las notas crédito son documentos históricos (solo creación/eliminación).
    """
    factura = models.OneToOneField(
        Factura,
        related_name="nota_credito",
        on_delete=models.PROTECT,  # ⚠️ Evita cascada accidental
        help_text=_("Factura a la que aplica esta Nota Crédito (1:1)."),
        verbose_name=_('Factura')
    )
    
    # ⚠️ v2.40: FK a Empresa (requerido para ENFORCED MODE y auditoría)
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='notas_credito',
        verbose_name=_('Empresa'),
        help_text=_('Empresa del tenant (SSoT)')
    )
    numero = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Número de Nota Crédito'),
        help_text=_('Ej: NC135')
    )
    cude = models.CharField(
        max_length=128,
        unique=True,
        verbose_name=_('CUDE'),
        help_text=_('Código Único de Documento Electrónico (identificador legal de la nota)')
    )
    fecha_emision = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha/hora de Emisión')
    )
    moneda = models.CharField(
        max_length=8,
        default="COP",
        verbose_name=_('Moneda')
    )

    # Totales (alineado a LegalMonetaryTotal del XML)
    subtotal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Subtotal')
    )
    impuestos = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Impuestos')
    )
    total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total')
    )

    # Motivo y referencia a la factura original (redundancia para consultas rápidas)
    motivo = models.TextField(
        blank=True,
        default="",
        verbose_name=_('Motivo'),
        help_text=_('Motivo de la nota crédito')
    )
    ref_factura_numero = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_('Número Factura Referenciada'),
        help_text=_('Número de la factura a la que aplica esta nota crédito')
    )
    ref_factura_cufe = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name=_('CUFE Factura Referenciada'),
        help_text=_('CUFE de la factura a la que aplica esta nota crédito')
    )

    # XML almacenado para endpoint pesado dedicado
    xml_content = models.TextField(
        blank=True,
        default="",
        verbose_name=_('XML UBL completo'),
        help_text=_('Contenido completo del XML UBL de la nota crédito')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Creado')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Actualizado')
    )

    class Meta:
        verbose_name = _('Nota Crédito')
        verbose_name_plural = _('Notas Crédito')
        ordering = ['-fecha_emision', '-created_at']
        indexes = [
            models.Index(fields=['cude']),
            models.Index(fields=['numero']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['factura']),
            models.Index(fields=['empresa']),  # ⚠️ v2.40: Índice para FK a Empresa
        ]
        constraints = [
            # ⚠️ COHERENCIA: Si se declara ref CUFE/número, deberían coincidir con la factura
            # (validación en service layer; aquí se omite constraint complejo por portabilidad)
        ]

    def __str__(self):
        return f"NC {self.numero} | {self.cude}"

    def save(self, *args, **kwargs):
        """Calcula total automáticamente si no está definido."""
        # ⚠️ v2.40: Auto-asignar empresa desde factura si no está asignada
        if not self.empresa_id and self.factura_id:
            self.empresa = self.factura.empresa
        
        if self.total is None or self.total == Decimal('0.00'):
            self.total = (self.subtotal or Decimal('0.00')) + (self.impuestos or Decimal('0.00'))
        super().save(*args, **kwargs)