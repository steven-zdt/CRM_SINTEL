"""
Script de auditoría para verificar la correcta exposición de segmentos DIAN
desde el modelo ContribuyenteTipo a través del provider.

Verifica:
1. Que el modelo ContribuyenteTipo tenga datos
2. Que el provider get_empresa_form_metadata() incluya segmentos_dian
3. Que la API exponga ContribuyenteTipo correctamente
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.impuestos.models import ContribuyenteTipo
from apps.public.impuestos.services.provider import get_empresa_form_metadata
from django_tenants.utils import schema_context


def audit_contribuyente_tipo_model():
    """Audita el modelo ContribuyenteTipo."""
    print("=" * 80)
    print("AUDITORÍA: Modelo ContribuyenteTipo")
    print("=" * 80)
    
    with schema_context('public'):
        tipos = ContribuyenteTipo.objects.filter(activo=True)
        print(f"\n[OK] Total de tipos activos: {tipos.count()}")
        
        if tipos.exists():
            print("\n[LISTA] Primeros 5 tipos:")
            for obj in tipos[:5]:
                print(f"  - {obj.nombre} ({obj.clase}) - Segmento: {obj.get_segmento_dian_display()}")
        
        # Verificar segmentos únicos
        segmentos_unicos = tipos.values_list('segmento_dian', flat=True).distinct()
        print(f"\n[OK] Segmentos DIAN unicos encontrados: {len(segmentos_unicos)}")
        for seg in sorted(segmentos_unicos):
            # Obtener el display name del primer objeto con ese segmento
            obj = tipos.filter(segmento_dian=seg).first()
            if obj:
                print(f"  - {seg}: {obj.get_segmento_dian_display()}")
    
    print("\n" + "=" * 80)


def audit_provider_metadata():
    """Audita el provider get_empresa_form_metadata()."""
    print("=" * 80)
    print("AUDITORÍA: Provider get_empresa_form_metadata()")
    print("=" * 80)
    
    with schema_context('public'):
        metadata = get_empresa_form_metadata()
        
        # Verificar segmentos_dian
        segmentos_dian = metadata.get('segmentos_dian', [])
        print(f"\n[OK] segmentos_dian encontrados: {len(segmentos_dian)}")
        
        if segmentos_dian:
            print("\n[LISTA] Lista de segmentos_dian:")
            for seg in segmentos_dian:
                print(f"  - {seg['value']}: {seg['label']}")
        else:
            print("[ERROR] segmentos_dian esta vacio o no existe")
        
        # Verificar tipo_contribuyente.segmentos
        tipo_contribuyente = metadata.get('tipo_contribuyente', {})
        segmentos_pn = tipo_contribuyente.get('segmentos', {}).get('PN', [])
        segmentos_pj = tipo_contribuyente.get('segmentos', {}).get('PJ', [])
        
        print(f"\n[OK] Segmentos PN: {len(segmentos_pn)}")
        print(f"[OK] Segmentos PJ: {len(segmentos_pj)}")
    
    print("\n" + "=" * 80)


def audit_api_exposure():
    """Audita la exposición de ContribuyenteTipo en la API."""
    print("=" * 80)
    print("AUDITORÍA: API de ContribuyenteTipo")
    print("=" * 80)
    
    from apps.public.impuestos.api.viewsets import ContribuyenteTipoViewSet
    from apps.public.impuestos.api.serializers import ContribuyenteTipoSerializer
    
    print("\n[OK] ViewSet encontrado: ContribuyenteTipoViewSet")
    print(f"[OK] Serializer encontrado: ContribuyenteTipoSerializer")
    
    # Verificar que el ViewSet esté registrado
    from apps.public.impuestos.api.viewsets import VIEWSETS
    contribuyente_registered = any(
        'contribuyentes-tipos' in prefix for prefix, _, _ in VIEWSETS
    )
    
    if contribuyente_registered:
        print("[OK] ContribuyenteTipoViewSet esta registrado en VIEWSETS")
    else:
        print("[ERROR] ContribuyenteTipoViewSet NO esta registrado en VIEWSETS")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    print("\n[INICIANDO AUDITORIA DE SEGMENTOS DIAN]\n")
    
    try:
        audit_contribuyente_tipo_model()
        audit_provider_metadata()
        audit_api_exposure()
        
        print("\n[AUDITORIA COMPLETADA]\n")
    except Exception as e:
        print(f"\n[ERROR EN AUDITORIA]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
