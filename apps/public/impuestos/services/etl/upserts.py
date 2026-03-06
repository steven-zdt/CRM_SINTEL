"""
Upserts atómicos para catálogos tributarios.

Garantiza atomicidad con transaction.atomic().
"""
from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any
from apps.public.impuestos.models import (
    TipoImpuesto,
    TarifaIVA,
    ConceptoRetencion,
    CodigoTributario,
    ActividadEconomica,
    NormaTributaria,
    DocumentoFuente,
)


@transaction.atomic
def upsert_catalogs(payload: Dict[str, List[Dict[str, Any]]], documento: DocumentoFuente) -> Dict[str, int]:
    """
    Inserta/actualiza catálogos y normas en un bloque atómico.
    
    Args:
        payload: Dict con listas de entidades a upsert
        documento: DocumentoFuente relacionado
        
    Returns:
        dict con métricas: {'tipos': creados, 'tarifas': creados, ...}
    """
    stats = {
        'tipos_creados': 0,
        'tipos_actualizados': 0,
        'tarifas_creadas': 0,
        'tarifas_actualizadas': 0,
        'retenciones_creadas': 0,
        'retenciones_actualizadas': 0,
        'codigos_creados': 0,
        'codigos_actualizados': 0,
        'actividades_creadas': 0,
        'actividades_actualizadas': 0,
        'normas_creadas': 0,
        'normas_actualizadas': 0,
    }
    
    # Upsert tipos de impuesto
    for tipo_data in payload.get('tipos', []):
        tipo, created = TipoImpuesto.objects.update_or_create(
            codigo=tipo_data['codigo'],
            defaults={
                'nombre': tipo_data['nombre'],
                'descripcion': tipo_data.get('descripcion'),
                'activo': tipo_data.get('activo', True),
                'fecha_vigencia': tipo_data['fecha_vigencia'],
                'fecha_fin_vigencia': tipo_data.get('fecha_fin_vigencia'),
            }
        )
        if created:
            stats['tipos_creados'] += 1
        else:
            stats['tipos_actualizados'] += 1
    
    # Upsert tarifas IVA
    for tarifa_data in payload.get('tarifas', []):
        tarifa, created = TarifaIVA.objects.update_or_create(
            codigo=tarifa_data['codigo'],
            fecha_vigencia=tarifa_data['fecha_vigencia'],
            defaults={
                'nombre': tarifa_data['nombre'],
                'porcentaje': tarifa_data['porcentaje'],
                'tipo_tarifa': tarifa_data.get('tipo_tarifa', 'general'),
                'descripcion': tarifa_data.get('descripcion'),
                'activo': tarifa_data.get('activo', True),
                'fecha_fin_vigencia': tarifa_data.get('fecha_fin_vigencia'),
            }
        )
        if created:
            stats['tarifas_creadas'] += 1
        else:
            stats['tarifas_actualizadas'] += 1
    
    # Upsert conceptos de retención
    for retencion_data in payload.get('retenciones', []):
        retencion, created = ConceptoRetencion.objects.update_or_create(
            codigo=retencion_data['codigo'],
            fecha_vigencia=retencion_data['fecha_vigencia'],
            defaults={
                'nombre': retencion_data['nombre'],
                'tipo_retencion': retencion_data.get('tipo_retencion', 'otro'),
                'porcentaje': retencion_data.get('porcentaje'),
                'base_minima': retencion_data.get('base_minima', 0),
                'descripcion': retencion_data.get('descripcion'),
                'activo': retencion_data.get('activo', True),
                'fecha_fin_vigencia': retencion_data.get('fecha_fin_vigencia'),
            }
        )
        if created:
            stats['retenciones_creadas'] += 1
        else:
            stats['retenciones_actualizadas'] += 1
    
    # Upsert códigos tributarios
    for codigo_data in payload.get('codigos', []):
        codigo, created = CodigoTributario.objects.update_or_create(
            codigo=codigo_data['codigo'],
            tipo=codigo_data['tipo'],
            defaults={
                'nombre': codigo_data['nombre'],
                'descripcion': codigo_data.get('descripcion'),
                'activo': codigo_data.get('activo', True),
                'fecha_vigencia': codigo_data.get('fecha_vigencia', timezone.now().date()),
                'fecha_fin_vigencia': codigo_data.get('fecha_fin_vigencia'),
            }
        )
        if created:
            stats['codigos_creados'] += 1
        else:
            stats['codigos_actualizados'] += 1
    
    # Upsert actividades económicas
    for actividad_data in payload.get('actividades', []):
        actividad, created = ActividadEconomica.objects.update_or_create(
            codigo=actividad_data['codigo'],
            defaults={
                'nombre': actividad_data['nombre'],
                'descripcion': actividad_data.get('descripcion'),
                'activo': actividad_data.get('activo', True),
            }
        )
        if created:
            stats['actividades_creadas'] += 1
        else:
            stats['actividades_actualizadas'] += 1
    
    # Upsert normas tributarias
    for norma_data in payload.get('normas', []):
        # Construir defaults
        defaults = {
            'tema': norma_data.get('tema'),
            'impuesto': norma_data.get('impuesto'),
            'vigencia_desde': norma_data.get('vigencia_desde'),
            'vigencia_hasta': norma_data.get('vigencia_hasta'),
            'texto_plano': norma_data['texto_plano'],
            'texto_html': norma_data.get('texto_html'),
            'referencias': norma_data.get('referencias', []),
        }
        
        # Buscar por documento + artículo + tema + impuesto
        lookup = {
            'documento_fuente': documento,
            'articulo': norma_data.get('articulo'),
            'tema': norma_data.get('tema'),
            'impuesto': norma_data.get('impuesto'),
        }
        
        # Si no hay artículo, usar solo documento + tema
        if not lookup['articulo']:
            lookup.pop('articulo')
        
        norma, created = NormaTributaria.objects.update_or_create(
            **lookup,
            defaults=defaults
        )
        if created:
            stats['normas_creadas'] += 1
        else:
            stats['normas_actualizadas'] += 1
    
    return stats
