"""
Script para poblar los regímenes de renta en el catálogo DIAN.
Ejecutar: python scripts/poblar_regimenes_renta.py
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.public.impuestos.models import RegimenRenta, ContribuyenteTipo, ResponsabilidadRUT

def poblar_regimenes_renta():
    """Pobla los regímenes de renta en el esquema public."""
    with schema_context('public'):
        print('Poblando regímenes de renta...')
        
        regimenes_renta = [
            {
                'codigo': RegimenRenta.ORD,
                'nombre': 'Régimen Ordinario',
                'descripcion': 'Régimen tributario ordinario según la DIAN',
                'tarifa_base_pj': 33.00,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
            {
                'codigo': RegimenRenta.RTE,
                'nombre': 'Régimen Tributario Especial (RTE)',
                'descripcion': 'Régimen Tributario Especial según Ley 1943 de 2018',
                'tarifa_base_pj': None,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
            {
                'codigo': RegimenRenta.SIMPLE,
                'nombre': 'Régimen Simple de Tributación (SIMPLE)',
                'descripcion': 'Régimen Simple de Tributación según Ley 1819 de 2016',
                'tarifa_base_pj': None,
                'requiere_facturacion_electronica': True,
                'aplica_retenciones': True,
            },
        ]

        for regimen_data in regimenes_renta:
            regimen, created = RegimenRenta.objects.get_or_create(
                codigo=regimen_data['codigo'],
                defaults={
                    'nombre': regimen_data['nombre'],
                    'descripcion': regimen_data['descripcion'],
                    'tarifa_base_pj': regimen_data['tarifa_base_pj'],
                    'requiere_facturacion_electronica': regimen_data['requiere_facturacion_electronica'],
                    'aplica_retenciones': regimen_data['aplica_retenciones'],
                    'activo': True,
                }
            )
            if created:
                print(f'  Creado: {regimen.codigo} - {regimen.nombre}')
            else:
                if not regimen.activo:
                    regimen.activo = True
                    regimen.save()
                    print(f'  Reactivado: {regimen.codigo} - {regimen.nombre}')
                else:
                    print(f'  Ya existe: {regimen.codigo} - {regimen.nombre}')

def poblar_tipos_contribuyente():
    """Pobla los tipos de contribuyente en el esquema public."""
    with schema_context('public'):
        print('\nPoblando tipos de contribuyente...')
        
        tipos_contribuyente = [
            {
                'clase': 'PN',
                'nombre': 'Persona Natural',
                'descripcion': 'Persona natural según clasificación DIAN',
            },
            {
                'clase': 'PJ',
                'nombre': 'Persona Jurídica',
                'descripcion': 'Persona jurídica según clasificación DIAN',
            },
        ]

        for tipo_data in tipos_contribuyente:
            tipo, created = ContribuyenteTipo.objects.get_or_create(
                clase=tipo_data['clase'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'activo': True,
                }
            )
            if created:
                print(f'  Creado: {tipo.clase} - {tipo.nombre}')
            else:
                if not tipo.activo:
                    tipo.activo = True
                    tipo.save()
                    print(f'  Reactivado: {tipo.clase} - {tipo.nombre}')
                else:
                    print(f'  Ya existe: {tipo.clase} - {tipo.nombre}')

def poblar_responsabilidades_rut():
    """Pobla las responsabilidades RUT en el esquema public."""
    with schema_context('public'):
        print('\nPoblando responsabilidades RUT...')
        
        responsabilidades = [
            {'codigo': '48', 'nombre': 'Responsable de IVA', 'descripcion': 'Responsable del Impuesto al Valor Agregado'},
            {'codigo': '49', 'nombre': 'No responsable de IVA', 'descripcion': 'No responsable del Impuesto al Valor Agregado'},
            {'codigo': '47', 'nombre': 'Responsable de IVA como agente de retención', 'descripcion': 'Responsable de IVA como agente de retención (Régimen SIMPLE)'},
            {'codigo': '52', 'nombre': 'Gran contribuyente', 'descripcion': 'Gran contribuyente según DIAN'},
            {'codigo': '13', 'nombre': 'Obligado a facturar electrónicamente', 'descripcion': 'Obligado a facturar electrónicamente'},
        ]

        for resp_data in responsabilidades:
            resp, created = ResponsabilidadRUT.objects.get_or_create(
                codigo=resp_data['codigo'],
                defaults={
                    'nombre': resp_data['nombre'],
                    'descripcion': resp_data['descripcion'],
                    'activo': True,
                }
            )
            if created:
                print(f'  Creado: {resp.codigo} - {resp.nombre}')
            else:
                if not resp.activo:
                    resp.activo = True
                    resp.save()
                    print(f'  Reactivado: {resp.codigo} - {resp.nombre}')
                else:
                    print(f'  Ya existe: {resp.codigo} - {resp.nombre}')

if __name__ == '__main__':
    print('=' * 60)
    print('Poblando catálogo DIAN (Regimenes, Tipos, Responsabilidades)')
    print('=' * 60)
    
    poblar_regimenes_renta()
    poblar_tipos_contribuyente()
    poblar_responsabilidades_rut()
    
    print('\n' + '=' * 60)
    print('Resumen:')
    with schema_context('public'):
        print(f'  - Regimenes de Renta: {RegimenRenta.objects.filter(activo=True).count()}')
        print(f'  - Tipos de Contribuyente: {ContribuyenteTipo.objects.filter(activo=True).count()}')
        print(f'  - Responsabilidades RUT: {ResponsabilidadRUT.objects.filter(activo=True).count()}')
    print('=' * 60)
    print('Listo!')
