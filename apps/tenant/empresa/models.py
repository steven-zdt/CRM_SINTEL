"""
Modelos de empresa por tenant.

# WARNING: IMPORTANTE: Estos modelos están en TENANT_APPS, por lo que:
- Cada tenant tiene sus propios datos de empresa
- NO usar foreign keys al esquema público (excepto User si es necesario)
- django-tenants maneja automáticamente el aislamiento por esquema
- No es necesario filtrar manualmente por tenant_id
"""
import uuid as uuid_module
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel


class Empresa(SintelTenantBaseModel):
    """
    Datos fiscales y de configuración de la empresa (por tenant).
    
    PATRÓN SINGLETON: Cada tenant tiene una única instancia de Empresa.
    La constraint UniqueConstraint sobre singleton_key garantiza singleton a nivel de base de datos.
    
    Principios:
    - Cero Signals: Toda la lógica está en la capa de servicios
    - Tenant Isolation: Cada tenant tiene sus propios datos
    - Service Layer: El cálculo del DV y la lógica de negocio están en servicios
    - DB-First: UniqueConstraint garantiza singleton a nivel de base de datos
    """
    # Nota: `SintelTenantBaseModel` añade un FK obligatorio `empresa`.
    # Para el modelo `Empresa` (la entidad SSoT raíz dentro del schema)
    # permitimos que `empresa` sea NULL durante la creación inicial y
    # la sobreescribimos aquí para evitar que `full_clean()` falle
    # con "Este campo no puede ser nulo." cuando se crea la instancia
    # por primera vez dentro del seed del onboarding.
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name=_('Empresa'),
        help_text=_('Empresa propietaria (SSoT por tenant). Puede ser NULL durante creación inicial.'),
        null=True,
        blank=True,
        db_index=True,
    )

    # Campo singleton para garantizar única instancia por tenant (esquema)
    singleton_key = models.PositiveSmallIntegerField(
        default=1,
        editable=False,
        verbose_name=_('Clave Singleton'),
        help_text=_('Campo técnico para garantizar singleton por tenant (siempre 1)')
    )
    
    razon_social = models.CharField(
        max_length=255,
        verbose_name=_('Razón Social'),
        help_text=_('Nombre legal de la empresa')
    )
    nit = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name=_('NIT'),
        help_text=_('Número de Identificación Tributaria (sin DV)')
    )
    dv = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        verbose_name=_('Dígito de Verificación'),
        help_text=_('Dígito verificador del NIT (calculado automáticamente)')
    )
    direccion = models.CharField(
        max_length=500,
        default="",
        verbose_name=_('Dirección'),
        help_text=_('Dirección completa de la empresa')
    )
    ciudad = models.CharField(
        max_length=100,
        default="",
        blank=True,
        verbose_name=_('Ciudad'),
        help_text=_('Ciudad principal de la empresa')
    )
    departamento = models.CharField(
        max_length=100,
        default="",
        blank=True,
        verbose_name=_('Departamento'),
        help_text=_('Departamento o estado de la empresa')
    )
    email = models.EmailField(
        default="",
        blank=True,
        verbose_name=_('Email'),
        help_text=_('Email principal de la empresa (alias de email_contacto)')
    )
    activa = models.BooleanField(
        default=True,
        verbose_name=_('Activa'),
        help_text=_('Indica si la empresa está activa')
    )
    telefono = models.CharField(
        max_length=20,
        default="",
        blank=True,
        verbose_name=_('Teléfono'),
        help_text=_('Teléfono de contacto')
    )
    email_contacto = models.EmailField(
        default="",
        blank=True,
        verbose_name=_('Email de Contacto'),
        help_text=_('Email de contacto de la empresa')
    )
    owner_email = models.EmailField(
        default="",
        blank=True,
        db_index=True,
        verbose_name=_('Email del Propietario'),
        help_text=_('Email del admin primario del tenant. Poblado durante el onboarding para Auto-Admin Elevation. No exponer en la UI de clientes.')
    )
    regimen_tributario = models.CharField(
        max_length=50,
        default="NO_RESPONDE",
        blank=True,
        verbose_name=_('Régimen Tributario'),
        help_text=_('Régimen tributario de la empresa')
    )
    moneda = models.CharField(
        max_length=8,
        default='COP',
        verbose_name=_('Moneda'),
        help_text=_('Código de moneda (ISO 4217)')
    )
    # Opcionales
    logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True,
        verbose_name=_('Logo'),
        help_text=_('Logo de la empresa')
    )
    website = models.URLField(
        blank=True,
        default="",
        verbose_name=_('Sitio Web'),
        help_text=_('URL del sitio web de la empresa')
    )
    
    # created_at y updated_at heredados de SintelTenantBaseModel
    
    class Meta:
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['razon_social']
        db_table = 'empresa_empresa'
        indexes = [
            models.Index(fields=["empresa"]),
            models.Index(fields=["nit"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['singleton_key'],
                name='unique_singleton_empresa_per_schema',
                violation_error_message=_('Solo se permite una empresa por tenant.')
            )
        ]
    
    def __str__(self):
        return f"{self.razon_social} ({self.nit})"
    
    def clean(self):
        """Normaliza campos antes de guardar."""
        if self.nit:
            self.nit = str(self.nit).strip()
        if self.dv:
            self.dv = str(self.dv).strip()
            if len(self.dv) > 2:
                self.dv = self.dv[:2]
        if self.email_contacto:
            self.email_contacto = self.email_contacto.lower().strip()
        if self.owner_email:
            self.owner_email = self.owner_email.lower().strip()
        if self.email:
            self.email = self.email.lower().strip()
        if self.razon_social:
            self.razon_social = self.razon_social.strip()
        if self.direccion:
            self.direccion = self.direccion.strip()
        if self.ciudad:
            self.ciudad = self.ciudad.strip()
        if self.departamento:
            self.departamento = self.departamento.strip()
        if self.telefono:
            self.telefono = self.telefono.strip()
        if self.website:
            self.website = self.website.strip()
    
    def save(self, *args, **kwargs):
                """Normalizar y guardar.

                Notas:
                - `SintelTenantBaseModel.save()` contiene una guardia que obliga a que
                    `empresa` no sea NULL. Eso impide crear la instancia `Empresa` misma
                    (bootstrap) ya que no existe aún una empresa a la que apuntar.
                - Para permitir el seed inicial dentro del onboarding, realizamos
                    `full_clean()` pero guardamos usando `models.Model.save()` para
                    evitar la validación adicional de la clase base.
                - Una vez creada la instancia, otros registros del tenant pueden
                    referenciarla explícitamente.
                """
                self.full_clean()
                # Guardar saltando la comprobación de SintelTenantBaseModel
                models.Model.save(self, *args, **kwargs)


class MailInboxConfig(SintelTenantBaseModel):
    """
    Configuración de buzones de correo para ingesta de facturas (por tenant).
    
    # WARNING: TENANT_APPS: Cada tenant tiene sus propias configuraciones (aislamiento por esquema).
    # WARNING: SSoT: Este es el único lugar donde se gestionan credenciales de correo.
    # WARNING: SEGURIDAD: En fase posterior, cifrar password (TODO: usar django-encrypted-model-fields o similar).
    # WARNING: CERO SIGNALS: Toda la lógica es explícita.
    # WARNING: GMAIL: Soporta preset Gmail con autocompletado de IMAP/SMTP.
    """
    PROTOCOL_CHOICES = (
        ("imap", "IMAP"),
        ("pop3", "POP3"),
    )
    
    PROVIDER_CHOICES = (
        ("custom", _("Personalizado")),
        ("gmail", _("Gmail")),
    )
    
    # Campos básicos
    nombre = models.CharField(
        max_length=100,
        verbose_name=_('Nombre'),
        help_text=_('Alias legible para identificar esta configuración')
    )
    email_address = models.EmailField(
        verbose_name=_('Email principal'),
        help_text=_('Dirección de correo principal (usado como username por defecto)'),
        blank=True,
        null=True
    )
    
    # Proveedor predefinido (Gmail/Custom)
    provider = models.CharField(
        max_length=16,
        choices=PROVIDER_CHOICES,
        default="custom",
        db_index=True,
        verbose_name=_('Proveedor'),
        help_text=_('Proveedor de correo: Gmail (autocompletado) o Personalizado')
    )
    
    # === CAMPOS LEGACY (mantener para compatibilidad) ===
    # Estos campos se mapean a imap_* cuando provider != "gmail"
    host = models.CharField(
        max_length=255,
        verbose_name=_('Servidor (Legacy)'),
        blank=True,
        null=True,
        help_text=_('# WARNING: DEPRECADO: Usar imap_host. Se mantiene para compatibilidad.')
    )
    port = models.PositiveIntegerField(
        default=993,
        verbose_name=_('Puerto (Legacy)'),
        blank=True,
        null=True,
        help_text=_('# WARNING: DEPRECADO: Usar imap_port. Se mantiene para compatibilidad.')
    )
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        default="imap",
        verbose_name=_('Protocolo (Legacy)'),
        help_text=_('# WARNING: DEPRECADO: Siempre IMAP. Se mantiene para compatibilidad.')
    )
    ssl = models.BooleanField(
        default=True,
        verbose_name=_('SSL (Legacy)'),
        help_text=_('# WARNING: DEPRECADO: Usar imap_ssl. Se mantiene para compatibilidad.')
    )
    username = models.CharField(
        max_length=255,
        verbose_name=_('Usuario (Legacy)'),
        blank=True,
        null=True,
        help_text=_('# WARNING: DEPRECADO: Usar imap_username. Se mantiene para compatibilidad.')
    )
    password = models.CharField(
        max_length=255,
        verbose_name=_('Contraseña (Legacy)'),
        blank=True,
        null=True,
        help_text=_('# WARNING: DEPRECADO: Usar imap_password. Se mantiene para compatibilidad.')
    )
    mailbox = models.CharField(
        max_length=255,
        default="INBOX",
        verbose_name=_('Carpeta (Legacy)'),
        blank=True,
        null=True,
        help_text=_('# WARNING: DEPRECADO: Usar imap_mailbox. Se mantiene para compatibilidad.')
    )
    mark_as_seen = models.BooleanField(
        default=True,
        verbose_name=_('Marcar como leído (Legacy)'),
        help_text=_('# WARNING: DEPRECADO: Usar imap_mark_as_seen. Se mantiene para compatibilidad.')
    )
    move_processed_to = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Mover procesados a (Legacy)'),
        help_text=_('# WARNING: DEPRECADO: Usar imap_move_processed_to. Se mantiene para compatibilidad.')
    )
    max_attachment_mb = models.PositiveIntegerField(
        default=50,
        verbose_name=_('Límite adjuntos (MB) (Legacy)'),
        help_text=_('# WARNING: DEPRECADO: Usar imap_max_attachment_mb. Se mantiene para compatibilidad.')
    )
    
    # === CAMPOS IMAP (recepción) ===
    # Valores por defecto pensados para Gmail: imap.gmail.com:993 SSL
    imap_host = models.CharField(
        max_length=255,
        default="imap.gmail.com",
        blank=True,
        verbose_name=_('Servidor IMAP'),
        help_text=_('Hostname del servidor IMAP (Gmail: imap.gmail.com)')
    )
    imap_port = models.PositiveIntegerField(
        default=993,
        blank=True,
        null=True,
        verbose_name=_('Puerto IMAP'),
        help_text=_('Puerto IMAP (Gmail: 993 para SSL, 143 para STARTTLS)')
    )
    imap_ssl = models.BooleanField(
        default=True,
        verbose_name=_('IMAP SSL/TLS'),
        help_text=_('Usar SSL/TLS implícito (puerto 993) o STARTTLS (puerto 143)')
    )
    imap_starttls = models.BooleanField(
        default=False,
        verbose_name=_('IMAP STARTTLS'),
        help_text=_('Usar STARTTLS en lugar de SSL implícito (solo si puerto 143)')
    )
    imap_username = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Usuario IMAP'),
        help_text=_('Usuario para autenticación IMAP (por defecto: email_address)')
    )
    imap_password = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Contraseña IMAP'),
        help_text=_('Contraseña o App Password para IMAP (Gmail: requiere App Password si 2FA activo)')
    )
    imap_mailbox = models.CharField(
        max_length=120,
        default="INBOX",
        blank=True,
        verbose_name=_('Carpeta IMAP'),
        help_text=_('Carpeta IMAP a monitorear (por defecto: INBOX)')
    )
    imap_mark_as_seen = models.BooleanField(
        default=True,
        verbose_name=_('Marcar como leído'),
        help_text=_('Marcar mensajes como leídos tras procesarlos')
    )
    imap_move_processed_to = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name=_('Mover procesados a'),
        help_text=_('Carpeta destino para mensajes procesados (opcional)')
    )
    imap_max_attachment_mb = models.PositiveIntegerField(
        default=50,
        blank=True,
        null=True,
        verbose_name=_('Límite adjuntos IMAP (MB)'),
        help_text=_('Límite máximo de tamaño de adjuntos en MB (1-50)')
    )
    
    # === CAMPOS SMTP (envío; opcional, útil para notificaciones futuras) ===
    # Valores por defecto pensados para Gmail: smtp.gmail.com:587 TLS o 465 SSL
    smtp_host = models.CharField(
        max_length=255,
        default="smtp.gmail.com",
        blank=True,
        null=True,
        verbose_name=_('Servidor SMTP'),
        help_text=_('Hostname del servidor SMTP (Gmail: smtp.gmail.com)')
    )
    smtp_port = models.PositiveIntegerField(
        default=587,
        blank=True,
        null=True,
        verbose_name=_('Puerto SMTP'),
        help_text=_('Puerto SMTP (Gmail: 587 para TLS, 465 para SSL)')
    )
    smtp_ssl = models.BooleanField(
        default=False,
        verbose_name=_('SMTP SSL'),
        help_text=_('Usar SSL implícito (puerto 465) o STARTTLS (puerto 587)')
    )
    smtp_starttls = models.BooleanField(
        default=True,
        verbose_name=_('SMTP STARTTLS'),
        help_text=_('Usar STARTTLS en lugar de SSL implícito (recomendado para puerto 587)')
    )
    smtp_username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Usuario SMTP'),
        help_text=_('Usuario para autenticación SMTP (por defecto: email_address)')
    )
    smtp_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Contraseña SMTP'),
        help_text=_('Contraseña o App Password para SMTP (Gmail: requiere App Password si 2FA activo)')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        verbose_name = _('Configuración de Buzón de Correo')
        verbose_name_plural = _('Configuraciones de Buzones de Correo')
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["email_address"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        if self.provider == "gmail":
            return f"{self.nombre} (Gmail: {self.email_address or self.imap_username})"
        return f"{self.nombre} ({self.imap_username}@{self.imap_host}:{self.imap_port}/{self.imap_mailbox})"


class Sede(SintelTenantBaseModel):
    """
    Sedes o sucursales de la empresa.
    """
    # WARNING: [ARQ-A2] Excepcion documentada e intencional a SintelTenantBaseModel
    # (que inyecta empresa con on_delete=PROTECT). EmpresaViewSet.destroy() (STAFF/ADMIN
    # unicamente) permite eliminar la Empresa del tenant; Sede es estructura organizativa
    # propia de esa empresa y debe desaparecer junto con ella, no bloquear su eliminacion.
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.CASCADE,
        related_name='sedes',
        verbose_name=_('Empresa'),
        null=False,
        blank=False,
        db_index=True,
    )
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    nombre = models.CharField(max_length=150, verbose_name=_('Nombre'))
    direccion = models.CharField(max_length=255, verbose_name=_('Direccion'), blank=True, default="")
    telefono = models.CharField(max_length=50, verbose_name=_('Telefono'), blank=True, default="")
    encargado_nombre = models.CharField(max_length=150, verbose_name=_('Nombre del Encargado'), blank=True, default="")

    class Meta:
        verbose_name = _('Sede')
        verbose_name_plural = _('Sedes')
        ordering = ['nombre']
        db_table = 'empresa_sede'
        indexes = [
            models.Index(fields=["empresa"]),
            models.Index(fields=["uuid"]),
            models.Index(fields=["nombre"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nombre'],
                name='unique_sede_nombre_per_empresa'
            )
        ]

    def __str__(self):
        return f"{self.nombre}"


class Area(SintelTenantBaseModel):
    """
    Areas o departamentos operativos dentro de una Sede.
    """
    # WARNING: [ARQ-A2] Excepcion documentada e intencional a SintelTenantBaseModel
    # (que inyecta empresa con on_delete=PROTECT). EmpresaViewSet.destroy() (STAFF/ADMIN
    # unicamente) permite eliminar la Empresa del tenant; Area es estructura organizativa
    # propia de esa empresa y debe desaparecer junto con ella, no bloquear su eliminacion.
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.CASCADE,
        related_name='areas',
        verbose_name=_('Empresa'),
        null=False,
        blank=False,
        db_index=True,
    )
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name='areas',
        verbose_name=_('Sede'),
        help_text=_('Sede a la que pertenece esta area')
    )
    nombre = models.CharField(max_length=150, verbose_name=_('Nombre'))
    codigo_funcionamiento = models.CharField(
        max_length=50,
        verbose_name=_('Codigo de Funcionamiento'),
        help_text=_('Codigo unico identificador del area dentro de la sede')
    )

    class Meta:
        verbose_name = _('Area')
        verbose_name_plural = _('Areas')
        ordering = ['nombre']
        db_table = 'empresa_area'
        indexes = [
            models.Index(fields=["empresa"]),
            models.Index(fields=["uuid"]),
            models.Index(fields=["nombre"]),
            models.Index(fields=["codigo_funcionamiento"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['sede', 'nombre'],
                name='unique_area_nombre_per_sede'
            ),
            models.UniqueConstraint(
                fields=['sede', 'codigo_funcionamiento'],
                name='unique_area_codigo_per_sede'
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.sede.nombre})"

