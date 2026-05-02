"""
Utilidades Generales para Tenant APIs v2.61.4

Componentes reutilizables:
- render_template_safe(): Wrapper robusto para TemplateHTMLRenderer
- NormalizationMixin: Validación y normalización Zero Trust completa
- Error handlers para integridad de datos
"""
import logging
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from rest_framework import serializers, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ============================================================================
# RENDERIZADO SEGURO DE TEMPLATES
# ============================================================================
def render_template_safe(context, template_name, request=None):
    """
    # WARNING: v2.61.4: Wrapper seguro para TemplateHTMLRenderer.
    
    Maneja:
    - TemplateDoesNotExist: Template no encontrada
    - OSError: Errores de lectura del filesystem
    - PermissionError: Permisos insuficientes
    
    Args:
        context: Dict con contexto para el template
        template_name: Ruta del template (ej: 'tenant/core/partials/...')
        request: HttpRequest para build_absolute_uri() en serializers
        
    Returns:
        Response: HTML renderizado O JSON con error amigable
        
    Raises:
        Exception: Solo si es error irrecuperable del sistema
        
    Ejemplo:
        return render_template_safe(
            {'cliente': cliente, 'contactos': contactos},
            'tenant/core/partials/clientes/offcanvas_form.html',
            request=request
        )
    """
    try:
        # # WARNING: Validación previa: Verificar que template existe
        try:
            get_template(template_name)
        except TemplateDoesNotExist:
            logger.error(f'[render_template_safe] Template no encontrada: {template_name}')
            return Response(
                {
                    'error': 'template_not_found',
                    'message': f'Template no encontrada: {template_name}',
                    'detail': 'El fichero de interfaz no está disponible. Por favor, contacte al administrador.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type='application/json'
            )
        
        # # WARNING: Renderizado seguro
        return Response(context, template_name=template_name)
    
    except (OSError, PermissionError) as e:
        logger.error(f'[render_template_safe] Error de lectura ({type(e).__name__}): {e}')
        return Response(
            {
                'error': 'template_read_error',
                'message': 'No se pudo leer la plantilla de interfaz',
                'detail': 'Verifique que el servidor tenga permisos de lectura en el directorio de templates'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='application/json'
        )
    
    except Exception as e:
        logger.critical(f'[render_template_safe] Error inesperado: {e}', exc_info=True)
        return Response(
            {
                'error': 'unexpected_error',
                'message': 'Error inesperado al renderizar plantilla',
                'detail': str(e) if not getattr(settings, 'PRODUCTION', False) else 'Por favor, contacte al administrador'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='application/json'
        )


# ============================================================================
# NORMALIZACIÓN Y VALIDACIÓN ZERO TRUST
# ============================================================================
class NormalizationMixin:
    """
    # WARNING: v2.61.4: Mixin de normalización E VALIDACIÓN (Zero Trust).
    
    Aplica:
    1. Limpieza de strings (strip, espacios dobles, sanitización)
    2. Estandarización de formatos (MAYÚSCULAS para técnicos)
    3. Validación numérica estricta
    4. Validación de relaciones FK
    5. Normalización de documentos
    
    Uso:
        class MiSerializer(NormalizationMixin, serializers.ModelSerializer):
            def validate(self, attrs):
                attrs = self.normalize_data(attrs)
                # Validaciones adicionales...
                return attrs
    """
    
    def normalize_data(self, attrs):
        """
        # WARNING: Zero Trust: Normalizar TODOS los campos antes de validar.
        
        Procesa:
        - Strings: .strip(), espacios múltiples, MAYÚSCULAS para técnicos
        - Decimales: Validación numérica con rango y precisión
        - Booleanos: Conversión explícita a bool
        """
        for key, value in attrs.items():
            # ============= STRINGS =============
            if isinstance(value, str):
                value = value.strip()
                # Eliminar espacios múltiples
                value = re.sub(r'\s+', ' ', value)
                # Campos técnicos (código, referencia, marca, unidad): Convertir a MAYÚSCULAS
                if key in ['codigo', 'referencia', 'marca', 'unidad', 'numero_documento', 'nit']:
                    value = value.upper()
                attrs[key] = value
            
            # ============= DECIMALES =============
            elif key in ['precio', 'precio_venta', 'costo_promedio', 'monto', 'cantidad', 
                        'valor', 'total', 'base_imponible', 'impuesto']:
                if value is not None:
                    try:
                        decimal_val = Decimal(str(value)).quantize(Decimal('0.01'))
                        if decimal_val < 0:
                            raise serializers.ValidationError(
                                f'{key} no puede ser negativo'
                            )
                        attrs[key] = decimal_val
                    except (InvalidOperation, ValueError, TypeError):
                        raise serializers.ValidationError(
                            f'{key} debe ser un número válido (recibido: {value})'
                        )
            
            # ============= BOOLEANOS =============
            elif key in ['activo', 'is_principal', 'is_default', 'retenido', 'facturado']:
                if value is not None:
                    attrs[key] = bool(value)
        
        return attrs
    
    def validate_foreign_key(self, fk_value, model_class, field_name, empresa_id=None):
        """
        # WARNING: Zero Trust: Validar que FK existe Y pertenece al tenant (si aplica).
        
        Args:
            fk_value: Valor de la FK (puede ser int o Instance)
            model_class: Clase del modelo a validar
            field_name: Nombre del campo para error message
            empresa_id: Si presente, validar que registro pertenece a empresa (SSoT)
            
        Returns:
            Instance: Objeto validado
            
        Raises:
            ValidationError: Si no existe o no pertenece al tenant
            
        Ejemplo:
            categoria = self.validate_foreign_key(
                attrs.get('categoria'),
                CategoriaProducto,
                'categoria',
                empresa_id=self.context.get('empresa_id')
            )
        """
        # # WARNING: Ya es instancia, validar que es tipo correcto
        if hasattr(fk_value, 'pk') and isinstance(fk_value, model_class):
            instance = fk_value
        else:
            # Es ID, traer objeto
            try:
                if empresa_id:
                    instance = model_class.objects.filter(
                        pk=fk_value,
                        empresa_id=empresa_id
                    ).first()
                    if not instance:
                        raise serializers.ValidationError({
                            field_name: [f'{model_class.__name__} no encontrado o no pertenece a esta empresa']
                        })
                else:
                    instance = model_class.objects.get(pk=fk_value)
            except model_class.DoesNotExist:
                raise serializers.ValidationError({
                    field_name: [f'{model_class.__name__} con ID {fk_value} no existe']
                })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    field_name: [f'ID inválido para {model_class.__name__} (recibido: {fk_value})']
                })
        
        return instance
    
    def normalize_document_number(self, document_number):
        """
        # WARNING: Zero Trust: Normalizar números de documento.
        
        Procesa:
        - Remover espacios, guiones, puntos
        - Validar caracteres alfanuméricos
        
        Args:
            document_number: Número de documento (ej: "123-456-789")
            
        Returns:
            str: Documento normalizado (ej: "123456789")
            
        Raises:
            ValidationError: Si documento contiene caracteres inválidos
        """
        if not document_number:
            return None
        # Remover espacios, guiones, puntos
        normalized = re.sub(r'[\s\-\.]', '', str(document_number).upper())
        if not normalized.isalnum():
            raise serializers.ValidationError('Número de documento contiene caracteres inválidos')
        return normalized
    
    def normalize_phone(self, phone_number):
        """
        # WARNING: Zero Trust: Normalizar números telefónicos.
        
        Procesa:
        - Remover espacios, guiones, paréntesis
        - Validar que contiene solo digitos y símbolos normales
        """
        if not phone_number:
            return None
        normalized = re.sub(r'[\s\-\(\)\.]+', '', str(phone_number))
        if not re.match(r'^\+?[\d\*\#]+$', normalized):
            raise serializers.ValidationError('Número telefónico contiene caracteres inválidos')
        return normalized
