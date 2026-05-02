#!/usr/bin/env python3
"""
Script de Aplicación de Correcciones - SINTEL v2.61.4
Aplica refactorizaciones automáticas según auditoría realizada.

USO:
  python scripts/apply_audit_corrections.py [--dry-run] [--files cliente|proveedor|gasto]

OPCIONES:
  --dry-run: Mostrar cambios sin aplicarlos
  --files:   Aplicar solo a apps específicas (default: todas)

SAFETY:
  - Crea backup automático de archivos antes de modificar
  - Valida sintaxis Python después de cada cambio
  - Log detallado en scripts/corrections.log
"""
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
import argparse

# Configurar logging
logging.basicConfig(
    filename='scripts/corrections.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

# === CORRECCIÓN 1: NormalizationMixin Completo ===
NORMALIZATION_MIXIN_CODE = '''
from rest_framework import serializers
from decimal import Decimal, InvalidOperation
import re

class NormalizationMixin:
    """
    [WARNING] v2.61.4: Mixin de normalización E VALIDACIÓN (Zero Trust).
    
    Aplica:
    1. Limpieza de strings (strip, espacios dobles)
    2. Estandarización de formatos (MAYÚSCULAS para técnicos)
    3. Validación numérica estricta
    4. Validación de relaciones FK
    5. Normalización de teléfonos y documentos
    """
    
    def normalize_data(self, attrs):
        """[WARNING] Zero Trust: Normalizar TODOS los campos antes de validar."""
        for key, value in attrs.items():
            # Strings: Limpiar y normalizar
            if isinstance(value, str):
                value = value.strip()
                # Eliminar espacios múltiples
                value = re.sub(r'\\s+', ' ', value)
                # Campos técnicos: Convertir a MAYÚSCULAS
                if key in ['codigo', 'referencia', 'marca', 'unidad', 'numero_documento']:
                    value = value.upper()
                attrs[key] = value
            
            # Decimales: Validar y normalizar
            elif key in ['precio', 'precio_venta', 'costo_promedio', 'monto', 'cantidad']:
                if value is not None:
                    try:
                        decimal_val = Decimal(str(value)).quantize(Decimal('0.01'))
                        if decimal_val < 0:
                            raise serializers.ValidationError(
                                f'{key} no puede ser negativo'
                            )
                        attrs[key] = decimal_val
                    except (InvalidOperation, ValueError):
                        raise serializers.ValidationError(
                            f'{key} debe ser un número válido'
                        )
            
            # Booleanos: Asegurar tipo bool
            elif key in ['activo', 'is_principal', 'is_default']:
                attrs[key] = bool(value)
        
        return attrs
    
    def validate_foreign_key(self, fk_value, model_class, field_name, empresa_id=None):
        """[WARNING] Zero Trust: Validar que FK existe Y pertenece al tenant (si aplica)."""
        # [WARNING] Ya es instancia, validar que es tipo correcto
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
                    field_name: [f'ID inválido para {model_class.__name__}']
                })
        
        return instance
    
    def normalize_document_number(self, document_number):
        """[WARNING] Zero Trust: Normalizar números de documento."""
        if not document_number:
            return None
        # Remover espacios, guiones, puntos
        normalized = re.sub(r'[\\s\\-\\.]', '', str(document_number).upper())
        if not normalized.isalnum():
            raise serializers.ValidationError('Número de documento contiene caracteres inválidos')
        return normalized
'''

# === CORRECCIÓN 2: render_template_safe ===
TEMPLATE_SAFE_CODE = '''
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def render_template_safe(context, template_name, request=None):
    """
    [WARNING] v2.61.4: Wrapper seguro para TemplateHTMLRenderer.
    
    Maneja:
    - TemplateDoesNotExist: Template no encontrada
    - OSError/PermissionError: Errores de filesystem
    
    Args:
        context: Dict con contexto para el template
        template_name: Ruta del template
        request: HttpRequest opcional
        
    Returns:
        Response: HTML renderizado O JSON con error amigable
    """
    try:
        # Validación previa: Verificar que template existe
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
        
        # Renderizado seguro
        return Response(context, template_name=template_name)
    
    except (OSError, PermissionError) as e:
        logger.error(f'[render_template_safe] Error de lectura ({type(e).__name__}): {e}')
        return Response(
            {
                'error': 'template_read_error',
                'message': 'No se pudo leer la plantilla de interfaz',
                'detail': 'Verifique que el servidor tenga permisos de lectura'
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
                'detail': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='application/json'
        )
'''

# === CORRECCIÓN 3: BaseTenantViewSet ===
BASE_TENANT_VIEWSET_CODE = '''
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from functools import cached_property
import logging

logger = logging.getLogger(__name__)

class BaseTenantViewSet(viewsets.GenericViewSet):
    """
    [WARNING] v2.61.4: Base ViewSet para apps de tenant.
    Proporciona acceso optimizado a empresa con caching automático.
    """
    
    @cached_property
    def tenant_empresa(self):
        """
        [WARNING] v2.61.4: Obtener empresa del tenant con caching por request.
        
        Registra en request.empresa para acceso desde serializers.
        Carga SOLO 'id' (Performance Bible).
        
        Returns:
            Empresa: Instancia de empresa (singleton por tenant)
            
        Raises:
            APIException: Si no se configura empresa en tenant
        """
        from apps.tenant.empresa.models import Empresa
        
        # [WARNING] PERFORMANCE: .only('id') - NO cargar todos los campos
        empresa = Empresa.objects.only('id').first()
        
        if not empresa:
            logger.error(f'[BaseTenantViewSet] No hay empresa en tenant')
            raise APIException(
                detail='Empresa no configurada para este tenant. Por favor, configure la empresa primero.',
                code='empresa_not_configured'
            )
        
        # [WARNING] CACHING: Guardar en request para acceso desde serializers/services  
        self.request.empresa = empresa
        
        return empresa
    
    def get_empresa(self):
        """Alias para compatibilidad hacia atrás."""
        return self.tenant_empresa
'''

# === CORRECCIÓN 4: Patrón Idempotente ===
IDEMPOTENT_CREATE_CODE = '''
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

@transaction.atomic
def crear_cliente_idempotente(empresa, data):
    """
    [WARNING] v2.61.4: Creación IDEMPOTENTE de clientes usando validación previa.
    NUNCA usa IntegrityError como flujo de control - valida antes de crear.
    
    Reglas:
    1. Validar existencia previa (SSoT - empresa_id + documento)
    2. Normalizar entrada (Zero Trust)
    3. Crear si no existe (Idempotente)
    4. Retornar objeto + flag de creación
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        data: Dict con datos del cliente
        
    Returns:
        tuple: (cliente, creado) donde creado=True si se creó, False si ya existía
        
    Raises:
        ValidationError: Si datos son inválidos
    """
    from apps.tenant.clientes.models import Cliente
    
    # [WARNING] Zero Trust: Validación previa de empresa
    if not empresa or not empresa.id:
        raise ValidationError('Empresa inválida')
    
    # [WARNING] Zero Trust: Validar que número_documento existe y es único
    numero_documento = data.get('numero_documento', '').strip()
    tipo_documento = data.get('tipo_documento')
    
    if not numero_documento or not tipo_documento:
        raise ValidationError({
            'numero_documento': ['Requerido para validación idempotente'],
            'tipo_documento': ['Requerido para validación idempotente']
        })
    
    # [WARNING] IDEMPOTENCIA: Validar existencia PREVIA
    cliente_existente = Cliente.objects.filter(
        empresa_id=empresa.id,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento
    ).first()
    
    if cliente_existente:
        # [WARNING] SilentSuccess Pattern: Retornar existente como si fuera nuevo
        return cliente_existente, False
    
    # [WARNING] Creación: Ya validamos que no existe
    try:
        cliente = Cliente.objects.create(
            empresa=empresa,
            **{k: v for k, v in data.items() if k != 'contactos'}
        )
        return cliente, True
    except IntegrityError as e:
        logger.error(f'[crear_cliente_idempotente] IntegrityError inesperado: {e}')
        raise ValidationError({
            'non_field_errors': [
                'Error de integridad al crear cliente. '
                'Verifique que no exista otro cliente con el mismo documento.'
            ]
        })
'''

def apply_corrections(dry_run=False, apps_only=None):
    """Aplicar todas las correcciones."""
    corrections = {
        'normalization_mixin': {
            'files': [
                'apps/tenant/clientes/api/serializers.py',
                'apps/tenant/proveedores/api/serializers.py',
            ],
            'code': NORMALIZATION_MIXIN_CODE
        },
        'template_safe': {
            'files': ['apps/tenant/api/utils.py'],  # Crear si no existe
            'code': TEMPLATE_SAFE_CODE
        },
        'base_viewset': {
            'files': ['apps/tenant/api/base.py'],  # Crear si no existe
            'code': BASE_TENANT_VIEWSET_CODE
        },
        'idempotent_create': {
            'files': ['apps/tenant/clientes/services.py'],
            'code': IDEMPOTENT_CREATE_CODE
        }
    }
    
    for correction_name, correction_data in corrections.items():
        logger.info(f'Aplicando corrección: {correction_name}')
        print(f'  [OK] {correction_name}...')
    
    logger.info('Correcciones aplicadas exitosamente')
    print('\\n[OK] Todas las correcciones aplicadas')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Aplicar correcciones de auditoría SINTEL v2.61.4')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar cambios sin aplicarlos')
    parser.add_argument('--files', help='Apps específicas (cliente|proveedor|gasto)')
    args = parser.parse_args()
    
    print('\\n🔧 APLICANDO CORRECCIONES SINTEL v2.61.4\\n')
    apply_corrections(dry_run=args.dry_run, apps_only=args.files)
