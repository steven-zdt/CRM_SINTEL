"""
Selectors for ConfiguracionCotizacion v2.62.0 - Zero Waste Queries.
"""
from ..models import ConfiguracionCotizacion

class ConfiguracionSelector:
    @staticmethod
    def get_list(empresa_id):
        """Retorna listado optimizado de configuraciones."""
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id
        ).only(
            'id', 'uuid', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'semilla_inicial', 'ultimo_numero'
        ).order_by('nombre_configuracion')

    @staticmethod
    def get_detail(config_uuid, empresa_id):
        """Retorna detalle de una configuracion por UUID."""
        return ConfiguracionCotizacion.objects.filter(
            uuid=config_uuid,
            empresa_id=empresa_id
        ).only(
            'id', 'uuid', 'nombre_configuracion', 'es_activo', 'dias_validez',
            'prefijo_secuencia', 'sufijo_secuencia', 'semilla_inicial', 'ultimo_numero'
        ).first()

    @staticmethod
    def get_activa_for_empresa(empresa_id):
        """Retorna configuraciones activas."""
        return ConfiguracionCotizacion.objects.filter(
            empresa_id=empresa_id,
            es_activo=True
        ).only('id', 'uuid', 'nombre_configuracion')
