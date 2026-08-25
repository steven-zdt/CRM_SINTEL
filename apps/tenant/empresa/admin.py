"""
Admin para la app empresa (por tenant).

# WARNING: v2.40: Alineado con arquitectura Tabulator Factory.
"""
from django import forms
from django.contrib import admin

from .models import Empresa, MailInboxConfig

# WARNING: SEGURIDAD FASE 15: los 5 campos de password (incluido el legacy `password`,
# que NO se cifra -- solo imap_password/smtp_password lo hacen via el serializer) se
# renderizaban con el widget de texto por defecto, mostrando el valor guardado (texto
# plano en el caso legacy, ciphertext Fernet en los nuevos) visible en el admin.
# PasswordInput(render_value=False) deja el campo vacio al cargar la pagina; solo se
# sobreescribe el valor guardado si el operador escribe uno nuevo explicitamente.
_PASSWORD_FIELDS = ("password", "imap_password", "smtp_password")


class MailInboxConfigAdminForm(forms.ModelForm):
    class Meta:
        model = MailInboxConfig
        fields = "__all__"
        widgets = {field: forms.PasswordInput(render_value=False) for field in _PASSWORD_FIELDS}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in _PASSWORD_FIELDS:
            self.fields[field].required = False

    def clean(self):
        # PasswordInput(render_value=False) siempre se muestra vacio en el HTML, asi que un
        # valor no vacio aqui SOLO puede venir de que el operador lo escribio recien -- se
        # cifra con el mismo helper que usa el serializer de la API. Si lo dejo en blanco
        # (el caso normal al editar cualquier otro campo), se conserva el valor ya guardado
        # (que puede ya estar cifrado) en vez de sobreescribirlo con "".
        cleaned = super().clean()
        from apps.services.security.crypto import encrypt_password

        for field in _PASSWORD_FIELDS:
            typed_value = cleaned.get(field)
            if typed_value:
                cleaned[field] = encrypt_password(typed_value)
            elif self.instance.pk:
                cleaned[field] = getattr(self.instance, field)
        return cleaned


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Admin para el modelo Empresa."""
    list_display = ['razon_social', 'nit', 'dv', 'regimen_tributario', 'moneda', 'created_at']
    list_filter = ['regimen_tributario', 'moneda', 'created_at']
    search_fields = ['razon_social', 'nit', 'email_contacto']
    readonly_fields = ['dv', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('razon_social',)
        }),
        ('Datos Fiscales', {
            'fields': ('nit', 'dv', 'regimen_tributario')
        }),
        ('Dirección y Contacto', {
            'fields': ('direccion', 'telefono', 'email_contacto')
        }),
        ('Configuración', {
            'fields': ('moneda', 'logo', 'website')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MailInboxConfig)
class MailInboxConfigAdmin(admin.ModelAdmin):
    """
    Admin para el modelo MailInboxConfig.
    
    # WARNING: v2.40: Alineado con arquitectura Tabulator Factory.
    # WARNING: SEGURIDAD: Passwords nunca se muestran en list_display.
    # WARNING: SEGURIDAD FASE 15: form = MailInboxConfigAdminForm oculta el valor guardado
    # (PasswordInput) y save_model() cifra cualquier password nuevo escrito aqui con el
    # mismo helper que usa el serializer -- el admin ya no puede guardar en texto plano.
    """
    form = MailInboxConfigAdminForm
    list_display = ['nombre', 'email_address', 'provider', 'imap_host', 'imap_port', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active', 'imap_ssl', 'created_at']
    search_fields = ['nombre', 'email_address', 'imap_host', 'imap_username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'email_address', 'provider', 'is_active')
        }),
        ('Configuración IMAP', {
            'fields': (
                'imap_host', 'imap_port', 'imap_ssl', 'imap_starttls',
                'imap_username', 'imap_password', 'imap_mailbox',
                'imap_mark_as_seen', 'imap_move_processed_to', 'imap_max_attachment_mb'
            )
        }),
        ('Configuración SMTP (Opcional)', {
            'fields': (
                'smtp_host', 'smtp_port', 'smtp_ssl', 'smtp_starttls',
                'smtp_username', 'smtp_password'
            ),
            'classes': ('collapse',)
        }),
        ('Campos Legacy (Deprecados)', {
            'fields': (
                'host', 'port', 'protocol', 'ssl', 'username', 'password',
                'mailbox', 'mark_as_seen', 'move_processed_to', 'max_attachment_mb'
            ),
            'classes': ('collapse',),
            'description': '# WARNING: DEPRECADO: Estos campos se mantienen solo para compatibilidad.'
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Passwords nunca se muestran como readonly, pero se ocultan en list_display."""
        readonly = list(self.readonly_fields)
        # No agregar passwords a readonly, se manejan con write_only en serializer
        return readonly
