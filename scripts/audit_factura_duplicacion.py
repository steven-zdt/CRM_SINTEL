#!/usr/bin/env python
"""
Auditoría de Factura: Detectar Triplicaciones en Upload

Este script valida que no haya triplicaciones de objetos Factura
cuando se sube un archivo XML único.

Ejecución:
  python manage.py shell
  exec(open('scripts/audit_factura_duplicacion.py').read())
"""

from django.db import connection
from django.utils import timezone
from apps.tenant.facturas.models import Factura, FacturaAnexos
from decimal import Decimal
import json


def audit_factura_duplicacion():
    """Auditoría completa de duplicación de facturas."""
    
    print("\n" + "="*80)
    print("🔍 AUDITORÍA: DUPLICACIÓN DE FACTURAS EN UPLOAD")
    print("="*80)
    
    # 1. Conectarse al esquema actual
    schema = getattr(connection, 'schema_name', 'public')
    print(f"\n📍 Schema actual: {schema}")
    
    # 2. Obtener todas las facturas agrupadas por CUFE
    facturas_por_cufe = {}
    for factura in Factura.objects.all().only('id', 'numero', 'cufe', 'created_at'):
        cufe = factura.cufe or f"(sin-cufe-{factura.id})"
        if cufe not in facturas_por_cufe:
            facturas_por_cufe[cufe] = []
        facturas_por_cufe[cufe].append({
            'id': factura.id,
            'numero': factura.numero,
            'created_at': factura.created_at.isoformat() if factura.created_at else None
        })
    
    # 3. Detectar duplicados
    duplicados = {k: v for k, v in facturas_por_cufe.items() if len(v) > 1}
    
    print(f"\n[CHART] Estadísticas:")
    print(f"   - Total de Facturas: {len(facturas_por_cufe)}")
    print(f"   - Duplicadas (por CUFE): {len(duplicados)}")
    
    if duplicados:
        print(f"\n[WARNING]  DUPLICADOS DETECTADOS:")
        for cufe, facturas in duplicados.items():
            print(f"\n   CUFE: {cufe}")
            for idx, fac in enumerate(facturas, 1):
                print(f"      [{idx}] ID: {fac['id']}, Número: {fac['numero']}, Creado: {fac['created_at']}")
    else:
        print(f"\n[OK] No hay duplicados por CUFE")
    
    # 4. Verificar integridad de FacturaAnexos (debe tener 1 anexo por factura)
    print(f"\n📎 Verificación de FacturaAnexos:")
    facturas_sin_anexo = []
    for factura in Factura.objects.all().only('id', 'numero'):
        try:
            anexo = FacturaAnexos.objects.get(factura=factura)
        except FacturaAnexos.DoesNotExist:
            facturas_sin_anexo.append(factura)
        except FacturaAnexos.MultipleObjectsReturned:
            print(f"   [WARNING]  PROBLEMA: Factura {factura.numero} (ID: {factura.id}) tiene múltiples anexos")
    
    if facturas_sin_anexo:
        print(f"   [WARNING]  Facturas sin anexo: {len(facturas_sin_anexo)}")
        for fac in facturas_sin_anexo[:5]:
            print(f"      - Factura {fac.numero} (ID: {fac.id})")
    else:
        print(f"   [OK] Todas las facturas tienen exactamente 1 anexo")
    
    # 5. Análisis de patrones de creación
    print(f"\n⏱️  Análisis de Creación (últimas 10):")
    ultimas_10 = Factura.objects.all().order_by('-created_at')[:10].only(
        'id', 'numero', 'cufe', 'created_at', 'estado'
    )
    for idx, fac in enumerate(ultimas_10, 1):
        cufe_short = (fac.cufe or "SIN-CUFE")[:20]
        print(f"   [{idx}] #{fac.numero} | CUFE: {cufe_short}... | Estado: {fac.estado} | {fac.created_at}")
    
    # 6. Reporte final
    print(f"\n" + "="*80)
    if duplicados:
        print("[ERROR] RESULTADO: DUPLICACIÓN DETECTADA")
        print("\nOrigen probable:")
        print("   1. Flujo de dos pasos (parseo + persistencia) en JavaScript")
        print("   2. Múltiples listeners disparando el mismo upload")
        print("   3. Form submission duplicada con HTMX")
        print("\nSolución recomendada:")
        print("   1. Usar un ÚNICO endpoint: /api/v1/facturas/upload-ubl/")
        print("   2. Eliminar flujo de preview previo")
        print("   3. Consolidar listeners en un solo punto de entrada")
    else:
        print("[OK] RESULTADO: SIN DUPLICACIÓN")
        print("   La arquitectura está funcionando correctamente.")
    
    print("="*80 + "\n")
    
    return {
        'schema': schema,
        'total_facturas': len(facturas_por_cufe),
        'duplicados': len(duplicados),
        'duplicados_detalle': duplicados,
        'facturas_sin_anexo': len(facturas_sin_anexo),
    }


def limpiar_duplicados():
    """Función auxiliar para limpiar duplicados (CUIDADO: usa con precaución)."""
    print("\n[WARNING]  FUNCIÓN PELIGROSA - SOLO PARA DESARROLLO")
    print("Este script eliminará los duplicados manteniendo el primero por fecha.")
    confirm = input("¿Continuar? (s/n): ").lower()
    
    if confirm != 's':
        print("Operación cancelada.")
        return
    
    # Obtener duplicados
    facturas_por_cufe = {}
    for factura in Factura.objects.all().order_by('created_at'):
        cufe = factura.cufe or f"(sin-cufe-{factura.id})"
        if cufe not in facturas_por_cufe:
            facturas_por_cufe[cufe] = []
        facturas_por_cufe[cufe].append(factura)
    
    # Eliminar duplicados (mantener el primero)
    deletadas = 0
    for cufe, facturas in facturas_por_cufe.items():
        if len(facturas) > 1:
            print(f"\n   CUFE: {cufe}")
            for idx, fac in enumerate(facturas[1:], 2):  # Saltar el primero
                print(f"      Eliminando: ID {fac.id}, Número {fac.numero}")
                fac.delete()
                deletadas += 1
    
    print(f"\n[OK] Total de facturas eliminadas: {deletadas}")


if __name__ == "__main__":
    result = audit_factura_duplicacion()
    
    # Opcional: limpiar duplicados si es necesario
    # limpiar_duplicados()
