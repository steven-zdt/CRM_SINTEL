from django.apps import AppConfig


class FacturasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant.facturas'
    verbose_name = 'Facturas'

    def ready(self) -> None:
        """
        MAIL-16: registra InvoiceHandler en el DocumentDispatcher compartido.

        Facturas se auto-anuncia como consumidor del Document Intake Service --
        maildigester (y cualquier otro productor) nunca necesita importar Facturas
        para saber que este handler existe.
        """
        from apps.tenant.facturas.document_intake import register
        register()
