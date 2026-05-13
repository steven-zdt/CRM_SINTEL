"""
CRUD Service for ConfiguracionCotizacion v2.62.0.
"""
from django.db import transaction
from ..models import ConfiguracionCotizacion

class ConfiguracionCRUDService:
    @staticmethod
    @transaction.atomic
    def create_configuracion(empresa, **datos):
        """Crea una nueva configuracion."""
        return ConfiguracionCotizacion.objects.create(
            empresa=empresa,
            **datos
        )

    @staticmethod
    @transaction.atomic
    def update_configuracion(instance, **datos):
        """Actualiza una configuracion existente."""
        for attr, value in datos.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def delete_configuracion(instance):
        """Elimina una configuracion."""
        instance.delete()
