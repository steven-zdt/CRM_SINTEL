"""
Configuracion de Perfiles v2.60 - SIMPLIFICADO (User-Driven)
# WARNING: v2.60: Refactorizado para modo User-Driven. Solo provee:
1. Logica de generacion de codigos (Prefijo, Sufijo, Semilla)
2. Dias de validez de la cotizacion (1 a 30 dias)
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
    - Generacion de codigos: prefijo_secuencia, sufijo_secuencia, semilla_inicial, ultimo_numero
    - Configuracion basica: empresa, nombre_configuracion, es_activo
    
    Campos nuevos:
    - dias_validez: Dias de validez de la cotizacion (1 a 30 dias)
    """
    uuid = models.UUIDField(default=uuid_module.uuid4, unique=True, db_index=True, editable=False)

    # empresa field inherited from SintelTenantBaseModel
    nombre_configuracion = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Configuracion'),
        help_text=_('Nombre descriptivo del perfil de configuracion')
    )
    es_activo = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Indica si este perfil esta activo y disponible para uso')
    )

    # # WARNING: v2.60: Dias de Validez de la Cotizacion
    dias_validez = models.IntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name=_('Dias de Validez'),
        help_text=_('Dias de validez de la cotizacion (1 a 30 dias). Se usa para calcular automaticamente la fecha de vencimiento.')
    )

    # # WARNING: v2.60: Gestion de Folios Dinamicos por Perfil
    prefijo_secuencia = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_('Prefijo de Secuencia'),
        help_text=_('Prefijo para la numeracion (ej: "Cot-", "Fact-")')
    )
    sufijo_secuencia = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_('Sufijo de Secuencia'),
        help_text=_('Sufijo para la numeracion (ej: "-2026", "-BOG")')
    )
    semilla_inicial = models.IntegerField(
        default=1,
        verbose_name=_('Semilla Inicial'),
        help_text=_('Numero desde el cual empezar la secuencia (ej: 1, 100, 1000)')
    )
    ultimo_numero = models.IntegerField(
        default=0,
        verbose_name=_('Ultimo Numero Generado'),
        help_text=_('Ultimo numero de secuencia generado para este perfil')
    )

    def __str__(self):
        return f"{self.nombre_configuracion}"

    class Meta:
        app_label = 'tenant_cotizaciones'
        db_table = 'tenant_cotizaciones_configuracion'
        verbose_name = _('Perfil de Configuracion')
        verbose_name_plural = _('Perfiles de Configuracion')
        constraints = [
            # Antes solo se validaba en ConfiguracionCotizacionDetailSerializer.validate()
            # (query + ValidationError, sin select_for_update) -- misma
            # condicion de carrera real que tenia Producto.codigo antes del
            # fix de hoy (hallazgo real, auditoria de modernizacion,
            # 2026-08-27). nombre_configuracion no es blank=True, a
            # diferencia de Producto.codigo, asi que el constraint no
            # necesita excluir vacios.
            models.UniqueConstraint(
                fields=['empresa', 'nombre_configuracion'],
                name='uniq_configuracion_nombre_por_empresa',
            ),
        ]