"""
Serializers para Configuración de Cotizaciones v2.60 - SIMPLIFICADO (User-Driven).

# WARNING: v2.60: Serializers simplificados para modo User-Driven.
Solo exponen: generación de códigos y días de validez.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import ConfiguracionCotizacion


class ConfiguracionCotizacionListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado Tabulator v2.60.
    
    # WARNING: v2.60: Mínima exposición para alto rendimiento en grillas remotas.
    Solo campos esenciales: nombre, días de validez, estado, empresa.
    """
    empresa_nombre = serializers.CharField(source='empresa.razon_social', read_only=True)
    estado_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ConfiguracionCotizacion
        fields = (
            'id', 'uuid', 'empresa', 'empresa_nombre',
            'nombre_configuracion',
            'dias_validez',
            'es_activo', 'estado_display',
            'ultimo_numero',
        )
        read_only_fields = ('id', 'uuid', 'empresa', 'empresa_nombre', 'estado_display', 'ultimo_numero')
    
    def get_estado_display(self, obj):
        """Retorna el estado en formato legible para el frontend."""
        return "Activo" if obj.es_activo else "Inactivo"


class ConfiguracionCotizacionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de perfil de configuración v2.60 - SIMPLIFICADO.
    
    # WARNING: v2.60: CRUD completo de perfiles de configuración.
    Solo incluye: generación de códigos y días de validez.
    """
    empresa_nombre = serializers.CharField(source='empresa.razon_social', read_only=True)
    estado_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ConfiguracionCotizacion
        fields = (
            'id', 'uuid', 'empresa', 'empresa_nombre',
            'nombre_configuracion',
            'dias_validez',
            'es_activo', 'estado_display',
            'prefijo_secuencia',
            'sufijo_secuencia',
            'semilla_inicial',
            'ultimo_numero',
        )
        read_only_fields = ('id', 'uuid', 'empresa', 'empresa_nombre', 'estado_display', 'ultimo_numero')
    
    def get_estado_display(self, obj):
        """Retorna el estado en formato legible para el frontend."""
        return "Activo" if obj.es_activo else "Inactivo"
    
    def validate_nombre_configuracion(self, value):
        """
        # WARNING: v2.60: Zero Trust - Sanitización de nombre de configuración.
        - Eliminar espacios al inicio y final
        - Eliminar espacios múltiples
        - Validar longitud mínima y máxima
        """
        if not value:
            raise serializers.ValidationError(_('El nombre de configuración es obligatorio.'))
        
        # Sanitización: strip y normalización de espacios
        nombre_limpio = ' '.join(str(value).strip().split())
        
        if len(nombre_limpio) < 3:
            raise serializers.ValidationError(_('El nombre debe tener al menos 3 caracteres.'))
        
        if len(nombre_limpio) > 100:
            raise serializers.ValidationError(_('El nombre no puede exceder 100 caracteres.'))
        
        return nombre_limpio
    
    def validate_dias_validez(self, value):
        """
        # WARNING: v2.60: Zero Trust - Validación de días de validez.
        Debe estar entre 1 y 30 días.
        """
        if value is not None:
            if value < 1 or value > 30:
                raise serializers.ValidationError(_('Los días de validez deben estar entre 1 y 30 días.'))
        return value
    
    def validate(self, data):
        """
        # WARNING: SSoT v2.60: Validaciones del perfil de configuración simplificado.
        - Validar unicidad de nombre_configuracion por empresa
        - Validar que dias_validez esté entre 1 y 30 (ya validado en validate_dias_validez, pero por seguridad)
        - La empresa se obtiene del tenant actual (singleton), nunca del payload
        """
        # # WARNING: SSoT: Eliminar 'empresa' del data si fue enviado por error
        data.pop('empresa', None)
        data.pop('empresa_id', None)
        
        # # WARNING: SSoT v2.60: Obtener empresa del tenant actual (singleton)
        # La empresa se obtiene del tenant, no del usuario
        from apps.tenant.empresa.models import Empresa
        
        empresa = None
        if self.instance:
            # Si es actualización, usar la empresa del instance
            empresa = self.instance.empresa
        else:
            request = self.context.get('request')
            if request:
                empresa = getattr(request, 'empresa', None)
                if not empresa:
                    tenant = getattr(request, 'tenant', None)
                    empresa = getattr(tenant, 'empresa', None)
            if not empresa:
                empresa = Empresa.objects.only('id').first()
            if not empresa:
                raise serializers.ValidationError({
                    'detail': _('No se encontró la empresa del tenant. Por favor, configure la empresa primero.')
                })
        
        # Validar unicidad de nombre_configuracion por empresa
        nombre_configuracion = data.get('nombre_configuracion')
        
        if nombre_configuracion and empresa:
            queryset = ConfiguracionCotizacion.objects.filter(
                empresa=empresa,
                nombre_configuracion=nombre_configuracion
            )
            
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'nombre_configuracion': _('Ya existe un perfil de configuración con este nombre para esta empresa.')
                })
        
        # Validar que dias_validez esté entre 1 y 30 (validación adicional por seguridad)
        dias_validez = data.get('dias_validez')
        if dias_validez is not None:
            if dias_validez < 1 or dias_validez > 30:
                raise serializers.ValidationError({
                    'dias_validez': _('Los días de validez deben estar entre 1 y 30 días.')
                })
        
        return data
