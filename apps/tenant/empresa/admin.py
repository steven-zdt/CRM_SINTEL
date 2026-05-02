"""
Admin para la app empresa (por tenant).

# WARNING: v2.40: Alineado con arquitectura Tabulator Factory.
"""
from django.contrib import admin

from .models import Empresa, MailInboxConfig


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
    """
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
