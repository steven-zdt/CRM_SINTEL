"""
Configuración de Perfiles v2.60 - SIMPLIFICADO (User-Driven)
# WARNING: v2.60: Refactorizado para modo User-Driven. Solo provee:
1. Lógica de generación de códigos (Prefijo, Sufijo, Semilla)
2. Días de validez de la cotización (1 a 30 días)
"""
import uuid as uuid_module

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel  # auto-inserted by autocorrect
from apps.tenant.empresa.models import Empresa


class ConfiguracionCotizacion(SintelTenantBaseModel):
    """
    # WARNING: v2.60: Modelo simplificado para modo User-Driven.
    
    Campos eliminados (obsoletos en User-Driven):
    - tipo_plantilla, tipo_cotizacion_default
    - iva_porcentaje_default, porcentaje_utilidad_default
    - usa_aiu, aiu_admin_default, aiu_imprevistos_default, aiu_utilidad_default
    - permitir_modelo_equipos, permitir_modelo_materiales, permitir_modelo_servicios
    
    Campos mantenidos:
    - Generación de códigos: prefijo_secuencia, sufijo_secuencia, semilla_inicial, ultimo_numero
    - Configuración básica: empresa, nombre_configuracion, es_activo
    
    Campos nuevos:
    - dias_validez: Días de validez de la cotización (1 a 30 días)
    """
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    # empresa field inherited from SintelTenantBaseModel
    nombre_configuracion = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Configuración'),
        help_text=_('Nombre descriptivo del perfil de configuración')
    )
    es_activo = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Indica si este perfil está activo y disponible para uso')
    )

    # # WARNING: v2.60: Días de Validez de la Cotización
    dias_validez = models.IntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name=_('Días de Validez'),
        help_text=_('Días de validez de la cotización (1 a 30 días). Se usa para calcular automáticamente la fecha de vencimiento.')
    )

    # # WARNING: v2.60: Gestión de Folios Dinámicos por Perfil
    prefijo_secuencia = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_('Prefijo de Secuencia'),
        help_text=_('Prefijo para la numeración (ej: "Cot-", "Fact-")')
    )
    sufijo_secuencia = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_('Sufijo de Secuencia'),
        help_text=_('Sufijo para la numeración (ej: "-2026", "-BOG")')
    )
    semilla_inicial = models.IntegerField(
        default=1,
        verbose_name=_('Semilla Inicial'),
        help_text=_('Número desde el cual empezar la secuencia (ej: 1, 100, 1000)')
    )
    ultimo_numero = models.IntegerField(
        default=0,
        verbose_name=_('Último Número Generado'),
        help_text=_('Último número de secuencia generado para este perfil')
    )

    def __str__(self):
        return f"{self.nombre_configuracion}"

    class Meta: 
        app_label = 'tenant_cotizaciones'
        db_table = 'tenant_cotizaciones_configuracion'
        verbose_name = _('Perfil de Configuración')
        verbose_name_plural = _('Perfiles de Configuración')