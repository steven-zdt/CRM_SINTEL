import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from apps.tenant.empleados.services.business_service import NominaCalculationService
from apps.tenant.empleados.models import Contrato
from apps.public.tenants.models import Client as Tenant

def run_smoke_test():
    print("--- INICIANDO PRUEBA DE HUMO (CÁLCULO NÓMINA) ---")
    
    # 1. Configurar Tenant (Necesario para multi-tenant)
    # Buscamos el primer tenant que no sea 'public'
    tenant = Tenant.objects.exclude(schema_name='public').first()
    if not tenant:
        print("CRITICAL: No se encontró ningún tenant configurado (excluyendo 'public').")
        print("Esquemas disponibles:", list(Tenant.objects.values_list('schema_name', flat=True)))
        return
        
    print(f"Usando Tenant: {tenant.schema_name} ({tenant.domain_url})")
    connection.set_tenant(tenant)
    
    # 2. Buscar Contrato
    contrato = Contrato.objects.filter(estado='ACTIVO', activo=True).first()
    if not contrato:
        print(f"No hay contratos activos en el tenant '{tenant.schema_name}' para probar.")
        return
        
    print(f"Probando cálculo para contrato ID: {contrato.id} - Empleado: {contrato.empleado} - Salario Mensual: {contrato.salario_mensual}")
    empresa_id = contrato.empresa_id
    
    # Prueba 1: 30 días
    print("\n[Prueba 1] 30 días laborados:")
    calc_30 = NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=Decimal('30'),
        empresa_id=empresa_id
    )
    for k, v in calc_30.items():
        print(f"  {k}: {v}")
        
    # Prueba 2: 15 días (Debe ser la mitad proporcional)
    print("\n[Prueba 2] 15 días laborados:")
    calc_15 = NominaCalculationService.calcular_liquidacion(
        contrato=contrato,
        dias_laborados=Decimal('15'),
        empresa_id=empresa_id
    )
    for k, v in calc_15.items():
        print(f"  {k}: {v}")

    # Verificar que el salario base de 15 días es la mitad de 30 días
    base_30 = Decimal(calc_30['salario_base'])
    base_15 = Decimal(calc_15['salario_base'])
    
    print(f"\nVerificación Proporcionalidad:")
    print(f"  Base 30d: {base_30}")
    print(f"  Base 15d: {base_15}")
    
    if abs(base_15 - (base_30 / Decimal('2'))) < Decimal('1'): # Tolerancia de 1 unidad
        print("\nSUCCESS: El cálculo proporcional es correcto según normativa colombiana.")
    else:
        print("\nFAILURE: La proporción no coincide.")

if __name__ == '__main__':
    try:
        run_smoke_test()
    except Exception as e:
        print(f"\nERROR DURANTE EL TEST: {str(e)}")
        import traceback
        traceback.print_exc()
