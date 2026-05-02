from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Configuración de la app accounts (usuarios globales).

    WARNING: ARQUITECTURA: Esta app está en SHARED_APPS (esquema public).
    Los usuarios son globales y se comparten entre todos los tenants.

    WARNING: REGLA DE ORO: NO hacer consultas a la BD en ready().
    - Cualquier lógica que requiera BD debe estar en comandos de management
    - ready() solo debe usarse para cargar signals (sin consultas en import-time)
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public.accounts"
    verbose_name = "Accounts"

    def ready(self):
        """
        Se ejecuta cuando todas las apps están listas.

        WARNING: CRÍTICO: NO hacer consultas a la BD aquí.
        - Esto causa RuntimeWarning: "Accessing the database during app initialization"
        - La lógica de verificación debe estar en comandos de management
        - Solo usar para cargar signals (sin consultas en import-time)
        """
        # Carga segura de señales u otras inicializaciones (sin consultas en import-time)
        # from . import signals  # Asegúrate que signals no haga queries al importar
